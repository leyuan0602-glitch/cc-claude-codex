---
name: multi-agent-verify
description: "Multi-agent parallel verification. Spawns 3 independent CLI agents (OpenCode, Codex, Claude Code) in separate git worktrees to review, test, and fix code. Synthesizes results and applies final fixes on the original branch."
---

# Multi-Agent Verify: Parallel Verification with 3 Independent Agents

You are the Main Agent (Claude Code). After all development is complete, you orchestrate 3 independent CLI agents to verify the work in parallel. Each agent works in its own git worktree, reviews code, writes tests, runs E2E verification, and fixes bugs independently. You then synthesize their findings and apply a final fix.

## Prerequisites

Before invoking:
1. All code changes are committed on the current branch
2. Requirements are available (from `status.md` or conversation context)
3. `opencode`, `codex`, and `claude` are all in PATH
4. `multi_agent_verify.py` is available at the skill scripts path

## Phase V1: Preparation

### Mode A: cc-claude-codex Integration

When called as cc-claude-codex Phase 3:
1. Read `.cc-claude-codex/status.md` — extract ALL requirements and scenarios
2. Run `git diff main...HEAD --name-status` to get the full list of changed files
3. Build the verification prompt using `references/verify-agent-prompt.md` template:
   - Replace `{REQUIREMENTS}` with the requirements text from status.md
   - Replace `{CHANGED_FILES}` with the changed files list
4. Write the filled prompt to `.cc-claude-codex/verify-prompt-{ts}.md`

### Mode B: Standalone

When invoked directly:
1. Get requirements from conversation context, or ask the user
2. Run `git diff main...HEAD --name-status` (or user-specified diff range) for changed files
3. Build the verification prompt using `references/verify-agent-prompt.md` template
4. Write the filled prompt to a temporary file (e.g., `/tmp/verify-prompt-{ts}.md`)

## Phase V2: Create Worktrees and Launch Agents

1. Generate a timestamp: `YYYYMMDD-HHMMSS`
2. Create 3 worktrees from current HEAD:
   ```bash
   git worktree add .claude/worktrees/verify-opencode-{ts} HEAD --detach
   git worktree add .claude/worktrees/verify-codex-{ts} HEAD --detach
   git worktree add .claude/worktrees/verify-claude-{ts} HEAD --detach
   ```
3. Launch the orchestrator script with `run_in_background: true`:
   ```bash
   python ~/.claude/skills/cc-claude-codex/scripts/multi_agent_verify.py \
     --worktree-base .claude/worktrees \
     --timestamp {ts} \
     --prompt-file {prompt_file_path}
   ```
4. **Monitoring loop**: Poll with `TaskOutput(block: true, timeout: 900000)` (15 min).
   - On timeout: read `verify-status.json` (in the working directory or `.cc-claude-codex/`) to check each agent's status
   - If all agents are still running normally → continue waiting (call TaskOutput again)
   - If an agent appears stuck or errored → decide whether to wait or intervene
   - When the script exits → all agents are done, proceed to Phase V3

## Phase V3: Collect and Synthesize Results

When the orchestrator returns its JSON report:

1. For each agent that completed successfully:
   - Read the agent's diff: `git -C {worktree_path} diff HEAD~1`
   - Read the agent's commit log: `git -C {worktree_path} log --oneline -5`
   - Read `_verify_issues.md` or `_verify_result.txt` if present in the worktree
2. Review all three agents' changes and findings
3. Determine which fixes are valuable and which issues are real

## Phase V4: Apply Final Fix

1. On the original branch (not a new branch), apply fixes based on your synthesis
2. Use your own judgment on how to fix — you may delegate to Codex, cherry-pick, or fix directly
3. Commit: `git add -A && git commit -m "multi-agent-verify: apply fixes from verification"`
4. If no fixes are needed (all agents found no issues), skip this phase

## Phase V5: Cleanup (Unconditional)

Always runs, regardless of success or failure:

```bash
# Remove worktrees
git worktree remove .claude/worktrees/verify-opencode-{ts} --force 2>/dev/null
git worktree remove .claude/worktrees/verify-codex-{ts} --force 2>/dev/null
git worktree remove .claude/worktrees/verify-claude-{ts} --force 2>/dev/null

# Prune stale references
git worktree prune

# Delete temporary prompt file
rm -f {prompt_file_path}

# Delete status file (if exists)
rm -f .cc-claude-codex/verify-status.json 2>/dev/null

# Clean up any leftover verification files in main worktree
find . -name "_verify_*" -delete 2>/dev/null
```

## Error Handling

- If a worktree fails to create → skip that agent, proceed with remaining
- If an agent crashes (non-zero exit, no output) → mark as failed in report
- Minimum 1 agent must complete successfully for synthesis to proceed
- If 0 agents complete → report FAIL, escalate to user
- Cleanup is always executed, even on total failure
