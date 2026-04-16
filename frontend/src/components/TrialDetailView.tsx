import { useState } from 'react';
import type { CustomEdits, TrialDetail } from '../types';
import { AiClassificationCard } from './AiClassificationCard';
import { FieldDiffPanel } from './FieldDiffPanel';
import { IngestionEventBadge } from './IngestionEventBadge';
import { OfficialVsCustomPanel } from './OfficialVsCustomPanel';
import { StatusBadge } from './StatusBadge';

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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-1">
          <h1 className="text-lg font-semibold text-gray-900 leading-snug">
            {trial.brief_title}
          </h1>
          <div className="flex items-center gap-2 shrink-0">
            <IngestionEventBadge event={trial.ingestion_event} />
            <StatusBadge status={trial.status} />
          </div>
        </div>
        <p className="text-sm text-gray-500">
          {trial.nct_id}
          {trial.phase && <> · {trial.phase}</>}
          {trial.last_update_post_date && <> · Updated {trial.last_update_post_date}</>}
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

      {/* Official vs Custom fields */}
      <section>
        <div className="grid grid-cols-2 gap-3 mb-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Official (ClinicalTrials.gov)</p>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Custom (AI / Admin)</p>
        </div>
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
