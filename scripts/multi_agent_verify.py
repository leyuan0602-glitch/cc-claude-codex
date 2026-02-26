#!/usr/bin/env python3
"""Multi-Agent Verify: Orchestrate 3 CLI agents in parallel worktrees.

Launches OpenCode, Codex, and Claude Code in separate git worktrees,
each performing independent verification. Monitors all agents, writes
periodic status to verify-status.json, and outputs a JSON report when
all agents complete.

Usage:
    python multi_agent_verify.py \
        --worktree-base .claude/worktrees \
        --timestamp 20260226-143000 \
        --prompt-file .cc-claude-codex/verify-prompt-20260226-143000.md
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

AGENTS = {
    "opencode": {
        "bin": "opencode",
        "build_cmd": lambda b, pf, wt: [
            b, "run",
            "--model", "opencode/minimax-m2.5-free",
            "--dir", str(wt),
            "--format", "json",
        ],
        "prompt_via": "stdin",
    },
    "codex": {
        "bin": "codex",
        "build_cmd": lambda b, pf, wt: [
            b, "exec",
            "--sandbox", "danger-full-access" if IS_WINDOWS else "workspace-write",
            "--json",
        ],
        "prompt_via": "arg",
    },
    "claude": {
        "bin": "claude",
        "build_cmd": lambda b, pf, wt: [
            b, "-p",
            "--output-format", "json",
            "--permission-mode", "bypassPermissions",
        ],
        "prompt_via": "arg",
    },
}


def configure_stdio():
    """Avoid UnicodeEncodeError on non-UTF-8 consoles (e.g., Windows GBK)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(errors="replace")
            except Exception:
                pass


def write_status(status_file: Path, agents_status: dict):
    """Write current agent status to JSON file."""
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": agents_status,
    }
    status_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def launch_agent(name: str, config: dict, prompt: str, worktree: Path, log_file: Path):
    """Launch a single agent subprocess. Returns (proc, log_handle) or (None, None)."""
    bin_path = shutil.which(config["bin"])
    if not bin_path:
        print(f"Warning: '{config['bin']}' not found in PATH, skipping {name}", file=sys.stderr)
        return None, None

    cmd = config["build_cmd"](bin_path, prompt, worktree)

    # Append prompt as argument for arg-based agents
    if config["prompt_via"] == "arg":
        cmd.append(prompt)

    lf = open(log_file, "w", encoding="utf-8")
    stdin_pipe = subprocess.PIPE if config["prompt_via"] == "stdin" else None
    # opencode uses --dir flag, so cwd not needed; others use cwd
    if name == "opencode":
        cwd = None
    else:
        cwd = str(worktree)

    # Clean env: remove CLAUDECODE to allow nested Claude Code sessions
    env = dict(__import__("os").environ)
    env.pop("CLAUDECODE", None)

    # Ensure Claude Code can find git-bash on Windows
    if IS_WINDOWS and name == "claude" and not env.get("CLAUDE_CODE_GIT_BASH_PATH"):
        bash_path = shutil.which("bash")
        if bash_path:
            # Prefer the Git/bin/bash.exe over usr/bin/bash.exe
            git_bash = Path(bash_path).resolve()
            # If found under usr/bin, try sibling Git/bin path
            if "usr" in git_bash.parts:
                alt = git_bash.parent.parent.parent / "bin" / "bash.exe"
                if alt.exists():
                    git_bash = alt
            env["CLAUDE_CODE_GIT_BASH_PATH"] = str(git_bash)

    proc = subprocess.Popen(
        cmd, stdout=lf, stderr=subprocess.STDOUT, text=True,
        stdin=stdin_pipe, cwd=cwd, env=env,
    )

    # Feed prompt via stdin if needed
    if config["prompt_via"] == "stdin":
        try:
            proc.stdin.write(prompt)
            proc.stdin.close()
        except Exception:
            pass

    return proc, lf


def check_worktree_changes(worktree: Path, baseline: str) -> bool:
    """Check if a worktree has new commits beyond the baseline."""
    try:
        result = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        current_head = result.stdout.strip()
        return current_head != baseline
    except Exception:
        return False


