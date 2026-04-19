import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

const CLASSIFICATION_SYSTEM_PROMPT = `You are a clinical trial relevance evaluator for the Osteosarcoma Now Foundation.

Your task: determine whether a clinical trial from ClinicalTrials.gov should be included
in the Osteosarcoma Now patient-facing database.

CRITICAL PRINCIPLE: When uncertain, use "unsure" — do NOT reject. Osteosarcoma is
a rare cancer with very few treatment options. Missing a relevant trial is far worse
than including an irrelevant one. The editorial team will make the final decision.

## WHAT OSTEOSARCOMA IS

Osteosarcoma (also called osteogenic sarcoma) is a primary malignant bone tumour. It is
DISTINCT from the following — do NOT classify these as relevant unless osteosarcoma is
also explicitly included:
- Soft tissue sarcomas (leiomyosarcoma, liposarcoma, synovial sarcoma, rhabdomyosarcoma, etc.)
- Kaposi sarcoma — a vascular tumour caused by HHV-8 infection, unrelated to bone
- Carcinosarcoma (e.g. uterine or ovarian carcinosarcoma) — a carcinoma variant, NOT a bone tumour
- Ewing sarcoma and chondrosarcoma are related bone tumours and ARE eligible when listed
  alongside osteosarcoma or in bone sarcoma cohorts

## LABEL: "confident"

Use "confident" if ANY of these apply:
- Osteosarcoma or osteogenic sarcoma is named in conditions, title, or eligibility criteria
- It is a bone sarcoma trial where osteosarcoma is an eligible or named diagnosis
- It targets relapsed, refractory, metastatic, or newly diagnosed osteosarcoma
- It is a sarcoma or solid tumour trial where osteosarcoma patients are clearly eligible
  per the inclusion criteria (e.g. bone sarcoma, high-grade sarcoma, paediatric sarcoma)
- It is a Phase 1 open-enrolment trial where osteosarcoma patients could reasonably qualify
- It studies patient-reported outcomes, rehabilitation, exercise, mobility, prosthetics,
  pain management, survivorship, or quality of life in sarcoma patients — these are directly
  relevant to osteosarcoma patients, particularly those who have undergone limb-salvage
  surgery or amputation
- It explores new therapies potentially relevant to osteosarcoma: immunotherapy, targeted
  therapy, NK cell therapy, cellular therapy, precision medicine, chemotherapy combinations,
  or surgical approaches in bone or sarcoma populations

## LABEL: "unsure"

Use "unsure" if you are uncertain whether osteosarcoma patients could enrol. Examples:
- Broad solid tumour trial with no explicit sarcoma mention, but no explicit exclusion either
- Paediatric/AYA cancer trial that does not name specific tumour types
- Supportive care study where sarcoma eligibility is ambiguous
- Trial mentions "sarcoma" but it is unclear whether bone sarcoma is eligible

## LABEL: "reject"

Use "reject" only when you are confident the trial is irrelevant to osteosarcoma. Typical reasons:
- Names only cancer types unrelated to osteosarcoma (ovarian, breast, leukemia, prostate,
  glioma, etc.) and osteosarcoma is not listed as an eligible diagnosis
- Kaposi sarcoma only — this is a vascular tumour caused by HHV-8, completely unrelated
  to bone tumours or osteosarcoma
- Explicitly excludes bone sarcomas or osteosarcoma from eligibility criteria
- Carcinosarcoma of the uterus or ovary only — this is a carcinoma variant, not a bone tumour
- Broad cancer population (any advanced solid tumour) with no sarcoma-specific cohort and no
  indication osteosarcoma patients could enrol
- Unrelated metabolic, endocrine, neurological, or pain condition without a sarcoma population
- Soft tissue sarcoma trial that explicitly excludes bone sarcomas
- Trial is Withdrawn or Terminated

REJECT TRAPS — do NOT let these trick you into rejecting:
- "Sarcoma" alone does not mean bone sarcoma — check eligibility criteria carefully
- "Carcinosarcoma" is NOT osteosarcoma — reject unless osteosarcoma is also listed
- The word "bone" in "bone metastases from carcinoma" is NOT osteosarcoma
- A trial for soft tissue sarcoma without bone sarcoma eligibility → reject or unsure, not confident

## CONCRETE EXAMPLES

KEEP (confident):
- Trial evaluating mobility and physical functioning in sarcoma patients after limb-salvage
  surgery or amputation → directly relevant to osteosarcoma rehabilitation
- Trial for bone sarcoma patients investigating NK cell therapy → osteosarcoma is eligible
- Trial studying exercise and chemotherapy uptake in newly diagnosed paediatric/AYA sarcoma
  patients → population includes osteosarcoma

REJECT:
- Trial for advanced ovarian, fallopian tube, or primary peritoneal cancer restricted to
  female patients with those diagnoses → osteosarcoma not eligible; "carcinosarcoma"
  in the name is a common false-positive trap
- Trial that explicitly excludes sarcomas originating in bone, including osteosarcoma
- Trial for Kaposi sarcoma (blood vessel tumour, HHV-8 infection) → unrelated to bone cancer

## OUTPUT FORMAT

Return ONLY valid JSON:
{
  "label": "confident",
  "reason": "1-2 sentence justification referencing the specific eligibility or study focus",
  "matching_criteria": ["osteosarcoma_in_conditions"]
}

Valid matching_criteria tags:
- osteosarcoma_in_title
- osteosarcoma_in_conditions
- osteosarcoma_in_eligibility
- bone_sarcoma_eligible
- broad_sarcoma_trial
- pediatric_aya_eligible
- phase1_open_enrollment
- solid_tumor_with_sarcoma
- survivorship_rehabilitation
- none`;

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

