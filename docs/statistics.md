# Statistics

The admin **Statistics** page (`/admin/statistics`) answers two questions: how many trials
reviewers approve versus reject, and where the AI classifier disagrees with them. The second
half closes the loop — it turns those disagreements into a proposed classifier prompt you can
backtest, apply and roll back.

Analysis logic lives in [accuracy.py](../app/services/accuracy.py), prompt storage in
[prompt_store.py](../app/services/prompt_store.py), and prompt patching in
[prompt_merge.py](../app/services/prompt_merge.py).

**Wording:** the AI labels are stored as `confident` / `unsure` / `reject` but shown as
**Match** / **Partial Match** / **Not Suitable** everywhere in the admin UI
(`formatAiLabel` in `frontend/src/utils/formatters.ts`). This document uses the stored values.

## API endpoints

All routes are auth-protected under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `GET /trials/statistics` | Headline approval counts and the AI-vs-human matrix |
| `GET /trials/insights` | Classifier accuracy signals and example trials |
| `POST /trials/insights/ai-advice` | On-demand LLM advice with a merged prompt proposal |
| `GET /trials/insights/advice-history` | Last 20 saved advice runs (newest first) |
| `GET /trials/classifier-prompt` | Active classifier prompt + version history |
| `POST /trials/classifier-prompt` | Create and activate a new prompt version |
| `POST /trials/classifier-prompt/{id}/activate` | Roll back to an existing version |
| `POST /trials/insights/backtest` | Re-classify a sample with a candidate prompt |

## Where the numbers come from

Every metric is derived from existing columns — no new tables were needed for the counts.
The reject flow moves a human-rejected trial from `clinical_trials` to `irrelevant_trials`
while preserving `ai_relevance_label` and the reviewer notes, which is what makes the
AI-vs-human comparison possible at all.

| Outcome | Source |
|---|---|
| Approved by admin | `clinical_trials`, `status = APPROVED` |
| Pending review | `clinical_trials`, `status = PENDING_REVIEW` |
| Rejected by admin | `irrelevant_trials`, `rejected_by IS NOT NULL` (plus legacy in-place `status = REJECTED`) |
| AI auto-rejected | `irrelevant_trials`, `rejected_by IS NULL` |
| False negatives | `clinical_trials`, `ai_relevance_label = reject` and `status = APPROVED` |

A false negative is only detectable if a human restores an AI-rejected trial and approves it,
so `restore_irrelevant_trial` copies `ai_relevance_label` / `ai_relevance_reason` back onto the
restored row.

## Metrics

`confident` trials are auto-published without review, so two things matter most: confident
errors must stay at zero, and the `unsure` bucket — which costs a manual review per trial —
should shrink.

- **Confident error rate (guardrail)** — share of human-decided `confident` trials a reviewer
  rejected. The card turns red as soon as it is above 0%.
- **`ai_confident_approval_rate`** — the inverse view used by the headline card:
  `confident_approved / (confident_approved + confident_rejected)`, `null` until at least one
  confident trial has been decided. Issue #43's goal is to drive this to 100%.
- **Unsure approval rate** — how reviewers resolve the `unsure` bucket, plus how many are
  still pending.
- **`by_ai_label`** — per AI label, the number of trials approved, human-rejected and pending.
  AI auto-rejections are excluded because no human verdict exists for them.
- **Reliable segment leans** — resolved `unsure` trials grouped by `phase`, `study_type` and
  `location_country`. With ~200 trials sourced worldwide a segment needs at least **3**
  reviewer decisions before it is shown, so a "100% rejected" country built on one or two
  trials is treated as noise rather than a pattern. A consistent lean is a candidate for
  teaching the classifier to decide instead of deferring.

## AI recommendations

**Generate AI recommendations** calls `POST /trials/insights/ai-advice`, which:

1. Collects disagreement examples (confident false positives, false negatives, resolved
   unsure trials) with the AI reason and the reviewer's notes.
2. Loads the **active** classifier prompt from `classifier_prompt_versions`.
3. Sends both to the LLM via `AIClient.analyze_accuracy()` (`temperature=0.2`,
   `response_format=json_object`). Prompt constants are in
   [prompts.py](../app/services/ai/prompts.py).
4. Merges the returned `prompt_edits` onto the active prompt with `prompt_merge.py` — surgical
   find/replace anchored inside the `## LABEL: "confident"` / `"unsure"` / `"reject"` sections,
   never a full rewrite, so untouched sections stay verbatim.
5. Returns `{ summary, patterns, recommendations, prompt_edits, proposed_system_prompt }` and
   saves the run to `accuracy_advice_runs` with a metric snapshot.

The UI shows the proposal in a unified diff editor with word-level highlights and an editable
draft. Advice history renders the last 20 runs as a dated list, so you can correlate a prompt
change with whether the rates actually moved. Rows are 1–3 KB, so the log stays negligible.

With no decided disagreements yet the endpoint returns a friendly message without calling the
LLM; a missing API key or a failed call fails safe with an empty advice payload.

**Model:** `AI_MODEL` defaults to `openai/gpt-4o-mini` (via OpenRouter) and is shared with
classification and summarisation. It is cheap enough for routine advice runs, but prompt
surgery benefits from stronger reasoning — a dedicated setting for this step (e.g. a Claude
Sonnet model) is a sensible follow-up before recommendations are trusted more.

## Prompt versioning and backtesting

The classifier prompt lives in `classifier_prompt_versions` rather than only in Python. The
store seeds version 1 from `CLASSIFICATION_SYSTEM_PROMPT` on first access; **Apply & activate**
writes a new row and flips `is_active`, recording `source` (`manual`, `ai_advice`) and an
optional note; activating an older row rolls back. `classify_trial` takes an optional
`system_prompt` so backtests and ingestion use the active version.

**Run backtest** (`POST /trials/insights/backtest`) re-classifies a random sample of
human-decided trials (60 by default, max 200, 5 concurrent calls) with the draft prompt and
compares candidate against baseline metrics: confident error rate, unsure rate, false-negative
count and correct auto-decision count. Ground truth is approved `clinical_trials` plus
human-rejected `irrelevant_trials`; AI-only rejections are excluded. Runs are logged to
`backtest_runs`.

## Schema

| Table / column | Migration | Role |
|---|---|---|
| `accuracy_advice_runs` | 009 | One row per advice generation: metric snapshot + advice payload |
| `classifier_prompt_versions` | 010 | Versioned classifier system prompts with an `is_active` flag |
| `backtest_runs` | 010 | Audit log of backtest requests |
| `accuracy_advice_runs.proposed_prompt` / `.prompt_version_id` | 010 | Merged proposal and the prompt it was based on |

On local SQLite (`sqlite+aiosqlite`) startup runs `create_all` instead of Alembic, so
[main.py](../app/main.py) calls `_sync_sqlite_columns()` to `ALTER TABLE` columns added by
later migrations onto an existing dev database.

## Typical workflow

1. Check the guardrail cards and the AI-vs-human matrix.
2. Read the disagreement examples and segment leans.
3. **Generate AI recommendations**, review the merged prompt in the diff editor.
4. **Run backtest**; apply only if the metrics hold up. Roll back from version history if not.
