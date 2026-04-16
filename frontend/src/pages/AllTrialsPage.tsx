import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTrialFacets, getTrials } from '../api';
import type { GetTrialsParams, TrialFacets } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { StatusBadge } from '../components/StatusBadge';
import type { TrialListItem, TrialsListResponse } from '../types';
import { formatPhase, getOverallStatusDisplay } from '../utils/formatters';

const PAGE_SIZE = 20;

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'PENDING_REVIEW', label: 'Pending Review' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'REJECTED', label: 'Rejected' },
];

const EVENT_OPTIONS = [
  { value: '', label: 'All events' },
  { value: 'NEW', label: 'New' },
  { value: 'UPDATED', label: 'Updated' },
];

const SORT_OPTIONS = [
  { value: 'last_update_post_date', label: 'Most Recently Updated' },
  { value: 'brief_title', label: 'Alphabetical' },
];

const PHASE_OPTIONS = [
  { value: 'PHASE1', label: 'Phase 1' },
  { value: 'PHASE2', label: 'Phase 2' },
  { value: 'PHASE3', label: 'Phase 3' },
  { value: 'PHASE4', label: 'Phase 4' },
];

const RECRUITING_STATUS_OPTIONS = [
  { value: 'recruiting', label: 'Recruiting now' },
  { value: 'not_recruiting', label: 'Not currently recruiting' },
  { value: 'finished', label: 'Finished trials' },
];

const AGE_GROUP_OPTIONS = [
  { value: 'child', label: 'Child (Under 18)' },
  { value: 'adult', label: 'Adult (18–64)' },
  { value: 'older_adult', label: 'Older Adult (65+)' },
];

const ADMIN_PHASE_OPTIONS = [
  { value: '', label: 'All phases' },
  ...PHASE_OPTIONS,
];

const ADMIN_RECRUITING_OPTIONS = [
  { value: '', label: 'All statuses' },
  ...RECRUITING_STATUS_OPTIONS,
];

const SELECT_CLS = 'border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-colors hover:border-gray-300';

interface AllTrialsPageProps {
  /** Admin mode: shows all statuses and status filter. Default (public mode): APPROVED only. */
  adminMode?: boolean;
}

function CountryCombobox({
  countries,
  value,
  onChange,
}: {
  countries: string[];
  value: string | undefined;
  onChange: (country: string | undefined) => void;
}) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery('');
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const filtered = query
    ? countries.filter((c) => c.toLowerCase().includes(query.toLowerCase()))
    : countries;

  function select(country: string | undefined) {
    onChange(country);
    setQuery('');
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <div
        className={`flex items-center gap-1.5 border rounded-lg px-3 py-2 bg-white cursor-text shadow-sm transition-colors ${open ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200 hover:border-gray-300'}`}
        onClick={() => setOpen(true)}
      >
        {/* search icon */}
        <svg className="w-3.5 h-3.5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          type="text"
          className="flex-1 text-sm outline-none bg-transparent min-w-0 text-gray-700 placeholder-gray-400"
          placeholder={value ?? 'All countries'}
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        />
        {value && !open && (
          <button
            onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); select(undefined); }}
            className="text-gray-300 hover:text-gray-500 transition-colors"
            aria-label="Clear country"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      {open && (
        <ul className="absolute z-10 left-0 right-0 mt-1.5 max-h-52 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg text-sm py-1">
          <li
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => select(undefined)}
            className="px-3 py-2 cursor-pointer hover:bg-gray-50 text-gray-400 border-b border-gray-100 mb-1"
          >
            All countries
          </li>
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-gray-400 italic">No results</li>
          ) : (
            filtered.map((c) => (
              <li
                key={c}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => select(c)}
                className={`px-3 py-2 cursor-pointer transition-colors ${c === value ? 'font-medium text-blue-600 bg-blue-50' : 'text-gray-700 hover:bg-gray-50'}`}
              >
                {c}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</h3>
      {children}
    </div>
  );
}

function RadioOption({
  name,
  value,
  checked,
  label,
  onChange,
}: {
  name: string;
  value: string;
  checked: boolean;
  label: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer py-0.5">
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onChange(value)}
        className="accent-blue-600"
      />
      {label}
    </label>
  );
}