const LABEL_CONFIG = {
  confident: {
    text: 'Confident',
    bg: 'bg-green-100',
    border: 'border-green-200',
    textColor: 'text-green-800',
    dot: 'bg-green-500',
    desc: 'Clearly relevant — osteosarcoma patients can enrol',
  },
  unsure: {
    text: 'Unsure',
    bg: 'bg-yellow-100',
    border: 'border-yellow-200',
    textColor: 'text-yellow-800',
    dot: 'bg-yellow-500',
    desc: 'Uncertain eligibility — sent to human review',
  },
  reject: {
    text: 'Reject',
    bg: 'bg-red-100',
    border: 'border-red-200',
    textColor: 'text-red-800',
    dot: 'bg-red-500',
    desc: 'Not relevant to osteosarcoma — filtered out',
  },
};

const PIPELINE_STEPS = [
  {
    number: 1,
    title: 'Automated Search',
    summary: 'Queries ClinicalTrials.gov every 24 hours',
    detail: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>
          Every 24 hours, the system queries the ClinicalTrials.gov API using a set of
          osteosarcoma-related search terms. It collects all matching trial IDs and their
          last-updated timestamps.
        </p>
        <p>
          Each result is compared against what's already in our database. Trials are
          categorised as <strong>new</strong> (never seen before),{' '}
          <strong>updated</strong> (data changed since last run), or{' '}
          <strong>already processed</strong> (no change, skip). This means the system
          catches both newly registered trials and updates to existing ones — nothing slips
          through.
        </p>
      </div>
    ),
  },
  {
    number: 2,
    title: 'AI Classification',
    summary: 'An AI model reads each trial and assigns a relevance label',
    detail: null, // rendered separately
  },
  {
    number: 3,
    title: 'AI Summarisation',
    summary: 'Generates a plain-language summary for patients and families',
    detail: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>
          For trials labelled <strong>confident</strong> or <strong>unsure</strong>, a
          second AI step generates a patient-friendly summary. Clinical trial descriptions
          are often written in dense medical language — the summary strips that away and
          explains what the trial is testing, who it's for, and where it's taking place.
        </p>
        <p>
          Rejected trials are skipped entirely at this stage to save time and cost. The
          editorial team can also edit any AI-generated summary before it goes live.
        </p>
      </div>
    ),
  },
  {
    number: 4,
    title: 'Human Review',
    summary: 'Editorial team at Osteosarcoma Now checks every trial',
    detail: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>
          Every trial classified as <strong>confident</strong> or <strong>unsure</strong>{' '}
          lands in a private review queue. A human reviewer from the Osteosarcoma Now
          Foundation reads the AI's classification reason, checks the original trial data,
          and can edit any field before making a final call.
        </p>
        <p>
          The reviewer can <strong>approve</strong> the trial (it goes live), or{' '}
          <strong>reject</strong> it (it's removed from the public database). If a
          previously approved trial is updated on ClinicalTrials.gov, it automatically
          re-enters the review queue with a diff showing exactly what changed.
        </p>
        <p className="text-gray-500 italic">
          AI is the first pass. Humans make the final call.
        </p>
      </div>
    ),
  },
  {
    number: 5,
    title: 'Published',
    summary: 'Approved trials appear in the public database',
    detail: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>
          Once approved, a trial is immediately visible in the public trial explorer.
          Patients, families, and clinicians can search and filter by phase, location, age
          range, and status.
        </p>
        <p>
          Each trial page shows the AI-generated plain-language summary alongside the
          official ClinicalTrials.gov data, with direct contact information and a link to
          the original registry entry.
        </p>
      </div>
    ),
  },
];

