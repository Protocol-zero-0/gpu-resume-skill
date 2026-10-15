<p align="center">
  <img src="docs/banner.svg" alt="GPU Resume — interruptible compute, durable progress" width="880">
</p>

<p align="center">
  <a href="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml"><img src="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml/badge.svg" alt="Checks"></a>
  <img src="https://img.shields.io/badge/SkyPilot-0.14.0-38bdf8" alt="SkyPilot 0.14.0">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-cbd5e1" alt="Apache 2.0"></a>
</p>

<p align="center"><strong>A small agent skill for GPU jobs that can stop, wait, and resume.</strong><br>
Powered by SkyPilot. Keep the scheduler upstream; keep workload-specific recovery here.</p>

## How it works

| Resource recovery | Progress recovery | One shared entry point |
| --- | --- | --- |
| SkyPilot finds resources and restarts managed jobs after interruptions. | Your workload restores a checkpoint or skips completed shards. | Agents on different machines connect to the same remote API server. |

This repository contains a thin skill, two task templates, an installer, and a
checkpoint example. The installer also links the official SkyPilot skill at a
locked commit. It does not create cloud resources or start a local controller.

## Install

Requires Git, Python 3.12+, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/Protocol-zero-0/gpu-resume-skill.git ~/work/gpu-resume-skill
cd ~/work/gpu-resume-skill
python3 scripts/install.py
gpu-resume self-test
gpu-resume doctor
```

The installer pins the SkyPilot client and links both skills into
`~/.agents/skills` and `~/.claude/skills`. Keep the checkout at its installed
location. Add `~/.local/bin` to `PATH` if needed. The skills are discoverable on
the next turn or in a new agent session. Existing conflicting files are preserved.

**No GPU yet?** The local self-test works now. `doctor` reports `setup_required`
(exit code 2) until a reachable remote API server is connected.

## Use it

Tell your agent:

> Use gpu-resume to prepare this workload for interruptible GPUs. Reuse its
> framework's checkpoint support, connect to our shared service, and show how
> much work can be lost on an interruption.

Or use the CLI after a shared SkyPilot service is available:

```bash
gpu-resume connect https://YOUR_API_SERVER
gpu-resume doctor
gpu-resume submit path/to/task.yaml
gpu-resume queue
gpu-resume logs JOB_ID --tail 100 --no-follow
```

Start from the [spot](skills/gpu-resume/templates/spot-demo.yaml) or
[SSH pool](skills/gpu-resume/templates/ssh-demo.yaml) example. Replace the
example GPU, storage prefix, and pool name before submitting. The demos run a
counter to exercise persistence, not GPU math. Real training should use its
framework's save/load APIs, including optimizer, RNG, and data position.

**Checkpoints must live outside the temporary GPU machine.** The example supports
a durable local directory or an existing S3 bucket with a unique job prefix.
The remote workload needs storage access; creating a bucket is not part of setup.
One writer owns each example prefix. Use separate prefixes for independent jobs.

## What is verified

`gpu-resume self-test` kills a real CPU worker at step 27, restores the durable
checkpoint at step 20, and completes with the expected result. It also retries
after completion to check that the final result remains the same.

This validates local checkpoint logic. It does **not** validate GPU replacement,
remote controller recovery, S3 connectivity, or training-state completeness.
Run a recovery canary on the actual infrastructure before relying on it.

## Updates

```bash
gpu-resume check-updates
```

A weekly GitHub workflow checks upstream releases and publishes a run summary.
It does not modify the installation. Review a release, update the [lock](skills/gpu-resume/upstream.lock.json),
validate CLI/server compatibility and recovery, then switch. Keep the previous
lock and deployment state for rollback; avoid pulling upstream master into a live runtime.

## 中文入口

安装后直接说：**“用 gpu-resume 把这个任务接到可中断 GPU 上，保存进度并支持续跑。”**
GPU 可以稍后接入；先运行 `gpu-resume self-test` 验证入口。skill 负责流程，
SkyPilot 负责资源恢复，任务代码负责进度恢复。

---

Built on [SkyPilot](https://github.com/skypilot-org/skypilot) and its
[official agent skill](https://github.com/skypilot-org/skypilot/tree/v0.14.0/agent/skills/skypilot).
See the [upstream managed-job documentation](https://docs.skypilot.ai/en/v0.14.0/examples/managed-jobs.html)
and [server deployment guide](https://docs.skypilot.ai/en/stable/reference/api-server/api-server.html).
