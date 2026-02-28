#!/usr/bin/env python3
"""Multi-agent verification orchestrator.

Launches OpenCode and Codex CLI agents in separate worktrees,
monitors their progress, enforces timeouts, and collects results.

Claude agent is NOT managed here — it runs via Task tool with
isolation: "worktree" directly from the main agent.

Usage:
    python multi_agent_verify.py \
        --repo-root /path/to/repo \
        --timestamp 20260228-020854 \
        --prompt-file /path/to/prompt.md \
        [--timeout 600]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

IS_WINDOWS = sys.platform == "win32"

# Subprocess defaults for Windows encoding compatibility
_SUBPROCESS_TEXT_KWARGS: dict[str, Any] = {"text": True}
if IS_WINDOWS:
    _SUBPROCESS_TEXT_KWARGS["encoding"] = "utf-8"
    _SUBPROCESS_TEXT_KWARGS["errors"] = "replace"


@dataclass
class AgentConfig:
    name: str
    cli_cmd: list[str]
    worktree_dir: str = ""


@dataclass
class AgentResult:
    name: str
    status: str = "pending"  # pending | running | completed | failed | timeout
    exit_code: int | None = None
    duration_seconds: float = 0.0
    files_changed: int = 0
    committed: bool = False
    commit_hash: str = ""
    error: str = ""


AGENTS = [
    AgentConfig(name="opencode", cli_cmd=["opencode", "run"]),
    AgentConfig(name="codex", cli_cmd=["codex", "exec", "--full-auto"]),
]


def which(cmd: str) -> str | None:
    """Return the full path to *cmd* (resolves .cmd/.bat on Windows)."""
    return shutil.which(cmd)


def create_worktree(repo_root: str, name: str, ts: str) -> str | None:
    """Create a detached worktree. Returns path or None on failure."""
    wt_path = os.path.join(repo_root, ".claude", "worktrees", f"verify-{name}-{ts}")
    try:
        subprocess.run(
            ["git", "worktree", "add", wt_path, "HEAD", "--detach"],
            cwd=repo_root, capture_output=True, check=True, **_SUBPROCESS_TEXT_KWARGS,
        )
        return wt_path
    except subprocess.CalledProcessError as e:
        print(f"[orchestrator] Failed to create worktree for {name}: {e.stderr}", file=sys.stderr)
        return None


def remove_worktree(repo_root: str, wt_path: str) -> None:
    """Force-remove a worktree."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", wt_path, "--force"],
            cwd=repo_root, capture_output=True, **_SUBPROCESS_TEXT_KWARGS,
        )
    except Exception:
        pass


def collect_git_result(wt_path: str) -> dict[str, Any]:
    """Collect commit and diff info from a worktree."""
    info: dict[str, Any] = {"files_changed": 0, "committed": False, "commit_hash": ""}

    # Check for uncommitted changes
    diff_stat = subprocess.run(
        ["git", "diff", "HEAD", "--stat"], cwd=wt_path,
        capture_output=True, **_SUBPROCESS_TEXT_KWARGS,
    )
    uncommitted = bool(diff_stat.stdout.strip())

    # Check for new commits (compare with detached HEAD parent)
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1", "--format=%H"], cwd=wt_path,
        capture_output=True, **_SUBPROCESS_TEXT_KWARGS,
    )
    current_hash = log_result.stdout.strip()

    # Count changed files (committed or uncommitted)
    if uncommitted:
        stat_cmd = ["git", "diff", "HEAD", "--name-only"]
    else:
        stat_cmd = ["git", "diff", "HEAD~1", "--name-only"]

    stat_result = subprocess.run(stat_cmd, cwd=wt_path, capture_output=True, **_SUBPROCESS_TEXT_KWARGS)
    changed_files = [f for f in stat_result.stdout.strip().split("\n") if f]
    info["files_changed"] = len(changed_files)

    # Check if agent committed
    parent_check = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=wt_path,
        capture_output=True, **_SUBPROCESS_TEXT_KWARGS,
    )
    original_head_file = os.path.join(wt_path, ".git")
    # If there's a new commit beyond the detached HEAD
    diff_check = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"], cwd=wt_path,
        capture_output=True, **_SUBPROCESS_TEXT_KWARGS,
    )
    if diff_check.returncode == 0 and diff_check.stdout.strip():
        info["committed"] = True
        info["commit_hash"] = current_hash

    return info


def launch_agent(agent: AgentConfig, prompt: str, wt_path: str) -> subprocess.Popen | None:
    """Launch a CLI agent as a subprocess in its worktree."""
    cmd_name = agent.cli_cmd[0]
    resolved = which(cmd_name)
    if not resolved:
        print(f"[orchestrator] {cmd_name} not found in PATH, skipping {agent.name}", file=sys.stderr)
        return None

    env = os.environ.copy()
    # Prevent Claude Code nesting detection for child processes
    env.pop("CLAUDECODE", None)

    # Use the fully-resolved path so Windows can execute .cmd/.bat wrappers
    cmd = [resolved] + agent.cli_cmd[1:] + [prompt]
    print(f"[orchestrator] Launching {agent.name}: {' '.join(agent.cli_cmd[:3])}... in {wt_path}")
    try:
        proc = subprocess.Popen(
            cmd, cwd=wt_path, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            **_SUBPROCESS_TEXT_KWARGS,
        )
        return proc
    except Exception as e:
        print(f"[orchestrator] Failed to launch {agent.name}: {e}", file=sys.stderr)
        return None


