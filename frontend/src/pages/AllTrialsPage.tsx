import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTrials } from '../api';
import type { GetTrialsParams } from '../api';
import { IngestionEventBadge } from '../components/IngestionEventBadge';
import { StatusBadge } from '../components/StatusBadge';
import type { TrialListItem, TrialsListResponse } from '../types';

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

export function AllTrialsPage() {
  const navigate = useNavigate();
  const [response, setResponse] = useState<TrialsListResponse | null>(null);
  const [params, setParams] = useState<GetTrialsParams>({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: 'last_update_post_date',
  });
  const [searchInput, setSearchInput] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        <h1 className="text-base font-semibold text-gray-700">All Trials</h1>
        <input
          type="search"
          placeholder="Search by title, summary, or eligibility…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <div className="flex items-center gap-3 flex-wrap">
          <select
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            onChange={(e) => setFilter('status', e.target.value)}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            onChange={(e) => setFilter('ingestion_event', e.target.value)}
          >
            {EVENT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
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
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b sticky top-0">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Title</th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-24">Phase</th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-32">Status</th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-24">Event</th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide w-28">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {response.items.map((trial: TrialListItem) => (
                <tr
                  key={trial.nct_id}
                  onClick={() => navigate(`/trials/${trial.nct_id}`)}
                  className="hover:bg-gray-50 cursor-pointer"
                >
                  <td className="px-6 py-3 font-medium text-gray-900 max-w-xs truncate">
                    {trial.brief_title}
                  </td>
                  <td className="px-3 py-3 text-gray-500 text-xs">{trial.phase ?? '—'}</td>
                  <td className="px-3 py-3"><StatusBadge status={trial.status} /></td>
                  <td className="px-3 py-3"><IngestionEventBadge event={trial.ingestion_event} /></td>
                  <td className="px-3 py-3 text-gray-400 text-xs">{trial.last_update_post_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {response && totalPages > 1 && (
        <div className="px-6 py-3 border-t bg-white flex items-center justify-end gap-3">
          <button
            disabled={params.page === 1}
            onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) - 1 }))}
            className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {params.page} of {totalPages}
          </span>
          <button
            disabled={params.page === totalPages}
            onClick={() => setParams((p) => ({ ...p, page: (p.page ?? 1) + 1 }))}
            className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
