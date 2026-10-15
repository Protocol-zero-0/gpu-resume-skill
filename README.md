<p align="center">
  <img src="docs/banner.zh.svg" alt="GPU Resume：用便宜的 GPU 跑长实验，中断后接着跑" width="880">
</p>

<p align="center"><strong>简体中文</strong> · <a href="README.en.md">English</a></p>

<p align="center">
  <a href="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml"><img src="https://github.com/Protocol-zero-0/gpu-resume-skill/actions/workflows/checks.yml/badge.svg" alt="自动检查"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-cbd5e1" alt="Apache 2.0 许可证"></a>
</p>

<p align="center"><strong>用便宜、可中断的 GPU 跑长实验，保住已经完成的工作。</strong><br>
让 coding agent 帮你把长任务准备成可恢复的实验，使用 Spot 或临时 GPU，中断后从已保存的进度继续。</p>

## 为谁准备

面向已经用 Claude Code、Codex 等 coding agent 跑实验的个人研究者和小型 ML 团队。
微调、评测或批量推理要跑几个小时；你能等待 GPU、接受少量重算，但不想反复写恢复脚本，
或整夜盯着任务重启。

让 agent 检查任务如何续跑、安排 checkpoint 或分片、生成配置，并接入 SkyPilot 的恢复能力。
**适合能够等待、重试的离线任务。**

## 你能省下什么

| 你遇到的事 | 接入后的流程 |
| --- | --- |
| Spot 或临时 GPU 被回收，长任务半途停止 | SkyPilot 在已接入的资源中重新安排任务，任务读取持久保存的进度继续执行。 |
| 评测或批量推理中断，分不清哪些输入已经做完 | 让 agent 按独立分片组织任务并记录完成状态，恢复时跳过已经提交结果的分片。 |
| 每个新项目都要重新解释保存、恢复、提交的细节 | 在 agent 中安装一次 skill，让它按同一流程适配各项目的任务。 |
| 换了开发机器，或结束了 agent 会话 | 已提交的任务由远程服务托管；新机器连接同一服务后继续查看和操作。 |

省掉重复计算和手工恢复，让你更容易选择价格更低、但随时可能被收回的资源。

**续跑需要任务代码配合：** 复用训练 checkpoint，或记录已完成分片；没有恢复能力就先补齐。
进度必须保存在临时 GPU 之外。仅安装 skill 不会让任意程序自动获得续跑能力。

## 从你的第一个任务开始

安装后，把任务代码交给 agent，例如：

> 用 gpu-resume 准备这个模型评测任务。我想用临时 GPU，资源回收后可以等下一张。
> 已完成的数据不要重跑，允许重算最近几分钟。先检查怎样拆分和保存进度，再验证能否恢复。

**提交前需准备远程 SkyPilot 服务、已接入的 GPU 和独立持久存储，团队可共享这些配置。**
服务部署见 [SkyPilot 官方文档](https://docs.skypilot.ai/en/stable/reference/api-server/api-server.html)。

## 安装

需要 Git、Python 3.12+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

```bash
git clone https://github.com/Protocol-zero-0/gpu-resume-skill.git ~/work/gpu-resume-skill
cd ~/work/gpu-resume-skill
python3 scripts/install.py
gpu-resume self-test
```

安装固定版本的 SkyPilot 客户端和两个 skill，供下一轮对话或新会话使用。
请保留仓库目录，并将 `~/.local/bin` 加入 `PATH`。安装不会申请 GPU 或创建远程服务。

有远程服务后，连接并提交任务：

```bash
gpu-resume connect https://YOUR_API_SERVER
gpu-resume doctor
gpu-resume submit path/to/task.yaml
gpu-resume queue
gpu-resume logs JOB_ID --tail 100 --no-follow
```

尚未配置远程服务时，`doctor` 会显示 `setup_required`，退出码为 2；本地 `self-test` 仍然可用。

## 先验证恢复，再跑长任务

提供 [Spot](skills/gpu-resume/templates/spot-demo.yaml)和
[SSH 资源池](skills/gpu-resume/templates/ssh-demo.yaml)模板；替换 GPU、资源池与存储位置后使用。
计数器示例验证进度保存，不执行模型训练。

本地 CPU 强制中断后续跑已验证；真实 GPU 更换、远程服务恢复与 S3 访问尚待实机验证。
首次接入请验证中断恢复，训练任务还需恢复 optimizer、随机数状态和数据位置。

## 为什么保留 Python

skill 主体是 Markdown。辅助脚本调用 [SkyPilot 官方 Python 客户端](https://github.com/skypilot-org/skypilot/blob/v0.14.0/setup.py)，
沿用 Python 可减少目标使用者的安装负担。

TypeScript 可以实现同样功能，但当前 CLI 方案下仍需 Python 客户端，并新增 Node.js。
纯 `npx` 分发或 Web 界面可考虑 TypeScript 直接调用远程 API；当前保留 Python，减少运行时依赖。

## 更新与维护

```bash
gpu-resume check-updates
```

复用 [SkyPilot](https://github.com/skypilot-org/skypilot) 和
[官方 skill](https://github.com/skypilot-org/skypilot/tree/v0.14.0/agent/skills/skypilot) 管理资源；本项目维护任务恢复流程。

每周检查上游版本，不自动升级。更新[版本记录](skills/gpu-resume/upstream.lock.json)前验证兼容性与恢复能力，保留旧版本以便回退。
