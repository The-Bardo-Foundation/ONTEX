import { useEffect, useState } from 'react';
import { generateAiAdvice, getAdviceHistory, getInsights } from '../api';
import type {
  AccuracyAdvice,
  AdviceRun,
  InsightsResponse,
  PatternBucket,
  TrialExample,
} from '../types';

const DIMENSION_LABEL: Record<string, string> = {
  phase: 'Phase',
  study_type: 'Study type',
  location_country: 'Country',
};

function pct(rate: number | null): string {
  return rate === null ? '—' : `${Math.round(rate * 100)}%`;
}

function ExampleList({ title, examples, emptyText }: {
  title: string;
  examples: TrialExample[];
  emptyText: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      </div>
      {examples.length === 0 ? (
        <div className="px-5 py-4 text-sm text-gray-500">{emptyText}</div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {examples.map((ex) => (
            <li key={ex.nct_id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-gray-900">{ex.brief_title}</span>
                <span className="shrink-0 text-xs text-gray-400">{ex.nct_id}</span>
              </div>
              <div className="mt-1 grid gap-1 text-xs text-gray-600 sm:grid-cols-2">
                <div>
                  <span className="font-medium text-gray-500">AI ({ex.ai_relevance_label ?? 'n/a'}): </span>
                  {ex.ai_relevance_reason ?? 'n/a'}
                </div>
                <div>
                  <span className="font-medium text-gray-500">
                    Reviewer ({ex.human_decision}):{' '}
                  </span>
                  {ex.reviewer_notes ?? 'n/a'}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PatternTable({ patterns }: { patterns: PatternBucket[] }) {
  if (patterns.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-5 py-4 text-sm text-gray-500">
        No resolved unsure trials yet.
      </div>
    );
  }
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
            <th className="px-5 py-3 font-medium">Segment</th>
            <th className="px-5 py-3 font-medium">Value</th>
            <th className="px-5 py-3 font-medium text-right">Approved</th>
            <th className="px-5 py-3 font-medium text-right">Rejected</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {patterns.map((p) => (
            <tr key={`${p.dimension}:${p.value}`}>
              <td className="px-5 py-2.5 text-gray-500">{DIMENSION_LABEL[p.dimension] ?? p.dimension}</td>
              <td className="px-5 py-2.5 font-medium text-gray-900">{p.value}</td>
              <td className="px-5 py-2.5 text-right text-green-600">{p.approved}</td>
              <td className="px-5 py-2.5 text-right text-red-600">{p.rejected}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdvicePanel({ advice }: { advice: AccuracyAdvice }) {
  return (
    <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-5 py-4">
      <p className="text-sm text-gray-800">{advice.summary}</p>
      {advice.patterns.length > 0 && (
        <div className="mt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-blue-700">Patterns</h4>
          <ul className="mt-1 list-disc pl-5 text-sm text-gray-700 space-y-1">
            {advice.patterns.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      {advice.recommendations.length > 0 && (
        <div className="mt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Recommendations
          </h4>
          <ul className="mt-1 list-disc pl-5 text-sm text-gray-700 space-y-1">
            {advice.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AdviceHistory({ runs }: { runs: AdviceRun[] }) {
  if (runs.length === 0) {
    return (
      <p className="mt-2 text-sm text-gray-500">
        No saved runs yet. Each generation is stored so you can track whether prompt changes
        move the rates over time.
      </p>
    );
  }
  return (
    <ul className="mt-2 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white shadow-sm">
      {runs.map((run) => (
        <li key={run.id} className="px-5 py-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
            <span className="font-medium text-gray-700">
              {new Date(run.created_at).toLocaleString()}
            </span>
            <span>confident error {pct(run.confident_error_rate)}</span>
            <span>unsure approval {pct(run.unsure_approval_rate)}</span>
            <span>false negatives {run.false_negative_count}</span>
            <span>{run.examples_used} examples</span>
            <span className="text-gray-400">{run.ai_model}</span>
          </div>
          {run.summary && <p className="mt-1 text-sm text-gray-700">{run.summary}</p>}
        </li>
      ))}
    </ul>
  );
}

export function AccuracyInsights() {
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [advice, setAdvice] = useState<AccuracyAdvice | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [adviceError, setAdviceError] = useState<string | null>(null);
  const [history, setHistory] = useState<AdviceRun[]>([]);

  const refreshHistory = () => {
    getAdviceHistory()
      .then((data) => setHistory(data.runs))
      .catch(() => {
        /* history is non-critical; ignore load errors */
      });
  };

  useEffect(() => {
    let cancelled = false;
    getInsights()
      .then((data) => {
        if (!cancelled) {
          setInsights(data);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Could not load accuracy insights.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    refreshHistory();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerateAdvice = async () => {
    setAdviceLoading(true);
    setAdviceError(null);
    try {
      const result = await generateAiAdvice();
      setAdvice(result);
      refreshHistory();
    } catch {
      setAdviceError('Could not generate AI recommendations.');
    } finally {
      setAdviceLoading(false);
    }
  };

  if (loading) {
    return <div className="mt-10 text-sm text-gray-500">Loading accuracy insights…</div>;
  }
  if (error || !insights) {
    return (
      <div className="mt-10 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error ?? 'Could not load accuracy insights.'}
      </div>
    );
  }

  const guardrailBreached = insights.confident_rejected > 0;

  return (
    <div className="mt-10">
      <h2 className="text-xl font-semibold text-gray-900">Accuracy insights</h2>
      <p className="mt-1 text-sm text-gray-500">
        Confident trials are auto-published, so the focus is keeping confident errors at zero
        and shrinking the unsure bucket that reviewers must process by hand.
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          className={`rounded-lg border p-5 shadow-sm ${
            guardrailBreached ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'
          }`}
        >
          <div className="text-sm text-gray-500">Confident error rate (guardrail)</div>
          <div
            className={`mt-1 text-3xl font-semibold ${
              guardrailBreached ? 'text-red-600' : 'text-green-600'
            }`}
          >
            {pct(insights.confident_error_rate)}
          </div>
          <div className="mt-1 text-xs text-gray-400">
            {insights.confident_rejected} of {insights.confident_approved + insights.confident_rejected}{' '}
            decided confident trials were rejected by a human. Must stay at 0% to auto-publish safely.
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm text-gray-500">Unsure approval rate</div>
          <div className="mt-1 text-3xl font-semibold text-amber-600">
            {pct(insights.unsure_approval_rate)}
          </div>
          <div className="mt-1 text-xs text-gray-400">
            {insights.unsure_approved} approved / {insights.unsure_rejected} rejected among
            reviewer-decided unsure trials. {insights.unsure_pending} still pending.
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="text-sm text-gray-500">False negatives</div>
          <div className="mt-1 text-3xl font-semibold text-gray-900">
            {insights.false_negative_count}
          </div>
          <div className="mt-1 text-xs text-gray-400">
            AI rejected, but a human restored and approved them.
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">Unsure trials by segment</h3>
        <p className="mt-0.5 mb-2 text-xs text-gray-500">
          Segments that are almost always approved or rejected are candidates to teach the
          classifier to decide confidently instead of deferring.
        </p>
        <PatternTable patterns={insights.unsure_patterns} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <ExampleList
          title="Confident, but rejected (errors)"
          examples={insights.confident_false_positives}
          emptyText="None — confident trials all held up."
        />
        <ExampleList
          title="Resolved unsure trials"
          examples={insights.unsure_resolved}
          emptyText="No unsure trials decided yet."
        />
        <ExampleList
          title="False negatives"
          examples={insights.false_negatives}
          emptyText="None detected."
        />
      </div>

      <div className="mt-6">
        <button
          onClick={handleGenerateAdvice}
          disabled={adviceLoading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {adviceLoading ? 'Analysing…' : 'Generate AI recommendations'}
        </button>
        {adviceError && <span className="ml-3 text-sm text-red-600">{adviceError}</span>}
        {advice && <AdvicePanel advice={advice} />}
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">Advice history</h3>
        <AdviceHistory runs={history} />
      </div>
    </div>
  );
}
