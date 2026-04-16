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

export function OfficialVsCustomPanel({ trial, edits, onChange }: Props) {
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
              {onChange ? (
                multiline ? (
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
                )
              ) : (
                <div className="rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700 whitespace-pre-wrap min-h-[48px]">
                  {customVal || <span className="text-gray-400 italic">Not provided</span>}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
