import { useEffect, useState } from 'react';
import { getStatistics } from '../api';
import type { StatisticsResponse } from '../types';

const LABEL_DISPLAY: Record<string, string> = {
  confident: 'Confident',
  unsure: 'Unsure',
  reject: 'Reject',
  none: 'No label',
};

function formatLabel(label: string): string {
  return LABEL_DISPLAY[label] ?? label;
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
      <div className={`text-3xl font-semibold ${accent}`}>{value}</div>
      <div className="mt-1 text-sm text-gray-500">{label}</div>
    </div>
  );
}

export function StatisticsPage() {
  const [stats, setStats] = useState<StatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getStatistics()
      .then((data) => {
        if (!cancelled) {
          setStats(data);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Could not load statistics.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const confidentRate = stats?.ai_confident_approval_rate;
  const confidentRateDisplay =
    confidentRate === null || confidentRate === undefined
      ? '—'
      : `${Math.round(confidentRate * 100)}%`;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-5xl mx-auto px-8 py-8">
        <h1 className="text-2xl font-semibold text-gray-900">Statistics</h1>
        <p className="mt-1 text-sm text-gray-500">
          How many trials are accepted by an admin versus rejected, and how well the AI
          relevance label agrees with the reviewer's decision.
        </p>

        {loading && (
          <div className="mt-8 text-sm text-gray-500">Loading statistics…</div>
        )}

        {error && !loading && (
          <div className="mt-8 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {stats && !loading && !error && (
          <>
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              <MetricCard
                label="Approved by admin"
                value={stats.approved_by_admin}
                accent="text-green-600"
              />
              <MetricCard
                label="Rejected by admin"
                value={stats.rejected_by_admin}
                accent="text-red-600"
              />
              <MetricCard
                label="Pending review"
                value={stats.pending_review}
                accent="text-amber-600"
              />
              <MetricCard
                label="AI auto-rejected"
                value={stats.ai_auto_rejected}
                accent="text-gray-600"
              />
              <MetricCard
                label="Total trials"
                value={stats.total}
                accent="text-gray-900"
              />
            </div>

            <div className="mt-6 bg-white border border-gray-200 rounded-lg shadow-sm p-6">
              <div className="text-sm text-gray-500">
                AI "confident" trials also approved by a human
              </div>
              <div className="mt-1 flex items-baseline gap-3">
                <span className="text-4xl font-semibold text-blue-600">
                  {confidentRateDisplay}
                </span>
                <span className="text-sm text-gray-500">
                  of reviewer-decided AI-confident trials were approved
                </span>
              </div>
              <p className="mt-2 text-xs text-gray-400">
                Goal: drive this toward 100% so confident AI classifications can be trusted
                without human latency. Shows "—" until at least one confident trial has been
                approved or rejected by a human.
              </p>
            </div>

            <div className="mt-6 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-900">
                  AI label vs. human decision
                </h2>
                <p className="mt-0.5 text-xs text-gray-500">
                  Each AI relevance label broken down by what reviewers decided.
                </p>
              </div>
              {stats.by_ai_label.length === 0 ? (
                <div className="px-6 py-6 text-sm text-gray-500">No data yet.</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-gray-400">
                      <th className="px-6 py-3 font-medium">AI label</th>
                      <th className="px-6 py-3 font-medium text-right">Approved</th>
                      <th className="px-6 py-3 font-medium text-right">Rejected</th>
                      <th className="px-6 py-3 font-medium text-right">Pending</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {stats.by_ai_label.map((row) => (
                      <tr key={row.label}>
                        <td className="px-6 py-3 font-medium text-gray-900">
                          {formatLabel(row.label)}
                        </td>
                        <td className="px-6 py-3 text-right text-green-600">{row.approved}</td>
                        <td className="px-6 py-3 text-right text-red-600">{row.rejected}</td>
                        <td className="px-6 py-3 text-right text-amber-600">{row.pending}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
