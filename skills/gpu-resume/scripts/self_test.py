#!/usr/bin/env python3
"""Kill a real worker and verify that its replacement resumes correctly, without GPUs."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def self_test():
    worker = Path(__file__).resolve().parents[1] / "examples/counter.py"
    with tempfile.TemporaryDirectory(prefix="gpu-resume-test-") as directory:
        command = [sys.executable, str(worker), "--state-uri", directory,
                   "--steps", "60", "--save-every", "10", "--delay", "0.01"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        last_step = 0
        try:
            for line in process.stdout:
                event = json.loads(line)
                if event["event"] == "progress":
                    last_step = event["step"]
                if last_step == 27:
                    process.kill()
                    break
            _, error = process.communicate(timeout=10)
            if process.returncode == 0 or last_step != 27:
                raise RuntimeError(f"Worker was not interrupted as expected: {error}")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        state = json.loads((Path(directory) / "checkpoint.json").read_text())
        saved = state["step"]
        if not 0 < saved < last_step or last_step - saved > 10:
            raise RuntimeError("Durable progress did not meet the loss bound.")
        resumed = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
        first = json.loads(resumed.stdout.splitlines()[0])
        if first != {"event": "resume", "step": saved}:
            raise RuntimeError("Replacement worker did not load the saved state.")
        result = json.loads((Path(directory) / "result.json").read_text())
        if result != {"steps": 60, "total": 1830}:
            raise RuntimeError("Resumed job produced an incorrect result.")
        # A retry after completion must commit the same result.
        subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
        if json.loads((Path(directory) / "result.json").read_text()) != result:
            raise RuntimeError("A completed retry changed the result.")
        return {"status": "passed", "test": "local CPU process kill and restart",
                "killed_at_step": last_step, "resumed_from_step": saved,
                "recomputed_steps": last_step - saved, "final_total": result["total"],
                "not_tested": ["GPU replacement", "SkyPilot controller recovery", "S3 persistence"]}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
