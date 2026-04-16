import { useEffect, useRef, useState } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ProgressEvent {
  step: string;
  label: string;
  count?: number;
  total?: number;
  // completion summary fields
  new?: number;
  updated?: number;
  relevant?: number;
  irrelevant?: number;
  fetch_errors?: number;
  classify_errors?: number;
  // error
  message?: string;
}

type StepState = 'waiting' | 'active' | 'done' | 'error';

interface StepDisplay {
  id: string;
  label: string;
  state: StepState;
  count?: number;
  total?: number;
  note?: string;
}

const PIPELINE_STEPS = [
  { id: 'searching',       label: 'Searching ClinicalTrials.gov' },
  { id: 'fetching_details', label: 'Fetching trial details' },
  { id: 'summarizing',     label: 'Generating summaries' },
  { id: 'classifying',     label: 'AI classification' },
];

// ── Component ─────────────────────────────────────────────────────────────────

export function IngestionProgressModal({ onClose }: { onClose: () => void }) {
  const [steps, setSteps] = useState<StepDisplay[]>(
    PIPELINE_STEPS.map((s) => ({ id: s.id, label: s.label, state: 'waiting' }))
  );
  const [summary, setSummary] = useState<ProgressEvent | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
    const es = new EventSource(`${API_URL}/ingestion/run-stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      let event: ProgressEvent;
      try {
        event = JSON.parse(e.data);
      } catch {
        return;
      }

      if (event.step === 'error') {
        setErrorMsg(event.message ?? 'Unknown error');
        setDone(true);
        es.close();
        return;
      }

      if (event.step === 'complete') {
        setSummary(event);
        setSteps((prev) =>
          prev.map((s) => (s.state === 'active' ? { ...s, state: 'done' } : s))
        );
        setDone(true);
        es.close();
        return;
      }

      if (event.step === 'searching_done') {
        setSteps((prev) =>
          prev.map((s) =>
            s.id === 'searching'
              ? { ...s, state: 'done', note: `${event.count?.toLocaleString()} candidates found` }
              : s
          )
        );
        return;
      }

      // Per-step progress update (searching / fetching_details / summarizing / classifying)
      setSteps((prev) =>
        prev.map((s) => {
          if (s.id !== event.step) return s;
          return {
            ...s,
            state: 'active',
            count: event.count,
            total: event.total,
          };
        })
      );
    };

    es.onerror = () => {
      if (!done) {
        setErrorMsg('Connection to server lost.');
        setDone(true);
      }
      es.close();
    };

    return () => {
      es.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-base font-semibold text-gray-900 mb-5">Running Ingestion</h2>

        <div className="space-y-4">
          {steps.map((step) => (
            <StepRow key={step.id} step={step} />
          ))}
        </div>

        {/* Summary */}
        {summary && (
          <div className="mt-5 pt-4 border-t text-sm text-gray-600 space-y-1">
            <p className="font-medium text-gray-800">Complete</p>
            <p>{summary.new} new &nbsp;·&nbsp; {summary.updated} updated &nbsp;·&nbsp; {summary.relevant} relevant &nbsp;·&nbsp; {summary.irrelevant} irrelevant</p>
            {(summary.fetch_errors ?? 0) > 0 && (
              <p className="text-amber-600">{summary.fetch_errors} fetch error{summary.fetch_errors !== 1 ? 's' : ''}</p>
            )}
            {(summary.classify_errors ?? 0) > 0 && (
              <p className="text-amber-600">{summary.classify_errors} classification error{summary.classify_errors !== 1 ? 's' : ''}</p>
            )}
          </div>
        )}

        {/* Error */}
        {errorMsg && (
          <div className="mt-5 pt-4 border-t text-sm text-red-600">
            {errorMsg}
          </div>
        )}

        {/* Close button — only when finished */}
        {done && (
          <button
            onClick={onClose}
            className="mt-5 w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        )}

        {/* Cancel while running */}
        {!done && (
          <button
            onClick={() => {
              esRef.current?.close();
              onClose();
            }}
            className="mt-5 w-full px-4 py-2 border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

// ── Step row sub-component ────────────────────────────────────────────────────

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
      <span className="w-4 h-4 flex items-center justify-center text-green-500 shrink-0">
        ✓
      </span>
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
      <span className="w-4 h-4 flex items-center justify-center text-red-500 shrink-0 text-xs font-bold">
        ✕
      </span>
    );
  }
  // waiting
  return <span className="w-4 h-4 rounded-full border border-gray-300 shrink-0" />;
}
