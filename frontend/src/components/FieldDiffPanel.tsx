import type { TrialDetail } from '../types';

const FIELD_LABELS: Partial<Record<keyof TrialDetail, string>> = {
  brief_title: 'Brief Title',
  brief_summary: 'Brief Summary',
  overall_status: 'Overall Status',
  phase: 'Phase',
  study_type: 'Study Type',
  location_country: 'Country',
  location_city: 'City',
  minimum_age: 'Minimum Age',
  maximum_age: 'Maximum Age',
  eligibility_criteria: 'Eligibility Criteria',
  intervention_description: 'Intervention Description',
  last_update_post_date: 'Last Updated',
};

export function FieldDiffPanel({ trial }: { trial: TrialDetail }) {
  if (trial.ingestion_event !== 'UPDATED' || !trial.previous_official_snapshot) return null;

  const snapshot: Partial<TrialDetail> = JSON.parse(trial.previous_official_snapshot);

  const changedFields = (Object.keys(FIELD_LABELS) as (keyof TrialDetail)[]).filter((field) => {
    const oldVal = snapshot[field as keyof typeof snapshot];
    const newVal = trial[field];
    return oldVal !== newVal && (oldVal || newVal);
  });

  if (changedFields.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Changes since last approved version
      </h3>
      <div className="space-y-3">
        {changedFields.map((field) => {
          const oldVal = snapshot[field as keyof typeof snapshot] as string | null;
          const newVal = trial[field] as string | null;
          return (
            <div key={field}>
              <p className="text-xs font-medium text-gray-500 mb-1">{FIELD_LABELS[field]}</p>
              {oldVal && (
                <p className="text-xs bg-red-50 border border-red-200 rounded p-2 text-red-700 line-through mb-1">
                  {oldVal}
                </p>
              )}
              {newVal && (
                <p className="text-xs bg-green-50 border border-green-200 rounded p-2 text-green-700">
                  {newVal}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
