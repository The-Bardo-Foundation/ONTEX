import { useEffect, useMemo, useRef, useState } from 'react';
import {
  activatePromptVersion,
  generateAiAdvice,
  getAdviceHistory,
  getClassifierPrompt,
  getInsights,
  runBacktest,
  saveClassifierPrompt,
} from '../api';
import type {
  AccuracyAdvice,
  AdviceRun,
  BacktestResponse,
  ClassifierPromptResponse,
  InsightsResponse,
  PatternBucket,
  PromptVersion,
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

const LABEL_BADGE: Record<string, string> = {
  confident: 'bg-green-50 text-green-700',
  unsure: 'bg-amber-50 text-amber-700',
  reject: 'bg-red-50 text-red-700',
  approved: 'bg-green-50 text-green-700',
  rejected: 'bg-red-50 text-red-700',
};

function Badge({ value }: { value: string | null }) {
  const key = (value ?? '').toLowerCase();
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
        LABEL_BADGE[key] ?? 'bg-gray-100 text-gray-600'
      }`}
    >
      {value ?? 'n/a'}
    </span>
  );
}

function ExampleList({ title, examples, emptyText }: {
  title: string;
  examples: TrialExample[];
  emptyText: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
        {examples.length > 0 && (
          <span className="text-xs font-medium text-gray-400">{examples.length}</span>
        )}
      </div>
      {examples.length === 0 ? (
        <div className="px-5 py-4 text-sm text-gray-500">{emptyText}</div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {examples.map((ex) => (
            <li key={ex.nct_id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate text-sm font-medium text-gray-900" title={ex.brief_title}>
                  {ex.brief_title}
                </span>
                <span className="shrink-0 text-xs text-gray-400">{ex.nct_id}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-xs text-gray-500">
                <Badge value={ex.ai_relevance_label} />
                <span aria-hidden>→</span>
                <Badge value={ex.human_decision} />
              </div>
              {ex.reviewer_notes && (
                <p className="mt-1.5 line-clamp-2 text-xs text-gray-600" title={ex.reviewer_notes}>
                  {ex.reviewer_notes}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// With only ~200 trials sourced worldwide, most segments hold a handful of
// decisions. A "100% rejected" country built on 1–2 trials is noise, not a
// pattern, so we only surface segments that clear a minimum decision count.
const MIN_PATTERN_DECISIONS = 3;

function leanLabel(approved: number, rejected: number): { text: string; className: string } {
  const total = approved + rejected;
  if (total === 0) return { text: 'no decisions', className: 'text-gray-400' };
  const approvalShare = approved / total;
  if (approvalShare >= 0.7) return { text: 'leans approve', className: 'text-green-600' };
  if (approvalShare <= 0.3) return { text: 'leans reject', className: 'text-red-600' };
  return { text: 'mixed', className: 'text-gray-500' };
}

function PatternTable({ patterns }: { patterns: PatternBucket[] }) {
  const significant = patterns
    .filter((p) => p.approved + p.rejected >= MIN_PATTERN_DECISIONS)
    .sort((a, b) => b.approved + b.rejected - (a.approved + a.rejected));

  if (significant.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-5 py-4 text-sm text-gray-500">
        Not enough resolved unsure trials yet. Segments appear here once they reach{' '}
        {MIN_PATTERN_DECISIONS} reviewer decisions, so the lean reflects a real pattern rather
        than a small-sample coincidence.
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
            <th className="px-5 py-3 font-medium text-right">Decisions</th>
            <th className="px-5 py-3 font-medium text-right">Approved</th>
            <th className="px-5 py-3 font-medium text-right">Rejected</th>
            <th className="px-5 py-3 font-medium text-right">Lean</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {significant.map((p) => {
            const total = p.approved + p.rejected;
            const lean = leanLabel(p.approved, p.rejected);
            return (
              <tr key={`${p.dimension}:${p.value}`}>
                <td className="px-5 py-2.5 text-gray-500">{DIMENSION_LABEL[p.dimension] ?? p.dimension}</td>
                <td className="px-5 py-2.5 font-medium text-gray-900">{p.value}</td>
                <td className="px-5 py-2.5 text-right text-gray-500">{total}</td>
                <td className="px-5 py-2.5 text-right text-green-600">{p.approved}</td>
                <td className="px-5 py-2.5 text-right text-red-600">{p.rejected}</td>
                <td className={`px-5 py-2.5 text-right font-medium ${lean.className}`}>{lean.text}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

type DiffSpan =
  | { kind: 'same'; text: string }
  | { kind: 'del'; text: string }
  | { kind: 'ins'; text: string };

function normalizeContent(text: string): string {
  return text.trim().replace(/\s+/g, ' ');
}

function lcsTable<T>(a: T[], b: T[], eq: (x: T, y: T) => boolean): number[][] {
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = eq(a[i], b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  return dp;
}

type LineOp =
  | { kind: 'same'; text: string }
  | { kind: 'del'; text: string }
  | { kind: 'ins'; text: string }
  | { kind: 'mod'; from: string; to: string };

function draftLineSuffix(draft: string, lineIndex: number, lineCount: number): string {
  if (lineIndex < lineCount - 1) return '\n';
  return draft.endsWith('\n') ? '\n' : '';
}

function alignPhysicalLines(from: string, to: string): LineOp[] {
  const aLines = from.split('\n');
  const bLines = to.split('\n');
  const aNorm = aLines.map((l) => normalizeContent(l));
  const bNorm = bLines.map((l) => normalizeContent(l));
  const dp = lcsTable(aNorm, bNorm, (x, y) => x === y && x !== '');
  const ops: LineOp[] = [];
  let i = 0;
  let j = 0;

  const bSuffix = (idx: number) => draftLineSuffix(to, idx, bLines.length);
  const aSuffix = (idx: number) => draftLineSuffix(from, idx, aLines.length);

  while (i < aLines.length && j < bLines.length) {
    if (aNorm[i] === bNorm[j]) {
      ops.push({
        kind: 'same',
        text: bNorm[j] === '' ? '\n' : `${bLines[j]}${bSuffix(j)}`,
      });
      i++;
      j++;
      continue;
    }

    if (dp[i + 1][j] > dp[i][j + 1]) {
      ops.push({
        kind: 'del',
        text: aNorm[i] === '' ? '\n' : `${aLines[i]}${aSuffix(i)}`,
      });
      i++;
      continue;
    }

    ops.push({
      kind: 'ins',
      text: bNorm[j] === '' ? '\n' : `${bLines[j]}${bSuffix(j)}`,
    });
    j++;
  }

  while (i < aLines.length) {
    const idx = i++;
    ops.push({
      kind: 'del',
      text: aNorm[idx] === '' ? '\n' : `${aLines[idx]}${aSuffix(idx)}`,
    });
  }
  while (j < bLines.length) {
    const idx = j++;
    ops.push({
      kind: 'ins',
      text: bNorm[idx] === '' ? '\n' : `${bLines[idx]}${bSuffix(idx)}`,
    });
  }

  const merged: LineOp[] = [];
  for (let k = 0; k < ops.length; k++) {
    const cur = ops[k];
    const next = ops[k + 1];
    if (
      cur.kind === 'del' &&
      next?.kind === 'ins' &&
      cur.text.trim() &&
      next.text.trim()
    ) {
      merged.push({
        kind: 'mod',
        from: cur.text,
        to: next.text,
      });
      k++;
      continue;
    }
    merged.push(cur);
  }
  return merged;
}

const EDITOR_FONT =
  'box-border whitespace-pre p-3 font-mono text-xs leading-5 [tab-size:2]';

function markChangedDraftLines(active: string, draft: string): boolean[] {
  const bLines = draft.split('\n');
  const changed = new Array<boolean>(bLines.length).fill(false);
  const ops = alignPhysicalLines(active, draft);
  let bi = 0;

  for (const op of ops) {
    if (op.kind === 'del') continue;

    if (bi >= bLines.length) break;

    if (op.kind === 'same') {
      bi++;
    } else if (op.kind === 'ins' || op.kind === 'mod') {
      changed[bi] = true;
      bi++;
    }
  }

  return changed;
}

function buildDraftOnlyHighlights(active: string, draft: string): DiffSpan[] {
  const lines = draft.split('\n');
  const changed = markChangedDraftLines(active, draft);

  return lines.map((line, i) => ({
    kind: changed[i] ? 'ins' : 'same',
    text: line + draftLineSuffix(draft, i, lines.length),
  })) as DiffSpan[];
}

function collectRemovedLines(active: string, draft: string): string[] {
  const ops = alignPhysicalLines(active, draft);
  return ops
    .filter((op): op is { kind: 'del'; text: string } => op.kind === 'del' && op.text.trim() !== '')
    .map((op) => op.text.trimEnd());
}

function renderHighlightSpans(spans: DiffSpan[]) {
  return spans.map((span, idx) => {
    if (span.kind === 'same') {
      return (
        <span key={idx} className="text-gray-800">
          {span.text}
        </span>
      );
    }
    return (
      <span key={idx} className="bg-green-100 text-green-800">
        {span.text}
      </span>
    );
  });
}

function PromptDiffEditor({
  activeContent,
  draft,
  onChange,
}: {
  activeContent: string;
  draft: string;
  onChange: (value: string) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlights = useMemo(
    () => buildDraftOnlyHighlights(activeContent, draft),
    [activeContent, draft],
  );
  const removed = useMemo(
    () => collectRemovedLines(activeContent, draft),
    [activeContent, draft],
  );
  const hasChanges = highlights.some((s) => s.kind === 'ins') || removed.length > 0;

  useEffect(() => {
    const backdrop = backdropRef.current;
    const textarea = textareaRef.current;
    if (!backdrop || !textarea) return;
    textarea.style.height = `${backdrop.scrollHeight}px`;
  }, [draft, highlights, hasChanges]);

  return (
    <div className="mt-2 overflow-hidden rounded border border-gray-200 bg-white">
      {removed.length > 0 && (
        <div className="border-b border-red-100 bg-red-50/60 px-3 py-2 text-xs leading-relaxed">
          <div className="mb-1 font-medium text-red-700">Removed vs active</div>
          {removed.map((line, idx) => (
            <div key={idx} className="text-red-800 line-through decoration-red-400">
              {line}
            </div>
          ))}
        </div>
      )}

      <div
        ref={scrollRef}
        className="relative h-72 overflow-auto [scrollbar-gutter:stable]"
      >
        <div className="relative min-h-full">
          <div
            ref={backdropRef}
            aria-hidden
            className={`pointer-events-none min-h-full ${EDITOR_FONT}`}
          >
            {hasChanges ? (
              renderHighlightSpans(highlights)
            ) : (
              <span className="text-gray-800">{draft}</span>
            )}
          </div>
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => onChange(e.target.value)}
            spellCheck={false}
            className={`absolute left-0 top-0 m-0 w-full resize-none overflow-hidden border-0 bg-transparent text-transparent caret-gray-900 focus:outline-none focus:ring-0 ${EDITOR_FONT}`}
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-gray-100 px-3 py-1.5 text-[11px] text-gray-400">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-green-100 ring-1 ring-green-200" />
          Added vs active
        </span>
        {removed.length > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-sm bg-red-100 ring-1 ring-red-200" />
            Removed vs active
          </span>
        )}
        <span>Edit directly — highlights update as you type</span>
      </div>
    </div>
  );
}

function metricDelta(
  candidate: number | null,
  baseline: number | null,
  lowerIsBetter: boolean,
): string {
  if (candidate === null || baseline === null) return 'text-gray-700';
  if (candidate === baseline) return 'text-gray-700';
  const improved = lowerIsBetter ? candidate < baseline : candidate > baseline;
  return improved ? 'text-green-600' : 'text-red-600';
}

function BacktestResultView({ result }: { result: BacktestResponse }) {
  const { candidate, baseline } = result;
  const rows: {
    label: string;
    base: string;
    cand: string;
    className: string;
  }[] = [
    {
      label: 'Confident error rate',
      base: pct(baseline.confident_error_rate),
      cand: pct(candidate.confident_error_rate),
      className: metricDelta(candidate.confident_error_rate, baseline.confident_error_rate, true),
    },
    {
      label: 'Unsure rate',
      base: pct(baseline.unsure_rate),
      cand: pct(candidate.unsure_rate),
      className: metricDelta(candidate.unsure_rate, baseline.unsure_rate, true),
    },
    {
      label: 'False negatives',
      base: String(baseline.false_negative_count),
      cand: String(candidate.false_negative_count),
      className: metricDelta(
        candidate.false_negative_count,
        baseline.false_negative_count,
        true,
      ),
    },
    {
      label: 'Correct auto-decisions',
      base: String(baseline.correct_auto_count),
      cand: String(candidate.correct_auto_count),
      className: metricDelta(candidate.correct_auto_count, baseline.correct_auto_count, false),
    },
  ];
  return (
    <div className="mt-3 rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-2 text-xs text-gray-500">
        Backtested on {result.sample_size} already-decided trials. Green means the candidate
        prompt improves on the current one.
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
            <th className="py-1 font-medium">Metric</th>
            <th className="py-1 font-medium text-right">Current</th>
            <th className="py-1 font-medium text-right">Candidate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r) => (
            <tr key={r.label}>
              <td className="py-1.5 text-gray-600">{r.label}</td>
              <td className="py-1.5 text-right text-gray-500">{r.base}</td>
              <td className={`py-1.5 text-right font-semibold ${r.className}`}>{r.cand}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PromptWorkbench({
  proposed,
  activeContent,
  onApplied,
}: {
  proposed: string;
  activeContent: string;
  onApplied: () => void;
}) {
  const [draft, setDraft] = useState(proposed);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(proposed);
    setBacktest(null);
    setError(null);
  }, [proposed]);

  const handleBacktest = async () => {
    setBacktestLoading(true);
    setError(null);
    try {
      setBacktest(await runBacktest(draft));
    } catch {
      setError('Backtest failed. The AI key may be missing or the request timed out.');
    } finally {
      setBacktestLoading(false);
    }
  };

  const handleApply = async () => {
    if (!window.confirm('Apply this prompt? It becomes the active classifier prompt for all future ingestions.')) {
      return;
    }
    setApplying(true);
    setError(null);
    try {
      await saveClassifierPrompt(draft, 'Applied from AI recommendation.', 'ai');
      onApplied();
    } catch {
      setError('Could not apply the prompt.');
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-blue-700">
        Proposed classifier prompt
      </h4>
      <p className="mt-1 text-xs text-gray-500">
        Edit in place — green highlights show additions vs the active prompt. Backtest, then
        apply to make it active.
      </p>
      <PromptDiffEditor
        activeContent={activeContent}
        draft={draft}
        onChange={setDraft}
      />

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={handleBacktest}
          disabled={backtestLoading || applying || !draft.trim()}
          className="rounded-md border border-blue-600 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"
        >
          {backtestLoading ? 'Backtesting…' : 'Run backtest'}
        </button>
        <button
          onClick={handleApply}
          disabled={applying || backtestLoading || !draft.trim()}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {applying ? 'Applying…' : 'Apply & activate'}
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {backtest && <BacktestResultView result={backtest} />}
    </div>
  );
}

function AdvicePanel({
  advice,
  activeContent,
  onApplied,
}: {
  advice: AccuracyAdvice;
  activeContent: string;
  onApplied: () => void;
}) {
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
      {advice.proposed_system_prompt && (
        <PromptWorkbench
          proposed={advice.proposed_system_prompt}
          activeContent={activeContent}
          onApplied={onApplied}
        />
      )}
    </div>
  );
}

function ClassifierPromptSection({
  data,
  onRefresh,
}: {
  data: ClassifierPromptResponse | null;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showActive, setShowActive] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  if (!data || !data.active) {
    return <p className="mt-2 text-sm text-gray-500">No classifier prompt versions yet.</p>;
  }

  const handleActivate = async (version: PromptVersion) => {
    if (version.is_active) return;
    if (!window.confirm('Roll back to this prompt version and make it active?')) return;
    setBusyId(version.id);
    try {
      await activatePromptVersion(version.id);
      onRefresh();
    } finally {
      setBusyId(null);
    }
  };

  const { active, versions } = data;

  return (
    <div className="mt-2 rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between px-5 py-3">
        <div className="text-sm">
          <span className="font-medium text-gray-900">Active version #{active.id}</span>
          <span className="ml-2 text-xs text-gray-400">
            {active.source} · {new Date(active.created_at).toLocaleString()}
            {active.created_by ? ` · ${active.created_by}` : ''}
          </span>
        </div>
        <button
          onClick={() => setShowActive((s) => !s)}
          className="text-xs font-medium text-blue-600 hover:underline"
        >
          {showActive ? 'Hide prompt' : 'View prompt'}
        </button>
      </div>
      {showActive && (
        <pre className="mx-5 mb-3 max-h-72 overflow-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs leading-relaxed text-gray-700">
          {active.content}
        </pre>
      )}

      <div className="border-t border-gray-100 px-5 py-2">
        <button
          onClick={() => setExpanded((s) => !s)}
          className="text-xs font-medium text-gray-600 hover:underline"
        >
          {expanded ? 'Hide version history' : `Version history (${versions.length})`}
        </button>
      </div>
      {expanded && (
        <ul className="divide-y divide-gray-100">
          {versions.map((v) => (
            <li key={v.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500">
                <span className="font-medium text-gray-700">#{v.id}</span>
                <span>{v.source}</span>
                <span>{new Date(v.created_at).toLocaleString()}</span>
                {v.note && <span className="text-gray-400">{v.note}</span>}
              </div>
              {v.is_active ? (
                <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                  active
                </span>
              ) : (
                <button
                  onClick={() => handleActivate(v)}
                  disabled={busyId === v.id}
                  className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                >
                  {busyId === v.id ? 'Activating…' : 'Roll back'}
                </button>
              )}
            </li>
          ))}
        </ul>
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
  const [promptData, setPromptData] = useState<ClassifierPromptResponse | null>(null);

  const refreshHistory = () => {
    getAdviceHistory()
      .then((data) => setHistory(data.runs))
      .catch(() => {
        /* history is non-critical; ignore load errors */
      });
  };

  const refreshPrompt = () => {
    getClassifierPrompt()
      .then((data) => setPromptData(data))
      .catch(() => {
        /* prompt info is non-critical; ignore load errors */
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
    refreshPrompt();
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
    } catch (err: unknown) {
      const detail =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setAdviceError(
        typeof detail === 'string' && detail
          ? detail
          : 'Could not generate AI recommendations.',
      );
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
        <h3 className="text-sm font-semibold text-gray-900">Reliable segment leans</h3>
        <p className="mt-0.5 mb-2 text-xs text-gray-500">
          Segments with at least {MIN_PATTERN_DECISIONS} reviewer decisions, sorted by sample
          size. Low-volume segments are hidden so a handful of trials from one country can't
          masquerade as a pattern. A consistent lean here is a candidate to teach the classifier
          to decide confidently instead of deferring.
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
        {advice && (
          <AdvicePanel
            advice={advice}
            activeContent={promptData?.active?.content ?? ''}
            onApplied={refreshPrompt}
          />
        )}
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">Classifier prompt</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          The active prompt is what the ingestion classifier uses. Every applied version is kept
          so you can roll back.
        </p>
        <ClassifierPromptSection data={promptData} onRefresh={refreshPrompt} />
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-900">Advice history</h3>
        <AdviceHistory runs={history} />
      </div>
    </div>
  );
}
