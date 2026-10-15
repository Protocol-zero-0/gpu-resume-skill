---
name: gpu-resume
description: Prepare, submit, and recover checkpointed GPU training or batch jobs on intermittent or spot resources using SkyPilot. Use for interruptible GPU workloads, resuming work on a replacement GPU, or connecting a new machine to the shared GPU service.
---

# Resumable GPU jobs

Use SkyPilot for resource management and recovery. This skill adds the task's
checkpoint contract and a remote-only entry point. It is not a scheduler.

## Start here

Run `python3 <this-skill>/scripts/gpu_resume.py doctor`. It checks the pinned
client and remote API connection without starting a local API server.

- If the client is missing, use the repository's `scripts/install.py` or install
  the exact `client_requirement` in `upstream.lock.json` using `uv tool install`.
- If no remote service is configured, obtain the shared endpoint and run
  `gpu-resume connect https://YOUR_API_SERVER`. Do not start a local controller
  as a substitute. A missing endpoint is setup work, not a failed GPU task.
- Read the installed `skypilot` skill for SkyPilot CLI/YAML details. If it is not
  installed, read its files at the exact commit in `upstream.lock.json`.

The user's project owns its task YAML, source, inputs, and outputs. Keep server
credentials, machine inventory, and actual storage locations outside this repo.

## Prepare a recoverable task

Establish these facts from the workload before submitting:

1. **Unit of work.** Independent input shards, experiment configurations/seeds,
   or a training loop. Split only where dependencies and result merging permit.
2. **Restore state.** Training usually needs model, optimizer, scheduler, RNG,
   and data position. Batch jobs need completed shard IDs and committed outputs.
   Reuse the framework's own checkpoint implementation and resume option.
3. **Durability.** Checkpoints must reach storage independent of the GPU host.
   Use an existing bucket or shared persistent filesystem. An ephemeral local
   disk or a save performed only at shutdown does not meet this contract.
4. **Loss budget.** Agree on allowable recomputation; choose the save interval
   from that budget and measured save/upload time. Count only fully committed
   checkpoints as durable progress. Use a unique prefix per logical job, shared
   by all its retry attempts; don't generate a fresh prefix on every restart.

If the program cannot restore state, report that it currently supports restart
only. Add the smallest workload adapter before promising bounded progress loss.
Code versions, compatible GPU requirements, and inputs must be reproducible.
Retries may execute a unit more than once; output commits must be idempotent.

## Submit and observe

Use `gpu-resume submit task.yaml` (delegates to `sky jobs launch`) for unattended
jobs. The helper requires a configured remote service and never starts a local
one. A working API connection does not authorize paid resources: honor the
task's authorized pools, GPU types, and spending bounds. Keep application errors
distinct from infrastructure interruptions; avoid unlimited retries for bad code.

Use `gpu-resume queue` and `gpu-resume logs JOB_ID --tail 100 --no-follow` for
status and recent output. Use SkyPilot's supported log streaming when waiting;
do not leave an agent polling indefinitely or resubmitting uncertain launches.
The remote managed-job controller continues recovery after the agent exits.

`templates/spot-demo.yaml` and `templates/ssh-demo.yaml` are examples, not an
approved resource selection. Replace the marked storage/pool fields and GPU
type before launching. The counter example exercises persistence and restart;
replace it with the actual framework's training or shard command for real work.

## Verify before relying on it

`gpu-resume self-test` kills and restarts a local CPU worker using durable local
files. This proves the example's checkpoint logic only. For the first actual
GPU task, interrupt a worker, recover on a replacement, and check the final
result and recomputation against the agreed loss budget. Checkpoint upload and
GPU/controller recovery remain unverified until that integration test passes.

## Updates

`gpu-resume check-updates` is read-only. A weekly GitHub workflow also checks
upstream. Keep the CLI and official skill pinned together; do not pull master
into the installed runtime. For an upgrade, stage a release and its exact commit,
update the lock, run local checks and a remote recovery canary, then switch during
an appropriate window. Follow SkyPilot's client/server compatibility guidance.
Retain the previous lock and deployment state for rollback.
