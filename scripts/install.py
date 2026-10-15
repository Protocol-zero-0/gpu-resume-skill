#!/usr/bin/env python3
"""Install the pinned upstream skill and local extension without starting services."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "gpu-resume"


def run(*args):
    subprocess.run(args, check=True)


def upstream_snapshot(lock):
    cache = ROOT / ".upstream"
    cache.mkdir(exist_ok=True)
    checkout = cache / lock["commit"]
    if not checkout.exists():
        with tempfile.TemporaryDirectory(dir=cache, prefix="install-") as temporary:
            staged = Path(temporary) / "repo"
            run("git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                "--branch", lock["tag"], lock["repository"], str(staged))
            run("git", "-C", str(staged), "sparse-checkout", "set", lock["skill_path"])
            actual = subprocess.check_output(
                ["git", "-C", str(staged), "rev-parse", "HEAD"], text=True).strip()
            if actual != lock["commit"]:
                raise RuntimeError("Upstream tag does not match the locked commit.")
            staged.rename(checkout)
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if actual != lock["commit"]:
        raise RuntimeError("Cached upstream checkout differs from the lock.")
    if subprocess.check_output(
            ["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip():
        raise RuntimeError("Cached upstream files have local changes; preserve them first.")
    source = checkout / lock["skill_path"]
    if not (source / "SKILL.md").is_file():
        raise RuntimeError("The locked upstream skill was not found.")
    return source


def install_links(home, upstream):
    links = []
    for directory in (home / ".agents/skills", home / ".claude/skills"):
        links.extend([(directory / "gpu-resume", SKILL),
                      (directory / "skypilot", upstream)])
    links.append((home / ".local/bin/gpu-resume", SKILL / "scripts/gpu_resume.py"))
    # Validate all destinations before changing any existing installation.
    for destination, source in links:
        if destination.exists() or destination.is_symlink():
            if not destination.is_symlink() or destination.resolve() != source.resolve():
                raise RuntimeError(f"Refusing to overwrite existing path: {destination}")
    for destination, source in links:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_symlink():
            destination.symlink_to(source, target_is_directory=source.is_dir())
        print(f"Linked {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-client", action="store_true",
                        help="Link skills only; leave the SkyPilot client unchanged")
    args = parser.parse_args()
    lock = json.loads((SKILL / "upstream.lock.json").read_text())
    if not args.skip_client:
        uv = shutil.which("uv")
        if not uv:
            parser.error("Install uv first: https://docs.astral.sh/uv/getting-started/installation/")
        run(uv, "tool", "install", "--python", "3.12", lock["client_requirement"])
    upstream = upstream_snapshot(lock)
    install_links(Path.home(), upstream)
    print("Installed. Skills are discoverable on the next turn/new session.")
    print("Next: gpu-resume doctor (no endpoint is required for the local self-test).")
    if str(Path.home() / ".local/bin") not in os.environ.get("PATH", "").split(os.pathsep):
        print("Add ~/.local/bin to PATH to use the gpu-resume command.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
