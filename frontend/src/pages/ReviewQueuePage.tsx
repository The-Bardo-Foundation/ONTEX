import { useEffect, useState } from 'react';
import { approveTrial, getReviewQueue, getTrial, rejectTrial } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { TrialDetailView } from '../components/TrialDetailView';
import type { CustomEdits, TrialDetail, TrialListItem } from '../types';

const RECRUITING_NOW = ['RECRUITING'];
const NOT_RECRUITING = ['NOT_YET_RECRUITING', 'ACTIVE_NOT_RECRUITING', 'ENROLLING_BY_INVITATION'];
const FINISHED = ['COMPLETED', 'TERMINATED', 'WITHDRAWN', 'SUSPENDED'];

type RecruitingFilter = '' | 'recruiting' | 'not_recruiting' | 'finished';
type AiFilter = '' | 'confident' | 'unsure' | 'reject';

export function ReviewQueuePage() {

  const [queue, setQueue] = useState<TrialListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TrialDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [recruitingFilter, setRecruitingFilter] = useState<RecruitingFilter>('');
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

  const filteredQueue = queue.filter((trial) => {
    if (recruitingFilter) {
      const status = trial.overall_status ?? '';
      if (recruitingFilter === 'recruiting' && !RECRUITING_NOW.includes(status)) return false;
      if (recruitingFilter === 'not_recruiting' && !NOT_RECRUITING.includes(status)) return false;
      if (recruitingFilter === 'finished' && !FINISHED.includes(status)) return false;
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
              onChange={(e) => setRecruitingFilter(e.target.value as RecruitingFilter)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            >
              <option value="">All recruiting statuses</option>
              <option value="recruiting">Recruiting</option>
              <option value="not_recruiting">Not recruiting</option>
              <option value="finished">Finished</option>
            </select>
            <select
              value={aiFilter}
              onChange={(e) => setAiFilter(e.target.value as AiFilter)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            >
              <option value="">All AI confidence levels</option>
              <option value="confident">Confident</option>
              <option value="unsure">Unsure</option>
              <option value="reject">Reject</option>
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
                className={`w-full text-left px-4 py-3 border-b hover:bg-gray-50 transition-colors ${
                  selectedId === trial.nct_id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
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
