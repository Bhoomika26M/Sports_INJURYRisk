import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { athletesAPI } from '../services/api';

/**
 * Chronological analysis history for one athlete, with per-activity trends.
 *
 * Each row links to the full analysis for that video, so the athlete's
 * progression can be traced session by session.
 */

const RISK_BADGE = {
  low: 'bg-green-100 text-green-800',
  moderate: 'bg-amber-100 text-amber-800',
  high: 'bg-orange-100 text-orange-800',
  very_high: 'bg-red-100 text-red-800',
};

const DIRECTION_STYLES = {
  improving: { text: 'text-green-700', arrow: '▼', label: 'Improving' },
  worsening: { text: 'text-red-700', arrow: '▲', label: 'Worsening' },
  stable: { text: 'text-gray-600', arrow: '—', label: 'Stable' },
  unknown: { text: 'text-gray-500', arrow: '—', label: 'Unknown' },
};

const fmt = (value, digits = 1) =>
  value === null || value === undefined ? '—' : Number(value).toFixed(digits);

const fmtDate = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const HistoryTimeline = ({ athleteId }) => {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activityFilter, setActivityFilter] = useState('');

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const params = activityFilter ? { activity: activityFilter } : {};
        const response = await athletesAPI.getHistory(athleteId, params);
        if (!cancelled) setHistory(response.data);
      } catch (err) {
        if (!cancelled) {
          const detail = err.response?.data?.detail;
          setError(typeof detail === 'string' ? detail : 'Failed to load history.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [athleteId, activityFilter]);

  const entries = history?.entries || [];
  const trends = history?.trends || [];

  // Newest first reads better in a table; the API returns oldest first.
  const rows = [...entries].reverse();

  // Activity options come from the unfiltered trends when available.
  const activityOptions = Array.from(
    new Set([...trends.map((t) => t.activity_type), ...entries.map((e) => e.activity_type)])
  ).sort();

  return (
    <div className="mt-8 p-4 bg-white rounded border-2 border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Analysis History</h2>
        {history && (
          <span className="text-sm text-gray-500">
            {history.total_analyses} recorded{' '}
            {history.total_analyses === 1 ? 'analysis' : 'analyses'}
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-gray-500">Loading history…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && history && (
        <>
          {trends.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
              {trends.map((t) => {
                const style = DIRECTION_STYLES[t.direction] || DIRECTION_STYLES.unknown;
                return (
                  <div key={t.activity_type} className="p-3 bg-gray-50 rounded border">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize">{t.activity_type}</span>
                      <span className={`text-xs font-medium ${style.text}`}>
                        <span aria-hidden="true">{style.arrow}</span> {style.label}
                      </span>
                    </div>
                    <div className="text-2xl font-bold mt-1">
                      {fmt(t.latest_risk_score)}
                      <span className="text-sm font-normal text-gray-500"> / 100</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {t.analysis_count} {t.analysis_count === 1 ? 'session' : 'sessions'} ·
                      avg {fmt(t.mean_risk_score)} ·{' '}
                      <span className={style.text}>
                        {t.risk_change > 0 ? '+' : ''}
                        {fmt(t.risk_change)} since first
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activityOptions.length > 1 && (
            <div className="mb-3">
              <label htmlFor="activity-filter" className="text-sm text-gray-600 mr-2">
                Filter by activity:
              </label>
              <select
                id="activity-filter"
                className="text-sm border border-gray-300 rounded px-2 py-1"
                value={activityFilter}
                onChange={(e) => setActivityFilter(e.target.value)}
              >
                <option value="">All activities</option>
                {activityOptions.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
          )}

          {rows.length === 0 ? (
            <p className="text-sm text-gray-500">
              No completed analyses yet. Upload and process a video to start building
              this athlete&apos;s history.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Activity</th>
                    <th className="py-2 pr-4">Risk</th>
                    <th className="py-2 pr-4">Findings</th>
                    <th className="py-2 pr-4">vs. Baseline</th>
                    <th className="py-2">Analysis</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((entry) => {
                    const comparison = entry.baseline_comparison;
                    const status = comparison?.status;
                    const isChanged = status === 'changed';
                    const worse = comparison?.deteriorations?.length > 0;
                    const better = comparison?.improvements?.length > 0;
                    return (
                      <tr key={entry.id} className="border-b last:border-b-0">
                        <td className="py-2 pr-4 whitespace-nowrap">
                          {fmtDate(entry.performed_at)}
                        </td>
                        <td className="py-2 pr-4 capitalize">{entry.activity_type}</td>
                        <td className="py-2 pr-4">
                          <span className="font-semibold">
                            {fmt(entry.overall_risk_score)}
                          </span>
                          <span
                            className={`ml-2 px-2 py-0.5 rounded text-xs capitalize ${
                              RISK_BADGE[entry.risk_level] || 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {entry.risk_level?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-2 pr-4">{entry.findings_count}</td>
                        <td className="py-2 pr-4 text-xs">
                          {!comparison || status === 'no_history' ? (
                            <span className="text-gray-400">baseline</span>
                          ) : status === 'insufficient_history' ? (
                            <span className="text-gray-500">limited history</span>
                          ) : isChanged ? (
                            <span
                              className={
                                worse && !better
                                  ? 'text-red-700'
                                  : better && !worse
                                    ? 'text-green-700'
                                    : 'text-blue-700'
                              }
                            >
                              {worse && !better
                                ? '▲ worse'
                                : better && !worse
                                  ? '▼ better'
                                  : 'mixed change'}
                            </span>
                          ) : (
                            <span className="text-gray-500">stable</span>
                          )}
                        </td>
                        <td className="py-2">
                          <Link
                            to={`/videos/${entry.video_id}`}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default HistoryTimeline;
