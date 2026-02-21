# Project Status

> Last Updated: YYYY-MM-DD HH:MM

## Requirement Spec

<!-- Claude Code: Describe the overall goal, user context, and technical constraints. Keep it concise but unambiguous. -->

**Goal:** One sentence describing what this project/feature achieves for the user.

**Context:** Background information, user scenario, and motivation.

**Tech Stack / Constraints:** Key technologies, patterns, and boundaries (e.g., "vanilla JS, no frameworks", "must use existing useQuery hook for API calls").

### Infrastructure
**Dev Server:** N/A
**Docker Services:** N/A
**Remote Target:** N/A
**Health Endpoint:** N/A

## Requirements

<!-- Each requirement is a distinct behavior the system must have. Use MUST/SHOULD/MAY (RFC 2119) to indicate priority. Every requirement needs at least one scenario. -->

### Requirement: [Name]

[Normative statement describing what the system MUST/SHOULD/MAY do.]

#### Scenario: [Description]
- **GIVEN** [initial state or precondition — optional]
- **WHEN** [user action or system trigger]
- **THEN** [expected observable outcome]
- **AND** [additional outcomes — optional]

<!-- Example:
### Requirement: Text transformation

The system MUST accept user input text and a selected scenario, then return a polished version via API call.

#### Scenario: Normal transformation
- **WHEN** user enters text and clicks "Transform"
- **THEN** the system calls the API with the text and selected scenario
- **AND** displays the transformed result in the output area

#### Scenario: Empty input
- **WHEN** user clicks "Transform" with empty input
- **THEN** the system shows a validation message without calling the API
-->

## Subtasks

<!-- Group into batches if >5 subtasks. Each subtask maps to one or more requirements above. -->

### Batch 1: [Theme]
- [ ] Subtask description
  - **Covers:** Requirement: [Name] > Scenario: [Name]
  - **Acceptance:** What specifically must be true for this to pass (restate or refine the scenario's THEN clause in implementation terms)
  - **Scope:** `path/to/file` — which files are expected to be created or modified

## Verification Results

<!-- Update after each review. Link each row to the scenario it verifies. -->
| Subtask | Scenario Verified | Status | Method | Notes |
|---------|-------------------|--------|--------|-------|

Status values: ✅ PASS / ❌ FAIL / ⏳ Pending / 🔄 Retrying

## Technical Decisions
- Decision and rationale

## Known Issues
- (None)

## Codex Execution Log
<!-- Append after each Codex invocation -->
| Time | Batch | exit_reason | Notes |
|------|-------|-------------|-------|
