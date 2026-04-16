# ONTEX — Project Roadmap

**ONTEX** (Osteosarcoma Now Clinical Trial Explorer) is an AI-augmented pipeline that fetches clinical trials from ClinicalTrials.gov, classifies their relevance using an LLM, and provides a curation dashboard where administrators can review, approve, and reject trials before they are published on the Osteosarcoma Now website.

---

## Current State

The project has solid infrastructure in place, but the core ingestion pipeline is not yet functional. Here is a summary of what is done and what is not:

### Done
- Database schema (`clinical_trials` and `irrelevant_trials` tables, dual-field `official` + `custom_*` pattern)
- Alembic migrations (schema versioning)
- ClinicalTrials.gov API v2 integration — trial index fetching (`study_index.py`) and trial detail fetching (`study_detail.py`)
- LLM prompt templates for relevance classification and AI summarisation
- OpenAI async client wrapper with retry logic and fail-safe behaviour
- Relevance classifier (`classifier.py`) — fully wired, Pydantic v2, reads confidence threshold from config
- AI summariser (`summarizer.py`) — generates patient-friendly `custom_*` fields; fail-safe on LLM error
- **Full ingestion pipeline** (`ingestion.py`) — Steps 1–7 implemented end-to-end:
  - Fetches NCT IDs, detects new/updated/rejected, fetches full study data,
    generates AI summaries, classifies relevance, upserts to DB, re-evaluates
    updated rejected trials, logs run summary
- `config.py` extended with `SEARCH_TERMS`, `INGESTION_SCHEDULE_HOURS`, `AI_MODEL`, `CONFIDENCE_THRESHOLD`, `PAGE_SIZE`
- `openai` added to `requirements.txt`
- Migration `002_add_ai_classification_columns` — adds `ai_relevance_confidence`, `ai_relevance_reason`, `ai_relevance_tier`, `ai_matching_criteria` to `clinical_trials`
- Migration `003_add_tracking_columns` — adds `approved_at`, `approved_by`, `previous_approved_at`, `previous_approved_by` to `clinical_trials`; adds `ingestion_runs` table
- `ingestion_runs` table: one row per pipeline execution with counts (new/updated/reeval/errors) — queryable audit trail
- `OPENAI_API_KEY` sentinel fix: `"Not Set"` default now correctly triggers RuntimeError in `AIClient`
- FastAPI backend with `GET /api/v1/trials` and `PATCH /api/v1/trials/{nct_id}`
- SQLAdmin panel for manual trial management
- React frontend with sidebar, trial detail view, and approve/reject buttons
- APScheduler running ingestion on configurable schedule (default 24 h), using `settings.SEARCH_TERMS`
- Development environment (Docker/SQLite), Railway deployment, GitHub Actions CI

### Not done (blocking)
- Authentication and user management
- Full trial detail API endpoint (`GET /api/v1/trials/{nct_id}`)
- Admin review queue (new/updated trials)
- Reviewer notes and audit log
- Search and filtering in both API and frontend

---

## Phases

### Phase 1 — Complete the ingestion pipeline ✅

This is the critical path. Nothing else matters until data flows end-to-end.

#### 1.1 Fix requirements and configuration ✅

- Add `openai` to `requirements.txt` (currently missing — the code imports it but it is not listed)
- Add a `config.yaml` (or extend `core/config.py`) for ingestion settings:
  - `search_terms: [list of strings]` — which queries to run against ClinicalTrials.gov
  - `ingestion_schedule_hours: 24`
  - `ai_model: gpt-4o-mini`
  - `confidence_threshold: 0.7`
  - `page_size: 100`
- Settings in this file should be readable from `app/core/config.py` so the scheduler and pipeline can consume them without hardcoding

#### 1.2 Implement `ingestion.py` Step 3 — fetch full trial data ✅

- For each NCT ID identified as new or needing re-evaluation, call `study_detail.py` to get the full study JSON
- Map every field from the ClinicalTrials.gov response to the corresponding `official_*` columns in `ClinicalTrial` / `IrrelevantTrial`
- Handle missing fields gracefully (nullable columns exist in the schema already)

