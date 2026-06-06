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

/** Split a comma-joined location string into deduplicated trimmed parts. */
export function parseLocationList(value: string | null | undefined): string[] {
  if (!value) return [];
  const seen = new Set<string>();
  const result: string[] = [];
  for (const part of value.split(',')) {
    const trimmed = part.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      result.push(trimmed);
    }
  }
  return result;
}

/** Whether raw city/country values should be shown behind an expand control. */
export function isLocationVerbose(
  city: string | null | undefined,
  country: string | null | undefined,
): boolean {
  const cities = parseLocationList(city);
  const countries = parseLocationList(country);
  const combinedLength = (city?.length ?? 0) + (country?.length ?? 0);
  return !(cities.length <= 3 && countries.length <= 2 && combinedLength <= 80);
}

function formatCountryPart(countries: string[]): string {
  if (countries.length === 0) return '';
  if (countries.length <= 3) return countries.join(', ');
  return `${countries.slice(0, 2).join(', ')} +${countries.length - 2} more`;
}

function formatLocationCount(count: number): string {
  return count === 1 ? '1 location' : `${count} locations`;
}

/**
 * Compact display for comma-joined city/country strings from multi-site trials.
 * Short values are shown as-is; long lists collapse to country summary + location count.
 */
export function formatLocationSummary(
  city: string | null | undefined,
  country: string | null | undefined,
): string {
  const cities = parseLocationList(city);
  const countries = parseLocationList(country);

  if (cities.length === 0 && countries.length === 0) return '';

  const combinedLength = (city?.length ?? 0) + (country?.length ?? 0);
  const isShort = cities.length <= 3 && countries.length <= 2 && combinedLength <= 80;

  if (isShort) {
    return [city, country].filter(Boolean).join(', ');
  }

  const parts: string[] = [];
  if (countries.length > 0) {
    parts.push(formatCountryPart(countries));
  }
  if (cities.length > 0) {
    parts.push(formatLocationCount(cities.length));
  }

  return parts.join(' · ');
}