export function AllTrialsPage({ adminMode = false }: AllTrialsPageProps) {
  const navigate = useNavigate();
  const [response, setResponse] = useState<TrialsListResponse | null>(null);
  const [facets, setFacets] = useState<TrialFacets | null>(null);
  const [params, setParams] = useState<GetTrialsParams>(() => ({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: 'last_update_post_date',
    // Public mode always shows APPROVED trials only
    status: adminMode ? undefined : 'APPROVED',
  }));
  const [searchInput, setSearchInput] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch facets once for filter dropdowns (public mode only)
  useEffect(() => {
    if (!adminMode) {
      getTrialFacets().then(setFacets).catch(console.error);
    }
  }, [adminMode]);

  // Fetch whenever params change
  useEffect(() => {
    getTrials(params).then(setResponse).catch(console.error);
  }, [params]);

  // Debounce search input → update params.q
  function handleSearchChange(value: string) {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setParams((p) => ({ ...p, q: value || undefined, page: 1 }));
    }, 300);
  }

  function setFilter(key: keyof GetTrialsParams, value: string) {
    setParams((p) => ({ ...p, [key]: value || undefined, page: 1 }));
  }

  const totalPages = response ? Math.ceil(response.total / PAGE_SIZE) : 1;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header bar */}
      <div className="px-6 py-4 border-b bg-white space-y-3">
        <h1 className="text-base font-semibold text-gray-700">
          {adminMode ? 'All Trials' : 'Clinical Trials'}
        </h1>
        <input
          type="search"
          placeholder="Search by title, summary, or eligibility…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <div className="flex items-center gap-3 flex-wrap">
          {adminMode && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('status', e.target.value)}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('ingestion_event', e.target.value)}
            >
              {EVENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('phase', e.target.value)}
            >
              {ADMIN_PHASE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('recruiting_status', e.target.value)}
            >
              {ADMIN_RECRUITING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          <select
            className={SELECT_CLS}
            defaultValue="last_update_post_date"
            onChange={(e) => setFilter('sort_by', e.target.value)}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          {response && (
            <span className="text-xs text-gray-400 ml-auto">
              {response.total} trial{response.total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Content area: filter sidebar (public only) + trial list */}
      <div className={`flex flex-1 overflow-hidden ${!adminMode ? 'flex-row' : 'flex-col'}`}>
        {/* Filter sidebar — public mode only */}
        {!adminMode && (
          <aside className="w-52 shrink-0 border-r bg-gray-50 overflow-y-auto p-4 space-y-5">
            {facets && facets.countries.length > 0 && (
              <FilterSection title="Country">
                <CountryCombobox
                  countries={facets.countries}
                  value={params.country}
                  onChange={(c) => setParams((p) => ({ ...p, country: c, page: 1 }))}
                />
              </FilterSection>
            )}

            <div className="border-t border-gray-200" />

            <FilterSection title="Age">
              <div className="space-y-1">
                <RadioOption
                  name="age_group"
                  value=""
                  checked={!params.age_group}
                  label="All ages"
                  onChange={() => setParams((p) => ({ ...p, age_group: undefined, page: 1 }))}
                />
                {AGE_GROUP_OPTIONS.map((o) => (
                  <RadioOption
                    key={o.value}
                    name="age_group"
                    value={o.value}
                    checked={params.age_group === o.value}
                    label={o.label}
                    onChange={(v) => setParams((p) => ({ ...p, age_group: v, page: 1 }))}
                  />
                ))}
              </div>
            </FilterSection>

            <div className="border-t border-gray-200" />

            <FilterSection title="Recruiting Status">
              <div className="space-y-1">
                <RadioOption
                  name="recruiting_status"
                  value=""
                  checked={!params.recruiting_status}
                  label="All statuses"
                  onChange={() => setParams((p) => ({ ...p, recruiting_status: undefined, page: 1 }))}
                />
                {RECRUITING_STATUS_OPTIONS.map((o) => (
                  <RadioOption
                    key={o.value}
                    name="recruiting_status"
                    value={o.value}
                    checked={params.recruiting_status === o.value}
                    label={o.label}
                    onChange={(v) => setParams((p) => ({ ...p, recruiting_status: v, page: 1 }))}
                  />
                ))}
              </div>
            </FilterSection>

            <div className="border-t border-gray-200" />

            <FilterSection title="Trial Phase">
              <div className="space-y-1">
                <RadioOption
                  name="phase"
                  value=""
                  checked={!params.phase}
                  label="All phases"
                  onChange={() => setParams((p) => ({ ...p, phase: undefined, page: 1 }))}
                />
                {PHASE_OPTIONS.map((o) => (
                  <RadioOption
                    key={o.value}
                    name="phase"
                    value={o.value}
                    checked={params.phase === o.value}
                    label={o.label}
                    onChange={(v) => setParams((p) => ({ ...p, phase: v, page: 1 }))}
                  />
                ))}
              </div>
            </FilterSection>

            {(params.phase || params.recruiting_status || params.age_group || params.country) && (
              <>
                <div className="border-t border-gray-200" />
                <button
                  onClick={() => setParams((p) => ({ ...p, phase: undefined, recruiting_status: undefined, age_group: undefined, country: undefined, page: 1 }))}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-full transition-colors"
                >
                  Clear filters
                </button>
              </>
            )}
          </aside>
        )}

        {/* Trial list */}
        <div className="flex-1 overflow-y-auto">
          {!response ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm text-gray-400">Loading…</p>
            </div>
          ) : response.items.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm text-gray-400">No trials found.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {response.items.map((trial: TrialListItem) => {
                const statusDisplay = getOverallStatusDisplay(trial.overall_status);
                const summary = trial.custom_brief_summary || trial.brief_summary;
                return (
                  <li
                    key={trial.nct_id}
                    onClick={() => navigate(`/trials/${trial.nct_id}`)}
                    className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <p className="text-sm font-semibold text-gray-900 leading-snug mb-1">
                      {trial.brief_title}
                    </p>
                    {summary && (
                      <p className="text-xs text-gray-500 leading-relaxed mb-2 line-clamp-2">
                        {summary}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-2">
                      {trial.overall_status && (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusDisplay.className}`}>
                          {statusDisplay.label}
                        </span>
                      )}
                      {trial.phase && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
                          {formatPhase(trial.phase)}
                        </span>
                      )}
                      {adminMode && <StatusBadge status={trial.status} />}
                      {adminMode && trial.ingestion_event && <IngestionEventBadge event={trial.ingestion_event} />}
                      <span className="text-xs text-gray-400 ml-auto">{trial.nct_id}</span>
                      {trial.last_update_post_date && (
                        <span className="text-xs text-gray-400">· Updated {trial.last_update_post_date}</span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Pagination */}
      {response && totalPages > 1 && (
        <div className="px-6 py-3 border-t bg-white flex items-center justify-end gap-3">
          <button
            disabled={params.page === 1}
            onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
            className="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">
            Page {params.page} of {totalPages}
          </span>
          <button
            disabled={params.page === totalPages}
            onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
            className="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
