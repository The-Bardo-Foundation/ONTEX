# Accuracy insights

The **Accuracy insights** section of the admin Statistics page (`/admin/statistics`) turns
reviewer approve/reject decisions into signals for improving the AI relevance classifier.
It is backed by two endpoints:

```
GET  /api/v1/trials/insights            (auth-protected)
POST /api/v1/trials/insights/ai-advice  (auth-protected, on-demand LLM call)
```

The analysis logic lives in [app/services/accuracy.py](../app/services/accuracy.py).

A third endpoint returns the saved history of advice generations:

```
GET /api/v1/trials/insights/advice-history  (auth-protected)
```

## Product assumption

`confident` trials are trusted enough to publish without human review. That makes two
things matter most:

1. **Guardrail — confident error rate**: the share of human-decided `confident` trials that
   a reviewer rejected (`confident_rejected / (confident_approved + confident_rejected)`).
   It must stay at 0% for auto-publishing confident trials to be safe; the UI turns the card
   red if any confident trial was rejected.
2. **Shrinking the unsure bucket**: every `unsure` trial costs a manual review. The
   `unsure_approval_rate` and the per-segment pattern table show which segments
   (`phase`, `study_type`, `location_country`) are almost always approved or rejected —
   candidates to teach the classifier to decide confidently instead of deferring.

## Where the data comes from

| Signal | Source |
|---|---|
| Confident/unsure approved | `clinical_trials` with `status = APPROVED` and matching `ai_relevance_label` |
| Confident/unsure human-rejected | `irrelevant_trials` with `rejected_by IS NOT NULL` and matching `ai_relevance_label` (the reject flow preserves the AI label and reviewer notes) |
| Unsure pending | `clinical_trials` with `status = PENDING_REVIEW`, `ai_relevance_label = unsure` |
| False negatives | `clinical_trials` with `ai_relevance_label = reject` and `status = APPROVED` |

### False-negative tracking depends on the restore flow

An AI-rejected trial only becomes a detectable false negative if a human restores it and
approves it. For that to work, `restore_irrelevant_trial` copies `ai_relevance_label` and
`ai_relevance_reason` back onto the restored `ClinicalTrial`, so the original `reject`
verdict survives. No schema change was required — both columns already exist on
`ClinicalTrial`.

## AI recommendations

The "Generate AI recommendations" button calls `POST /trials/insights/ai-advice`, which
gathers the disagreement examples (confident false positives, false negatives, and resolved
unsure trials — with the AI reason and the reviewer's notes) and asks the LLM to return
`{ summary, patterns, recommendations }` aimed at keeping confident errors at zero,
shrinking the unsure bucket, and avoiding false negatives. It is a no-op with a friendly
message when there is no data, and fails safe when the AI key is missing or the call errors.

## Tracking accuracy over time

Every successful generation is appended to the `accuracy_advice_runs` table
(model `AccuracyAdviceRun`, migration `009`): a snapshot of the metrics at that moment
(confident error rate, unsure approval rate, false-negative count, examples used, AI model)
plus the advice payload. `GET /trials/insights/advice-history` returns the last 20 runs
(newest first), rendered as a compact dated list under the AI-advice button. This lets you
correlate edits to `CLASSIFICATION_SYSTEM_PROMPT` with whether the rates actually improved.
Rows are small (~1-3 KB each), so the log stays negligible even over years of use.
