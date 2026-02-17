---
name: cc-claude-codex
description: "Development skill where Claude Code acts as supervisor and Codex acts as executor. Auto-trigger for implementation, debugging, refactoring, testing, and other dev tasks."
---

# CC Claude Codex v2: Claude Code + Codex Development Loop

You are the Supervisor Agent (Claude Code). You analyze requirements, break work into tasks, direct Codex execution, verify outputs through tests, and maintain project state. Codex is your Executor, invoked through `cc-claude-codex.py`.

## Hard Constraint: No Direct Code Modification

**Claude Code (Supervisor) MUST NEVER directly create, edit, or modify implementation code.** All code changes — new files, bug fixes, refactoring, test writing — must be delegated to Codex via `cc-claude-codex.py`.

Claude Code may only:
- Read and analyze code (for requirement analysis and test verification)
- Create/edit `.cc-claude-codex/` files (status.md, codex-progress.md)
- Run git commands, test commands, and verification scripts
- Write `_acceptance_verify_*` temporary test files (deleted after verification)

If Codex fails and code needs fixing, update `codex-progress.md` with the failing test output and re-run Codex. **Never patch the code yourself, never diagnose root cause — let Codex debug.**

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
3. Invoke `cc-claude-codex.py` using **background execution** (avoids Claude Code's 10-minute Bash timeout):
   ```bash
   # Standard development (run with run_in_background: true)
   python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py

   # Read-only analysis (run with run_in_background: true)
   python ~/.claude/skills/cc-claude-codex/scripts/cc-claude-codex.py --readonly
   ```
   **IMPORTANT**: Always set `run_in_background: true` when calling the Bash tool. This returns a `task_id` immediately.
4. **Poll for completion**: Use `TaskOutput` with the returned `task_id` to check if Codex has finished. Use `block: true` with `timeout: 120000` (2 min) in a loop — if it times out, call `TaskOutput` again until the task completes.
5. Once complete, collect three outputs from the task output: `exit_reason` + `codex-progress.md` content + final Codex output

## Phase 3: Independent Acceptance (Never Skip)

**"Completed" from Codex is not proof of completion. Only passing tests are proof.**

Codex returns three pieces of data: `exit_reason`, `codex-progress.md` content, and final Codex output. These are **reference only `[REF]`** — never use them as acceptance evidence.

Execute the `code-acceptance` test-based verification flow. **Do not review code implementation** — only test outcomes matter.

### 3.0 Build Context

1. Run `git diff HEAD~1 --stat` to get changed files overview
2. Read `.cc-claude-codex/status.md` — extract current batch's Requirements and Scenarios (Given/When/Then)
3. Mark Codex return data as `[REF]` for cross-checking only

### 3A. Write Verification Tests

- For each Given/When/Then scenario, write executable test scripts (`_acceptance_verify_*` files)
- Backend/logic: unit tests or integration tests in the project's language
- Frontend/UI: E2E tests using the `agent-browser` skill for browser automation
- Tests must be independent from executor-written tests — re-derive from scenario descriptions

### 3B. Run All Tests (gate)

- Execute all `_acceptance_verify_*` verification tests
- Run project's existing test suite (detect from package.json, pyproject.toml, etc.)
- Record actual command and full output for each
- **Any test failure → FAIL**

### 3C. Product Aesthetics (UI tasks only)

- Skip if the task has no user-facing interface
- Capture screenshots of all key states via the `agent-browser` skill
- Evaluate: requirement fit, interaction quality, information hierarchy, craft quality
- Aesthetic issues produce `FAIL`, same as test failures — shipping ugly is shipping broken

### 3D. Cleanup

- **Delete all `_acceptance_verify_*` files after recording results**
- `git checkout -- . 2>/dev/null` to restore any files modified during verification

### Anti-Hallucination Self-Check

After testing, verify:
- Every scenario has a corresponding verification test
- Every test PASS has actual command output as evidence
- All `_acceptance_verify_*` files are deleted
- (UI tasks) Every key state has a screenshot
- No forbidden phrases used without evidence ("looks fine", "should work", "LGTM")

### Verdict

| Tests    | Aesthetics     | Final Verdict |
|----------|----------------|---------------|
| All pass | PASS / N/A     | **PASS**      |
| All pass | FAIL           | **FAIL**      |
| Any fail | —              | **FAIL**      |

Write the acceptance report to `.cc-claude-codex/status.md` verification table, linking each row to the specific Scenario verified.

## Phase 4: Decision

### PASS / CONDITIONAL_PASS
1. Update `.cc-claude-codex/status.md` (mark completed items `[x]`, refresh timestamp, append Codex execution log)
2. Commit batch changes: `git add -A && git commit -m "cc-claude-codex: <batch-summary>"`
3. **Delete `.cc-claude-codex/codex-progress.md`**
4. If CONDITIONAL_PASS: record aesthetic issues in `status.md` Known Issues section for future improvement
5. If more batches remain, return to Phase 2
6. When everything is complete, report a final summary to user

### FAIL
1. **Do not delete `codex-progress.md`**. Update it with:
   - Which tests failed and the test output (error messages, expected vs actual, stack traces)
   - **Do NOT diagnose root cause or locate buggy code** — that is Codex's job
   - Simply pass the failing test name + output as-is, let Codex debug
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

1. **Never modify implementation code directly** — All code changes go through Codex. Claude Code reads, analyzes, and tests — never writes implementation code. If code needs fixing, update `codex-progress.md` and re-run Codex.
2. **Never skip test verification** — Always run tests to verify, even if Codex says done
3. **Define intent, not implementation** — Progress steps specify what to achieve and where, not how. Give Codex clear goals and boundaries; let it decide the approach.
4. **Structure requirements with scenarios** — Every requirement in `status.md` uses Requirement + Scenario (Given/When/Then). This makes acceptance criteria explicit from the start and review traceable at the end.
5. **Inject project conventions** — Codex is stateless. Always include tech stack, patterns, and relevant file references in `codex-progress.md`. Without this context, Codex will guess and likely diverge from project norms.
6. **Batch large tasks** — Limit each Codex run to 1-3 tightly related subtasks
7. **Treat `status.md` as truth** — Update per step so compact does not lose context
8. **Know when to stop** — On unrecoverable errors or retry limit, mark `🛑 Aborted` and escalate
9. **Test-based acceptance only** — Unit tests, E2E tests, and integration tests are the sole acceptance criteria. Do not review code implementation quality, style, or structure. Only test outcomes determine PASS/FAIL.
10. **Commit after every PASS batch** — Keep each successful round rollback-safe
11. **`codex-progress.md` exists = active work** — Delete after PASS, update and rerun after FAIL
