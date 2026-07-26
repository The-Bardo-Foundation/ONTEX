import { Link } from 'react-router-dom';

/*
 * The three framing facts, shown as figures rather than prose. The colour is
 * per-stat on purpose: brand blue for the patient count, accent olive for the
 * stalled-treatment point, near-black for the registry size — one accent each,
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
    figure: 'Decades',
    figureColor: 'text-accent-700',
    body: (
      <>
        since standard treatment last changed. Trials are often the only path to something
        newer.
      </>
    ),
  },
  {
    figure: '300k+',
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

/*
 * The three classification labels, shown as chips under pipeline step 2. Soft
 * tints rather than saturated pills — these are not the semantic recruitment-status
 * badges in `utils/formatters.ts`, which stay green/yellow/red.
 */
const CLASSIFICATION_CHIPS = [
  { text: 'Match', className: 'bg-accent-50 text-accent-800' },
  { text: 'Partial Match', className: 'bg-brand-50 text-brand-600' },
  { text: 'Not Suitable', className: 'bg-surface-muted text-gray-600' },
];

const PIPELINE_STEPS = [
  {
    number: 1,
    title: 'Automated Search',
    summary:
      'Queries ClinicalTrials.gov every 24 hours and sorts results into new, updated, or unchanged.',
  },
  {
    number: 2,
    title: 'AI Classification',
    summary: 'Each trial is read in full and assigned one of three labels.',
  },
  {
    number: 3,
    title: 'AI Summarisation',
    summary:
      'Dense medical language becomes a plain-language summary, editable by staff before it goes live.',
  },
  {
    number: 4,
    title: 'Publish & Review',
    summary:
      "Matches publish automatically; partial matches wait for a reviewer's final call, with a diff shown on any later update.",
  },
  {
    number: 5,
    title: 'Published',
    summary: 'Live in the public explorer — searchable by phase, location, age, and status.',
  },
];

// Step 2 is the stage the page is really explaining, so its numeral is filled.
const EMPHASISED_STEP = 2;

export function LandingPage() {
  return (
    <div className="bg-white">
      {/* ── Hero ── */}
      <section className="border-b border-line">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center sm:py-20">
          <img
            src="/osn-bardo-logo.png"
            alt="Osteosarcoma Now — managed by Bardo Foundation"
            className="mx-auto h-14 w-auto"
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
            A rare cancer, treated the same way for decades — with trials nobody can keep up
            with.
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
            Automated end to end, with a human checking anything uncertain.
          </p>

          {/* Vertical timeline: the rail is drawn behind each step's numeral circle */}
          <ol className="mt-9">
            {PIPELINE_STEPS.map((step, i) => {
              const isEmphasised = step.number === EMPHASISED_STEP;
              const isLast = i === PIPELINE_STEPS.length - 1;

              return (
                <li key={step.number} className={`relative ${isLast ? '' : 'pb-8'}`}>
                  {!isLast && (
                    <span
                      aria-hidden
                      className="absolute bottom-2 left-[13px] top-8 w-px bg-line"
                    />
                  )}
                  <div className="flex items-start gap-4">
                    <span
                      className={`relative z-10 flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                        isEmphasised ? 'bg-brand-600 text-white' : 'bg-brand-50 text-brand-600'
                      }`}
                    >
                      {step.number}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[0.9375rem] font-semibold text-gray-900">
                        {step.title}
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-gray-500">
                        {step.summary}
                      </p>
                      {isEmphasised && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {CLASSIFICATION_CHIPS.map(({ text, className }) => (
                            <span
                              key={text}
                              className={`rounded px-2.5 py-1 text-xs font-semibold ${className}`}
                            >
                              {text}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
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
