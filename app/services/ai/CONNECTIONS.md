# Workflow Connections: classifier.py

## Input

**Function:** `classify_trial(client, trial)`

- TODO: Who calls this? (e.g. ingestion pipeline, an API endpoint)
- TODO: What object is passed as `trial`? (e.g. `ClinicalTrial` from `app/db/models.py`, a dict from the API)

**Fields needed from the trial object:**

| Field | TODO |
|-------|------|
| `nct_id` | TODO: where does this come from? |
| `brief_title` | TODO: where does this come from? |
| `brief_summary` | TODO: where does this come from? |
| `study_type` | TODO: where does this come from? |
| `phase` | TODO: where does this come from? |
| `overall_status` | TODO: where does this come from? |
| `eligibility_criteria` | TODO: where does this come from? |
| `intervention_description` | TODO: where does this come from? |

---

## Output

**Returns:** `ClassificationResult`

```python
ClassificationResult(
    is_relevant=True,        # bool — relevant to osteosarcoma patients?
    confidence=0.92,         # float 0.0-1.0
    reason="...",            # 1-2 sentence justification
    relevance_tier="primary", # "primary" | "secondary" | "irrelevant"
    matching_criteria=[...]  # which criteria matched
)
```

- TODO: What happens with `is_relevant`? (e.g. route to `clinical_trials` or `irrelevant_trials` table)
- TODO: Who reads the result and decides the next step?

---

## Example Call

```python
# TODO: fill in when wiring up
client = AIClient()
result = await classify_trial(client, some_trial_object)

if result.is_relevant:
    # TODO: store in clinical_trials table
    pass
else:
    # TODO: store in irrelevant_trials table with result.reason
    pass
```
