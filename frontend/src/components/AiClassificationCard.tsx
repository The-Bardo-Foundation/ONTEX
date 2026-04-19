import type { TrialDetail } from '../types';

const LABEL_STYLES: Record<string, string> = {
  confident: 'bg-green-100 text-green-800',
  unsure: 'bg-yellow-100 text-yellow-800',
  reject: 'bg-red-100 text-red-800',
};

export function AiClassificationCard({ trial }: { trial: TrialDetail }) {
  const { ai_relevance_label, ai_relevance_reason, ai_matching_criteria } = trial;

  if (ai_relevance_label === null && !ai_relevance_reason) return null;

  const criteria: string[] = ai_matching_criteria ? JSON.parse(ai_matching_criteria) : [];
  const labelStyle = ai_relevance_label ? (LABEL_STYLES[ai_relevance_label] ?? 'bg-gray-100 text-gray-700') : null;

  return (
    <div className="rounded-lg border p-4 bg-gray-50 border-gray-200">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">AI Classification</h3>

      {ai_relevance_label && labelStyle && (
        <div className="mb-3">
          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${labelStyle}`}>
            {ai_relevance_label}
          </span>
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
