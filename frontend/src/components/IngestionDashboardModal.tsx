import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';

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
}

interface LiveStatus {
  running: boolean;
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
  const [done, setDone] = useState(false);
  const [starting, setStarting] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const headersRef = useRef<Record<string, string>>({});

  // ── Auth headers ─────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const token = await getToken();
        if (token) headersRef.current = { Authorization: `Bearer ${token}` };
      } catch { /* test env */ }
    })();
  }, [getToken]);

  // ── Fetch history once on open ────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Wait a tick for headersRef to populate
      await new Promise(r => setTimeout(r, 50));
      try {
        const res = await fetch(`${API_URL}/ingestion/history`, {
          headers: headersRef.current,
        });
        if (!cancelled && res.ok) setHistory(await res.json());
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [API_URL]);

  // ── Poll live status ──────────────────────────────────────────────────────────
  useEffect(() => {
    let stopped = false;

    const poll = async () => {
      if (stopped) return;
      try {
        const res = await fetch(`${API_URL}/ingestion/status`, {
          headers: headersRef.current,
        });
        if (!res.ok || stopped) return;
        const data: LiveStatus = await res.json();
        setStatus(data);

        if (data.error && !done) {
          clearInterval(intervalRef.current!);
          setErrorMsg(data.error);
          setDone(true);
        } else if (data.summary && !done) {
          clearInterval(intervalRef.current!);
          setSummary(data.summary);
          setDone(true);
          // Refresh history so the new run shows in the table
          const hRes = await fetch(`${API_URL}/ingestion/history`, {
            headers: headersRef.current,
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
  }, [API_URL, done]);

  // ── Run Now ───────────────────────────────────────────────────────────────────
  const handleRunNow = async () => {
    setStarting(true);
    setErrorMsg(null);
    setSummary(null);
    setDone(false);
    try {
      const res = await fetch(`${API_URL}/ingestion/start`, {
        method: 'POST',
        headers: headersRef.current,
      });
      if (!res.ok && res.status !== 409) {
        setErrorMsg(`Failed to start: ${res.status}`);
        setDone(true);
      }
    } catch {
      setErrorMsg('Could not reach server.');
      setDone(true);
    } finally {
      setStarting(false);
    }
  };

  const isRunning = status?.running ?? false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-base font-semibold text-gray-900 mb-5">Ingestion</h2>

        {/* ── Live progress (when running) ─────────────────────────────────── */}
        {isRunning && status && (
          <div className="mb-5">
            <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-3">Running</p>
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

        {/* ── Actions ───────────────────────────────────────────────────────── */}
        <div className="flex gap-3">
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
