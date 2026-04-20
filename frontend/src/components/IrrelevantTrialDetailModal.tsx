import { useEffect, useState } from 'react';
import { getIrrelevantTrial, restoreIrrelevantTrial } from '../api';
import type { IrrelevantTrialDetail } from '../types';
import { formatPhase, getOverallStatusDisplay } from '../utils/formatters';

interface Props {
  nctId: string;
  onClose: () => void;
  onRestored: (nctId: string) => void;
}

export function IrrelevantTrialDetailModal({ nctId, onClose, onRestored }: Props) {
  const [trial, setTrial] = useState<IrrelevantTrialDetail | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getIrrelevantTrial(nctId).then(setTrial).catch(() => setError('Failed to load trial.'));
  }, [nctId]);

  async function handleRestore() {
    setRestoring(true);
    setError(null);
    try {
      await restoreIrrelevantTrial(nctId);
      onRestored(nctId);
      onClose();
    } catch {
      setError('Failed to restore trial. Please try again.');
      setRestoring(false);
    }
  }

  const title = trial?.custom_brief_title || trial?.brief_title || '';
  const summary = trial?.custom_brief_summary || trial?.brief_summary;
  const status = trial?.custom_overall_status || trial?.overall_status;
  const phase = trial?.custom_phase || trial?.phase;
  const statusLabel = status ? getOverallStatusDisplay(status).label : null;

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      {/* Backdrop */}
      <div className="flex-1 bg-black/30" />

      {/* Panel */}
      <div
        className="w-full max-w-2xl bg-white shadow-xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-6 py-4 border-b shrink-0">
          <h2 className="text-base font-semibold text-gray-900 leading-snug">
            {title || <span className="text-gray-400">Loading…</span>}
          </h2>
          <button
            onClick={onClose}
            className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {!trial && !error && (
            <p className="text-sm text-gray-400">Loading…</p>
          )}

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}

          {trial && (
            <>
              {/* Irrelevance reason */}
              {trial.irrelevance_reason && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-1">
                    Marked irrelevant
                  </p>
                  <p className="text-sm text-amber-800">{trial.irrelevance_reason}</p>
                </div>
              )}

              {/* Metadata chips */}
              <div className="flex flex-wrap gap-2">
                {phase && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
                    {formatPhase(phase)}
                  </span>
                )}
                {statusLabel && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    {statusLabel}
                  </span>
                )}
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 font-mono">
                  {trial.nct_id}
                </span>
                {trial.last_update_post_date && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                    Updated {trial.last_update_post_date}
                  </span>
                )}
              </div>

              {/* Summary */}
              {summary && (
                <p className="text-sm text-gray-600 leading-relaxed">{summary}</p>
              )}

              {/* ClinicalTrials.gov link */}
              <p className="text-xs text-gray-400">
                <a
                  href={`https://clinicaltrials.gov/study/${trial.nct_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-gray-600"
                >
                  View on ClinicalTrials.gov
                </a>
              </p>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t px-6 py-4 flex items-center justify-between gap-3 bg-white">
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex gap-3 ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
            >
              Close
            </button>
            <button
              onClick={handleRestore}
              disabled={restoring || !trial}
              className="px-4 py-2 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {restoring ? 'Restoring…' : 'Restore to Review Queue'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
