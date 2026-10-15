<p align="center">
  <img src="docs/banner.svg" alt="GPU Resume: use cheaper GPUs for long experiments and resume after interruptions" width="880">
</p>

<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

<p align="center">
  <a href="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml"><img src="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml/badge.svg" alt="Checks"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-cbd5e1" alt="Apache 2.0 license"></a>
</p>

<p align="center"><strong>Run long experiments on cheaper, interruptible GPUs. Keep the work you have finished.</strong><br>
Let your coding agent prepare long jobs for spot or temporary GPUs, with a path back from the last saved checkpoint.</p>

## Who this is for

You are an individual researcher or a developer on a small ML team, already using
Claude Code, Codex, or another coding agent to write and run experiments. A fine-tune,
model evaluation, or batch inference job takes hours. You can wait for a GPU and
repeat a little recent work, but you don't want to rebuild recovery scripts for
every project or watch for failures all night.

GPU Resume gives your agent a reusable workflow: check whether the job can resume,
plan checkpoints or input shards, prepare the job configuration, and connect it to
SkyPilot's resource recovery. **It fits offline jobs that can wait and retry.**

## What it saves you

| What happens today | The workflow after setup |
| --- | --- |
| A spot or temporary GPU is reclaimed halfway through a long run. | SkyPilot reschedules the job on connected resources; the workload reloads its durable progress. |
| An evaluation or inference batch stops, leaving you unsure which inputs finished. | Have the agent organize independent shards and record completion so retries skip committed results. |
| Every new project needs the same explanation of saving, restoring, and submitting work. | Install the skill once in your agent and reuse the workflow when adapting each workload. |
| You change development machines or close the agent session. | Submitted jobs remain with the remote service; reconnect from another machine to inspect and manage them. |

A lower GPU rate helps only if interruptions don't keep wasting the computation
you already paid for. This skill connects cheaper resource choices with preserving
completed work. Actual savings depend on prices, checkpoint overhead, and recomputation.

**The workload must support recovery.** Reuse its training checkpoints, or record
completed shards when inputs can be processed independently. If the program only
starts from zero, the agent must first add a recovery path. Store checkpoints and
results outside the temporary GPU machine; installing a skill cannot make an
arbitrary program resumable by itself.

## Start with your first workload

After installation, give your agent the code and a request such as:

> Use gpu-resume to prepare this model evaluation for temporary GPUs. If a GPU
> is reclaimed, waiting for the next one is fine. Keep completed inputs and allow
> a few minutes of recomputation. Check how to split and save the work, then
> verify that it can resume.

The agent examines your code to establish a recovery method and acceptable loss
of recent work before launching a long job. **Actual submission also needs a
reachable remote SkyPilot service, connected GPU resources, and independent
persistent storage.** Your team can share these. See SkyPilot's
[server deployment guide](https://docs.skypilot.ai/en/stable/reference/api-server/api-server.html).

## Install

Requires Git, Python 3.12+, and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/Protocol-zero-0/gpu-resume-skill.git ~/work/gpu-resume-skill
cd ~/work/gpu-resume-skill
python3 scripts/install.py
gpu-resume self-test
```

The installer pins the SkyPilot client and installs both this skill and the official
SkyPilot skill into `~/.agents/skills` and `~/.claude/skills`. They are discoverable
on the next turn or in a new session. Keep the checkout in its installed location
and ensure `~/.local/bin` is on `PATH`.
Installation does not provision GPUs, create storage, or start a local controller.

Once a remote service is available:

```bash
gpu-resume connect https://YOUR_API_SERVER
gpu-resume doctor
gpu-resume submit path/to/task.yaml
gpu-resume queue
gpu-resume logs JOB_ID --tail 100 --no-follow
```

Without a remote service, `doctor` reports `setup_required` with exit code 2.
The local `self-test` still works.

## Test recovery before a long run

The [spot example](skills/gpu-resume/templates/spot-demo.yaml) and
[SSH pool example](skills/gpu-resume/templates/ssh-demo.yaml) can exercise submission
and recovery after you replace their GPU, pool, and storage settings. Their counter
workload tests persistence; it does not train a model.

Local CPU process termination and checkpoint recovery have been verified, including
correct final output. Actual GPU replacement, remote controller recovery, and S3
access still need integration testing. Interrupt and recover your own workload
before relying on it for long experiments. For training, also verify optimizer,
RNG, and data-position restoration.

## Why Python

The skill itself is Markdown. Python supports the installer, CLI helpers, and
recovery example. The current implementation calls the
[official SkyPilot Python client](https://github.com/skypilot-org/skypilot/blob/v0.14.0/setup.py),
and the intended users' training and evaluation environments typically already
include Python. The helpers therefore avoid adding another runtime.

TypeScript could implement the same functionality through the CLI or remote API.
Keeping the current CLI integration in TypeScript would still require SkyPilot's
Python client, plus Node.js. A standalone `npx` distribution or web interface could
justify a TypeScript client that talks directly to the remote API. For the present
workflow, Python keeps installation and maintenance smaller.

## Updates and maintenance

```bash
gpu-resume check-updates
```

This project reuses [SkyPilot](https://github.com/skypilot-org/skypilot) and its
[official skill](https://github.com/skypilot-org/skypilot/tree/v0.14.0/agent/skills/skypilot).
Upstream manages resources and the lifecycle of managed jobs. This repository
maintains the workload-recovery workflow and small supporting scripts.

A weekly GitHub workflow checks upstream releases without upgrading the runtime.
Update the [lock](skills/gpu-resume/upstream.lock.json), verify client/server
compatibility and recovery, then switch. Retain the previous version and deployment
state for rollback.
