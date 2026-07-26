import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { getIrrelevantTrials, getTrialFacets, getTrials } from '../api';
import type { GetIrrelevantTrialsParams, GetTrialsParams, IrrelevantTrialListItem, IrrelevantTrialsListResponse, StatusFacet, TrialFacets } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { IrrelevantTrialDetailModal } from '../components/IrrelevantTrialDetailModal';
import { StatusBadge } from '../components/StatusBadge';
import type { TrialListItem, TrialsListResponse } from '../types';
import { formatLocationSummary, formatPhase, getOverallStatusDisplay, groupStatuses } from '../utils/formatters';
import { useDocumentTitle } from '../utils/useDocumentTitle';

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

const AGE_GROUP_OPTIONS = [
  { value: 'child', label: 'Child (Under 18)' },
  { value: 'adult', label: 'Adult (18–64)' },
  { value: 'older_adult', label: 'Older Adult (65+)' },
];

const ADMIN_PHASE_OPTIONS = [
  { value: '', label: 'All phases' },
  ...PHASE_OPTIONS,
];

const SELECT_CLS = 'border border-line rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-400 transition-colors hover:border-gray-300';

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
        className={`flex items-center gap-1.5 border rounded-lg px-3 py-2 bg-white cursor-text shadow-sm transition-colors ${open ? 'border-brand-400 ring-2 ring-brand-100' : 'border-line hover:border-gray-300'}`}
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
        <ul className="absolute z-10 left-0 right-0 mt-1.5 max-h-52 overflow-y-auto bg-white border border-line rounded-lg shadow-lg text-sm py-1">
          <li
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => select(undefined)}
            className="px-3 py-2 cursor-pointer hover:bg-surface text-gray-400 border-b border-line-soft mb-1"
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
                className={`px-3 py-2 cursor-pointer transition-colors ${c === value ? 'font-medium text-brand-600 bg-brand-50' : 'text-gray-700 hover:bg-surface'}`}
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

function CheckboxOption({
  checked,
  indeterminate = false,
  label,
  count,
  onChange,
  className = '',
}: {
  checked: boolean;
  indeterminate?: boolean;
  label: string;
  count?: number;
  onChange: () => void;
  className?: string;
}) {
  return (
    <label className={`flex items-start gap-2 text-sm text-gray-700 cursor-pointer py-0.5 ${className}`}>
      <input
        type="checkbox"
        checked={checked}
        ref={(el) => {
          // Indeterminate is a DOM property, not an attribute — React cannot set it via JSX.
          if (el) el.indeterminate = indeterminate && !checked;
        }}
        onChange={onChange}
        className="accent-brand-600 mt-0.5 shrink-0"
      />
      <span>
        {label}
        {count !== undefined && <span className="text-gray-400"> ({count})</span>}
      </span>
    </label>
  );
}

/**
 * Two-level recruitment-status filter: plain-English groups that expand to the
 * individual ClinicalTrials.gov statuses inside them.
 *
 * Only statuses present in `statuses` (the facet, i.e. what the visible trials
 * actually have) are offered, and anything outside a known group is listed as a
 * standalone option — so no trial can be unreachable through this filter.
 */
