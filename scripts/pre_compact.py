#!/usr/bin/env python3
"""PreCompact hook: Snapshot .cc-claude-codex/status.md before context compact.

Reads hook input from stdin (JSON) for cwd. Copies status.md to
.cc-claude-codex/snapshots/YYYYMMDD-HHMMSS.md.
"""

import json
import shutil
import sys
from datetime import datetime
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

    snapshots_dir = cwd / ".cc-claude-codex" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = snapshots_dir / f"{ts}.md"
    shutil.copy2(status_file, dest)

    print(f"Status snapshot saved: {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()