function LabelBadge({ label }: { label: keyof typeof LABEL_CONFIG }) {
  const cfg = LABEL_CONFIG[label];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.textColor} border ${cfg.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.text}
    </span>
  );
}

function ClassificationStep({ onShowPrompt }: { onShowPrompt: () => void }) {
  return (
    <div className="space-y-6 text-sm text-gray-600">
      <p>
        For each new or updated trial, Claude AI reads the full study record — title,
        conditions, eligibility criteria, phase, and more — and assigns one of three
        labels:
      </p>

      <div className="grid gap-3 sm:grid-cols-3">
        {(Object.keys(LABEL_CONFIG) as (keyof typeof LABEL_CONFIG)[]).map((key) => {
          const cfg = LABEL_CONFIG[key];
          return (
            <div
              key={key}
              className={`rounded-lg border p-3 ${cfg.bg} ${cfg.border}`}
            >
              <LabelBadge label={key} />
              <p className={`mt-2 text-xs ${cfg.textColor}`}>{cfg.desc}</p>
            </div>
          );
        })}
      </div>

      <div>
        <p className="font-medium text-gray-700 mb-3">
          How might the AI classify these three trials?
        </p>
        <div className="space-y-3">
          {EXAMPLES.map((ex) => (
            <div
              key={ex.label}
              className="rounded-lg border border-gray-200 bg-white p-4 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium text-gray-900 text-sm leading-snug">{ex.title}</p>
                <LabelBadge label={ex.label} />
              </div>
              <p className="text-xs text-gray-500">{ex.description}</p>
              <p className="text-xs text-gray-600">
                <span className="font-medium">AI reasoning:</span> {ex.reason}
              </p>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={onShowPrompt}
        className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
      >
        <span>See exactly what the AI is asked</span>
        <span aria-hidden>→</span>
      </button>
    </div>
  );
}

function PromptModal({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousFocusedElement = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) {
        return;
      }

      const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );

      if (focusableElements.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocusedElement?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      aria-hidden="true"
    >
      <div
        ref={dialogRef}
        className="relative bg-gray-900 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-system-prompt-title"
        aria-describedby="ai-system-prompt-description"
        tabIndex={-1}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div>
            <p id="ai-system-prompt-title" className="text-sm font-semibold text-white">
              AI System Prompt
            </p>
            <p id="ai-system-prompt-description" className="text-xs text-gray-400 mt-0.5">
              Sent to the AI classification system before every trial classification
            </p>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-5">
          <pre className="text-xs font-mono text-green-300 whitespace-pre-wrap leading-relaxed">
            {CLASSIFICATION_SYSTEM_PROMPT}
          </pre>
        </div>
      </div>
    </div>
  );
}

export function LandingPage() {
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  const toggleStep = (n: number) => setActiveStep((prev) => (prev === n ? null : n));

  return (
    <div className="bg-gray-50">
      {showPrompt && <PromptModal onClose={() => setShowPrompt(false)} />}

      {/* ── Hero ── */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-6 py-20 text-center">
          <div className="flex items-center justify-center gap-8 mb-10">
            <img src="/bardo-logo.png" alt="The Bardo Foundation" className="h-16 w-auto" />
            <div className="w-px h-12 bg-gray-200" />
            <img src="/osteosarcoma-logo.png" alt="Osteosarcoma Now" className="h-16 w-auto" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight mb-4">
            Osteosarcoma Clinical Trial Explorer
          </h1>
          <p className="text-lg text-gray-500 max-w-xl mx-auto mb-8">
            An automated, AI-assisted pipeline that monitors ClinicalTrials.gov daily and
            surfaces relevant osteosarcoma trials — reviewed by humans before they reach
            patients.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              to="/trials"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
            >
              Browse Trials
            </Link>
            <a
              href="#how-it-works"
              className="px-6 py-3 bg-white text-gray-700 border border-gray-300 rounded-lg text-sm font-semibold hover:bg-gray-50 transition-colors"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      {/* ── Why section ── */}
      <section className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Why this exists</h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {[
            {
              heading: 'A rare cancer',
              body: 'Osteosarcoma affects roughly 1,000 people in the US each year, primarily children and teenagers. It is the most common primary bone cancer.',
            },
            {
              heading: 'Few options',
              body: 'Treatment has changed little in decades. Clinical trials often represent the best — sometimes only — path to newer therapies. Knowing they exist matters.',
            },
            {
              heading: 'An overwhelming search',
              body: 'ClinicalTrials.gov lists hundreds of thousands of studies. Finding the ones that actually apply to osteosarcoma, and keeping that list current, is a full-time job.',
            },
          ].map(({ heading, body }) => (
            <div key={heading} className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="font-semibold text-gray-900 mb-2">{heading}</p>
              <p className="text-sm text-gray-500 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pipeline ── */}
      <section id="how-it-works" className="max-w-3xl mx-auto px-6 pb-16">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">How it works</h2>
        <p className="text-sm text-gray-500 mb-8">
          Click any step to see what happens under the hood.
        </p>

        <div className="space-y-3">
          {PIPELINE_STEPS.map((step) => {
            const isOpen = activeStep === step.number;
            const isAI = step.number === 2;

            return (
              <div
                key={step.number}
                className={`bg-white rounded-xl border transition-all ${
                  isOpen ? 'border-blue-200 shadow-sm' : 'border-gray-200'
                }`}
              >
                <button
                  onClick={() => toggleStep(step.number)}
                  className="w-full flex items-center gap-4 px-5 py-4 text-left"
                >
                  <span
                    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                      isOpen
                        ? 'bg-blue-600 text-white'
                        : 'bg-blue-50 text-blue-600'
                    }`}
                  >
                    {step.number}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 text-sm">{step.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{step.summary}</p>
                  </div>
                  <span
                    className={`text-gray-400 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  >
                    ▾
                  </span>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pt-1 border-t border-gray-100">
                    {isAI ? (
                      <ClassificationStep onShowPrompt={() => setShowPrompt(true)} />
                    ) : (
                      step.detail
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Automation callout ── */}
        <div className="mt-8 rounded-xl bg-blue-50 border border-blue-100 px-6 py-5 flex gap-4 items-start">
          <span className="text-2xl">⏱</span>
          <div>
            <p className="font-semibold text-blue-900 text-sm">Runs automatically every 24 hours</p>
            <p className="text-sm text-blue-700 mt-1">
              When a trial is updated on ClinicalTrials.gov, it is re-fetched, re-classified,
              and sent back through human review — with a diff showing exactly what changed.
              Nothing slips through, and no trial is ever silently outdated.
            </p>
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="border-t border-gray-200 bg-white">
        <div className="max-w-3xl mx-auto px-6 py-16 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Find a trial that fits
          </h2>
          <p className="text-sm text-gray-500 mb-8 max-w-md mx-auto">
            Every trial in this database has been automatically screened and manually
            reviewed for relevance to osteosarcoma.
          </p>
          <Link
            to="/trials"
            className="px-8 py-3 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
          >
            Browse Trials
          </Link>
        </div>
      </section>
    </div>
  );
}
