# ONTEX AI Agent: Clinical Trial Relevance Classifier

## 1. Purpose

This agent receives a clinical trial object and determines whether it is
relevant to osteosarcoma patients. That is its only job.

The database exists because there are VERY FEW clinical trials for osteosarcoma
and patients have LIMITED TREATMENT OPTIONS. The editorial team at Osteosarcoma
Now makes the final decision — this agent only pre-filters.

### Critical Design Principle

**INCLUDE rather than EXCLUDE when uncertain.**

It is far better to flag a possibly relevant study for human review than to
miss one that could help a patient.

---

## 2. Input / Output

### Input

A `ClinicalTrial` object with these fields:
- `nct_id` — ClinicalTrials.gov identifier
- `brief_title` — short study title
- `brief_summary` — study description
- `overall_status` — Recruiting, Completed, etc.
- `phase` — Phase 1, 2, 3, 4
- `study_type` — Interventional, Observational
- `eligibility_criteria` — full inclusion/exclusion text
- `intervention_description` — what treatment is being tested
- `minimum_age`, `maximum_age`
- `location_country`, `location_city`

### Output

JSON classification result:
```json
{
  "label": "confident",
  "reason": "Trial explicitly targets recurrent osteosarcoma in pediatric patients."
}
```

Fields:
- `label`: `"confident"` | `"unsure"` | `"reject"`
- `reason`: 1–2 sentence justification

---

## 3. Relevance Criteria

### 3.1 RELEVANT — Include These Trials

**Primary (High Confidence):**
- Osteosarcoma explicitly mentioned in title, conditions, or inclusion criteria
- Osteogenic sarcoma mentioned in title, conditions, or inclusion criteria
- Bone sarcoma studies where osteosarcoma is one of the qualifying diagnoses
- Recurrent/refractory osteosarcoma trials
- Metastatic osteosarcoma, including lung metastases from osteosarcoma

**Secondary (Include with Caution, flag for review):**
- Broad solid tumor / sarcoma trials where osteosarcoma is listed in
  inclusion criteria or eligible conditions
- Pediatric/AYA (adolescent and young adult) cancer trials where osteosarcoma
  patients are eligible based on inclusion criteria
- Phase 1 trials that are not osteosarcoma-specific but where osteosarcoma
  patients CAN enroll (important: very few treatment options exist)

**Eligible Study Types:**
- Interventional (all phases: 1, 1/2, 2, 2/3, 3, 4)
- Observational
- Expanded access programs

**Eligible Statuses:**
- Recruiting
- Not yet recruiting
- Active, not recruiting
- Enrolling by invitation
- Completed (historical value for research)

### 3.2 IRRELEVANT — Exclude These Trials

- General cancer trials with NO osteosarcoma/bone sarcoma mention in
  inclusion criteria or conditions
- Soft tissue sarcoma ONLY (e.g., liposarcoma, rhabdomyosarcoma) with no
  osteosarcoma mention in eligibility
- Other bone marrow cancers (leukemia, myeloma, lymphoma) without overlap
- Adult solid tumors (lung, breast, colorectal, prostate) without sarcoma link
- General surgery studies without a cancer treatment angle
- Trials where osteosarcoma is ONLY mentioned in background/literature text,
  NOT in inclusion/exclusion criteria or conditions
- Withdrawn or Terminated trials with no active recruitment

**Duplicate Handling:**
- If the same trial appears under multiple NCT numbers, keep only the most
  recent one. Flag duplicates in the irrelevance reason.

### 3.3 Confidence Thresholds

- confidence >= 0.7 AND is_relevant=true → auto-classify as RELEVANT
- confidence >= 0.7 AND is_relevant=false → auto-classify as IRRELEVANT
- confidence < 0.7 → classify as RELEVANT (err on side of inclusion),
  add note "Low confidence — needs human review"

---

## 4. Workflow

```
1. Receive ClinicalTrial object
2. Send trial fields to LLM for classification
3. Apply confidence threshold override (section 3.4)
4. Return classification result
```

The caller decides what to do with the result (store in DB, etc.).
This agent does NOT fetch data, write to DB, or generate summaries.

---

## 5. Error Handling

- All failures (including invalid JSON responses, timeouts, and other API errors)
  may be retried according to the AI client's configured retry policy (e.g. `max_retries`).
- After retries are exhausted, return a `ClassificationResult` with `failed=True`
  (label `unsure`, `reason="AI evaluation failed: <error>"`).
- The `failed` flag tells the ingestion pipeline to **skip the trial entirely this
  run** — no row is written — so the trial is refetched and re-evaluated on the next
  daily run rather than parked with a verdict the AI never actually made.
- A genuine `unsure`/`reject`/`confident` verdict always has `failed=False`.
- `failed` is set by our code only. Never trust a `failed` field coming back from the
  LLM's JSON — the client overrides it to `False` when parsing a successful response.

### Why skipping is safe (this used to say "NEVER silently drop a trial")

Dropping the trial for one run is not data loss, because **nothing is written**:

- A **new** trial gets no row, so the next run still sees it as new.
- An **updated** trial keeps its old `last_update_post_date`, so it still mismatches
  CT.gov and Step 2's date diff flags it as updated again.
- A **rejected** trial stays in `irrelevant_trials` with its old date, so re-evaluation
  is triggered again.

In every case the trial resurfaces on the next daily run and is re-classified then. The
alternative — storing `unsure` — is worse: it puts a verdict the AI never made in front
of the editorial team, and once the row exists with a current date, the date diff stops
flagging it, so the AI never looks at that trial again.

The cost is that a sustained LLM outage means a day (or more) of no ingestion. That is
visible as `classify_errors` on the ingestion run record and in the admin dashboard.

---

## 6. LLM Configuration

- Provider: OpenRouter (via `OPENROUTER_API_KEY` in config)
- Model: `openai/gpt-4o-mini`
- Temperature: 0.1
- Response format: JSON mode
