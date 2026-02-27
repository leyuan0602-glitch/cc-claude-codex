---
name: multi-agent-verify
description: "Multi-agent parallel verification. Spawns 3 independent agents (OpenCode CLI, Codex CLI, Claude Task subagent) in separate git worktrees to review, test, and fix code. Synthesizes results and applies final fixes on the original branch."
---

# Multi-Agent Verify: Parallel Verification with 3 Independent Agents

You are the Main Agent (Claude Code). You orchestrate 3 independent agents to verify code in parallel. Each agent works in its own git worktree, reviews code, writes tests, runs verification, and fixes bugs independently. You then synthesize their findings and apply a final fix.

## Agent Launch Methods

Each agent uses a DIFFERENT launch mechanism:

| Agent | Method | Why |
|-------|--------|-----|
| **OpenCode** | `Bash` CLI: `opencode run "..."` | External CLI, no nesting issues |
| **Codex** | `Bash` CLI: `codex exec --full-auto "..."` | External CLI, no nesting issues |
| **Claude** | `Task` tool with `isolation: "worktree"` | MUST use Task tool — `claude` CLI CANNOT run nested inside Claude Code (detects `CLAUDECODE` env var and refuses) |

**CRITICAL**: Never launch `claude` via Bash CLI from within Claude Code. Always use the Task tool with `isolation: "worktree"` and `run_in_background: true`.

## Prerequisites

Before invoking:
1. All code changes are committed on the current branch
2. Requirements are available (from `status.md` or conversation context)
3. `opencode` and `codex` are in PATH (check with `which`)
4. No external orchestrator script is required — launch agents directly

## Phase V1: Preparation

### Mode A: cc-claude-codex Integration

When called as cc-claude-codex Phase 3:
1. Read `.cc-claude-codex/status.md` — extract ALL requirements and scenarios
2. Run `git diff main...HEAD --name-status` to get the full list of changed files
   - If `main` doesn't exist, try `master` or use the appropriate base branch
3. Build the verification prompt (see Prompt Template below)
4. Write the filled prompt to `.cc-claude-codex/verify-prompt-{ts}.md`

### Mode B: Standalone

When invoked directly:
1. Get requirements from conversation context, or ask the user
2. Identify changed files via `git diff {base}...HEAD --name-status`
   - Try `main`, `master`, or ask user for the base branch
3. Build the verification prompt (see Prompt Template below)
4. Write the filled prompt to `.claude/verify-prompt-{ts}.md`

### Prompt Template

Build the prompt inline — no external template file needed. Include:
- What the code does (system description)
- Changed files list
- Review focus areas (security, reliability, architecture, code quality)
- Instructions: read files, find real bugs, fix them, create `_verify_issues.md`, commit

## Phase V2: Launch Agents in Parallel

Generate a timestamp: `date +%Y%m%d-%H%M%S`

There are two ways to launch the CLI agents (OpenCode + Codex). Choose based on preference:

### Option A: Use the orchestrator script (recommended)

The orchestrator script handles worktree creation, process management, timeouts, and result collection for CLI agents automatically. Launch it alongside the Claude Task agent in a single message:

**CLI agents (OpenCode + Codex)** — Bash with `run_in_background: true`:
```bash
python ~/.claude/skills/multi-agent-verify/scripts/multi_agent_verify.py \
  --repo-root {repo_root} \
  --timestamp {ts} \
  --prompt-file {prompt_file} \
  --timeout 600 \
  --output .claude/verify-status-{ts}.json
```

**Claude agent** — Task tool (in the same message, parallel):
```
Task(
  subagent_type: "general-purpose",
  isolation: "worktree",
  run_in_background: true,
  prompt: "<contents of prompt file>"
)
```

The orchestrator outputs a JSON report with per-agent status, exit codes, file counts, and commit hashes.

### Option B: Launch agents directly (manual)

#### Step 1: Create worktrees for CLI agents only

Claude uses Task tool's built-in worktree isolation, so only create 2 worktrees:

```bash
git worktree add .claude/worktrees/verify-opencode-{ts} HEAD --detach
git worktree add .claude/worktrees/verify-codex-{ts} HEAD --detach
```

#### Step 2: Launch all 3 agents in a SINGLE message (parallel)