#### 1.3 Implement `ingestion.py` Step 4 — AI summarization ✅

Create a new function `ai_generate_summaries(client, trial_data: dict) -> dict` in `app/services/ai/`:

- Input: raw trial data dict fetched from ClinicalTrials.gov
- Output: dict of `custom_*` values to write to the database
- One LLM call per trial (or batched if costs are a concern)
- Fields to generate:
  - `custom_brief_summary` — Short patient-friendly summary of the trial
- Write a system prompt for summarization (analogous to the existing classification prompt in `prompts.py`)
- Fail-safe: if the LLM call fails, set all `custom_*` fields to `None` and let the admin fill them in manually

#### 1.4 Implement `ingestion.py` Step 5 — relevance classification and database writes ✅

- Wire `classifier.py` into the pipeline: call `classify_trial()` with the full trial data
- Based on the result:
  - `is_relevant=True`: upsert into `clinical_trials` with `status=PENDING_REVIEW`
  - `is_relevant=False`: upsert into `irrelevant_trials` with `irrelevance_reason` set to the LLM's reason string
- Store the `classification_result` object fields (`confidence`, `reason`, `relevance_tier`, `matching_criteria`) somewhere reviewable — add columns to `clinical_trials` for `ai_relevance_confidence`, `ai_relevance_reason`, `ai_relevance_tier`, `ai_matching_criteria`

#### 1.5 Implement `ingestion.py` Step 6 — detect new vs. updated trials ✅

- **New trial**: NCT ID not in either table → run Steps 3–5, insert as `PENDING_REVIEW`
- **Updated trial**: NCT ID already in `clinical_trials` with `status=APPROVED`, and `last_update_post_date` has changed → re-run Steps 3–5, set `status=PENDING_REVIEW`, store the previous `approved_at` timestamp and `approved_by` so reviewers can compare
- **Previously rejected**: NCT ID in `irrelevant_trials` → re-evaluate only if `last_update_post_date` has changed; otherwise skip
- **No change**: NCT ID already in `clinical_trials` with same `last_update_post_date` → skip
- `approved_at`, `approved_by`, `previous_approved_at`, `previous_approved_by` columns added to `clinical_trials` (migration 003)

#### 1.6 Implement `ingestion.py` Step 7 — logging and error handling ✅

- Log each run: number of new trials found, number updated, number classified as irrelevant, fetch errors, classify errors
- `ingestion_runs` table added (migration 003): one row per run with all counts — queryable audit trail
- Per-trial error handling: one bad trial does not abort the run; `fetch_errors` and `classify_errors` are tracked and written to `ingestion_runs`

#### 1.7 Fix the PHP template API endpoint ✅

- Added `GET /api/v1/trail?trail_id={nct_id}` to FastAPI (`app/api/endpoints.py`)
- Returns full trial data in PascalCase JSON (`{ "result": [...] }`) matching what the PHP template expects — all fields are PascalCase except `key_information` which is snake_case (the PHP template reads it as `$customresult->key_information`)
- Only returns `APPROVED` trials; returns 404 for missing or non-approved trials
- Updated `templates/template-single-study.php` to call the new path; host is read from the `ONTEX_API_BASE` WordPress constant (set in `wp-config.php`) instead of hardcoded
- 3 tests added to `tests/test_api.py` covering 404-missing, 404-non-approved, and 200-approved cases

---

### Phase 2 — Testing ✅

38 tests passing. All LLM and HTTP calls mocked. Temporary file-backed SQLite used for test isolation.

#### 2.1 Ingestion pipeline tests ✅

11 integration tests in `tests/test_ingestion.py`:
- Categorisation logic (new / updated / already-rejected / no-change)
- Field mapping from ClinicalTrials.gov JSON to model fields (`map_api_to_model`)
- Full ingestion run with mocked API and LLM calls (all 7 pipeline steps)
- AI fail-safe behaviour (summarisation failure, classification failure)
- Admin-edited custom fields preserved on re-ingestion

#### 2.2 AI service tests ✅

