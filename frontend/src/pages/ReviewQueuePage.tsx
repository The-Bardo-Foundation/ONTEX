import { useEffect, useState } from 'react';
import { useUser } from '@clerk/clerk-react';
import { approveTrial, getReviewQueue, getTrial, rejectTrial } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { TrialDetailView } from '../components/TrialDetailView';
import type { CustomEdits, TrialDetail, TrialListItem } from '../types';

export function ReviewQueuePage() {
  const { user } = useUser();
  const reviewerUsername =
    user?.primaryEmailAddress?.emailAddress ?? user?.username ?? 'admin';

  const [queue, setQueue] = useState<TrialListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TrialDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

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

  async function handleApprove(reviewerNotes: string, edits: CustomEdits) {
    if (!selectedId) return;
    await approveTrial(selectedId, {
      username: reviewerUsername,
      reviewer_notes: reviewerNotes || undefined,
      ...edits,
    });
    setQueue((q) => q.filter((t) => t.nct_id !== selectedId));
    setSelectedId(null);
  }

  async function handleReject(reviewerNotes: string) {
    if (!selectedId) return;
    await rejectTrial(selectedId, {
      username: reviewerUsername,
      reviewer_notes: reviewerNotes || undefined,
    });
    setQueue((q) => q.filter((t) => t.nct_id !== selectedId));
    setSelectedId(null);
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-80 shrink-0 border-r bg-white flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h1 className="text-sm font-semibold text-gray-700">Review Queue</h1>
          <p className="text-xs text-gray-400">{queue.length} trial{queue.length !== 1 ? 's' : ''} pending</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {queue.length === 0 ? (
            <p className="px-4 py-6 text-sm text-gray-400 text-center">No trials pending review.</p>
          ) : (
            queue.map((trial) => (
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
