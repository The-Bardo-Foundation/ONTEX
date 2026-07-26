import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDocumentTitle } from '../utils/useDocumentTitle';

/*
 * Muted tints rather than saturated green/yellow/red pills — the three labels stay
 * distinguishable without turning the page into a traffic light. These are not the
 * semantic recruitment-status badges in `utils/formatters.ts`.
 */
const LABEL_CONFIG = {
  confident: {
    text: 'Match',
    chip: 'bg-accent-50 text-accent-800',
    desc: 'Clearly relevant — published automatically',
  },
  unsure: {
    text: 'Partial Match',
    chip: 'bg-brand-50 text-brand-600',
    desc: 'Uncertain eligibility — sent to editorial review',
  },
  reject: {
    text: 'Not Suitable',
    chip: 'bg-surface-muted text-gray-600',
    desc: 'Not relevant to osteosarcoma — filtered out',
  },
} as const;

type LabelKey = keyof typeof LABEL_CONFIG;

const LABEL_KEYS = Object.keys(LABEL_CONFIG) as LabelKey[];

const EXAMPLES = [
  {
    label: 'confident' as const,
    title: 'NK Cell Therapy for Relapsed/Refractory Bone Sarcoma',
    description:
      'Phase 1/2 trial of allogeneic NK cell infusion in patients with relapsed or refractory osteosarcoma, Ewing sarcoma, or chondrosarcoma.',
    reason:
      'Osteosarcoma is explicitly named as an eligible diagnosis in a bone sarcoma cohort.',
  },
  {
    label: 'unsure' as const,
    title: 'Phase 1 Open-Label Study in Pediatric Solid Tumors',
    description:
      'A first-in-child dose escalation study of a novel kinase inhibitor in patients aged 2–21 with relapsed or refractory solid tumors. No specific tumor type required.',
    reason:
      'Osteosarcoma is not named, but the broad pediatric solid tumor eligibility means patients could qualify. Needs human review.',
  },
  {
    label: 'reject' as const,
    title: 'Treatment of Advanced Ovarian Carcinosarcoma',
    description:
      'A randomized trial evaluating carboplatin plus paclitaxel vs. ifosfamide in patients with Stage III–IV uterine or ovarian carcinosarcoma.',
    reason:
      'Carcinosarcoma of the ovary/uterus is a carcinoma variant — completely unrelated to bone tumors. Osteosarcoma is not eligible.',
  },
];

/*
 * The three framing facts, shown as figures rather than prose. The colour is
 * per-stat on purpose: brand blue for the patient count, accent olive for the
 * staying-current point, near-black for the registry size — one accent each,
 * no traffic light.
 */
const WHY_STATS = [
  {
    figure: '~1,000',
    figureColor: 'text-brand-600',
    body: (
      <>
        people diagnosed with osteosarcoma in the US every year — mostly children and
        teenagers.
      </>
    ),
  },
  {
    figure: 'Daily',
    figureColor: 'text-accent-700',
    body: (
      <>
        trials open, close, and change who they can enrol. Weeks-old information can mean
        missing the one that fits.
      </>
    ),
  },
  {
    figure: '~600k',
    figureColor: 'text-gray-900',
    body: (
      <>
        studies listed on{' '}
        <a
          href="https://clinicaltrials.gov"
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-600 underline decoration-brand-200 underline-offset-2 transition-colors hover:decoration-brand-500"
        >
          ClinicalTrials.gov
        </a>
        . Finding the handful that apply is a full-time job.
      </>
    ),
  },
];

