# CC Claude Codex

这是一个 Agent skill：让 Claude Code 编排 Codex 完成复杂项目自动化，并通过 Markdown 文件进行可靠的状态跟踪。

Claude Code 作为监督者（规划、基于测试的验收），Codex 负责所有代码实现。Claude Code 禁止直接修改实现代码。

英文文档请见 `README.md`。

## 工作流程

![工作流图](./docs/images/workflow-zh.png)

## 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Codex](https://github.com/openai/codex) CLI（`npm i -g @openai/codex`）
- [OpenCode](https://opencode.ai) CLI（`npm i -g opencode-ai`）— 可选，用于多 Agent 验证
- Python 3.8+

## 快速开始

```bash
python scripts/setup.py
```

`setup.py` 会自动：
- 将 skill 文件复制到 `~/.claude/skills/cc-claude-codex/`
- 将 hooks 配置合并到 `~/.claude/settings.json`


在任意项目目录中，直接向 Claude Code 提出具体开发需求，例如：

```text
实现用户登录接口，并补充对应单元测试。
```

Claude Code 会自动创建并维护 `.cc-claude-codex/`，再调用 Codex 执行并回写进度。

## 使用

在 Claude Code 中直接描述你的开发需求即可。CC Claude Codex 会自动触发，例如：

- “实现用户登录功能”
- “修复 API 返回 500 的 bug”
- “把这个模块重构成 TypeScript”

Claude Code 会自动执行完整流程：需求分析 -> Codex 执行 -> 测试验收 -> 提交。

### 手动调用 Codex

```bash
# 标准模式（Codex 可读写）
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py

# 只读模式（Codex 不可写）
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --readonly

# 自定义超时
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --max-timeout 600 --stale-timeout 180
```

## 项目结构

```
.
|-- README.md
|-- README.zh-CN.md
|-- SKILL.md
|-- scripts/
|   |-- cc-claude-codex.py
|   |-- multi_agent_verify.py
|   |-- setup.py
|   |-- stop_check.py
|   |-- pre_compact.py
|   `-- session_inject.py
|-- references/
|   |-- hooks-config.md
|   |-- status-template.md
|   |-- progress-template.md
|   `-- verify-agent-prompt.md
|-- multi-agent-verify/
|   `-- SKILL.md
|-- code-acceptance/
|   `-- SKILL.md
`-- docs/
    `-- images/
        |-- workflow-en.png
        `-- workflow-zh.png
```

运行时会在项目根目录生成：

```
.cc-claude-codex/
|-- status.md
|-- codex-progress.md
|-- logs/
`-- snapshots/
```

## 核心机制

### 两个关键文件

| 文件 | 维护者 | 用途 |
|------|--------|------|
| `status.md` | Claude Code 独占维护 | 需求规格、全局任务状态、验证结果 |
| `codex-progress.md` | 双方读写 | 当前批次步骤与执行进度 |

`codex-progress.md` 存在表示仍有活跃任务未完成。

### Hooks

通过 Claude Code hooks 实现自动保护：

- **Stop**：`status.md` 中存在未完成任务时阻止结束
- **PreCompact**：compact 前自动快照 `status.md`
- **SessionStart**：compact/startup/resume 后自动注入 `status.md`

### 基础设施自动化

Phase 3 验证使用 `multi-agent-verify`，启动3个独立 CLI agent（OpenCode、Codex、Claude Code）在各自的 git worktree 中并行工作。每个 agent 独立审查代码、编写测试、运行 E2E 验证并修复 bug。主 Agent 综合所有发现，在原分支上应用最终修复。

未安装的 agent 会自动跳过——只有 `claude` 是必需的。

### 验证取代代码审查

所有 Codex 批次完成后，Claude Code 运行多 Agent 验证，而非手动测试验收：

- 3个 agent 并行工作，各自在独立 worktree 中
- 每个 agent：代码审查 → 写测试 → 跑测试 → E2E 验证 → 修 bug → commit
- 主 Agent 收集所有 diff，综合修复，在原分支应用最终修复
- 所有临时 worktree 无条件清理

## 配置

### `cc-claude-codex.py` 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--readonly` | false | 只读沙箱模式 |
| `--max-timeout` | 0 | 硬超时（秒，0 表示无限） |
| `--stale-timeout` | 120 | 无日志活动超时秒数 |
| `--sandbox` | 未设置 | 覆盖沙箱模式 |

### `multi_agent_verify.py` 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--worktree-base` | 必填 | worktree 父目录 |
| `--timestamp` | 必填 | worktree 名称的时间戳后缀 |
| `--prompt-file` | 必填 | 填充后的 prompt 文件路径 |
| `--check-interval` | 900 | 状态检查间隔（秒） |

### 手动配置 Hooks

若不使用 `setup.py`，请参考 `references/hooks-config.md` 手动配置。

## License

MIT
