# CC Claude Codex

CC Claude Codex 是一个双 Agent 开发编排工作流：Claude Code 作为 Supervisor，Codex 作为 Executor。

Claude Code 负责需求分析、任务拆解和代码 Review；Codex 负责实现。两者通过 `.cc-claude-codex/` 目录中的 Markdown 文件协作，形成 **规划 -> 执行 -> 审查 -> 修正** 的自动化闭环。

英文文档请见 `README.md`。

## 工作流程

![工作流图](./docs/images/workflow-zh.png)

## 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Codex](https://github.com/openai/codex) CLI（`npm i -g @openai/codex`）
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

Claude Code 会自动执行完整流程：需求分析 -> Codex 执行 -> Review -> 提交。

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
|   |-- setup.py
|   |-- stop_check.py
|   |-- pre_compact.py
|   `-- session_inject.py
|-- references/
|   |-- hooks-config.md
|   |-- status-template.md
|   `-- progress-template.md
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

### Review 不可跳过

每轮 Codex 执行后，Claude Code 都必须用 `git diff` 做验证：

- 功能是否满足验收标准
- 文件改动范围是否准确
- 代码质量与安全性
- 如有测试，必须执行并通过

如果不通过，需要更新修复指引并重试，直到通过或达到重试上限。

## 配置

### `cc-claude-codex.py` 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--readonly` | false | 只读沙箱模式 |
| `--max-timeout` | 0 | 硬超时（秒，0 表示无限） |
| `--stale-timeout` | 120 | 无日志活动超时秒数 |
| `--sandbox` | 未设置 | 覆盖沙箱模式 |

### 手动配置 Hooks

若不使用 `setup.py`，请参考 `references/hooks-config.md` 手动配置。

## License

MIT