const PIPELINE_STEPS = [
  {
    number: 1,
    title: 'Automated Search',
    summary:
      'Queries ClinicalTrials.gov every 24 hours and sorts results into new, updated, or unchanged.',
    detail: (
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">
        <p>
          Every 24 hours the system queries the ClinicalTrials.gov API with a set of
          osteosarcoma-related search terms, collecting all matching trial IDs and their
          last-updated timestamps.
        </p>
        <p>
          Each result is compared against what is already in the database and sorted into{' '}
          <strong className="font-semibold text-gray-900">new</strong> (never seen before),{' '}
          <strong className="font-semibold text-gray-900">updated</strong> (changed since the
          last run), or{' '}
          <strong className="font-semibold text-gray-900">already processed</strong> (no
          change, skipped). That way the system catches both newly registered trials and
          edits to existing ones.
        </p>
      </div>
    ),
  },
  {
    number: 2,
    title: 'AI Classification',
    summary: 'Each trial is read in full and assigned one of three labels.',
    detail: null, // rendered separately by ClassificationStep
  },
  {
    number: 3,
    title: 'AI Summarisation',
    summary:
      'Dense medical language becomes a plain-language summary, editable by staff before it goes live.',
    detail: (
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">
        <p>
          For trials labelled <em>Match</em> or <em>Partial Match</em>, a second step
          generates a patient-friendly summary. Trial descriptions are often written in dense
          medical language — the summary strips that away and explains what the trial is
          testing, who it is for, and where it is taking place.
        </p>
        <p>
          Trials found not suitable are skipped at this stage. The editorial team can edit any
          generated summary before it goes live.
        </p>
      </div>
    ),
  },
  {
    number: 4,
    title: 'Publish & Review',
    summary:
      "Matches publish automatically; partial matches wait for a reviewer's final call, with a diff shown on any later update.",
    detail: (
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">
        <p>
          Trials classified as <em>Match</em> are approved automatically and published
          straight away. Trials classified as <em>Partial Match</em> land in a private review
          queue, where a reviewer from the Osteosarcoma Now Foundation reads the
          classification reason, checks the original trial data, and can edit any field before
          making a final call.
        </p>
        <p>
          The reviewer can approve a queued trial, which sends it live, or reject it, which
          removes it from the public database. When an already-published trial changes on
          ClinicalTrials.gov, purely administrative edits — dates, contact details, locations
          — are synced silently. Otherwise the trial is re-classified: a clear match stays
          published, while an uncertain one returns to the review queue with a diff showing
          exactly what changed.
        </p>
        <p className="text-gray-500">
          Nothing goes stale, and nothing slips through. Automation handles the clear cases;
          people decide everything uncertain.
        </p>
      </div>
    ),
  },
  {
    number: 5,
    title: 'Published',
    summary: 'Live in the public explorer — searchable by phase, location, age, and status.',
    detail: (
      <div className="space-y-3 text-sm leading-relaxed text-gray-600">
        <p>
          Once approved, a trial is immediately visible in the public trial explorer. Patients,
          families, and clinicians can search and filter by phase, location, age range, and
          recruitment status.
        </p>
        <p>
          Each trial page shows the plain-language summary alongside the official
          ClinicalTrials.gov data, with direct contact information and a link to the original
          registry entry.
        </p>
      </div>
    ),
  },
];

