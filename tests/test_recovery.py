import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/gpu-resume"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


counter = load_module("counter", SKILL / "examples/counter.py")
self_test = load_module("self_test", SKILL / "scripts/self_test.py")


class RecoveryTests(unittest.TestCase):
    def test_hard_kill_and_replacement_produce_complete_result(self):
        result = self_test.self_test()
        self.assertEqual(result["status"], "passed")
        self.assertGreater(result["resumed_from_step"], 0)
        self.assertLessEqual(result["recomputed_steps"], 10)
        self.assertEqual(result["final_total"], 1830)

    def test_failed_checkpoint_commit_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = counter.Store(directory)
            store.write("checkpoint.json", {"step": 10})
            with mock.patch.object(counter.os, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    store.write("checkpoint.json", {"step": 20})
            self.assertEqual(store.read("checkpoint.json"), {"step": 10})

    def test_invalid_or_wrong_workload_state_is_not_silently_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            checkpoint.write_text(json.dumps({"identity": "wrong", "step": 20, "total": 210}))
            with self.assertRaisesRegex(ValueError, "incompatible"):
                counter.run(directory, 60, 10, 0)
            checkpoint.write_text("incomplete upload")
            with self.assertRaises(json.JSONDecodeError):
                counter.run(directory, 60, 10, 0)


if __name__ == "__main__":
    unittest.main()
