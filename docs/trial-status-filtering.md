# Recruitment status filtering

How ONTEX filters trials by their ClinicalTrials.gov recruitment status
(`overall_status`), and why it is built the way it is.

## The bug this design replaced

A clinician asked to refer a patient to
[NCT07630974](https://clinicaltrials.gov/study/NCT07630974). The trial was
approved and live on OSN, but they could not find it and concluded it was
missing. It wasn't — the filter hid it:

- The trial's status was `NOT_YET_RECRUITING`.
- Filtering by **"Recruiting now"** excluded it.
- Its only other home was a filter called **"Not currently recruiting"**, which
  reads as *closed* — no reason to look there when placing a referral.
- Meanwhile its badge read **"Not yet recruiting"**, a label that appeared
  nowhere in the filter list.

So one trial was described two different ways at the same moment, and the
label that would have found it was never shown. The reporter reasonably
assumed ClinicalTrials.gov had renamed a status. They had not: `overall_status`
had genuinely changed from `NOT_YET_RECRUITING` to `RECRUITING` on 2026-07-06,
and "Not currently recruiting" was never a CT.gov status at all — it was our
own group label, inherited from the legacy WordPress template.

Two structural faults made this possible:

1. **Three hardcoded buckets covered only 8 of CT.gov's 14 statuses.** The
   other six (`UNKNOWN`, `AVAILABLE`, `NO_LONGER_AVAILABLE`,
   `TEMPORARILY_NOT_AVAILABLE`, `APPROVED_FOR_MARKETING`, `WITHHELD`) belonged
   to no bucket, so *every* filter option excluded them. In our osteosarcoma
   search set that is 104 of 848 trials — 12%, mostly `UNKNOWN`.
2. **The bucket lists were triplicated** across the API, the review queue, and
   the badge label map, with nothing keeping them in sync.

## How it works now

**The API filters on individual statuses. Groups exist only in the UI.**

### Backend

`GET /trials?overall_status=RECRUITING|NOT_YET_RECRUITING` takes a
pipe-separated list of raw CT.gov values, OR'd together — the same syntax
CT.gov's own API uses. Values are upper-cased and blanks dropped, so
`recruiting| |` is valid. There is no notion of a group server-side.

`GET /trials/facets` returns `statuses: [{value, count}]` — the statuses that
*actually occur* in the caller's visible trials, ordered by
`_STATUS_DISPLAY_ORDER` (patient-actionable first, then closed to enrolment,
then stopped/finished). Anything not in that list is appended alphabetically,
so a status CT.gov introduces later still becomes a filter option on its own.

The endpoint is auth-aware, matching `GET /trials`: anonymous callers get
facets over `APPROVED` trials only, authenticated callers over all trials.
This keeps options and results in agreement — an option is offered only when
at least one visible trial has that status.

### Frontend

`STATUS_GROUPS` in `frontend/src/utils/formatters.ts` is the **single** place
groupings are defined. A group is just a preset that ticks its member
statuses; selecting one sends `overall_status=A|B|C`.

`groupStatuses(available)` intersects the groups with the statuses actually
present and returns leftovers as `ungrouped`, which callers render as
standalone options. **This is what guarantees no trial can be unreachable** —
a status missing from every group still gets its own checkbox.

- **Public search sidebar** — group checkboxes, collapsed by default, expanding
  to the individual statuses within. Multi-select, with counts.
- **Admin dropdowns** (All Trials, Review Queue) — native `<optgroup>`s, with an
  "All \<group\>" entry above each group's individual statuses.

## Why groups are presentation-only

Patients and families do not know CT.gov vocabulary; "Enrolling by invitation"
means little without context. Plain-English groups help them. But encoding
those groups in the data model is what caused the original bug — statuses
outside a bucket became invisible, and the group label overrode the trial's
real one.

Keeping groups in the view layer gives both: plain-English scaffolding at the
top level, exact CT.gov statuses one click down, and an API where every status
is equally addressable.

## Adding or changing a group

Edit `STATUS_GROUPS` in `frontend/src/utils/formatters.ts`. Nothing else needs
to change — not the API, not the database, not the tests for the filter
itself. A status you remove from a group simply becomes a standalone option
rather than disappearing.

To change the order options are listed in, edit `_STATUS_DISPLAY_ORDER` in
`app/api/endpoints.py`.

## A note on the label

The middle group is deliberately named **"Not recruiting yet or no longer
recruiting"** rather than the old "Not currently recruiting". It names both
ends of what it contains. The old wording implied *closed*, which is what hid
not-yet-recruiting trials — the ones still worth a referral — from the person
looking for them.

## Known gap

Filtering uses `overall_status` only, not `custom_overall_status`. An admin
override changes the badge (`TrialDetailView.tsx`) but not which filter the
trial answers to. The countries facet does coalesce the two; statuses do not.
Deliberate, to keep the change contained — worth revisiting.
