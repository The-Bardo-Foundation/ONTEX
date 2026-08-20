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
  // Expanded-access statuses. Rarer than the interventional ones above, but they
  // do occur in our search set and AGENT.md lists expanded access as eligible.
  AVAILABLE:                   { label: 'Available',                 className: 'bg-green-100 text-green-800' },
  TEMPORARILY_NOT_AVAILABLE:   { label: 'Temporarily not available',  className: 'bg-yellow-100 text-yellow-800' },
  NO_LONGER_AVAILABLE:         { label: 'No longer available',        className: 'bg-gray-100 text-gray-600' },
  APPROVED_FOR_MARKETING:      { label: 'Approved for marketing',     className: 'bg-gray-100 text-gray-600' },
  WITHHELD:                    { label: 'Withheld',                   className: 'bg-gray-100 text-gray-500' },
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

export interface StatusGroup {
  /** Stable key for React lists and expand/collapse state. */
  key: string;
  label: string;
  statuses: string[];
}

/**
 * Plain-English groupings of ClinicalTrials.gov statuses, used to organise the
 * recruiting-status filter into a two-level list.
 *
 * These are PRESENTATION ONLY. The API filters on individual `overall_status`
 * values (see GET /trials?overall_status=A|B), so a group is just a preset that
 * ticks its member statuses. Nothing is stored grouped, and a status missing
 * from every group here still gets its own filter option — see
 * groupStatuses(), which returns leftovers as `ungrouped`.
 *
 * Note the middle label: it deliberately names BOTH ends of the group. The
 * previous wording, "Not currently recruiting", read as "closed" and hid the
 * fact that not-yet-recruiting trials — which are still worth a referral —
 * were inside it.
 */
export const STATUS_GROUPS: StatusGroup[] = [
  {
    key: 'recruiting',
    label: 'Recruiting now',
    statuses: ['RECRUITING', 'AVAILABLE'],
  },
  {
    key: 'not_recruiting',
    label: 'Not recruiting yet or no longer recruiting',
    statuses: [
      'NOT_YET_RECRUITING',
      'ENROLLING_BY_INVITATION',
      'ACTIVE_NOT_RECRUITING',
      'TEMPORARILY_NOT_AVAILABLE',
    ],
  },
  {
    key: 'finished',
    label: 'Finished trials',
    statuses: [
      'COMPLETED',
      'TERMINATED',
      'WITHDRAWN',
      'SUSPENDED',
      'NO_LONGER_AVAILABLE',
      'APPROVED_FOR_MARKETING',
      // CT.gov's glossary is explicit: a study is UNKNOWN when its last known
      // status was recruiting/not yet recruiting/active-not-recruiting, it has
      // passed its completion date, and nobody has verified it in 2 years —
      // "Studies with an unknown status are considered closed studies."
      // https://clinicaltrials.gov/study-basics/glossary
      'UNKNOWN',
    ],
  },
];

/**
 * Distributes the statuses actually present in the database across STATUS_GROUPS,
 * dropping group members nothing has and collecting anything unrecognised.
 *
 * Callers render `groups` as parent/child options and `ungrouped` as standalone
 * ones, which guarantees every status in `available` stays reachable — including
 * values CT.gov may add after this code was written.
 */
export function groupStatuses(available: string[]): {
  groups: StatusGroup[];
  ungrouped: string[];
} {
  const present = new Set(available);
  const groups = STATUS_GROUPS
    .map((g) => ({ ...g, statuses: g.statuses.filter((s) => present.has(s)) }))
    .filter((g) => g.statuses.length > 0);

  const claimed = new Set(STATUS_GROUPS.flatMap((g) => g.statuses));
  return { groups, ungrouped: available.filter((s) => !claimed.has(s)) };
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
