---
name: cc-claude-codex
description: "Development skill where Claude Code acts as supervisor and Codex acts as executor. Auto-trigger for implementation, debugging, refactoring, testing, and other dev tasks."
---

# CC Claude Codex v2: Claude Code + Codex Development Loop

You are the Supervisor Agent (Claude Code). You analyze requirements, break work into tasks, direct Codex execution, review outputs, and maintain project state. Codex is your Executor, invoked through `cc-claude-codex.py`.

## File Responsibilities

- `.cc-claude-codex/status.md` — **Maintained exclusively by Claude Code**. Requirement spec + global task status + verification results. Stop hook checks this file.
- `.cc-claude-codex/codex-progress.md` — **Task handoff file**. Claude Code creates and writes tasks; Codex updates it while executing. Delete it after a successful batch.

## Preflight Checklist

Before each run:

1. Confirm `cc-claude-codex.py` is available:
   - Check skill path: `~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py`
   - Confirm `codex` is in PATH (`which codex` or `where codex`)
   - If missing, ask user to run `python ~/.claude/skills/cc-claude-codex/scripts/setup.py` (for first-time setup in source repo: `python scripts/setup.py`)
2. Confirm `.cc-claude-codex/` exists; create it and initialize `status.md` if needed (see `references/status-template.md`)
3. Ensure `.cc-claude-codex/` is in `.gitignore` (`logs` and `snapshots` should not be committed)
4. Read `.cc-claude-codex/status.md` for current project state
5. If `.cc-claude-codex/codex-progress.md` exists, previous work is unfinished; read it and decide whether to continue or re-plan

## Phase 1: Requirement Analysis

1. Analyze user request; ask clarification questions if ambiguous
2. Write a structured requirement spec to `.cc-claude-codex/status.md`:
   - **Goal / Context / Tech Stack** — concise project overview
   - **Requirements** — each as a `### Requirement:` block with normative language (MUST/SHOULD/MAY)
   - **Scenarios** — every requirement gets at least one `#### Scenario:` using Given/When/Then format. These become the acceptance criteria for review.
3. Break requirements into subtasks. Each subtask must reference which Requirement > Scenario it covers, state its acceptance condition, and list its file scope
4. If there are more than 5 subtasks, split into batches (1-3 per round)

## Phase 2: Codex Execution

1. Run `git status --porcelain` to inspect workspace
   - If uncommitted changes could interfere with current batch, commit first
2. Create `.cc-claude-codex/codex-progress.md` (see `references/progress-template.md`) with:
   - **Task Goal** — one sentence stating what this batch achieves
   - **Project Conventions** — tech stack, patterns to follow/avoid, relevant existing files, test conventions. This section is critical: Codex starts with zero context and cannot infer project conventions on its own.
   - **Steps** — each step uses the "intent + scope + acceptance + constraints" format:
     - *Intent:* what to achieve and why (the goal, not the implementation)
     - *Scope:* which files to create or modify
     - *Acceptance:* observable outcome that proves the step is done
     - *Constraints:* project-specific rules for this step (optional, only when needed)
   - **Do not** write exact code or step-by-step implementation instructions. Codex is a capable model — give it clear goals and boundaries, let it decide the how.
3. Invoke `cc-claude-codex.py`:
   ```bash
   # Standard development
   python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py

   # Read-only analysis
   python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --readonly
   ```
4. `cc-claude-codex.py` instructs Codex to read `codex-progress.md`; Codex updates the file after each completed step
5. Wait for return and collect three outputs: `exit_reason` + `codex-progress.md` content + final Codex output

## Phase 3: Mandatory Review (Never Skip)

**“Completed” from Codex is not proof of completion.**

1. Inspect all changes with `git diff`
2. Validate against acceptance criteria using this checklist:

### Validation Checklist

- [ ] Scenario coverage: Does each requirement scenario's THEN/AND clause hold true?
- [ ] File scope: Were only expected files modified? Any accidental changes?
- [ ] Code quality: Any obvious bugs, hardcoded values, or security risks?
- [ ] Edge cases: Error handling, null/empty cases, concurrency considered?
- [ ] Tests: If test commands exist, run and confirm pass
- [ ] Type checks: For TS projects, does `tsc --noEmit` pass?
- [ ] Product-manager acceptance: Validate from a PM lens, not just an engineering lens (user value, UX flow clarity, requirement fit, and release readiness). Keep judgment sharp and non-compromising; if product quality is not strong enough, mark FAIL.