function LabelChip({ label }: { label: LabelKey }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold ${LABEL_CONFIG[label].chip}`}
    >
      {LABEL_CONFIG[label].text}
    </span>
  );
}

function ClassificationStep() {
  return (
    <div className="space-y-6 text-sm leading-relaxed text-gray-600">
      <p>
        For each new or updated trial, the model reads the full study record — title,
        conditions, eligibility criteria, phase, and more — and assigns one of three labels.
      </p>

      <dl className="space-y-2.5">
        {LABEL_KEYS.map((key) => (
          <div key={key} className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-4">
            <dt className="sm:w-32 sm:shrink-0">
              <LabelChip label={key} />
            </dt>
            <dd className="text-sm text-gray-500">{LABEL_CONFIG[key].desc}</dd>
          </div>
        ))}
      </dl>

      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Worked examples
        </p>
        {EXAMPLES.map((ex) => (
          <div key={ex.label} className="rounded border border-line bg-surface p-4">
            <div className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
              <p className="text-sm font-semibold leading-snug text-gray-900">{ex.title}</p>
              <span className="shrink-0">
                <LabelChip label={ex.label} />
              </span>
            </div>
            <p className="mt-1.5 text-sm text-gray-500">{ex.description}</p>
            <p className="mt-1.5 text-sm text-gray-600">
              <span className="font-semibold text-gray-900">Reasoning: </span>
              {ex.reason}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LandingPage() {
  useDocumentTitle('Clinical Trial Explorer');

  const [activeStep, setActiveStep] = useState<number | null>(null);

  const toggleStep = (n: number) => setActiveStep((prev) => (prev === n ? null : n));

  return (
    <div className="bg-white">
      {/* ── Hero ── */}
      <section className="border-b border-line">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center sm:py-20">
          {/*
            max-h rather than a fixed h: the logo is 5.6:1, so at this size it is
            wider than a phone screen. Both constraints being maxima lets the width
            bind on narrow viewports without squashing the aspect ratio.
          */}
          <img
            src="/osn-bardo-logo.png"
            alt="Osteosarcoma Now — managed by Bardo Foundation"
            className="mx-auto max-h-20 max-w-full"
          />
          <h1 className="mt-10 text-4xl font-bold leading-[1.15] tracking-tight text-gray-900">
            Osteosarcoma Clinical Trial Explorer
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-gray-500">
            An automated, AI-assisted pipeline that monitors ClinicalTrials.gov daily and
            surfaces relevant osteosarcoma trials — reviewed by humans before they reach
            patients.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/trials"
              className="rounded bg-brand-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              Browse Trials
            </Link>
            <a
              href="#how-it-works"
              className="rounded border border-line bg-white px-6 py-3 text-sm font-semibold text-brand-600 transition-colors hover:border-brand-200 hover:bg-brand-50"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      {/* ── Why this exists ── */}
      <section className="border-b border-line bg-surface">
        <div className="mx-auto max-w-4xl px-6 py-14">
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
            Why this exists
          </h2>
          <p className="mt-5 max-w-xl text-[1.75rem] font-bold leading-snug tracking-tight text-gray-900">
            A rare cancer, with trials nobody can keep up with.
          </p>

          <dl className="mt-10 grid gap-8 sm:grid-cols-3 sm:gap-0">
            {WHY_STATS.map(({ figure, figureColor, body }, i) => (
              <div
                key={figure}
                className={`sm:px-6 ${i === 0 ? 'sm:pl-0' : 'sm:border-l sm:border-line'}`}
              >
                <dt className={`text-3xl font-bold tracking-tight ${figureColor}`}>
                  {figure}
                </dt>
                <dd className="mt-2 text-sm leading-relaxed text-gray-500">{body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── Pipeline ── */}
      <section id="how-it-works" className="border-b border-line">
        <div className="mx-auto max-w-4xl px-6 py-14">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-600">
            How it works
          </p>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-gray-900">
            Five steps, every 24 hours
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Automated end to end, with a human checking anything uncertain. Select a step for
            the detail.
          </p>

          {/* Vertical timeline: the rail is drawn behind each step's numeral circle */}
          <ol className="mt-9">
            {PIPELINE_STEPS.map((step, i) => {
              const isOpen = activeStep === step.number;
              const isClassification = step.number === 2;
              const isLast = i === PIPELINE_STEPS.length - 1;

              return (
                <li key={step.number} className={`relative ${isLast ? '' : 'pb-8'}`}>
                  {!isLast && (
                    <span
                      aria-hidden
                      className="absolute bottom-2 left-[13px] top-8 w-px bg-line"
                    />
                  )}
                  <button
                    onClick={() => toggleStep(step.number)}
                    aria-expanded={isOpen}
                    className="group flex w-full items-start gap-4 text-left"
                  >
                    <span
                      className={`relative z-10 flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                        isOpen
                          ? 'bg-brand-600 text-white'
                          : 'bg-brand-50 text-brand-600 group-hover:bg-brand-100'
                      }`}
                    >
                      {step.number}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.9375rem] font-semibold text-gray-900 transition-colors group-hover:text-brand-700">
                        {step.title}
                      </span>
                      <span className="mt-1 block text-sm leading-relaxed text-gray-500">
                        {step.summary}
                      </span>
                    </span>
                    {/* The only thing signalling that a step opens, so it gets a
                        resting tint of its own rather than appearing on hover. */}
                    <svg
                      aria-hidden
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={`mt-1 h-4 w-4 shrink-0 transition-transform duration-200 ${
                        isOpen
                          ? 'rotate-180 text-brand-600'
                          : 'text-brand-400 group-hover:text-brand-600'
                      }`}
                    >
                      <path d="M4 6.5l4 4 4-4" />
                    </svg>
                  </button>

                  {/* The three labels stay visible on step 2 even when collapsed —
                      they are the shorthand for what the whole pipeline produces. */}
                  {isClassification && !isOpen && (
                    <div className="mt-3 flex flex-wrap gap-2 pl-10">
                      {LABEL_KEYS.map((key) => (
                        <LabelChip key={key} label={key} />
                      ))}
                    </div>
                  )}

                  {isOpen && (
                    <div className="pl-10 pt-4">
                      {isClassification ? (
                        <ClassificationStep />
                      ) : (
                        step.detail
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* ── Closing CTA ── */}
      <section className="bg-surface">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center">
          <h2 className="text-2xl font-bold tracking-tight text-gray-900">
            Find a trial that fits
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-gray-500">
            Every trial has been automatically screened for relevance, with uncertain cases
            reviewed by the editorial team.
          </p>
          <Link
            to="/trials"
            className="mt-8 inline-block rounded bg-brand-600 px-7 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Browse Trials
          </Link>
        </div>
      </section>
    </div>
  );
}