def run_agents(
    repo_root: str,
    timestamp: str,
    prompt: str,
    timeout: int = 600,
) -> dict[str, Any]:
    """Main orchestration: create worktrees, launch agents, wait, collect results."""
    results: dict[str, AgentResult] = {}
    processes: dict[str, tuple[subprocess.Popen, str, float]] = {}  # name -> (proc, wt_path, start_time)
    worktree_paths: list[str] = []

    # Create worktrees and launch agents
    for agent in AGENTS:
        result = AgentResult(name=agent.name)
        wt_path = create_worktree(repo_root, agent.name, timestamp)
        if wt_path is None:
            result.status = "failed"
            result.error = "worktree creation failed"
            results[agent.name] = result
            continue

        worktree_paths.append(wt_path)
        agent.worktree_dir = wt_path

        proc = launch_agent(agent, prompt, wt_path)
        if proc is None:
            result.status = "failed"
            result.error = f"{agent.cli_cmd[0]} not found in PATH"
            results[agent.name] = result
            continue

        result.status = "running"
        results[agent.name] = result
        processes[agent.name] = (proc, wt_path, time.time())

    if not processes:
        print("[orchestrator] No agents launched successfully", file=sys.stderr)
        # Clean up worktrees that were created but whose agents failed to launch
        for wt in worktree_paths:
            remove_worktree(repo_root, wt)
        return {"agents": {k: asdict(v) for k, v in results.items()}, "success": False}

    # Poll until all done or timeout
    print(f"[orchestrator] Waiting for {len(processes)} agents (timeout={timeout}s)...")
    while processes:
        for name in list(processes.keys()):
            proc, wt_path, start_time = processes[name]
            elapsed = time.time() - start_time

            ret = proc.poll()
            if ret is not None:
                # Process finished
                results[name].status = "completed" if ret == 0 else "failed"
                results[name].exit_code = ret
                results[name].duration_seconds = round(elapsed, 1)
                if ret != 0:
                    output = proc.stdout.read() if proc.stdout else ""
                    results[name].error = output[-500:] if len(output) > 500 else output
                # Collect git info
                git_info = collect_git_result(wt_path)
                results[name].files_changed = git_info["files_changed"]
                results[name].committed = git_info["committed"]
                results[name].commit_hash = git_info["commit_hash"]
                del processes[name]
                print(f"[orchestrator] {name} finished: status={results[name].status}, "
                      f"exit={ret}, files={git_info['files_changed']}, "
                      f"duration={results[name].duration_seconds}s")

            elif elapsed > timeout:
                # Timeout — kill
                print(f"[orchestrator] {name} timed out after {timeout}s, killing...")
                try:
                    proc.terminate()
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                results[name].status = "timeout"
                results[name].duration_seconds = round(elapsed, 1)
                results[name].error = f"exceeded {timeout}s timeout"
                # Still collect any partial results
                git_info = collect_git_result(wt_path)
                results[name].files_changed = git_info["files_changed"]
                results[name].committed = git_info["committed"]
                results[name].commit_hash = git_info["commit_hash"]
                del processes[name]

        if processes:
            time.sleep(5)

    # Summary
    completed = sum(1 for r in results.values() if r.status == "completed")
    report = {
        "agents": {k: asdict(v) for k, v in results.items()},
        "completed_count": completed,
        "total_count": len(results),
        "success": completed > 0,
        "worktree_paths": worktree_paths,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-agent verification orchestrator")
    parser.add_argument("--repo-root", required=True, help="Path to the git repository root")
    parser.add_argument("--timestamp", required=True, help="Timestamp for worktree naming (YYYYMMDD-HHMMSS)")
    parser.add_argument("--prompt-file", required=True, help="Path to the verification prompt file")
    parser.add_argument("--timeout", type=int, default=600, help="Per-agent timeout in seconds (default: 600)")
    parser.add_argument("--output", default=None, help="Path to write JSON report (default: stdout)")
    args = parser.parse_args()

    prompt_path = Path(args.prompt_file)
    if not prompt_path.is_file():
        print(f"[orchestrator] Prompt file not found: {args.prompt_file}", file=sys.stderr)
        sys.exit(1)

    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        print("[orchestrator] Prompt file is empty", file=sys.stderr)
        sys.exit(1)

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        print(f"[orchestrator] Not a git repository: {repo_root}", file=sys.stderr)
        sys.exit(1)

    print(f"[orchestrator] Starting multi-agent verification")
    print(f"  repo: {repo_root}")
    print(f"  timestamp: {args.timestamp}")
    print(f"  prompt: {len(prompt)} chars")
    print(f"  timeout: {args.timeout}s per agent")

    report = run_agents(
        repo_root=repo_root,
        timestamp=args.timestamp,
        prompt=prompt,
        timeout=args.timeout,
    )

    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(report_json, encoding="utf-8")
        print(f"[orchestrator] Report written to {args.output}")
    else:
        print(report_json)

    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()




