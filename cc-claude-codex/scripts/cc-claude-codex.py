#!/usr/bin/env python3
"""CC Claude Codex: Cross-platform Codex exec wrapper.

Claude Code writes task info to .cc-claude-codex/codex-progress.md,
then this script tells Codex to read that file and work from it.
Codex updates the same file as it progresses.

Usage:
    python cc-claude-codex.py [--readonly] [--max-timeout N] [--stale-timeout N] [--sandbox MODE]
"""

import argparse
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

CODEX_PROMPT = """Read .cc-claude-codex/codex-progress.md. This is your task file.

Working rules:
1. Read .cc-claude-codex/codex-progress.md first to understand goals and current progress.
2. Start from the first unfinished step.
3. After each finished step, immediately update .cc-claude-codex/codex-progress.md:
   - Mark that step as [x]
   - Append what you changed and which files were modified in the "Execution Log" section
4. Only modify files required by the task.
5. If blocked and unable to continue, record the reason in the "Blockers" section and stop.
6. After all steps are done, set the top status to ✅ Completed."""


def configure_stdio():
    """Avoid UnicodeEncodeError on non-UTF-8 consoles (e.g., Windows GBK)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(errors="replace")
            except Exception:
                pass


def main():
    configure_stdio()

    parser = argparse.ArgumentParser(description="CC Claude Codex exec wrapper")
    parser.add_argument("--readonly", action="store_true", help="Read-only sandbox")
    parser.add_argument("--max-timeout", type=int, default=0, help="Hard kill timeout in seconds (0=no limit)")
    parser.add_argument("--stale-timeout", type=int, default=120, help="Seconds without log activity before killing Codex (default: 120)")
    parser.add_argument("--sandbox", default=None, help="Sandbox mode override")
    args = parser.parse_args()

    # Resolve full path — required on Windows where .cmd shims aren't found by Popen
    codex_bin = shutil.which("codex")
    if not codex_bin:
        print("Error: 'codex' not found in PATH. Install: npm i -g @openai/codex", file=sys.stderr)
        sys.exit(1)

    state_dir = Path(".cc-claude-codex")
    progress_file = state_dir / "codex-progress.md"
    if not progress_file.exists():
        print("Error: .cc-claude-codex/codex-progress.md not found. Claude Code should create it first.", file=sys.stderr)
        sys.exit(1)

    # On Windows, --full-auto and --sandbox workspace-write silently fall back to
    # read-only, so we must use danger-full-access. On Linux/Mac workspace-write
    # works correctly and is the safer default.
    if args.sandbox:
        sandbox = args.sandbox
    elif args.readonly:
        sandbox = "read-only"
    elif IS_WINDOWS:
        sandbox = "danger-full-access"
    else:
        sandbox = "workspace-write"

    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"codex-{ts}.log"
    out_file = log_dir / f"codex-{ts}-output.md"

    cmd = [
        codex_bin,
        "exec",
        "--sandbox",
        sandbox,
        "-o",
        str(out_file),
        CODEX_PROMPT,
    ]

    proc = None
    lf = None
    try:
        lf = open(log_file, "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True)

        start = time.time()
        last_activity = time.time()
        poll_interval = 30
        stale_timeout = args.stale_timeout
        max_timeout = args.max_timeout
        exit_reason = None
        last_log_size = 0

        # Poll loop: check log file size growth for health
        while True:
            try:
                proc.wait(timeout=poll_interval)
                break  # Process exited
            except subprocess.TimeoutExpired:
                now = time.time()

                # Hard kill if max-timeout exceeded
                if max_timeout > 0 and int(now - start) >= max_timeout:
                    proc.kill()
                    proc.wait()
                    exit_reason = f"hard_timeout ({max_timeout}s)"
                    break

                # Stale check: compare actual file size on disk
                current_size = log_file.stat().st_size
                if current_size > last_log_size:
                    last_log_size = current_size
                    last_activity = time.time()
                elif int(now - last_activity) >= stale_timeout:
                    proc.kill()
                    proc.wait()
                    exit_reason = f"stale ({stale_timeout}s no log activity)"
                    break

        lf.close()

        # Build result for Claude Code: 3 pieces of info
        result_parts = []

        # 1. Exit reason
        if exit_reason:
            result_parts.append(f"exit_reason: {exit_reason}")
        elif proc.returncode != 0:
            result_parts.append(f"exit_reason: error (code={proc.returncode})")
        else:
            result_parts.append("exit_reason: done")

        # 2. Progress file
        if progress_file.exists():
            result_parts.append(f"\n--- codex-progress.md ---\n{progress_file.read_text(encoding='utf-8-sig')}\n---")

        # 3. Codex final output
        if out_file.exists():
            result_parts.append(f"\n--- codex output ---\n{out_file.read_text(encoding='utf-8-sig')}\n---")

        print("\n".join(result_parts))

        # Exit code: 0 for done, 1 for error, 124 for timeout/stale
        if exit_reason:
            sys.exit(124)
        elif proc.returncode != 0:
            sys.exit(1)

    except KeyboardInterrupt:
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait()
        if lf and not lf.closed:
            lf.close()
        result_parts = ["exit_reason: interrupted"]
        if progress_file.exists():
            result_parts.append(f"\n--- codex-progress.md ---\n{progress_file.read_text(encoding='utf-8-sig')}\n---")
        if out_file.exists():
            result_parts.append(f"\n--- codex output ---\n{out_file.read_text(encoding='utf-8-sig')}\n---")
        print("\n".join(result_parts))
        sys.exit(130)


if __name__ == "__main__":
    main()
