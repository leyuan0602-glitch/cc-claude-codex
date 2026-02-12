#!/usr/bin/env python3
"""SessionStart hook: Re-inject .cc-claude-codex/status.md after compact/startup.

Reads hook input from stdin (JSON) for cwd. Outputs JSON with
additionalContext containing the current status.md content.
"""

import json
import sys
from pathlib import Path


def get_cwd(hook_input: dict) -> Path:
    """Return cwd from hook input, falling back to current directory."""
    cwd = hook_input.get("cwd")
    if isinstance(cwd, (str, bytes)):
        return Path(cwd)
    return Path(".")


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = get_cwd(hook_input)
    status_file = cwd / ".cc-claude-codex" / "status.md"

    if not status_file.exists():
        sys.exit(0)

    # Use utf-8-sig to tolerate BOM-prefixed UTF-8 files on Windows.
    content = status_file.read_text(encoding="utf-8-sig")

    output = {
        "additionalContext": (
            "## CC Claude Codex Project Status (Auto-injected)\n"
            "Below is the current content of .cc-claude-codex/status.md. Continue from this state:\n\n"
            f"{content}"
        )
    }

    # Keep stdout ASCII-safe so GBK consoles do not crash on print().
    print(json.dumps(output))


if __name__ == "__main__":
    main()
