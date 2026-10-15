#!/usr/bin/env python3
"""A remote-only entry point for SkyPilot managed jobs."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


SKILL = Path(__file__).resolve().parents[1]


def lock():
    return json.loads((SKILL / "upstream.lock.json").read_text())


def sky_env():
    return {**os.environ, "SKYPILOT_DISABLE_LOCAL_API_SERVER": "1",
            "SKYPILOT_DISABLE_USAGE_COLLECTION": "1"}


def redact(text):
    return re.sub(r"(https?://)[^/\s]+@", r"\1[redacted]@", text)


def sky_command(args, capture=False):
    executable = shutil.which("sky")
    if not executable:
        raise RuntimeError(f"SkyPilot is missing. Install {lock()['client_requirement']}")
    return subprocess.run([executable, *args], env=sky_env(), text=True,
                          capture_output=capture, timeout=30 if capture else None)


def doctor():
    version = sky_command(["--version"], capture=True)
    expected = lock()["tag"].removeprefix("v")
    actual = (version.stdout + version.stderr).strip()
    if version.returncode or not re.search(rf"(?<![\d.]){re.escape(expected)}(?![\d.])", actual):
        print(json.dumps({"status": "version_mismatch", "expected": expected,
                          "detail": redact(actual)}, indent=2))
        return 1
    info = sky_command(["api", "info", "-o", "json"], capture=True)
    # SkyPilot 0.14 can return exit 0 with plain text when disconnected.
    try:
        server = json.loads(info.stdout).get("server", {})
        endpoint = urllib.parse.urlsplit(server.get("url", ""))
        host = endpoint.hostname or ""
        local = host == "localhost" or host.endswith(".localhost")
        try:
            local = local or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        reachable = (info.returncode == 0 and server.get("status") == "healthy"
                     and endpoint.scheme in ("http", "https") and bool(host) and not local)
    except (ValueError, AttributeError, TypeError):
        server, reachable = {}, False
    status = "setup_required"
    result = 2
    if reachable:
        status = "ready" if server.get("version") == expected else "server_version_mismatch"
        result = 0 if status == "ready" else 1
    print(json.dumps({"client": expected, "status": status,
                      "local_server_autostart": False,
                      "server_version": server.get("version"),
                      "next": "Use managed jobs." if result == 0 else
                      "Connect a reachable remote API server running the pinned version."}, indent=2))
    return result


def check_updates():
    current = lock()
    request = urllib.request.Request(
        "https://api.github.com/repos/skypilot-org/skypilot/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "gpu-resume-skill"})
    with urllib.request.urlopen(request, timeout=20) as response:
        latest = json.load(response)
    print(json.dumps({"installed_tag": current["tag"],
                      "latest_release": latest["tag_name"],
                      "update_available": current["tag"] != latest["tag_name"],
                      "release_url": latest["html_url"],
                      "action": "Review and test before changing the lock; no update was applied."},
                     indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("check-updates")
    commands.add_parser("self-test")
    connect = commands.add_parser("connect")
    connect.add_argument("endpoint")
    for name in ("submit", "queue", "logs"):
        command = commands.add_parser(name)
        command.add_argument("arguments", nargs=argparse.REMAINDER)
    forwarded = sys.argv[2:] if sys.argv[1:2] and sys.argv[1] in ("submit", "queue", "logs") else None
    args = parser.parse_args(sys.argv[1:2] if forwarded is not None else None)
    if args.command == "doctor":
        return doctor()
    if args.command == "check-updates":
        return check_updates()
    if args.command == "self-test":
        return subprocess.call([sys.executable, str(SKILL / "scripts/self_test.py")])
    if args.command == "connect":
        endpoint = urllib.parse.urlsplit(args.endpoint)
        if endpoint.scheme not in ("https", "http") or not endpoint.hostname:
            parser.error("Provide the remote API server's http(s) endpoint.")
        if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            parser.error("Keep credentials out of the URL; use SkyPilot's login flow.")
        return sky_command(["api", "login", "-e", args.endpoint]).returncode
    arguments = forwarded
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if args.command == "submit":
        if not arguments or not Path(arguments[0]).is_file():
            parser.error("submit requires a task YAML file followed by optional SkyPilot flags.")
        status = doctor()
        if status:
            return status
        return sky_command(["jobs", "launch", *arguments]).returncode
    return sky_command(["jobs", "queue" if args.command == "queue" else "logs",
                        *arguments]).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(redact(str(exc))) from exc
