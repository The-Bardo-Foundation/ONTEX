import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { isAxiosError } from 'axios';
import {
  createKeyword,
  deleteKeyword,
  getKeywords,
  pauseIngestion,
  resumeIngestion,
  stopIngestion,
  type SearchKeyword,
  updateKeyword,
} from '../api';

// ── Types ──────────────────────────────────────────────────────────────────────

type StepState = 'waiting' | 'active' | 'done' | 'error';

interface StepDisplay {
  id: string;
  label: string;
  state: StepState;
  count?: number;
  total?: number;
  note?: string;
}

interface IngestionSummary {
  new?: number;
  updated?: number;
  relevant?: number;
  irrelevant?: number;
  fetch_errors?: number;
  classify_errors?: number;
  pruned_trials?: number;
}

interface RunRecord {
  id: number;
  run_at: string;
  candidates_found: number;
  new_trials: number;
  updated_trials: number;
  relevant_processed: number;
  irrelevant_processed: number;
  fetch_errors: number;
  classify_errors: number;
  pruned_trials: number;
}

interface LiveStatus {
  running: boolean;
  paused?: boolean;
  stop_requested?: boolean;
  steps: StepDisplay[];
  error: string | null;
  summary: IngestionSummary | null;
}

interface History {
  next_run: string | null;
  recent_runs: RunRecord[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export function IngestionDashboardModal({ onClose }: { onClose: () => void }) {
  const { getToken } = useAuth();
  const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

  const [history, setHistory] = useState<History | null>(null);
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [summary, setSummary] = useState<IngestionSummary | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<SearchKeyword[]>([]);
  const [keywordInput, setKeywordInput] = useState('');
  const [keywordError, setKeywordError] = useState<string | null>(null);
  const [keywordBusyId, setKeywordBusyId] = useState<number | null>(null);
  const [isAddingKeyword, setIsAddingKeyword] = useState(false);
  const [pruneMessage, setPruneMessage] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [starting, setStarting] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // True once this client has observed an in-progress run. Prevents showing
  // a stale summary from a previous run when the modal first opens.
  const sawRunningRef = useRef(false);

  const getAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
    try {
      const token = await getToken();
      return token ? { Authorization: `Bearer ${token}` } : {};
    } catch {
      return {};
    }
  }, [getToken]);