Send one message containing all 3 tool calls:

**OpenCode** — Bash with `run_in_background: true`:
```bash
cd {repo}/.claude/worktrees/verify-opencode-{ts} && \
  opencode run "$(cat {prompt_file})"
```

**Codex** — Bash with `run_in_background: true`:
```bash
cd {repo}/.claude/worktrees/verify-codex-{ts} && \
  codex exec --full-auto "$(cat {prompt_file})"
```

**Claude** — Task tool (NOT Bash):
```
Task(
  subagent_type: "general-purpose",
  isolation: "worktree",
  run_in_background: true,
  prompt: "<contents of prompt file>"
)
```

#### Step 3: Wait for completion

- You will be notified as each background task completes
- Use `TaskOutput(block: true, timeout: 600000)` if needed to wait
- If an agent runs >10 minutes, check its output and consider stopping it with `TaskStop`
- Proceed to Phase V3 once at least 2 agents complete (or all finish)

## Phase V3: Collect and Synthesize Results

For each agent that completed:

### OpenCode / Codex (CLI agents in worktrees)
1. Check for commits: `git -C {worktree_path} log --oneline HEAD~1..HEAD`
2. Read the diff: `git -C {worktree_path} diff HEAD~1` (if committed) or `git -C {worktree_path} diff HEAD` (if uncommitted)
3. Read `_verify_issues.md` or `_verify_result.txt` if present

### Claude (Task subagent)
1. The Task tool returns its output directly — read the result
2. If `isolation: "worktree"` was used, check the returned worktree path for changes

### Synthesis
1. Compare all agents' findings — identify overlapping issues (high confidence) vs unique findings
2. Evaluate each fix: is it a real bug? Does it break anything? Is it over-engineered?
3. Decide what to keep, what to skip, and what to adapt
4. Prefer cherry-picking from the best agent's commit as a base, then layer unique fixes from others

## Phase V4: Apply Final Fix

1. On the original branch, apply the synthesized fixes:
   - Option A: `git cherry-pick --no-commit {best_agent_commit}` then layer additional edits
   - Option B: Apply fixes directly via Edit tool
2. Stage specific files (not `git add -A`) and commit:
   ```
   git commit -m "multi-agent-verify: synthesized fixes from verification

   <summary of what was fixed and why>

   Verified by: <agent1> (N fixes), <agent2> (N fixes), ...
   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
   ```
3. If no fixes are needed (all agents found no issues), skip this phase

## Phase V5: Cleanup (Unconditional)

Always runs, regardless of success or failure:

```bash
# Remove CLI agent worktrees (Option A: orchestrator creates these; Option B: you created them)
git worktree remove .claude/worktrees/verify-opencode-{ts} --force 2>/dev/null
git worktree remove .claude/worktrees/verify-codex-{ts} --force 2>/dev/null

# Claude's Task tool worktree is auto-cleaned if no changes were made
# If it persists, remove it too:
git worktree remove .claude/worktrees/verify-claude-{ts} --force 2>/dev/null

# Prune stale references
git worktree prune

# Delete temporary prompt file and orchestrator report
rm -f {prompt_file_path}
rm -f .claude/verify-status-{ts}.json 2>/dev/null

# Clean up verification artifacts in main worktree
find . -name "_verify_*" -delete 2>/dev/null
```

## Error Handling

- If a worktree fails to create → skip that agent, proceed with remaining
- If an agent crashes or times out → read partial output, mark as failed
- If `opencode` or `codex` is not in PATH → skip that agent, log warning
- Minimum 1 agent must complete successfully for synthesis to proceed
- If 0 agents complete → report FAIL, escalate to user
- Cleanup is always executed, even on total failure

## Common Pitfalls

| Problem | Solution |
|---------|----------|
| `claude` CLI refuses to start | NEVER use CLI — use Task tool with `isolation: "worktree"` |
| `codex` unknown flag `-q` | Use `codex exec --full-auto "prompt"` (not `-q`) |
| `opencode` unknown flag `-p` | Use `opencode run "prompt"` (not `-p`) |
| `git diff main...HEAD` fails | Try `master` or other base branch |
| Agent runs forever | Stop after 10min with `TaskStop`, read partial output |
| Cherry-pick conflicts | Apply fixes manually via Edit tool instead |
