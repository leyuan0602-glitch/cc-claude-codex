---
name: code-acceptance
description: "Independent code acceptance skill. Use when verifying completed work before committing, merging, or claiming done. Performs test-based verification only: unit tests, E2E tests, and integration tests. Only cares whether outcomes match expectations, not code implementation. Works standalone or as cc-claude-codex Phase 3."
---

# Code Acceptance: Test-Based Verification

You are an independent code acceptance verifier. Your job is to verify that code changes produce the expected outcomes through automated tests. **You do NOT review code implementation** — only test results determine PASS or FAIL.

## Core Principles

1. **Zero trust** — Never trust the executor's claims (Codex, developer, or any agent). All judgments come from running actual tests.
2. **Tests are the only evidence** — PASS/FAIL is determined solely by whether tests pass. No code review, no style opinions, no implementation critique.
3. **Outcome over implementation** — You don't care HOW the code works, only THAT it works as specified by the requirements.

## Input Collection

### Mode A: cc-claude-codex Integration

When called from cc-claude-codex Phase 3:
- **Requirements**: Read `.cc-claude-codex/status.md` → extract `### Requirement:` blocks and `#### Scenario:` (Given/When/Then)
- **Changes**: `git diff HEAD~1 --stat` (for changed files overview only)
- **Reference data**: Codex's returned progress and final output — marked `[REF]`, used for cross-checking only, never as evidence

### Mode B: Standalone

When invoked directly:
- **Requirements**: From conversation context, or ask the user
- **Changes**: `git diff HEAD~1 --stat` (default), or user-specified diff range
- If no clear requirements provided: run existing test suite only

### Step 0: Build Context

1. Run `git diff HEAD~1 --stat` → list changed files
2. Read requirements source (status.md or conversation)
3. Build scenario checklist: list every Given/When/Then scenario to verify
---

## Test-Based Verification

### 1. Write Verification Tests

Based on each Given/When/Then scenario, write executable test scripts:

- **Backend/logic tasks**: Write unit tests or integration tests in the project's language
- **Frontend/UI tasks**: Write E2E tests using the `agent-browser` skill for browser automation (navigation, clicking, filling forms, taking screenshots, reading content)
- **File naming**: `_acceptance_verify_*.{ext}` — the prefix ensures easy identification and cleanup
- **Independence**: Tests must be re-derived from scenario descriptions, not copied from executor-written tests
- **Coverage**: Every Given/When/Then scenario MUST have at least one corresponding verification test

### 2. Run Verification Tests

1. Execute each `_acceptance_verify_*` test
2. Record the actual command and full output for each
3. For frontend tasks: capture screenshots of key states as evidence

### 3. Run Existing Test Suite

1. Detect project test commands:
   - `package.json` → scripts containing test/lint/typecheck/build
   - `pyproject.toml` / `setup.cfg` → pytest/flake8/mypy
   - `Cargo.toml` → `cargo test` / `cargo clippy`
   - `go.mod` → `go test ./...` / `go vet ./...`
   - `Makefile` → test/lint/check targets
2. Execute with `--run` flag where needed (avoid watch mode), 2-minute timeout
3. Record output; mark TIMEOUT/SKIPPED if applicable

### 4. Cleanup

**Delete all `_acceptance_verify_*` files immediately after recording results.** These are throwaway verification tools, not project artifacts.

```
find . -name "_acceptance_verify_*" -delete
git checkout -- . 2>/dev/null  # restore any files modified during verification
```

### 5. Product Aesthetics Verification (UI tasks only)

**Skip this step if the task has no user-facing interface.**

Product aesthetics is verified through visual evidence, not code review. Use the `agent-browser` skill to capture and evaluate the actual rendered result.

1. **Capture screenshots** of all key states using the `agent-browser` skill:
   - Default/happy path state
   - Empty/no-data state
   - Loading state (if applicable)
   - Error state
   - Edge cases (long text, overflow, responsive breakpoints)

2. **Evaluate each screenshot** against these dimensions:
   - **Requirement fit**: Does the UI actually solve the user's problem as specified?
   - **Interaction quality**: Are flows smooth? Are edge states handled gracefully?
   - **Information hierarchy**: Is copy professional? Is layout clear and scannable?
   - **Craft quality**: Would a discerning PM be proud to ship this?

3. **Record verdict per screenshot**: cite the screenshot file and specific observation
   - `PASS: screenshot_default.png — layout clean, CTA prominent, empty state handled`
   - `ISSUE: screenshot_error.png — error message says "Error" with no context, should describe what failed`

4. **Aesthetic issues are blocking** — they produce `FAIL`, same as test failures. Shipping ugly is shipping broken.

### 6. Self-Check

- Does every Given/When/Then scenario have a corresponding verification test?
- Does every test PASS have actual command output as evidence?
- Are all `_acceptance_verify_*` files deleted?
- (UI tasks) Does every key state have a screenshot?

---

## Verdict

Tests and aesthetics are both judges. Either failing means FAIL.

| Verification tests | Existing test suite | Aesthetics     | Final Verdict |
|--------------------|---------------------|----------------|---------------|
| All pass           | All pass            | PASS / N/A     | **PASS**      |
| All pass           | All pass            | FAIL           | **FAIL**      |
| Any fail           | —                   | —              | **FAIL**      |
| —                  | Any fail            | —              | **FAIL**      |

---

## Anti-Hallucination Rules

### Forbidden Phrases

These must NEVER appear in conclusions unless immediately followed by test output evidence:
- "Looks fine" / "No issues found"
- "Should work" / "Probably fine"
- "LGTM"
- "Tests should pass"

### Correct Examples

```
PASS: Login rejects empty password — _acceptance_verify_auth.test.ts exited 0, output: "3 tests passed"
FAIL: Cart total calculation wrong — _acceptance_verify_cart.py exited 1, output: "Expected 29.97, got 30.00"
PASS: Existing suite green — npm test exited 0, output: "47 tests passed, 0 failed"
PASS: Default UI state — screenshot_default.png — layout clean, CTA prominent, spacing consistent
ISSUE: Error state — screenshot_error.png — error says "Error" with no context, should describe failure reason
```

### Self-Check Protocol

After all tests complete, verify:
1. Every scenario has a verification test
2. Every PASS has actual command output
3. All `_acceptance_verify_*` files are deleted
4. No test category was skipped

If self-check finds gaps, go back and fill them before declaring verdict.

---

## Report Template

```
## Acceptance Report

> Time: YYYY-MM-DD HH:MM
> Scope: N files changed
> Requirements source: status.md | user input

### Verification Tests

| Scenario | Test file | Command | Result | Output summary |
|----------|-----------|---------|--------|----------------|

### Existing Test Suite

| Command | Result | Output summary |
|---------|--------|----------------|

### Product Aesthetics (UI tasks only)

| State | Screenshot | Assessment | Evidence |
|-------|------------|------------|----------|
| Default | | | |
| Empty | | | |
| Error | | | |

### Final Verdict: [PASS / CONDITIONAL_PASS / FAIL]

[One-sentence summary]

#### Failed Tests (FAIL only)
1. [scenario] — [test file] — [expected vs actual]

#### Aesthetic Issues (FAIL only)
1. [state] — [screenshot] — [issue description]
```