12 unit tests in `tests/test_ai_services.py`:
- `ai_generate_summaries()`: success, LLM returns None (null dict), extra keys ignored
- `classify_trial()`: relevant unchanged, irrelevant high-confidence unchanged, irrelevant low-confidence flipped to SECONDARY, no duplicate tags, threshold read from settings
- `AIClient`: JSON parse success for generate and classify, all-retries-exhausted returns None / safe default

#### 2.3 API endpoint tests ✅

12 tests in `tests/test_api.py`:
- `GET /api/v1/trials`: empty list, status filter APPROVED, status filter PENDING_REVIEW
- `PATCH /api/v1/trials/{nct_id}`: approve, reject, 404 not found, custom_brief_summary update
- `GET /api/v1/trail`: 404 missing, 404 non-approved, 200 approved (full field validation)
- `POST /api/v1/debug/run-ingestion`: scheduler integration

#### 2.4 Test conventions

- `pytest_configure` hook in `conftest.py` sets `DATABASE_URL=sqlite+aiosqlite:///:memory:`, `OPENAI_API_KEY=sk-test-not-real`, `SKIP_MIGRATIONS=1` before any app module is imported — fixes the module-level SQLAlchemy engine isolation issue
- All tests use in-memory SQLite via `db_engine` fixture
- LLM calls always mocked; no real OpenAI API calls in tests
- Tests run in GitHub Actions CI on every push

---

### Phase 3 — Admin dashboard: review queue

The current frontend is a bare-bones prototype. This phase turns it into a proper admin tool for reviewing new and updated trials.

#### 3.1 Database additions

Add columns to `clinical_trials`:

| Column | Type | Purpose |
|---|---|---|
| `ai_relevance_confidence` | Float | LLM confidence score (0–1) |
| `ai_relevance_reason` | Text | LLM explanation for relevance decision |
| `ai_relevance_tier` | String | e.g. "primary", "secondary" |
| `ai_matching_criteria` | JSON/Text | List of matching criteria tags |
| `ingestion_event` | Enum: `NEW` / `UPDATED` | Was this trial new or updated in the last run? |
| `previous_status` | Enum | Status before the last ingestion update |
| `previous_approved_at` | DateTime | When it was last approved (if applicable) |
| `approved_at` | DateTime | When admin approved the current version |
| `approved_by` | String | Username of the approver |
| `rejected_at` | DateTime | When admin rejected |
| `rejected_by` | String | Username of the rejector |
| `reviewer_notes` | Text | Optional free-text note from the reviewer |

#### 3.2 API additions for the review queue

- `GET /api/v1/trials/review-queue` — returns trials with `status=PENDING_REVIEW`, including `ingestion_event` (NEW / UPDATED)
- `GET /api/v1/trials/{nct_id}` — returns full trial detail: all official and custom fields, AI classification metadata, reviewer notes, history
- `PATCH /api/v1/trials/{nct_id}/approve` — sets `status=APPROVED`, records `approved_by`, `approved_at`, optional `reviewer_notes`
- `PATCH /api/v1/trials/{nct_id}/reject` — sets `status=REJECTED`, records `rejected_by`, `rejected_at`, optional `reviewer_notes`
- `GET /api/v1/trials` — extend with search (`q=`), filter (`status=`, `ingestion_event=`, `phase=`, `location_country=`), and sort (`sort_by=last_update_post_date`)

#### 3.3 Review queue frontend

Add a dedicated **Review Queue** page to the React frontend:

- List view showing all `PENDING_REVIEW` trials, grouped or tagged as NEW or UPDATED
- For each trial in the list: title, phase, locations, date ingested, `ingestion_event` badge
- Click a trial → open a review detail page

**Review detail page for a NEW trial:**
- Top section: AI classification result — confidence score, relevance tier, matching criteria tags, LLM explanation text
- Middle section: all `custom_*` fields (AI-generated) displayed clearly alongside their `official_*` counterparts
- Key information bullets (from `key_information` field)
- Bottom: Approve / Reject buttons, optional reviewer notes textarea

**Review detail page for an UPDATED trial:**
- All of the above, plus
- A diff panel showing what changed since the last approved version (which fields have new values)
- Previous approval context: who approved it, when, and what reviewer notes they wrote at the time

