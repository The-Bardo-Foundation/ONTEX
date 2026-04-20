import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { approveTrial, editTrial, getTrial, markTrialIrrelevant, rejectTrial } from '../api';
import { TrialDetailView } from '../components/TrialDetailView';
import type { CustomEdits, TrialDetail } from '../types';

export function TrialDetailPage() {
  const { nct_id } = useParams<{ nct_id: string }>();
  const navigate = useNavigate();
  const { isSignedIn } = useAuth();
  const [detail, setDetail] = useState<TrialDetail | null>(null);
  const [notFound, setNotFound] = useState(false);

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
      reviewer_notes: reviewerNotes || undefined,
      ...edits,
    });
    setDetail(updated);
  }

  async function handleReject(reviewerNotes: string) {
    if (!nct_id) return;
    await rejectTrial(nct_id, { reviewer_notes: reviewerNotes || undefined });
    navigate('/trials');
  }

  async function handleEdit(edits: CustomEdits) {
    if (!nct_id) return;
    const updated = await editTrial(nct_id, edits);
    setDetail(updated);
  }

  async function handleMarkIrrelevant(reason: string) {
    if (!nct_id) return;
    await markTrialIrrelevant(nct_id, { irrelevance_reason: reason || undefined });
    navigate('/admin/trials');
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
        onEdit={isSignedIn ? handleEdit : undefined}
        onMarkIrrelevant={isSignedIn ? handleMarkIrrelevant : undefined}
        adminMode={!!isSignedIn}
      />
    </div>
  );
}
