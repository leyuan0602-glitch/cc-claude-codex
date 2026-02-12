#!/usr/bin/env python3
"""Stop hook: Block if .cc-claude-codex/status.md has incomplete tasks.

Reads hook input from stdin (JSON). Exits 2 + stderr message to block,
exits 0 to allow.
"""

import json
import re
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

    # Allow stop if explicitly aborted
    if "🛑" in content:
        sys.exit(0)

    unchecked = re.findall(r"^- \[ \] (.+)$", content, re.MULTILINE)

    if unchecked:
        msg = "CC Claude Codex: The following tasks are incomplete, cannot end session:\n"
        for task in unchecked:
            msg += f"  - {task}\n"
        msg += "Complete all tasks first, or mark them as done manually."
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
