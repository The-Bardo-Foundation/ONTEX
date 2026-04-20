import type { TrialDetail } from '../types';

const LABEL_STYLES: Record<string, string> = {
  confident: 'bg-green-100 text-green-800',
  unsure: 'bg-yellow-100 text-yellow-800',
  reject: 'bg-red-100 text-red-800',
};

const BORDER_ACCENT: Record<string, string> = {
  confident: 'border-l-green-400',
  unsure: 'border-l-yellow-400',
  reject: 'border-l-red-400',
};

export function AiClassificationCard({ trial }: { trial: TrialDetail }) {
  const { ai_relevance_label, ai_relevance_reason } = trial;

  if (ai_relevance_label === null && !ai_relevance_reason) return null;

  const labelStyle = ai_relevance_label ? (LABEL_STYLES[ai_relevance_label] ?? 'bg-gray-100 text-gray-700') : null;
  const borderAccent = ai_relevance_label ? (BORDER_ACCENT[ai_relevance_label] ?? 'border-l-gray-300') : 'border-l-gray-300';

  return (
    <div className={`rounded-lg border border-l-4 p-4 bg-gray-50 border-gray-200 ${borderAccent}`}>
      <div className="flex items-center gap-1.5 mb-2">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-indigo-400 shrink-0" aria-hidden="true">
          <path d="M7 0L8.5 5.5L14 7L8.5 8.5L7 14L5.5 8.5L0 7L5.5 5.5L7 0Z" fill="currentColor" />
        </svg>
        <h3 className="text-sm font-semibold text-gray-700">AI Classification</h3>
      </div>

      <hr className="border-gray-200 mb-3" />

      {ai_relevance_label && labelStyle && (
        <div className="mb-3">
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${labelStyle}`}>
            {ai_relevance_label}
          </span>
        </div>
      )}

      {ai_relevance_reason && (
        <p className="text-sm text-gray-700">{ai_relevance_reason}</p>
      )}
    </div>
  );
}
