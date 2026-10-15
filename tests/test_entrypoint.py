import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = load_module("entrypoint", ROOT / "skills/gpu-resume/scripts/gpu_resume.py")
installer = load_module("installer", ROOT / "scripts/install.py")


class EntrypointTests(unittest.TestCase):
    def test_missing_endpoint_is_not_ready_even_with_zero_exit_code(self):
        replies = [subprocess.CompletedProcess([], 0, "sky, version 0.14.0", ""),
                   subprocess.CompletedProcess([], 0, json.dumps({"status": "not_connected"}), "")]
        with mock.patch.object(cli, "sky_command", side_effect=replies), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.doctor(), 2)

    def test_plain_text_disconnect_and_local_server_are_not_ready(self):
        for response in ("No SkyPilot API server is connected", json.dumps({"server": {
                "url": "http://127.0.0.1:46580", "version": "0.14.0", "status": "healthy"}})):
            replies = [subprocess.CompletedProcess([], 0, "sky, version 0.14.0", ""),
                       subprocess.CompletedProcess([], 0, response, "")]
            with mock.patch.object(cli, "sky_command", side_effect=replies), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.doctor(), 2)

    def test_healthy_compatible_remote_is_ready(self):
        replies = [subprocess.CompletedProcess([], 0, "sky, version 0.14.0", ""),
                   subprocess.CompletedProcess([], 0, json.dumps({"server": {
                       "url": "https://gpu.example.org", "version": "0.14.0", "status": "healthy"}}), "")]
        with mock.patch.object(cli, "sky_command", side_effect=replies), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.doctor(), 0)

    def test_flags_are_forwarded_without_reordering(self):
        with mock.patch.object(sys, "argv", ["gpu-resume", "queue", "-o", "json"]), \
                mock.patch.object(cli, "sky_command", return_value=subprocess.CompletedProcess([], 0)) as command:
            self.assertEqual(cli.main(), 0)
            command.assert_called_once_with(["jobs", "queue", "-o", "json"])

    def test_unhealthy_or_incompatible_server_blocks_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / "task.yaml"
            task.write_text("run: echo example\n")
            with mock.patch.object(sys, "argv", ["gpu-resume", "submit", str(task)]), \
                    mock.patch.object(cli, "doctor", return_value=2), \
                    mock.patch.object(cli, "sky_command") as command:
                self.assertEqual(cli.main(), 2)
                command.assert_not_called()

    def test_submission_uses_managed_jobs_exactly_once(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / "task.yaml"
            task.write_text("run: echo example\n")
            with mock.patch.object(sys, "argv", ["gpu-resume", "submit", str(task), "-d"]), \
                    mock.patch.object(cli, "doctor", return_value=0), \
                    mock.patch.object(cli, "sky_command", return_value=subprocess.CompletedProcess([], 0)) as command:
                self.assertEqual(cli.main(), 0)
                command.assert_called_once_with(["jobs", "launch", str(task), "-d"])

    def test_client_never_autostarts_local_server(self):
        with mock.patch.object(cli.shutil, "which", return_value="/example/sky"), \
                mock.patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as command:
            cli.sky_command(["jobs", "queue"])
            self.assertEqual(command.call_args.kwargs["env"]["SKYPILOT_DISABLE_LOCAL_API_SERVER"], "1")

    def test_link_install_is_idempotent_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            upstream = home / "upstream"
            upstream.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                installer.install_links(home, upstream)
                installer.install_links(home, upstream)
            link = home / ".agents/skills/gpu-resume"
            self.assertEqual(link.resolve(), installer.SKILL)
            link.unlink()
            link.mkdir()
            (link / "keep.txt").write_text("existing installation")
            with self.assertRaisesRegex(RuntimeError, "overwrite"):
                installer.install_links(home, upstream)
            self.assertEqual((link / "keep.txt").read_text(), "existing installation")


if __name__ == "__main__":
    unittest.main()
