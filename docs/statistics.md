# Statistics

The admin **Statistics** page (`/admin/statistics`) summarises how many trials are
accepted by an admin versus rejected, and how well the AI relevance label agrees with
the human reviewer's decision. It is backed by a single read-only endpoint:

```
GET /api/v1/trials/statistics   (auth-protected)
```

No schema changes were needed — every metric is derived from existing columns.

## Where the data comes from

| Outcome | Source |
|---|---|
| Approved by admin | `clinical_trials` with `status = APPROVED` |
| Pending review | `clinical_trials` with `status = PENDING_REVIEW` |
| Rejected by admin | `irrelevant_trials` with `rejected_by IS NOT NULL` (plus any legacy in-place `clinical_trials.status = REJECTED`) |
| AI auto-rejected | `irrelevant_trials` with `rejected_by IS NULL` |

The reject endpoint moves a human-rejected trial from `clinical_trials` to
`irrelevant_trials` while preserving `ai_relevance_label`, which is what makes the
AI-vs-human comparison possible.

## Metric definitions

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
