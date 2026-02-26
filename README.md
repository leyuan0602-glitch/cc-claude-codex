# CC Claude Codex

Agent skill that lets Claude Code orchestrate Codex for complex project automation, using Markdown files for reliable state tracking.

Claude Code acts as supervisor (planning, test-based acceptance) while Codex handles all code implementation. Claude Code never directly modifies implementation code.

For Chinese documentation, see `README.zh-CN.md`.

## Workflow

![Workflow Diagram](./docs/images/workflow-en.png)

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Codex](https://github.com/openai/codex) CLI (`npm i -g @openai/codex`)
- [OpenCode](https://opencode.ai) CLI (`npm i -g opencode-ai`) — optional, for multi-agent verification
- Python 3.8+

## Quickstart

```bash
python scripts/setup.py
```

`setup.py` automatically:
- Copies skill files to `~/.claude/skills/cc-claude-codex/`
- Merges hook config into `~/.claude/settings.json`

In any project directory, ask Claude Code for a concrete development task, for example:

```text
Implement user login endpoints and add unit tests.
```

Claude Code will create and maintain `.cc-claude-codex/` and invoke Codex to execute and report progress.

## Usage

Describe your development request directly in Claude Code. CC Claude Codex will auto-trigger, for example:

- "Implement user login"
- "Fix the API 500 error"
- "Refactor this module to TypeScript"

Claude Code will run the full flow: analysis -> Codex execution -> test verification -> commit.

### Run Codex Manually

```bash
# Standard mode (Codex can read/write)
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py

# Read-only mode (Codex cannot write)
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --readonly

# Custom timeouts
python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --max-timeout 600 --stale-timeout 180
```

## Project Structure

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

Runtime files created in your project root:

```
.cc-claude-codex/
|-- status.md
|-- codex-progress.md
|-- logs/
`-- snapshots/
```

## Core Mechanism

### Two Key Files

| File | Owner | Purpose |
|------|-------|---------|
| `status.md` | Claude Code only | Requirement spec, global task status, verification results |
| `codex-progress.md` | Shared | Current batch steps and execution progress |

If `codex-progress.md` exists, active work is still in progress.

### Hooks

Claude Code hooks provide automated safeguards:

- **Stop**: Block session end when unfinished tasks exist in `status.md`
- **PreCompact**: Snapshot `status.md` before context compact
- **SessionStart**: Inject `status.md` after compact/startup/resume

### Infrastructure Automation

Phase 3 verification uses `multi-agent-verify` to spawn 3 independent CLI agents (OpenCode, Codex, Claude Code) in separate git worktrees. Each agent independently reviews code, writes tests, runs E2E verification, and fixes bugs. The main agent then synthesizes all findings and applies a final fix on the original branch.

Agents that are not installed are automatically skipped — only `claude` is required.

### Verification Replaces Code Review

After all Codex batches are complete, Claude Code runs multi-agent verification instead of manual test-based acceptance:

- 3 agents work in parallel, each in its own worktree
- Each agent: code review → write tests → run tests → E2E verify → fix bugs → commit
- Main agent collects all diffs, synthesizes fixes, applies final fix on original branch
- All temporary worktrees are cleaned up unconditionally

## Configuration

### `cc-claude-codex.py` options

| Option | Default | Description |
|--------|---------|-------------|
| `--readonly` | false | Run Codex in read-only sandbox |
| `--max-timeout` | 0 | Hard timeout in seconds (0 = no limit) |
| `--stale-timeout` | 120 | Kill when no log activity for N seconds |
| `--sandbox` | unset | Override sandbox mode |

### `multi_agent_verify.py` options

| Option | Default | Description |
|--------|---------|-------------|
| `--worktree-base` | required | Parent directory for worktrees |
| `--timestamp` | required | Timestamp suffix for worktree names |
| `--prompt-file` | required | Path to the filled prompt file |
| `--check-interval` | 900 | Status check interval in seconds |

### Manual Hook Configuration

If you do not use `setup.py`, configure hooks manually using `references/hooks-config.md`.

## License

MIT
