# Hook Configuration Guide

CC Claude Codex v2 uses Claude Code hooks for automated safeguards. Add the configuration below to `~/.claude/settings.json`.

## Full Configuration

> Note: `$SKILL_DIR` below is a placeholder, not a real environment variable. Replace it with the actual path when configuring manually. Recommended: run `python scripts/setup.py` in the skill root to generate correct paths automatically.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$SKILL_DIR/scripts/stop_check.py\"",
            "timeout": 10000
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$SKILL_DIR/scripts/pre_compact.py\"",
            "timeout": 5000
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$SKILL_DIR/scripts/session_inject.py\"",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

## Actual Installation Path

`setup.py` generates platform-correct paths automatically. For manual setup, replace `$SKILL_DIR` with:

- Windows: `%USERPROFILE%\.claude\skills\cc-claude-codex`
- macOS/Linux: `~/.claude/skills/cc-claude-codex`

### Windows Example

```json
"command": "python \"C:\\Users\\USERNAME\\.claude\\skills\\cc-claude-codex\\scripts\\stop_check.py\""
```

### macOS/Linux Example

```json
"command": "python3 \"/Users/USERNAME/.claude/skills/cc-claude-codex/scripts/stop_check.py\""
```

## Hook Behavior

### Stop Hook (`stop_check.py`)
- Trigger: when Claude attempts to end the session
- Behavior: checks for unfinished `- [ ]` tasks in `.cc-claude-codex/status.md`
- If unfinished tasks exist: exits with code 2 and stderr output -> blocks end
- If all tasks are complete: exits with code 0 -> allows end

### PreCompact Hook (`pre_compact.py`)
- Trigger: before context compact
- Behavior: copies `.cc-claude-codex/status.md` to `.cc-claude-codex/snapshots/YYYYMMDD-HHMMSS.md`
- Purpose: preserve state across compact

### SessionStart Hook (`session_inject.py`)
- Trigger: matches `compact|startup|resume`
- Behavior: reads `.cc-claude-codex/status.md` and injects it via `additionalContext`
- Purpose: restore project-state awareness immediately after compact/startup/resume
