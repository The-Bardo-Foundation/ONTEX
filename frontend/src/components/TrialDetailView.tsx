import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { CustomEdits, TrialDetail } from '../types';
import { formatPhase, getOverallStatusDisplay } from '../utils/formatters';
import { AiClassificationCard } from './AiClassificationCard';
import { FieldDiffPanel } from './FieldDiffPanel';
import { IngestionEventBadge } from './IngestionEventBadge';
import { OfficialVsCustomPanel } from './OfficialVsCustomPanel';
import { StatusBadge } from './StatusBadge';

function InfoField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-900/60 mb-0.5">{label}</p>
      <div className="text-sm text-gray-800 leading-snug">{children}</div>
    </div>
  );
}

interface Props {
  trial: TrialDetail;
  onApprove?: (reviewerNotes: string, edits: CustomEdits) => Promise<void>;
  onReject?: (reviewerNotes: string) => Promise<void>;
}

export function TrialDetailView({ trial, onApprove, onReject }: Props) {
  const [edits, setEdits] = useState<CustomEdits>({});
  const [reviewerNotes, setReviewerNotes] = useState(trial.reviewer_notes ?? '');
  const [submitting, setSubmitting] = useState(false);

  function handleFieldChange(field: keyof CustomEdits, value: string) {
    setEdits((prev) => ({ ...prev, [field]: value }));
  }

  async function handleApprove() {
    if (!onApprove) return;
    setSubmitting(true);
    try {
      await onApprove(reviewerNotes, edits);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReject() {
    if (!onReject) return;
    setSubmitting(true);
    try {
      await onReject(reviewerNotes);
    } finally {
      setSubmitting(false);
    }
  }

  const showActions = Boolean(onApprove || onReject);
  const navigate = useNavigate();

  // ── Public view ────────────────────────────────────────────────────────────
  if (!showActions) {
    const title    = trial.custom_brief_title    || trial.brief_title;
    const summary  = trial.custom_brief_summary  || trial.brief_summary;
    const status   = trial.custom_overall_status || trial.overall_status;
    const phase    = trial.custom_phase          || trial.phase;
    const type     = trial.custom_study_type     || trial.study_type;
    const country  = trial.custom_location_country || trial.location_country;
    const city     = trial.custom_location_city  || trial.location_city;
    const minAge   = trial.custom_minimum_age    || trial.minimum_age;
    const maxAge   = trial.custom_maximum_age    || trial.maximum_age;
    const contact  = trial.custom_central_contact_name  || trial.central_contact_name;
    const phone    = trial.custom_central_contact_phone || trial.central_contact_phone;
    const email    = trial.custom_central_contact_email || trial.central_contact_email;
    const eligibility   = trial.custom_eligibility_criteria    || trial.eligibility_criteria;
    const intervention  = trial.custom_intervention_description || trial.intervention_description;
    const statusLabel   = status ? getOverallStatusDisplay(status).label : null;

    return (
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-7">
        {/* Back */}
        <button
          onClick={() => navigate('/trials')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          All trials
        </button>

        {/* Title */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900 leading-snug">{title}</h1>
          <p className="text-xs text-gray-400">
            {trial.nct_id}
            {trial.last_update_post_date && <> · Updated {trial.last_update_post_date}</>}
            {' · '}
            <a
              href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-600"
            >
              View on ClinicalTrials.gov
            </a>
          </p>
        </div>

        {/* Summary */}
        {summary && (
          <p className="text-base text-gray-600 leading-relaxed">{summary}</p>
        )}

        {/* Info box */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-10 gap-y-5">
            {/* Column 1 */}
            <div className="space-y-5">
              {country  && <InfoField label="Country">{country}</InfoField>}
              {city     && <InfoField label="Location">{city}</InfoField>}
              {type     && <InfoField label="Trial Type">{type}</InfoField>}
              {phase    && <InfoField label="Trial Phase">{formatPhase(phase)}</InfoField>}
            </div>

            {/* Column 2 */}
            <div className="space-y-5">
              {statusLabel && <InfoField label="Trial Status">{statusLabel}</InfoField>}
              {minAge && <InfoField label="Minimum Age">{minAge}</InfoField>}
              {maxAge && <InfoField label="Maximum Age">{maxAge}</InfoField>}
            </div>

            {/* Column 3 */}
            <div className="space-y-5">
              {(contact || phone || email) && (
                <InfoField label="Key Contact">
                  {contact && <p>{contact}</p>}
                  {phone   && <p className="text-gray-500">{phone}</p>}
                  {email   && (
                    <a href={`mailto:${email}`} className="text-blue-600 hover:underline break-all">
                      {email}
                    </a>
                  )}
                </InfoField>
              )}
              <InfoField label="Clinical Trial ID">
                <span className="font-mono">{trial.nct_id}</span>
              </InfoField>
            </div>
          </div>
        </div>

        {/* Key information (admin-curated free text) */}
        {trial.key_information && (
          <section className="space-y-2">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Key Information</h2>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{trial.key_information}</p>
          </section>
        )}

        {/* Eligibility criteria */}
        {eligibility && (
          <section className="space-y-2">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Eligibility Criteria</h2>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">{eligibility}</p>
          </section>
        )}

        {/* Interventions */}
        {intervention && (
          <section className="space-y-2">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Interventions</h2>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">{intervention}</p>
          </section>
        )}
      </div>
    );
  }

  // ── Admin view ─────────────────────────────────────────────────────────────
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <h1 className="text-xl font-semibold text-gray-900 leading-snug">
            {trial.brief_title}
          </h1>
          <div className="flex items-center gap-2 shrink-0">
            <IngestionEventBadge event={trial.ingestion_event} />
            <StatusBadge status={trial.status} />
          </div>
        </div>

        {/* Metadata chips */}
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {trial.phase && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
              {formatPhase(trial.phase)}
            </span>
          )}
          {trial.study_type && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              {trial.study_type}
            </span>
          )}
          {(trial.location_city || trial.location_country) && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {[trial.location_city, trial.location_country].filter(Boolean).join(', ')}
            </span>
          )}
          {(trial.minimum_age || trial.maximum_age) && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              Ages {[trial.minimum_age, trial.maximum_age].filter(Boolean).join(' – ')}
            </span>
          )}
        </div>

        <p className="text-xs text-gray-400">
          {trial.nct_id}
          {trial.last_update_post_date && <> · Updated {trial.last_update_post_date}</>}
          {' · '}
          <a
            href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-gray-600"
            onClick={(e) => e.stopPropagation()}
          >
            View on ClinicalTrials.gov
          </a>
        </p>

        {trial.ingestion_event === 'UPDATED' && trial.previous_approved_by && (
          <p className="text-xs text-gray-400 mt-1">
            Previously approved by {trial.previous_approved_by}
            {trial.previous_approved_at && ` on ${new Date(trial.previous_approved_at).toLocaleDateString()}`}
          </p>
        )}
      </div>

      {/* AI classification */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">AI Classification</h2>
        <AiClassificationCard trial={trial} />
      </section>

      {/* Diff panel — only for UPDATED trials */}
      {trial.ingestion_event === 'UPDATED' && <FieldDiffPanel trial={trial} />}

      {/* Trial details */}
      <section>
        {showActions && (
          <div className="grid grid-cols-2 gap-3 mb-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Official (ClinicalTrials.gov)</p>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Custom (AI / Admin)</p>
          </div>
        )}
        <OfficialVsCustomPanel trial={trial} edits={edits} onChange={showActions ? handleFieldChange : undefined} />
      </section>

      {/* Reviewer notes + action buttons */}
      {showActions && (
        <section className="sticky bottom-0 bg-white border-t pt-4 -mx-6 px-6 pb-2">
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">Reviewer notes (optional)</label>
            <textarea
              className="w-full border border-gray-300 rounded p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
              rows={2}
              placeholder="Add a note for the record…"
              value={reviewerNotes}
              onChange={(e) => setReviewerNotes(e.target.value)}
            />
          </div>
          <div className="flex gap-3 justify-end">
            {onReject && (
              <button
                onClick={handleReject}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                Reject
              </button>
            )}
            {onApprove && (
              <button
                onClick={handleApprove}
                disabled={submitting}
                className="px-4 py-2 text-sm font-medium rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
              >
                Approve
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
