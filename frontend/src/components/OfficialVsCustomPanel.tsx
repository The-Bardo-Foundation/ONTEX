import { useState } from 'react';
import type { CustomEdits, TrialDetail } from '../types';

interface Field {
  label: string;
  officialKey: keyof TrialDetail;
  customKey: keyof CustomEdits;
  multiline?: boolean;
}

const FIELDS: Field[] = [
  { label: 'Brief Summary', officialKey: 'brief_summary', customKey: 'custom_brief_summary', multiline: true },
  { label: 'Overall Status', officialKey: 'overall_status', customKey: 'custom_overall_status' },
  { label: 'Phase', officialKey: 'phase', customKey: 'custom_phase' },
  { label: 'Eligibility Criteria', officialKey: 'eligibility_criteria', customKey: 'custom_eligibility_criteria', multiline: true },
  { label: 'Intervention', officialKey: 'intervention_description', customKey: 'custom_intervention_description', multiline: true },
];

interface Props {
  trial: TrialDetail;
  edits: CustomEdits;
  onChange?: (field: keyof CustomEdits, value: string) => void;
}

/** Read-only public view: shows the curated (custom) value prominently, with the official source behind a toggle. */
function PublicFieldRow({ label, officialVal, customVal }: { label: string; officialVal: string | null; customVal: string | null }) {
  const [showSource, setShowSource] = useState(false);
  const displayVal = customVal || officialVal;

  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      {displayVal ? (
        <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{displayVal}</p>
      ) : (
        <p className="text-sm text-gray-400 italic">Not provided</p>
      )}
      {officialVal && (
        <div className="mt-1">
          <button
            onClick={() => setShowSource((s) => !s)}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            {showSource ? 'Hide source' : 'View source (ClinicalTrials.gov)'}
          </button>
          {showSource && (
            <div className="mt-2 rounded border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
              {officialVal}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function OfficialVsCustomPanel({ trial, edits, onChange }: Props) {
  // Admin edit mode: retain the original side-by-side comparison layout
  if (onChange) {
    return (
      <div className="space-y-4">
        {FIELDS.map(({ label, officialKey, customKey, multiline }) => {
          const officialVal = trial[officialKey] as string | null;
          const customVal = edits[customKey] !== undefined ? edits[customKey] : (trial[customKey as keyof TrialDetail] as string | null) ?? '';

          return (
            <div key={label}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700 whitespace-pre-wrap min-h-[48px]">
                  {officialVal || <span className="text-gray-400 italic">Not provided</span>}
                </div>
                {multiline ? (
                  <textarea
                    className="rounded border border-gray-300 p-2 text-xs text-gray-900 resize-y min-h-[48px] focus:outline-none focus:ring-2 focus:ring-blue-400"
                    value={customVal ?? ''}
                    onChange={(e) => onChange(customKey, e.target.value)}
                    placeholder="Edit custom value…"
                  />
                ) : (
                  <input
                    type="text"
                    className="rounded border border-gray-300 p-2 text-xs text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    value={customVal ?? ''}
                    onChange={(e) => onChange(customKey, e.target.value)}
                    placeholder="Edit custom value…"
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Public read-only mode: curated value front and centre, source behind a toggle
  return (
    <div className="space-y-6">
      {FIELDS.map(({ label, officialKey, customKey }) => {
        const officialVal = trial[officialKey] as string | null;
        const customVal = (trial[customKey as keyof TrialDetail] as string | null);
        return (
          <PublicFieldRow
            key={label}
            label={label}
            officialVal={officialVal}
            customVal={customVal}
          />
        );
      })}
    </div>
  );
}
