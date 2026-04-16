import type { TrialDetail } from '../types';

export function AiClassificationCard({ trial }: { trial: TrialDetail }) {
  const { ai_relevance_confidence, ai_relevance_reason, ai_relevance_tier, ai_matching_criteria } = trial;

  if (ai_relevance_confidence === null && !ai_relevance_reason) return null;

  const criteria: string[] = ai_matching_criteria ? JSON.parse(ai_matching_criteria) : [];
  const pct = ai_relevance_confidence !== null ? Math.round(ai_relevance_confidence * 100) : null;

  const tierBg = ai_relevance_tier === 'primary' ? 'bg-blue-50 border-blue-200' : 'bg-yellow-50 border-yellow-200';

  return (
    <div className={`rounded-lg border p-4 ${tierBg}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">AI Classification</h3>
        {ai_relevance_tier && (
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            {ai_relevance_tier}
          </span>
        )}
      </div>

      {pct !== null && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>Confidence</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {criteria.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {criteria.map((c) => (
            <span key={c} className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs">
              {c.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {ai_relevance_reason && (
        <p className="text-xs text-gray-600">{ai_relevance_reason}</p>
      )}
    </div>
  );
}
