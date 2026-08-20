import { useEffect, useState } from 'react';
import { approveTrial, getReviewQueue, getTrial, rejectTrial } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { TrialDetailView } from '../components/TrialDetailView';
import type { CustomEdits, TrialDetail, TrialListItem } from '../types';
import { getOverallStatusDisplay, groupStatuses } from '../utils/formatters';
import { useDocumentTitle } from '../utils/useDocumentTitle';

type AiFilter = '' | 'confident' | 'unsure' | 'reject';

export function ReviewQueuePage() {
  useDocumentTitle('Review Queue');

  const [queue, setQueue] = useState<TrialListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TrialDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  // Pipe-joined overall_status values, matching the GET /trials?overall_status syntax.
  // Empty string means "all". Filtering is client-side over the already-loaded queue.
  const [recruitingFilter, setRecruitingFilter] = useState<string>('');
  const [aiFilter, setAiFilter] = useState<AiFilter>('');

  useEffect(() => {
    getReviewQueue().then(setQueue).catch(console.error);
  }, []);

  useEffect(() => {
    let isCurrent = true;

    if (!selectedId) {
      setDetail(null);
      setLoadingDetail(false);
      return () => {
        isCurrent = false;
      };
    }

    setLoadingDetail(true);
    getTrial(selectedId)
      .then((trialDetail) => {
        if (isCurrent) {
          setDetail(trialDetail);
        }
      })
      .catch((error) => {
        if (isCurrent) {
          console.error(error);
        }
      })
      .finally(() => {
        if (isCurrent) {
          setLoadingDetail(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedId]);

  // Offer only the statuses the pending trials actually have, so the dropdown
  // never lists an option that returns nothing.
  const { groups: statusGroups, ungrouped: statusUngrouped } = groupStatuses(
    [...new Set(queue.map((t) => t.overall_status).filter((s): s is string => !!s))],
  );

  const filteredQueue = queue.filter((trial) => {
    if (recruitingFilter && !recruitingFilter.split('|').includes(trial.overall_status ?? '')) {
      return false;
    }
    if (aiFilter && trial.ai_relevance_label !== aiFilter) return false;
    return true;
  });

  async function handleApprove(reviewerNotes: string, edits: CustomEdits) {
    if (!selectedId) return;
    await approveTrial(selectedId, {
      reviewer_notes: reviewerNotes || undefined,
      ...edits,
    });
    setQueue((q) => q.filter((t) => t.nct_id !== selectedId));
    setSelectedId(null);
  }

  async function handleReject(reviewerNotes: string) {
    if (!selectedId) return;
    await rejectTrial(selectedId, {
      reviewer_notes: reviewerNotes || undefined,
    });
    setQueue((q) => q.filter((t) => t.nct_id !== selectedId));
    setSelectedId(null);
  }

  const isFiltered = recruitingFilter !== '' || aiFilter !== '';
  const countLabel = isFiltered
    ? `${filteredQueue.length} of ${queue.length} trial${queue.length !== 1 ? 's' : ''}`
    : `${queue.length} trial${queue.length !== 1 ? 's' : ''} pending`;

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-80 shrink-0 border-r bg-white flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h1 className="text-sm font-semibold text-gray-700">Review Queue</h1>
          <p className="text-xs text-gray-400">{countLabel}</p>
          <div className="mt-2 flex flex-col gap-1.5">
            <select
              value={recruitingFilter}
              onChange={(e) => setRecruitingFilter(e.target.value)}
              className="w-full text-xs border border-line rounded px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-brand-400"
            >
              <option value="">All recruiting statuses</option>
              {statusGroups.map((group) => (
                <optgroup key={group.key} label={group.label}>
                  <option value={group.statuses.join('|')}>All {group.label.toLowerCase()}</option>
                  {group.statuses.map((s) => (
                    <option key={s} value={s}>{getOverallStatusDisplay(s).label}</option>
                  ))}
                </optgroup>
              ))}
              {statusUngrouped.map((s) => (
                <option key={s} value={s}>{getOverallStatusDisplay(s).label}</option>
              ))}
            </select>
            <select
              value={aiFilter}
              onChange={(e) => setAiFilter(e.target.value as AiFilter)}
              className="w-full text-xs border border-line rounded px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-brand-400"
            >
              <option value="">All AI confidence levels</option>
              <option value="confident">Match</option>
              <option value="unsure">Partial Match</option>
              <option value="reject">Not Suitable</option>
            </select>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {filteredQueue.length === 0 ? (
            <p className="px-4 py-6 text-sm text-gray-400 text-center">
              {isFiltered ? 'No trials match the current filters.' : 'No trials pending review.'}
            </p>
          ) : (
            filteredQueue.map((trial) => (
              <button
                key={trial.nct_id}
                onClick={() => setSelectedId(trial.nct_id)}
                className={`w-full text-left px-4 py-3 border-b hover:bg-surface transition-colors ${
                  selectedId === trial.nct_id ? 'bg-brand-50 border-l-2 border-l-brand-500' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-gray-800 leading-snug line-clamp-2">
                    {trial.brief_title}
                  </p>
                  <IngestionEventBadge event={trial.ingestion_event} />
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {trial.phase ?? 'Phase unknown'}
                  {trial.last_update_post_date && ` · ${trial.last_update_post_date}`}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto">
        {loadingDetail && (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-gray-400">Loading…</p>
          </div>
        )}
        {!loadingDetail && !detail && (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-gray-400">Select a trial from the queue to review it.</p>
          </div>
        )}
        {!loadingDetail && detail && (
          <TrialDetailView
            trial={detail}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}
      </div>
    </div>
  );
}
