import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth, useUser } from '@clerk/clerk-react';
import { approveTrial, getTrial, rejectTrial } from '../api';
import { TrialDetailView } from '../components/TrialDetailView';
import type { CustomEdits, TrialDetail } from '../types';

export function TrialDetailPage() {
  const { nct_id } = useParams<{ nct_id: string }>();
  const navigate = useNavigate();
  const { isSignedIn } = useAuth();
  const { user } = useUser();
  const [detail, setDetail] = useState<TrialDetail | null>(null);
  const [notFound, setNotFound] = useState(false);

  const reviewerUsername =
    user?.primaryEmailAddress?.emailAddress ?? user?.username ?? 'admin';

  useEffect(() => {
    if (!nct_id) return;
    getTrial(nct_id)
      .then(setDetail)
      .catch((err) => {
        if (err.response?.status === 404) setNotFound(true);
        else console.error(err);
      });
  }, [nct_id]);

  async function handleApprove(reviewerNotes: string, edits: CustomEdits) {
    if (!nct_id) return;
    const updated = await approveTrial(nct_id, {
      username: reviewerUsername,
      reviewer_notes: reviewerNotes || undefined,
      ...edits,
    });
    setDetail(updated);
  }

  async function handleReject(reviewerNotes: string) {
    if (!nct_id) return;
    const updated = await rejectTrial(nct_id, {
      username: reviewerUsername,
      reviewer_notes: reviewerNotes || undefined,
    });
    setDetail(updated);
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-gray-500">Trial not found.</p>
        <button onClick={() => navigate('/trials')} className="text-sm text-blue-600 hover:underline">
          Back to All Trials
        </button>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    );
  }

  const isPending = detail.status === 'PENDING_REVIEW';
  const canReview = isSignedIn && isPending;

  return (
    <div className="overflow-y-auto h-full">
      <TrialDetailView
        trial={detail}
        onApprove={canReview ? handleApprove : undefined}
        onReject={canReview ? handleReject : undefined}
      />
    </div>
  );
}