  // ── Fetch history once on open ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Wait a tick for headersRef to populate
      await new Promise(r => setTimeout(r, 50));
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${API_URL}/ingestion/history`, {
          headers,
        });
        if (!cancelled && res.ok) setHistory(await res.json());
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [API_URL, getAuthHeaders]);

  const refreshKeywords = useCallback(async () => {
    try {
      setKeywordError(null);
      const data = await getKeywords();
      setKeywords(data);
    } catch (error: unknown) {
      if (isAxiosError(error) && error.response?.status === 401) {
        setKeywordError('Could not load keywords (not authenticated).');
      } else if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
        setKeywordError(error.response.data.detail);
      } else {
        setKeywordError('Could not load keywords.');
      }
    }
  }, []);

  useEffect(() => {
    refreshKeywords();
  }, [refreshKeywords]);

  // ── Poll live status ──────────────────────────────────────────────────────────
  useEffect(() => {
    let stopped = false;

    const poll = async () => {
      if (stopped) return;
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${API_URL}/ingestion/status`, {
          headers,
        });
        if (!res.ok || stopped) return;
        const data: LiveStatus = await res.json();
        setStatus(data);

        if (data.running) sawRunningRef.current = true;

        if (data.error && !done && sawRunningRef.current) {
          clearInterval(intervalRef.current!);
          setErrorMsg(data.error);
          setDone(true);
        } else if (data.summary && !done && sawRunningRef.current) {
          clearInterval(intervalRef.current!);
          setSummary(data.summary);
          setDone(true);
          // Refresh history so the new run shows in the table
          const refreshedHeaders = await getAuthHeaders();
          const hRes = await fetch(`${API_URL}/ingestion/history`, {
            headers: refreshedHeaders,
          });
          if (hRes.ok && !stopped) setHistory(await hRes.json());
        }
      } catch { /* transient hiccup */ }
    };

    poll(); // immediate first check
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      stopped = true;
      if (intervalRef.current !== null) clearInterval(intervalRef.current);
    };
  }, [API_URL, done, getAuthHeaders]);

  // ── Run Now ───────────────────────────────────────────────────────────────────
  const handleRunNow = async () => {
    setStarting(true);
    setErrorMsg(null);
    setSummary(null);
    setDone(false);
    // Re-arm the gate so a stale summary from a previous run can't match
    // before /start has cleared it on the backend.
    sawRunningRef.current = false;
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${API_URL}/ingestion/start`, {
        method: 'POST',
        headers,
      });
      if (!res.ok && res.status !== 409) {
        setErrorMsg(`Failed to start: ${res.status}`);
        setDone(true);
      } else {
        // /start clears the backend summary before returning, so any
        // non-null summary we see from here on belongs to this run —
        // including sub-poll-tick runs that finish before we observe
        // running=true.
        sawRunningRef.current = true;
      }
    } catch {
      setErrorMsg('Could not reach server.');
      setDone(true);
    } finally {
      setStarting(false);
    }
  };

  const isRunning = status?.running ?? false;
  const isPaused = status?.paused ?? false;
  const activeKeywords = keywords.filter((k) => k.is_active);

  const handlePauseResume = async () => {
    try {
      if (isPaused) {
        await resumeIngestion();
      } else {
        await pauseIngestion();
      }
    } catch {
      setErrorMsg(isPaused ? 'Could not resume ingestion.' : 'Could not pause ingestion.');
    }
  };

  const handleStop = async () => {
    try {
      await stopIngestion();
    } catch {
      setErrorMsg('Could not stop ingestion.');
    }
  };

  const handleAddKeyword = async () => {
    const term = keywordInput.trim();
    if (!term) return;
    setIsAddingKeyword(true);
    setKeywordError(null);
    setPruneMessage(null);
    try {
      await createKeyword(term);
      setKeywordInput('');
      await refreshKeywords();
    } catch (error: unknown) {
      if (isAxiosError(error) && error.response?.status === 409) {
        setKeywordError('Keyword already exists.');
      } else if (isAxiosError(error) && error.response?.status === 500) {
        setKeywordError('Could not add keyword (backend schema may be outdated).');
      } else if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
        setKeywordError(error.response.data.detail);
      } else {
        setKeywordError('Could not add keyword.');
      }
    } finally {
      setIsAddingKeyword(false);
    }
  };

  const handleSetKeywordActive = async (keywordId: number, isActive: boolean) => {
    setKeywordBusyId(keywordId);
    setKeywordError(null);
    setPruneMessage(null);
    try {
      await updateKeyword(keywordId, isActive);
      await refreshKeywords();
    } catch {
      setKeywordError('Could not update keyword status.');
    } finally {
      setKeywordBusyId(null);
    }
  };

  const handleDeleteKeyword = async (keywordId: number, term: string) => {
    const confirmed = window.confirm(
      `Delete keyword "${term}"? This prunes non-approved trials outside active keywords.`
    );
    if (!confirmed) return;
    setKeywordBusyId(keywordId);
    setKeywordError(null);
    setPruneMessage(null);
    try {
      const result = await deleteKeyword(keywordId);
      await refreshKeywords();
      if (result.pruned_trials > 0) {
        setPruneMessage(`${result.pruned_trials} trial(s) were pruned.`);
      }
    } catch {
      setKeywordError('Could not delete keyword.');
    } finally {
      setKeywordBusyId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-base font-semibold text-gray-900 mb-5">Ingestion</h2>

        {/* ── Live progress (when running) ─────────────────────────────────── */}
        {isRunning && status && (
          <div className="mb-5">
            <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-3">Running</p>
            {isPaused && (
              <p className="text-xs text-amber-700 mb-3">Paused by admin</p>
            )}
            <div className="space-y-4">
              {status.steps.map((step) => (
                <StepRow key={step.id} step={step} />
              ))}
            </div>
          </div>
        )}

        {/* ── Completion summary (after run finishes) ───────────────────────── */}
        {summary && (
          <div className="mb-5 p-3 bg-green-50 rounded-lg border border-green-100 text-sm text-gray-700 space-y-1">
            <p className="font-medium text-green-800">Run complete</p>
            <p>{summary.new} new · {summary.updated} updated · {summary.relevant} relevant · {summary.irrelevant} irrelevant</p>
            {(summary.pruned_trials ?? 0) > 0 && (
              <p className="text-amber-700">{summary.pruned_trials} pruned outside active keywords</p>
            )}
            {(summary.fetch_errors ?? 0) > 0 && (
              <p className="text-amber-600">{summary.fetch_errors} fetch error{summary.fetch_errors !== 1 ? 's' : ''}</p>
            )}
            {(summary.classify_errors ?? 0) > 0 && (
              <p className="text-amber-600">{summary.classify_errors} classification error{summary.classify_errors !== 1 ? 's' : ''}</p>
            )}
          </div>
        )}

        {/* ── Error ─────────────────────────────────────────────────────────── */}
        {errorMsg && (
          <div className="mb-5 p-3 bg-red-50 rounded-lg border border-red-100 text-sm text-red-700">
            {errorMsg}
          </div>
        )}

        {/* ── Schedule info ─────────────────────────────────────────────────── */}
        {history && (
          <div className="mb-5 text-sm text-gray-600 space-y-1">
            {history.next_run && (
              <p>
                <span className="font-medium text-gray-700">Next scheduled: </span>
                {formatDatetime(history.next_run)}
              </p>
            )}
            {history.recent_runs.length > 0 && (
              <p>
                <span className="font-medium text-gray-700">Last run: </span>
                {formatDatetime(history.recent_runs[0].run_at)}
              </p>
            )}
          </div>
        )}

        {/* ── Recent runs table ─────────────────────────────────────────────── */}
        {history && history.recent_runs.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Recent runs</p>
            <div className="overflow-x-auto rounded-lg border border-gray-100">
              <table className="w-full text-xs text-gray-700">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-3 py-2 font-medium text-gray-500">Date</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">Cand.</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">New</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">Updated</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">Relevant</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">Pruned</th>
                    <th className="px-3 py-2 font-medium text-gray-500 text-right">Errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {history.recent_runs.map((run) => (
                    <tr key={run.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 whitespace-nowrap">{formatDatetime(run.run_at)}</td>
                      <td className="px-3 py-2 text-right">{run.candidates_found.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right">{run.new_trials}</td>
                      <td className="px-3 py-2 text-right">{run.updated_trials}</td>
                      <td className="px-3 py-2 text-right">{run.relevant_processed}</td>
                      <td className="px-3 py-2 text-right">{run.pruned_trials ?? 0}</td>
                      <td className={`px-3 py-2 text-right ${(run.fetch_errors + run.classify_errors) > 0 ? 'text-amber-600' : ''}`}>
                        {run.fetch_errors + run.classify_errors}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {history && history.recent_runs.length === 0 && !isRunning && (
          <p className="mb-5 text-sm text-gray-400 italic">No ingestion runs recorded yet.</p>
        )}

        {/* ── Keyword management ─────────────────────────────────────────────── */}
        <div className="mb-5 p-3 border border-gray-100 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Search keywords</p>
            <span className="text-xs text-gray-400">
              {activeKeywords.length} active
            </span>
          </div>

          {keywords.length === 0 ? (
            <p className="text-sm text-gray-400">No keywords configured.</p>
          ) : (
            <div className="space-y-2">
              {keywords.map((keyword) => {
                const isBusy = keywordBusyId === keyword.id;
                return (
                  <div
                    key={keyword.id}
                    className="flex items-center justify-between gap-2 rounded border border-gray-100 px-2 py-1.5"
                  >
                    <span className="text-sm text-gray-700">{keyword.term}</span>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleSetKeywordActive(keyword.id, true)}
                        disabled={isBusy || keyword.is_active}
                        className="px-2 py-1 text-xs rounded border border-green-200 text-green-700 disabled:opacity-40"
                      >
                        Active
                      </button>
                      <button
                        onClick={() => handleSetKeywordActive(keyword.id, false)}
                        disabled={isBusy || !keyword.is_active}
                        className="px-2 py-1 text-xs rounded border border-amber-200 text-amber-700 disabled:opacity-40"
                      >
                        Inactive
                      </button>
                      <button
                        onClick={() => handleDeleteKeyword(keyword.id, keyword.term)}
                        disabled={isBusy}
                        className="px-2 py-1 text-xs rounded border border-red-200 text-red-700 disabled:opacity-40"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2">
            <input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="Add keyword"
              className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm"
            />
            <button
              onClick={handleAddKeyword}
              disabled={isAddingKeyword || !keywordInput.trim()}
              className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white disabled:opacity-40"
            >
              +
            </button>
          </div>
          {keywordError && <p className="text-xs text-red-600">{keywordError}</p>}
          {pruneMessage && <p className="text-xs text-amber-700">{pruneMessage}</p>}
        </div>

        {/* ── Actions ───────────────────────────────────────────────────────── */}
        <div className="flex gap-3">
          {isRunning && (
            <>
              <button
                onClick={handlePauseResume}
                className="flex-1 px-4 py-2 border border-amber-300 text-amber-700 text-sm font-medium rounded-lg hover:bg-amber-50 transition-colors"
              >
                {isPaused ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={handleStop}
                className="flex-1 px-4 py-2 border border-red-300 text-red-700 text-sm font-medium rounded-lg hover:bg-red-50 transition-colors"
              >
                Stop
              </button>
            </>
          )}
          {!isRunning && !done && (
            <button
              onClick={handleRunNow}
              disabled={starting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {starting ? 'Starting…' : 'Run Now'}
            </button>
          )}
          <button
            onClick={() => {
              if (intervalRef.current !== null) clearInterval(intervalRef.current);
              onClose();
            }}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            {isRunning ? 'Close (runs in background)' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StepRow({ step }: { step: StepDisplay }) {
  const pct =
    step.total && step.total > 0 ? Math.round(((step.count ?? 0) / step.total) * 100) : 0;

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <StateIcon state={step.state} />
        <span
          className={`text-sm font-medium ${
            step.state === 'waiting' ? 'text-gray-400' : 'text-gray-800'
          }`}
        >
          {step.label}
        </span>
      </div>
      {step.state === 'done' && step.note && (
        <p className="text-xs text-gray-500 ml-6">{step.note}</p>
      )}
      {step.state === 'active' && step.total != null && step.total > 0 && (
        <div className="ml-6">
          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {(step.count ?? 0).toLocaleString()} / {step.total.toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
}

function StateIcon({ state }: { state: StepState }) {
  if (state === 'done') {
    return (
      <span className="w-4 h-4 flex items-center justify-center text-green-500 shrink-0">✓</span>
    );
  }
  if (state === 'active') {
    return (
      <span className="w-4 h-4 shrink-0">
        <svg className="animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      </span>
    );
  }
  if (state === 'error') {
    return (
      <span className="w-4 h-4 flex items-center justify-center text-red-500 shrink-0 text-xs font-bold">✕</span>
    );
  }
  return <span className="w-4 h-4 rounded-full border border-gray-300 shrink-0" />;
}

function formatDatetime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
