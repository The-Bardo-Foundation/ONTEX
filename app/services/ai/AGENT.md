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
  "is_relevant": true,
  "confidence": 0.92,
  "reason": "Trial explicitly targets recurrent osteosarcoma in pediatric patients.",
  "relevance_tier": "primary",
  "matching_criteria": ["osteosarcoma_in_conditions", "osteosarcoma_in_eligibility"]
}
```

Fields:
- `is_relevant`: boolean
- `confidence`: float 0.0–1.0
- `reason`: 1–2 sentence justification
- `relevance_tier`: `"primary"` | `"secondary"` | `"irrelevant"`
- `matching_criteria`: list of tags that matched (see section 3.3)

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

### 3.3 Valid matching_criteria Tags

- `osteosarcoma_in_title`
- `osteosarcoma_in_conditions`
- `osteosarcoma_in_eligibility`
- `bone_sarcoma_eligible`
- `broad_sarcoma_trial`
- `pediatric_aya_eligible`
- `phase1_open_enrollment`
- `solid_tumor_with_sarcoma`
- `none`

### 3.4 Confidence Thresholds

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
- After retries are exhausted, return the safe default:
  `is_relevant=true, confidence=0.0, reason="AI evaluation failed — needs manual review"`
- **NEVER silently drop a trial.** On any failure (after applying the retry policy), default to RELEVANT.

---

## 6. LLM Configuration

- Provider: OpenAI (via `OPENAI_API_KEY` in config)
- Model: `gpt-4o-mini`
- Temperature: 0.1
- Response format: JSON mode