function StatusFilter({
  statuses,
  selected,
  onChange,
}: {
  statuses: StatusFacet[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const { groups, ungrouped } = groupStatuses(statuses.map((s) => s.value));
  const countOf = (value: string) => statuses.find((s) => s.value === value)?.count ?? 0;

  const selectedSet = new Set(selected);
  const toggleStatus = (value: string) =>
    onChange(
      selectedSet.has(value)
        ? selected.filter((s) => s !== value)
        : [...selected, value],
    );

  function toggleGroup(members: string[]) {
    const allOn = members.every((s) => selectedSet.has(s));
    onChange(
      allOn
        ? selected.filter((s) => !members.includes(s))
        : [...selected.filter((s) => !members.includes(s)), ...members],
    );
  }

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <div className="space-y-1">
      <CheckboxOption
        checked={selected.length === 0}
        label="All statuses"
        onChange={() => onChange([])}
      />
      {groups.map((group) => {
        const isOpen = expanded.has(group.key);
        const groupCount = group.statuses.reduce((sum, s) => sum + countOf(s), 0);
        return (
          <div key={group.key}>
            <div className="flex items-start gap-1">
              <button
                type="button"
                onClick={() => toggleExpanded(group.key)}
                aria-expanded={isOpen}
                aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${group.label}`}
                className="text-gray-400 hover:text-gray-600 mt-0.5 w-3 shrink-0 text-xs leading-5"
              >
                {isOpen ? '▾' : '▸'}
              </button>
              <CheckboxOption
                checked={group.statuses.every((s) => selectedSet.has(s))}
                indeterminate={group.statuses.some((s) => selectedSet.has(s))}
                label={group.label}
                count={groupCount}
                onChange={() => toggleGroup(group.statuses)}
              />
            </div>
            {isOpen && (
              <div className="ml-4 pl-2 border-l border-line">
                {group.statuses.map((status) => (
                  <CheckboxOption
                    key={status}
                    checked={selectedSet.has(status)}
                    label={getOverallStatusDisplay(status).label}
                    count={countOf(status)}
                    onChange={() => toggleStatus(status)}
                    className="text-xs text-gray-600"
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
      {ungrouped.map((status) => (
        <CheckboxOption
          key={status}
          checked={selectedSet.has(status)}
          label={getOverallStatusDisplay(status).label}
          count={countOf(status)}
          onChange={() => toggleStatus(status)}
        />
      ))}
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
        className="accent-brand-600"
      />
      {label}
    </label>
  );
}

export function AllTrialsPage({ adminMode = false }: AllTrialsPageProps) {
  useDocumentTitle(adminMode ? 'All Trials' : 'Search Trials');

  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'relevant' | 'irrelevant'>('relevant');
  const [response, setResponse] = useState<TrialsListResponse | null>(null);
  const [irrelevantResponse, setIrrelevantResponse] = useState<IrrelevantTrialsListResponse | null>(null);
  const [facets, setFacets] = useState<TrialFacets | null>(null);
  const [params, setParams] = useState<GetTrialsParams>(() => ({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: 'last_update_post_date',
    // Public mode always shows APPROVED trials only
    status: adminMode ? undefined : 'APPROVED',
  }));
  const [irrelevantParams, setIrrelevantParams] = useState<GetIrrelevantTrialsParams>({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: 'last_update_post_date',
  });
  const [searchInput, setSearchInput] = useState('');
  const [selectedIrrelevantId, setSelectedIrrelevantId] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch facets once for filter controls. Needed in both modes: the public
  // sidebar and the admin status dropdown are both built from the statuses that
  // actually exist. The endpoint is auth-aware, so admins get all trials'
  // statuses while the public gets only approved ones.
  useEffect(() => {
    getTrialFacets().then(setFacets).catch(console.error);
  }, []);

  // Fetch relevant trials whenever params change (always in public mode; relevant tab in admin)
  useEffect(() => {
    if (!adminMode || activeTab === 'relevant') {
      getTrials(params).then(setResponse).catch(console.error);
    }
  }, [params, adminMode, activeTab]);

  // Fetch irrelevant trials whenever irrelevantParams change (admin irrelevant tab only)
  useEffect(() => {
    if (adminMode && activeTab === 'irrelevant') {
      getIrrelevantTrials(irrelevantParams).then(setIrrelevantResponse).catch(console.error);
    }
  }, [irrelevantParams, adminMode, activeTab]);

  // Debounce search input → update params.q / irrelevantParams.q
  function handleSearchChange(value: string) {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (activeTab === 'irrelevant') {
        setIrrelevantParams((p) => ({ ...p, q: value || undefined, page: 1 }));
      } else {
        setParams((p) => ({ ...p, q: value || undefined, page: 1 }));
      }
    }, 300);
  }

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  function setFilter(key: keyof GetTrialsParams, value: string) {
    setParams((p) => ({ ...p, [key]: value || undefined, page: 1 }));
  }

  function switchTab(tab: 'relevant' | 'irrelevant') {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setActiveTab(tab);
    setSearchInput('');
    setParams((p) => ({ ...p, q: undefined, page: 1 }));
    setIrrelevantParams((p) => ({ ...p, q: undefined, page: 1 }));
  }

  const { groups: statusSelectGroups, ungrouped: statusSelectUngrouped } = groupStatuses(
    facets?.statuses.map((s) => s.value) ?? [],
  );

  const currentTotal = activeTab === 'irrelevant' ? irrelevantResponse?.total : response?.total;
  const totalPages = currentTotal !== undefined ? Math.ceil(currentTotal / PAGE_SIZE) : 1;
  const currentPage = activeTab === 'irrelevant' ? (irrelevantParams.page ?? 1) : (params.page ?? 1);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header bar */}
      <div className="px-6 py-4 border-b bg-white space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-base font-semibold text-gray-700">
            {adminMode ? 'All Trials' : 'Clinical Trials'}
          </h1>
          {adminMode && (
            <div className="flex rounded-lg border border-line overflow-hidden text-sm">
              <button
                onClick={() => switchTab('relevant')}
                className={`px-3 py-1 transition-colors ${activeTab === 'relevant' ? 'bg-brand-600 text-white font-medium' : 'bg-white text-gray-600 hover:bg-surface'}`}
              >
                Relevant
              </button>
              <button
                onClick={() => switchTab('irrelevant')}
                className={`px-3 py-1 border-l border-line transition-colors ${activeTab === 'irrelevant' ? 'bg-brand-600 text-white font-medium' : 'bg-white text-gray-600 hover:bg-surface'}`}
              >
                Irrelevant
              </button>
            </div>
          )}
        </div>
        <input
          type="search"
          placeholder="Search by title or summary…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
        />
        <div className="flex items-center gap-3 flex-wrap">
          {adminMode && activeTab === 'relevant' && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('status', e.target.value)}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && activeTab === 'relevant' && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('ingestion_event', e.target.value)}
            >
              {EVENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && activeTab === 'relevant' && (
            <select
              className={SELECT_CLS}
              onChange={(e) => setFilter('phase', e.target.value)}
            >
              {ADMIN_PHASE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          )}
          {adminMode && activeTab === 'relevant' && facets && facets.statuses.length > 0 && (
            <select
              className={SELECT_CLS}
              value={params.overall_status ?? ''}
              onChange={(e) => setFilter('overall_status', e.target.value)}
            >
              <option value="">All statuses</option>
              {statusSelectGroups.map((group) => (
                <optgroup key={group.key} label={group.label}>
                  {/* Whole-group option first, then each status within it. Values are
                      pipe-joined so they pass straight through to the API. */}
                  <option value={group.statuses.join('|')}>All {group.label.toLowerCase()}</option>
                  {group.statuses.map((s) => (
                    <option key={s} value={s}>{getOverallStatusDisplay(s).label}</option>
                  ))}
                </optgroup>
              ))}
              {statusSelectUngrouped.map((s) => (
                <option key={s} value={s}>{getOverallStatusDisplay(s).label}</option>
              ))}
            </select>
          )}
          <select
            className={SELECT_CLS}
            defaultValue="last_update_post_date"
            onChange={(e) => {
              if (activeTab === 'irrelevant') {
                setIrrelevantParams((p) => ({ ...p, sort_by: e.target.value || undefined, page: 1 }));
              } else {
                setFilter('sort_by', e.target.value);
              }
            }}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          {currentTotal !== undefined && (
            <span className="text-xs text-gray-400 ml-auto">
              {currentTotal} trial{currentTotal !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Content area: filter sidebar (public only) + trial list */}
      <div className={`flex flex-1 overflow-hidden ${!adminMode ? 'flex-row' : 'flex-col'}`}>
        {/* Filter sidebar — public mode only */}
        {!adminMode && (
          <aside className="w-52 shrink-0 border-r bg-surface overflow-y-auto p-4 space-y-5">
            {facets && facets.countries.length > 0 && (
              <FilterSection title="Country">
                <CountryCombobox
                  countries={facets.countries}
                  value={params.country}
                  onChange={(c) => setParams((p) => ({ ...p, country: c, page: 1 }))}
                />
              </FilterSection>
            )}

            <div className="border-t border-line" />

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

            <div className="border-t border-line" />

            {facets && facets.statuses.length > 0 && (
              <FilterSection title="Recruiting Status">
                <StatusFilter
                  statuses={facets.statuses}
                  selected={params.overall_status?.split('|').map((s) => s.trim()).filter(Boolean) ?? []}
                  onChange={(next) =>
                    setParams((p) => ({ ...p, overall_status: next.join('|') || undefined, page: 1 }))
                  }
                />
              </FilterSection>
            )}

            <div className="border-t border-line" />

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

            {(params.phase || params.overall_status || params.age_group || params.country) && (
              <>
                <div className="border-t border-line" />
                <button
                  onClick={() => setParams((p) => ({ ...p, phase: undefined, overall_status: undefined, age_group: undefined, country: undefined, page: 1 }))}
                  className="text-xs font-medium text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded-full transition-colors"
                >
                  Clear filters
                </button>
              </>
            )}
          </aside>
        )}

        {/* Trial list */}
        <div className="flex-1 overflow-y-auto">
          {adminMode && activeTab === 'irrelevant' ? (
            !irrelevantResponse ? (
              <div className="flex items-center justify-center h-32">
                <p className="text-sm text-gray-400">Loading…</p>
              </div>
            ) : irrelevantResponse.items.length === 0 ? (
              <div className="flex items-center justify-center h-32">
                <p className="text-sm text-gray-400">No irrelevant trials found.</p>
              </div>
            ) : (
              <ul className="divide-y divide-line-soft">
                {irrelevantResponse.items.map((trial: IrrelevantTrialListItem) => {
                  const statusDisplay = getOverallStatusDisplay(trial.overall_status);
                  return (
                    <li
                      key={trial.nct_id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedIrrelevantId(trial.nct_id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setSelectedIrrelevantId(trial.nct_id);
                        }
                      }}
                      className="px-6 py-4 hover:bg-surface cursor-pointer transition-colors"
                    >
                      <p className="text-sm font-semibold text-gray-900 leading-snug mb-1">
                        {trial.brief_title}
                      </p>
                      {trial.ai_relevance_reason && (
                        <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 mb-2 leading-relaxed">
                          {trial.ai_relevance_reason}
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
                        <span className="text-xs text-gray-400 ml-auto">{trial.nct_id}</span>
                        {trial.last_update_post_date && (
                          <span className="text-xs text-gray-400">· Updated {trial.last_update_post_date}</span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )
          ) : !response ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm text-gray-400">Loading…</p>
            </div>
          ) : response.items.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm text-gray-400">No trials found.</p>
            </div>
          ) : (
            <ul className="divide-y divide-line-soft">
              {response.items.map((trial: TrialListItem) => {
                const statusDisplay = getOverallStatusDisplay(trial.overall_status);
                const summary = trial.custom_brief_summary || trial.brief_summary;
                const city = trial.custom_location_city ?? trial.location_city;
                const country = trial.custom_location_country ?? trial.location_country;
                const location = formatLocationSummary(city, country);
                return (
                  <li
                    key={trial.nct_id}
                    onClick={() => navigate(`/trials/${trial.nct_id}`)}
                    className="px-6 py-4 hover:bg-surface cursor-pointer transition-colors"
                  >
                    <p className="text-sm font-semibold text-gray-900 leading-snug mb-1">
                      {trial.brief_title}
                    </p>
                    {summary && (
                      <p className="text-xs text-gray-500 leading-relaxed mb-2 line-clamp-2">
                        {summary}
                      </p>
                    )}
                    {location && (
                      <p className="text-xs text-gray-400 mb-2">{location}</p>
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
      {totalPages > 1 && (
        <div className="px-6 py-3 border-t bg-white flex items-center justify-end gap-3">
          <button
            disabled={currentPage === 1}
            onClick={() => {
              if (activeTab === 'irrelevant') {
                setIrrelevantParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }));
              } else {
                setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }));
              }
            }}
            className="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-line rounded-lg shadow-sm hover:bg-surface hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-400">
            Page {currentPage} of {totalPages}
          </span>
          <button
            disabled={currentPage === totalPages}
            onClick={() => {
              if (activeTab === 'irrelevant') {
                setIrrelevantParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }));
              } else {
                setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }));
              }
            }}
            className="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-line rounded-lg shadow-sm hover:bg-surface hover:border-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {selectedIrrelevantId && (
        <IrrelevantTrialDetailModal
          nctId={selectedIrrelevantId}
          onClose={() => setSelectedIrrelevantId(null)}
          onRestored={(id) => {
            setIrrelevantResponse((prev) =>
              prev
                ? { ...prev, items: prev.items.filter((t) => t.nct_id !== id), total: prev.total - 1 }
                : prev
            );
            setSelectedIrrelevantId(null);
          }}
        />
      )}
    </div>
  );
}
