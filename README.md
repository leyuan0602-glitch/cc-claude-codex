# CC Claude Codex

Agent skill that lets Claude Code orchestrate Codex for complex project automation, using Markdown files for reliable state tracking.

It combines Claude Code's stronger taste and communication for planning/review with Codex's precise execution for implementation.

For Chinese documentation, see `README.zh-CN.md`.

## Workflow

![Workflow Diagram](./docs/images/workflow-en.png)

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [Codex](https://github.com/openai/codex) CLI (`npm i -g @openai/codex`)
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

Claude Code will run the full flow: analysis -> Codex execution -> review -> commit.

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

### Review Is Mandatory

After every Codex run, Claude Code must validate with `git diff`:

- Functional completeness against acceptance criteria
- File scope discipline
- Code quality and safety
- Test execution (if tests exist)

If validation fails, update guidance and retry until pass or retry limit.

## Configuration

### `cc-claude-codex.py` options

| Option | Default | Description |
|--------|---------|-------------|
| `--readonly` | false | Run Codex in read-only sandbox |
| `--max-timeout` | 0 | Hard timeout in seconds (0 = no limit) |
| `--stale-timeout` | 120 | Kill when no log activity for N seconds |
| `--sandbox` | unset | Override sandbox mode |

### Manual Hook Configuration

If you do not use `setup.py`, configure hooks manually using `references/hooks-config.md`.

## License

MIT
