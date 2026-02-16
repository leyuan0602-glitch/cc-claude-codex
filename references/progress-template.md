# Codex Task Progress

> Status: ⏳ In Progress
> Start Time: YYYY-MM-DD HH:MM
> Last Updated: YYYY-MM-DD HH:MM

<!-- FOR CODEX — How to update this file as you work:
1. Before starting a step: read its Intent, Scope, Acceptance, and Constraints
2. After completing a step: check it off (- [ ] → - [x]), append a row to the Execution Log
3. If blocked: describe the issue in the Blockers section and move on to the next step if possible
4. After all steps are done: change Status at the top from "⏳ In Progress" to "✅ Completed" and update Last Updated
5. Do NOT modify Task Goal, Project Conventions, or step definitions — only update checkboxes, Execution Log, and Blockers
-->

## Task Goal

<!-- Claude Code: One clear sentence stating what this batch achieves. -->

## Project Conventions

<!-- Claude Code: Inject project-specific patterns and constraints that Codex cannot infer on its own. This section is critical — Codex starts with zero context. -->

- **Tech stack:** [e.g., React 18 + TypeScript + Zustand]
- **Patterns to follow:** [e.g., "All API calls use `src/lib/api.ts` wrapper", "Components use CSS Modules"]
- **Patterns to avoid:** [e.g., "Do not use Redux", "No inline styles"]
- **Relevant existing files:** [e.g., "`src/hooks/useQuery.ts` — existing data fetching hook, reuse it"]
- **Test conventions:** [e.g., "Tests live in `__tests__/` next to source, use Vitest"]

## Steps

<!--
Each step defines WHAT to achieve and WHERE, not HOW to implement it.
Codex decides the implementation approach.

Format:
- Intent: what this step accomplishes (the "what" and "why")
- Scope: which files to create or modify
- Acceptance: how to verify it's done correctly (observable outcome, not implementation detail)
- Constraints: project-specific rules that apply to this step (optional, only if needed)
-->

- [ ] **Step 1: [Intent — what to achieve]**
  - **Scope:** `path/to/file` — create | modify
  - **Acceptance:** [Observable outcome that proves this step is done. E.g., "Running `node --check app.js` exits with 0", "The page renders a form with input field and submit button"]
  - **Constraints:** [Optional. E.g., "Must use existing `fetchWrapper` from `src/lib/api.ts`"]

- [ ] **Step 2: [Intent]**
  - **Scope:** `path/to/file`
  - **Acceptance:** [Observable outcome]

<!-- Example:

- [ ] **Step 1: Create the text input form with scenario selector**
  - **Scope:** `index.html` — create, `style.css` — create
  - **Acceptance:** Opening index.html in a browser shows a textarea, a dropdown with 4 scenario options, and a "Transform" button. Layout is centered and responsive.

- [ ] **Step 2: Implement API call and result display**
  - **Scope:** `app.js` — create
  - **Acceptance:** Clicking "Transform" with text input sends a POST to the configured API endpoint and displays the response in the output area. Empty input shows a validation message without calling the API.
  - **Constraints:** Use fetch API. API endpoint and key are read from localStorage with a settings UI fallback.
-->

## Execution Log
<!-- Codex: Append after each completed step -->
| Time | Step | Files Changed | Notes |
|------|------|---------------|-------|

## Blockers
<!-- Codex: Record any issue that prevents further progress -->
(None)