def main():
    configure_stdio()

    parser = argparse.ArgumentParser(description="Multi-Agent Verify orchestrator")
    parser.add_argument("--worktree-base", required=True, help="Parent directory for worktrees")
    parser.add_argument("--timestamp", required=True, help="Timestamp suffix for worktree names")
    parser.add_argument("--prompt-file", required=True, help="Path to the filled prompt file")
    parser.add_argument("--check-interval", type=int, default=900, help="Status check interval in seconds (default: 900)")
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    prompt = prompt_path.read_text(encoding="utf-8-sig")

    state_dir = Path(".cc-claude-codex")
    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    status_file = state_dir / "verify-status.json"

    ts = args.timestamp
    wt_base = Path(args.worktree_base)

    # Record baseline commit for change detection
    try:
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        baseline = ""

    # Launch all agents
    procs = {}  # name -> {"proc", "log_handle", "log_file", "worktree", "start_time"}
    for name, config in AGENTS.items():
        worktree = wt_base / f"verify-{name}-{ts}"
        if not worktree.exists():
            print(f"Warning: worktree not found: {worktree}, skipping {name}", file=sys.stderr)
            continue
        log_file = log_dir / f"verify-{name}-{ts}.log"
        proc, lf = launch_agent(name, config, prompt, worktree, log_file)
        if proc:
            procs[name] = {
                "proc": proc,
                "log_handle": lf,
                "log_file": log_file,
                "worktree": worktree,
                "start_time": time.time(),
            }
            print(f"Launched {name} (PID {proc.pid}) in {worktree}", file=sys.stderr)

    if not procs:
        print("Error: no agents could be launched", file=sys.stderr)
        sys.exit(1)

    # Monitor loop
    try:
        while True:
            all_done = True
            agents_status = {}

            for name, info in procs.items():
                elapsed = int(time.time() - info["start_time"])
                rc = info["proc"].poll()
                if rc is not None:
                    # Already finished
                    agents_status[name] = {
                        "status": "done",
                        "exit_code": rc,
                        "elapsed_min": round(elapsed / 60, 1),
                        "worktree": str(info["worktree"]),
                    }
                else:
                    all_done = False
                    agents_status[name] = {
                        "status": "running",
                        "pid": info["proc"].pid,
                        "elapsed_min": round(elapsed / 60, 1),
                        "worktree": str(info["worktree"]),
                    }

            write_status(status_file, agents_status)

            if all_done:
                break

            time.sleep(args.check_interval)

    except KeyboardInterrupt:
        # Kill all running agents
        for name, info in procs.items():
            if info["proc"].poll() is None:
                info["proc"].kill()
                info["proc"].wait()
        # Close log handles
        for info in procs.values():
            if info["log_handle"] and not info["log_handle"].closed:
                info["log_handle"].close()
        # Output partial report
        agents_status = {}
        for name, info in procs.items():
            rc = info["proc"].poll()
            elapsed = int(time.time() - info["start_time"])
            agents_status[name] = {
                "status": "done" if rc is not None else "interrupted",
                "exit_code": rc,
                "elapsed_min": round(elapsed / 60, 1),
                "worktree": str(info["worktree"]),
                "has_changes": check_worktree_changes(info["worktree"], baseline),
            }
        report = {"agents": agents_status, "summary": {"interrupted": True}}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(130)

    # Close all log handles
    for info in procs.values():
        if info["log_handle"] and not info["log_handle"].closed:
            info["log_handle"].close()

    # Build final report
    agents_report = {}
    completed = 0
    failed = 0
    for name, info in procs.items():
        rc = info["proc"].returncode
        elapsed = int(time.time() - info["start_time"])
        has_changes = check_worktree_changes(info["worktree"], baseline)

        if rc == 0:
            completed += 1
            status = "done"
        else:
            failed += 1
            status = "error"

        # Read last 50 lines of log for context
        log_tail = ""
        try:
            lines = info["log_file"].read_text(encoding="utf-8", errors="replace").splitlines()
            log_tail = "\n".join(lines[-50:])
        except Exception:
            pass

        agents_report[name] = {
            "status": status,
            "exit_code": rc,
            "elapsed_min": round(elapsed / 60, 1),
            "worktree": str(info["worktree"]),
            "has_changes": has_changes,
            "log_tail": log_tail,
        }

    report = {
        "agents": agents_report,
        "summary": {
            "completed": completed,
            "failed": failed,
            "total": len(procs),
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # Exit 0 if at least one agent completed, 1 if all failed
    sys.exit(0 if completed > 0 else 1)


if __name__ == "__main__":
    main()
