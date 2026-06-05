# Statistics

The admin **Statistics** page (`/admin/statistics`) has two layers:

1. **Headline metrics** — how many trials were approved, rejected, or are still pending,
   and how well the AI relevance label agrees with human reviewers.
2. **Accuracy insights** — a closed loop for improving the classifier: surface disagreements,
   generate surgical prompt edits, backtest a candidate prompt, apply it, and track history.

Deeper detail on the insights metrics and data sources lives in [insights.md](insights.md).

## API endpoints

All routes are auth-protected under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `GET /trials/statistics` | Headline approval counts and AI-vs-human matrix |
| `GET /trials/insights` | Classifier accuracy signals and example trials |
| `POST /trials/insights/ai-advice` | On-demand LLM advice with merged prompt proposal |
| `GET /trials/insights/advice-history` | Last 20 saved advice runs (newest first) |
| `GET /trials/classifier-prompt` | Active classifier prompt + full version history |
| `POST /trials/classifier-prompt` | Create and activate a new prompt version |
| `POST /trials/classifier-prompt/{id}/activate` | Roll back to an existing version |
| `POST /trials/insights/backtest` | Re-classify a sample with a candidate prompt |

## Headline metrics (`GET /trials/statistics`)

No schema changes were needed — every metric is derived from existing columns.

### Where the data comes from

| Outcome | Source |
|---|---|
| Approved by admin | `clinical_trials` with `status = APPROVED` |
| Pending review | `clinical_trials` with `status = PENDING_REVIEW` |
| Rejected by admin | `irrelevant_trials` with `rejected_by IS NOT NULL` (plus any legacy in-place `clinical_trials.status = REJECTED`) |
| AI auto-rejected | `irrelevant_trials` with `rejected_by IS NULL` |

The reject endpoint moves a human-rejected trial from `clinical_trials` to
`irrelevant_trials` while preserving `ai_relevance_label`, which is what makes the
AI-vs-human comparison possible.

### Metric definitions

- **Headline counts**: `approved_by_admin`, `rejected_by_admin`, `pending_review`,
  `ai_auto_rejected`, and `total` (the sum of those four).
- **`ai_confident_approval_rate`**: of the AI-`confident` trials that a human has
  actually decided on, the fraction that were approved
  (`confident_approved / (confident_approved + confident_human_rejected)`). It is `null`
  until at least one confident trial has been decided. The goal (issue #43) is to drive
  this toward 100% so confident AI classifications can be trusted without human latency.
- **`by_ai_label`**: per AI label (`confident` / `unsure` / `reject`), the number of
  trials that were `approved`, `rejected` (by a human), and still `pending`. AI
  auto-rejected trials (`rejected_by IS NULL`) are intentionally excluded from this
  matrix because no human verdict exists for them.

## Accuracy insights (UI section)

The **Accuracy insights** block below the headline cards focuses on classifier quality.
Key guardrails:

- **Confident error rate** — share of human-decided `confident` trials that a reviewer
  rejected. Must stay at 0% for auto-publishing confident trials to be safe.
- **Unsure bucket** — every `unsure` trial needs manual review; segment patterns show where
  the classifier could decide more confidently.
- **False negatives** — AI `reject` trials that a human later approved (requires the
  restore flow to preserve the original AI label).

### Reliable segment leans

The **Reliable segment leans** table groups resolved `unsure` trials by segment
(`phase`, `study_type`, `location_country`). With only ~200 trials sourced worldwide,
most segments hold a handful of decisions. Segments need at least **3** reviewer
decisions before they appear, so a "100% rejected" country built on one or two trials
is treated as noise rather than a pattern.

Example lists (confident false positives, false negatives, resolved unsure trials) show
the AI label, human decision, and truncated reviewer notes.

## AI recommendations and prompt editing

**Generate AI recommendations** calls `POST /trials/insights/ai-advice`. The server:

1. Loads disagreement examples (confident false positives, false negatives, resolved unsure).
2. Fetches the **active** classifier prompt from `classifier_prompt_versions`.
3. Asks the LLM for `{ summary, patterns, recommendations, prompt_edits }`.
4. Merges `prompt_edits` onto the active prompt via [prompt_merge.py](../app/services/prompt_merge.py)
   (surgical find/replace anchored inside `## LABEL: "confident"`, `"unsure"`, `"reject"` sections).
5. Returns `proposed_system_prompt` (the merged result) and persists the run in
   `accuracy_advice_runs` (including `proposed_prompt` and `prompt_version_id`).

The UI shows the proposal in a **unified diff editor**: inline word-level highlights on
changed lines, editable draft text, and buttons to backtest or apply.

Advice history (`GET /trials/insights/advice-history`) renders the last 20 runs as a compact
dated list so you can correlate prompt changes with whether rates improved.

## Classifier prompt versioning

Prompt text is no longer only a Python constant. Versioned prompts live in
`classifier_prompt_versions` (migration `010`), managed by
[prompt_store.py](../app/services/prompt_store.py):

- On first access, the store seeds version 1 from `CLASSIFICATION_SYSTEM_PROMPT` if the
  table is empty.
- `GET /trials/classifier-prompt` returns the active version and full history.
- **Apply & activate** (`POST /trials/classifier-prompt`) creates a new row, flips
  `is_active`, and records `source` (`manual`, `ai_advice`, etc.) plus optional `note`.
- **Rollback** (`POST /trials/classifier-prompt/{id}/activate`) re-activates a prior version.

`classify_trial` accepts an optional `system_prompt` argument so backtests and future
ingestion runs can use the active version instead of the hard-coded constant.

## Backtesting

Before applying a candidate prompt, **Run backtest** calls `POST /trials/insights/backtest`
with the draft prompt text. The endpoint:

1. Builds ground truth from human-decided trials only: approved `clinical_trials` (keep)
   and human-rejected `irrelevant_trials` (`rejected_by IS NOT NULL`). AI-only rejections
   are excluded because there is no human verdict.
2. Randomly samples up to **60** trials by default (max **200**, configurable).
3. Re-classifies each with the candidate prompt (5 concurrent calls).
4. Compares **candidate** metrics against **baseline** metrics from stored labels:
   confident error rate, unsure rate, false-negative count, and correct-auto count.

Results are shown side by side in the UI. Backtest runs are persisted in `backtest_runs`.

## Schema (migration 010)

| Table / column | Role |
|---|---|
| `classifier_prompt_versions` | Versioned classifier system prompts with `is_active` flag |
| `backtest_runs` | Optional audit log of backtest requests |
| `accuracy_advice_runs.proposed_prompt` | Merged prompt proposal from each advice run |
| `accuracy_advice_runs.prompt_version_id` | Which active prompt the advice was based on |

### Local SQLite dev

When `DATABASE_URL` uses `sqlite+aiosqlite`, startup runs `create_all` instead of Alembic.
[main.py](../app/main.py) also runs `_sync_sqlite_columns()` to `ALTER TABLE` any columns
added by later migrations (e.g. `proposed_prompt`) onto existing SQLite databases.

## Typical workflow

1. Review headline metrics and accuracy guardrails on `/admin/statistics`.
2. Inspect disagreement examples and segment leans.
3. **Generate AI recommendations** → review merged prompt in the diff editor.
4. **Run backtest** on the proposal; confirm metrics improve or regress acceptably.
5. **Apply & activate** to publish a new prompt version (or edit manually first).
6. Use advice history and version history to roll back or compare over time.
