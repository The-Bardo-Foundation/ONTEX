/**
 * Converts raw ClinicalTrials.gov phase strings to human-readable form.
 * Examples:
 *   "PHASE1"          → "Phase 1"
 *   "PHASE1_PHASE2"   → "Phase 1 / Phase 2"
 *   "EARLY_PHASE1"    → "Early Phase 1"
 *   "NA"              → "N/A"
 *   null              → "—"
 */
export function formatPhase(phase: string | null | undefined): string {
  if (!phase) return '—';
  if (phase === 'NA') return 'N/A';
  return phase
    .replace(/EARLY_PHASE(\d)/g, 'Early Phase $1')
    .replace(/PHASE(\d)/g, 'Phase $1')
    .replace(/_/g, ' / ');
}

interface StatusDisplay {
  label: string;
  className: string;
}

const OVERALL_STATUS_MAP: Record<string, StatusDisplay> = {
  RECRUITING:                  { label: 'Recruiting',               className: 'bg-green-100 text-green-800' },
  NOT_YET_RECRUITING:          { label: 'Not yet recruiting',        className: 'bg-yellow-100 text-yellow-800' },
  ACTIVE_NOT_RECRUITING:       { label: 'Active, not recruiting',    className: 'bg-blue-100 text-blue-800' },
  ENROLLING_BY_INVITATION:     { label: 'Enrolling by invitation',   className: 'bg-teal-100 text-teal-800' },
  COMPLETED:                   { label: 'Completed',                 className: 'bg-gray-100 text-gray-600' },
  SUSPENDED:                   { label: 'Suspended',                 className: 'bg-orange-100 text-orange-800' },
  TERMINATED:                  { label: 'Terminated',                className: 'bg-red-100 text-red-800' },
  WITHDRAWN:                   { label: 'Withdrawn',                 className: 'bg-red-100 text-red-800' },
  UNKNOWN:                     { label: 'Unknown',                   className: 'bg-gray-100 text-gray-500' },
};

/**
 * Returns a human-readable label and Tailwind classes for a ClinicalTrials.gov overall_status value.
 */
export function getOverallStatusDisplay(status: string | null | undefined): StatusDisplay {
  if (!status) return { label: '—', className: 'bg-gray-100 text-gray-400' };
  return OVERALL_STATUS_MAP[status.toUpperCase()] ?? {
    label: status.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()),
    className: 'bg-gray-100 text-gray-600',
  };
}