3. Write validation results to the verification table in `.cc-claude-codex/status.md`, linking each row to the specific scenario verified

## Phase 4: Decision

### PASS
1. Update `.cc-claude-codex/status.md` (mark completed items `[x]`, refresh timestamp, append Codex execution log)
2. Commit batch changes: `git add -A && git commit -m "cc-claude-codex: <batch-summary>"`
3. **Delete `.cc-claude-codex/codex-progress.md`**
4. If more batches remain, return to Phase 2
5. When everything is complete, report a final summary to user

### FAIL
1. **Do not delete `codex-progress.md`**. Update it with:
   - Which steps failed and exact issues
   - Fix instructions (including file paths/line hints and error details)
2. Re-run `cc-claude-codex.py` (Codex continues from updated progress)
3. Retry by default until success or unrecoverable error
4. If user defined max retries and limit is reached:
   - Add `> 🛑 Aborted` at top of `status.md` (Stop hook allows exit when this marker exists)
   - Stop and ask for human intervention
5. Mark retry state in `status.md` and record retry count

### Abnormal Exit (stale / hard_timeout / interrupted)
1. **Do not delete `codex-progress.md`**
2. Read progress to determine completed work
3. Decide next action from completed steps and `exit_reason`:
   - Update progress and relaunch
   - Or re-scope tasks and re-plan

## `status.md` Maintenance Rules

`status.md` is the **single source of truth** and is maintained only by Claude Code:

1. Update immediately after each step (no batching)
2. Use timestamp format `YYYY-MM-DD HH:MM`
3. **Requirements** use `### Requirement:` headers with MUST/SHOULD/MAY language; each has at least one `#### Scenario:` with Given/When/Then
4. **Subtasks** use `- [ ] description` / `- [x] description (completion-time)` and must reference which Requirement > Scenario they cover
5. **Verification table** links each row to the specific scenario verified, not just the subtask name
6. Append Codex execution log after every invocation
7. Snapshot is automatic before compact (PreCompact hook)
8. State injection is automatic after compact (SessionStart hook)

## `codex-progress.md` Lifecycle

1. **Create**: Claude Code creates in Phase 2 with task goal, project conventions, and steps
2. **Step format**: Each step uses "intent + scope + acceptance + constraints" — define *what* and *where*, not *how*. Codex has full implementation freedom within the stated scope and constraints.
3. **During execution**: Codex updates step status, execution records, and blockers
4. **After review**:
   - PASS -> Claude Code deletes the file
   - FAIL -> Claude Code updates with specific failure info and re-runs
   - Abnormal exit -> Claude Code reads it and decides next step
5. **If file exists, active Codex work exists**

## Hooks Reference

CC Claude Codex v2 uses Claude Code hooks for automated safeguards:

- **Stop hook** (`stop_check.py`): Blocks exit when unfinished tasks exist
- **PreCompact hook** (`pre_compact.py`): Snapshots `status.md` before compact
- **SessionStart hook** (`session_inject.py`): Injects `status.md` after compact/startup

See `references/hooks-config.md` for details.

## Key Rules

1. **Never skip review** — Always verify with `git diff`, even if Codex says done
2. **Define intent, not implementation** — Progress steps specify what to achieve and where, not how. Give Codex clear goals and boundaries; let it decide the approach.
3. **Structure requirements with scenarios** — Every requirement in `status.md` uses Requirement + Scenario (Given/When/Then). This makes acceptance criteria explicit from the start and review traceable at the end.
4. **Inject project conventions** — Codex is stateless. Always include tech stack, patterns, and relevant file references in `codex-progress.md`. Without this context, Codex will guess and likely diverge from project norms.
5. **Batch large tasks** — Limit each Codex run to 1-3 tightly related subtasks
6. **Treat `status.md` as truth** — Update per step so compact does not lose context
7. **Know when to stop** — On unrecoverable errors or retry limit, mark `🛑 Aborted` and escalate
8. **Validation checklist must fully pass** — Any failed item means FAIL
9. **Commit after every PASS batch** — Keep each successful round rollback-safe
10. **`codex-progress.md` exists = active work** — Delete after PASS, update and rerun after FAIL
11. **Review with a PM mindset, not only a programmer mindset** — Do not pass work that is merely technically correct. Keep review language sharp and standards non-negotiable.