#### 3.4 Trials library page

A separate **All Trials** page (existing Approved/Rejected tabs):
- Search bar (full-text across title, summary, eligibility)
- Filter dropdowns: status, phase, location country, ingestion event
- Sort: by last update, by date ingested, alphabetically
- Paginated results
- Click a trial → full detail view with the option to change status

---

### Phase 4 — Authentication and user management

#### 4.1 Authentication provider

Use a free, pre-built auth service — recommended options:

- **Clerk** (free tier is generous, excellent React SDK, invite-based team management built in)

The choice should prioritise: free tier with invite-based user management, a React SDK, and JWT-based API auth that FastAPI can verify.

#### 4.2 What needs to be implemented

- Protect all `/api/v1/*` endpoints — require a valid JWT from the auth provider
- Add auth middleware to FastAPI (verify JWT signature using the provider's public key)
- Update the React frontend to show a login page and include the auth token in all API requests
- Admin user creates an account; additional reviewers are invited by email via the auth provider's invite flow
- No custom user table needed — the auth provider handles user records

#### 4.3 Roles (minimal)

- **Admin** — can approve, reject, edit custom fields, invite other users, change config
- **Reviewer** — can approve and reject, can write notes, cannot invite or change config

Role can be stored as a claim in the JWT or in a small `user_roles` table.

---

### Phase 5 — Configuration management

#### 5.1 Config file

Create `config.yaml` at the repo root:

```yaml
ingestion:
  search_terms:
    - osteosarcoma
    - bone sarcoma
    - osteogenic sarcoma
  schedule_hours: 24
  page_size: 100

ai:
  model: gpt-4o-mini
  confidence_threshold: 0.7
  temperature: 0.1
  max_retries: 2
```

- Load via `app/core/config.py` at startup
- Settings here are the source of truth for the ingestion scheduler

#### 5.2 Config API (optional, lower priority)

If desired, expose a read-only `GET /api/v1/config` endpoint for the frontend to display current settings, and a `PATCH /api/v1/config` endpoint (admin-only) to update search terms and schedule without a redeploy. This is secondary — editing the YAML and redeploying is acceptable for now.

---

### Phase 6 — WordPress integration

The legacy `template-single-study.php` already fetches from our API. This phase ensures the handoff works correctly.

- Verify that the `/api/v1/trail?trail_id={nct_id}` endpoint returns the exact shape the PHP template expects
- Handle the case where a trial is in the database but not yet `APPROVED` — return a 404 or empty response so the WordPress page degrades gracefully
- Verify that `template-results.php` either calls our API for approved trials or continues to call ClinicalTrials.gov directly for search (decide which approach is correct)
- Write a small integration test that simulates what the PHP template does: fetch a trial by NCT ID and verify the response shape

---

## Open questions

These are things that need a decision before or during implementation:

1. **Search terms**: The current code searches for `"osteosarcoma"` only. Should Phase 1 add more terms (`"bone sarcoma"`, `"osteogenic sarcoma"`)? This affects how many trials are ingested and how aggressive the classifier needs to be.

2. **AI summarization model**: Should summarization use the same `gpt-4o-mini` as classification, or a more capable model for better quality summaries? Cost vs. quality tradeoff.

3. **Re-evaluation of approved trials**: If a trial is `APPROVED` and the next daily run finds it has been updated, should we reset it to `PENDING_REVIEW` automatically? (This is specified in Phase 1.5.) Confirm this is the intended behaviour — it means approved trials could disappear from the published list until reviewed again.

4. **Auth provider choice**: Clerk, Auth0, or Supabase Auth? This affects the implementation in Phase 4.

5. **`template-results.php`**: Should the search/results page eventually be replaced by the React frontend, or should it remain a PHP/WordPress page that calls our API?

6. **Ingestion run history**: Should a history of ingestion runs be stored in the database for the admin to see (e.g. "Last run: April 15, 2026 — 3 new trials, 1 updated")? This is a small addition to Phase 1.6 but useful for observability.
