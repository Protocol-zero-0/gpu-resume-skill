#!/usr/bin/env python3
"""A deterministic checkpoint example. Supports local durable files or S3."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit


class Store:
    def __init__(self, uri):
        parsed = urlsplit(uri)
        self.s3 = None
        if parsed.scheme == "s3":
            if not parsed.netloc or not parsed.path.strip("/"):
                raise ValueError("Use a bucket and a unique job prefix: s3://bucket/job-key")
            import boto3
            self.s3 = boto3.client("s3")
            self.bucket = parsed.netloc
            self.prefix = parsed.path.strip("/")
        elif parsed.scheme:
            raise ValueError("This example supports a local directory or s3:// URI.")
        else:
            self.directory = Path(uri)
            self.directory.mkdir(parents=True, exist_ok=True)

    def read(self, name):
        if self.s3:
            try:
                response = self.s3.get_object(Bucket=self.bucket, Key=f"{self.prefix}/{name}")
                return json.loads(response["Body"].read())
            except self.s3.exceptions.ClientError as exc:
                if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    return None
                raise
        path = self.directory / name
        return json.loads(path.read_text()) if path.exists() else None

    def write(self, name, value):
        data = json.dumps(value, sort_keys=True).encode()
        if self.s3:
            # One completed object PUT is the commit; don't emulate POSIX rename on a bucket mount.
            self.s3.put_object(Bucket=self.bucket, Key=f"{self.prefix}/{name}",
                               Body=data, ContentType="application/json")
            return
        descriptor, temporary = tempfile.mkstemp(dir=self.directory, prefix=".pending-")
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.directory / name)
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def run(uri, steps, save_every, delay):
    if steps < 1 or save_every < 1 or delay < 0:
        raise ValueError("steps/save-every must be positive; delay must be nonnegative")
    store = Store(uri)
    identity = hashlib.sha256(f"counter-v1:{steps}".encode()).hexdigest()
    state = store.read("checkpoint.json")
    if state is None:
        state = {"identity": identity, "step": 0, "total": 0}
    step = state["step"]
    if (state["identity"] != identity or not 0 <= step <= steps
            or state["total"] != step * (step + 1) // 2):
        raise ValueError("Checkpoint is incompatible or invalid; refusing to silently restart.")
    print(json.dumps({"event": "resume", "step": step}), flush=True)
    resumed_from = step
    for step in range(step + 1, steps + 1):
        time.sleep(delay)
        state["step"] = step
        state["total"] += step
        print(json.dumps({"event": "progress", "step": step}), flush=True)
        if step % save_every == 0 or step == steps:
            store.write("checkpoint.json", state)
            print(json.dumps({"event": "checkpoint", "step": step}), flush=True)
    result = {"steps": steps, "total": state["total"]}
    store.write("result.json", result)
    print(json.dumps({"event": "completed", "resumed_from": resumed_from, **result}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-uri", required=True)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.1)
    options = parser.parse_args()
    run(options.state_uri, options.steps, options.save_every, options.delay)
