# 恢复契约与验证范围

GPU Resume 提供 Agent 工作流、CLI 与示例。Agent 按任务适配代码；现有脚本并非通用自动改造引擎。

## 恢复契约

- 训练任务恢复 model、optimizer、scheduler、RNG 与数据位置；优先复用框架自带 checkpoint。
- 分片任务记录已提交结果，重复执行时保持输出幂等。每个逻辑任务使用独立存储前缀，重试沿用该前缀。
- 状态必须持久保存到 GPU 主机之外。只把完整提交的 checkpoint 计为可恢复进度。
- 保存频率与上传耗时共同决定重算范围；接入后通过实际中断测试验证。

## 验证矩阵

| 范围 | 当前证据 |
| --- | --- |
| 本地 CPU 示例强制终止与恢复 | 已验证恢复进度、最终结果与重算范围 |
| checkpoint 损坏、任务不匹配、提交失败 | 本地单元测试覆盖 |
| CLI 远程连接检查与提交路由 | 本地单元测试覆盖 |
| SkyPilot YAML | 固定版本客户端解析通过 |
| GPU 更换、远程控制器恢复、S3 持久化 | 尚待实际环境集成验证 |
| 用户自己的训练或推理程序 | 每个任务单独验证；self-test 不覆盖用户代码 |

示例是计数器，不执行模型训练。首次接入需终止实际 worker，在替代节点恢复，检查最终结果与丢失进度是否符合要求。安装不申请 GPU、不创建存储或控制器。

## English

GPU Resume provides an agent workflow, CLI, and examples. Agents adapt individual workloads; the scripts are not a universal code transformation engine.

### Recovery contract

- Training restores model, optimizer, scheduler, RNG, and data position. Reuse framework-native checkpoints.
- Sharded jobs track committed results and use idempotent output commits. Use a unique prefix per logical job, shared across retries.
- Keep durable state outside the GPU host. Only complete checkpoint commits count as recoverable progress.
- Save frequency and upload time determine recomputation. Measure this through interruption tests.

### Verification matrix

| Scope | Current evidence |
| --- | --- |
| Forced termination and recovery of the local CPU example | Restored progress, final result, and recomputation verified |
| Corrupt state, workload mismatch, failed commits | Covered by local unit tests |
| CLI remote connection checks and submission routing | Covered by local unit tests |
| SkyPilot YAML | Parsed with the pinned client |
| GPU replacement, remote controller recovery, S3 persistence | Integration testing pending |
| User training or inference code | Validate per workload; self-test does not exercise user code |

The example is a counter, not model training. Before relying on a deployment, terminate a real worker, recover on a replacement, and check results and lost progress against the workload requirements. Installation provisions no GPUs, storage, or controllers.
