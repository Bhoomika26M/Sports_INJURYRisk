import React from 'react';

/**
 * Shows how one analysis compares against the athlete's rolling baseline.
 *
 * The comparison is a *recorded historical fact* (computed once, when the
 * analysis completed), not a live calculation - so the same video always shows
 * the same verdict even after the athlete uploads more videos.
 */

const VERDICT_STYLES = {
  deterioration: {
    badge: 'bg-red-100 text-red-800 border-red-200',
    label: 'Worse',
    arrow: '▲',
    text: 'text-red-700',
  },
  improvement: {
    badge: 'bg-green-100 text-green-800 border-green-200',
    label: 'Better',
    arrow: '▼',
    text: 'text-green-700',
  },
  neutral: {
    badge: 'bg-gray-100 text-gray-600 border-gray-200',
    label: 'Stable',
    arrow: '—',
    text: 'text-gray-600',
  },
};

const STATUS_HEADLINE = {
  no_history: {
    title: 'Baseline established',
    tone: 'bg-gray-50 border-gray-200 text-gray-700',
  },
  insufficient_history: {
    title: 'Limited history',
    tone: 'bg-amber-50 border-amber-200 text-amber-800',
  },
  stable: {
    title: 'Stable vs. baseline',
    tone: 'bg-green-50 border-green-200 text-green-800',
  },
  changed: {
    title: 'Change detected vs. baseline',
    tone: 'bg-blue-50 border-blue-200 text-blue-800',
  },
};

const fmt = (value, digits = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return Number(value).toFixed(digits);
};

const SIGNED = (value, digits = 1) => {
  if (value === null || value === undefined) return '—';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}`;
};

const ComparisonPanel = ({ comparison, loading, error }) => {
  if (loading) {
    return (
      <div className="mb-6 p-4 bg-white rounded border-2 border-gray-200">
        <h2 className="text-xl font-semibold mb-2">Comparison with History</h2>
        <p className="text-sm text-gray-500">Loading baseline comparison…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-6 p-4 bg-white rounded border-2 border-gray-200">
        <h2 className="text-xl font-semibold mb-2">Comparison with History</h2>
        <p className="text-sm text-gray-500">{error}</p>
      </div>
    );
  }

  if (!comparison) return null;

  const headline = STATUS_HEADLINE[comparison.status] || STATUS_HEADLINE.no_history;
  const deltas = comparison.deltas || [];

  return (
    <div className="mb-6 p-4 bg-white rounded border-2 border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold">Comparison with History</h2>
        {comparison.baseline_size > 0 && (
          <span className="text-xs text-gray-500">
            vs. {comparison.baseline_size} prior{' '}
            {comparison.baseline_size === 1 ? 'analysis' : 'analyses'}
          </span>
        )}
      </div>

      <div className={`p-3 rounded border mb-4 ${headline.tone}`}>
        <div className="font-semibold">{headline.title}</div>
        {comparison.summary && (
          <div className="text-sm mt-1">{comparison.summary}</div>
        )}
      </div>

      {deltas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2 pr-4">Metric</th>
                <th className="py-2 pr-4">This analysis</th>
                <th className="py-2 pr-4">Baseline</th>
                <th className="py-2 pr-4">Change</th>
                <th className="py-2 pr-4">Baseline range</th>
                <th className="py-2">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {deltas.map((d) => {
                const style = VERDICT_STYLES[d.verdict] || VERDICT_STYLES.neutral;
                const unit = d.unit ? ` ${d.unit}` : '';
                return (
                  <tr
                    key={d.metric}
                    className={`border-b last:border-b-0 ${d.notable ? 'font-medium' : ''}`}
                  >
                    <td className="py-2 pr-4">{d.label}</td>
                    <td className="py-2 pr-4">
                      {fmt(d.current)}
                      {unit}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {fmt(d.baseline)}
                      {unit}
                    </td>
                    <td className={`py-2 pr-4 ${style.text}`}>
                      {SIGNED(d.delta)}
                      {unit}
                      {d.percent_change !== null &&
                        d.percent_change !== undefined && (
                          <span className="text-xs text-gray-500 ml-1">
                            ({SIGNED(d.percent_change, 0)}%)
                          </span>
                        )}
                    </td>
                    <td className="py-2 pr-4 text-gray-500 text-xs">
                      {d.baseline_range?.[0] !== undefined
                        ? `${fmt(d.baseline_range[0])} – ${fmt(d.baseline_range[1])}`
                        : '—'}
                    </td>
                    <td className="py-2">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs ${style.badge}`}
                      >
                        <span aria-hidden="true">{style.arrow}</span>
                        {style.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {deltas.length === 0 && comparison.status !== 'no_history' && (
        <p className="text-sm text-gray-500">
          No comparable metrics were recorded for this activity type.
        </p>
      )}

      {/* The baseline reference values themselves - shown even when there is
          not yet enough history to produce a comparison. */}
      {comparison.baseline_metrics?.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Athlete baseline ({comparison.baseline_size} prior{' '}
            {comparison.baseline_size === 1 ? 'analysis' : 'analyses'}, same activity)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {comparison.baseline_metrics.map((m) => (
              <div key={m.metric} className="p-2 bg-gray-50 rounded border text-sm">
                <div className="text-xs text-gray-500">{m.label}</div>
                <div className="font-semibold">
                  {fmt(m.mean)}
                  {m.unit ? ` ${m.unit}` : ''}
                </div>
                <div className="text-xs text-gray-400">
                  range {fmt(m.min)}–{fmt(m.max)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparisonPanel;
