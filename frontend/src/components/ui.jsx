import { Bar, Line } from "react-chartjs-2";
import {
  BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, Filler);
ChartJS.defaults.font.family = "Inter, ui-sans-serif, system-ui, sans-serif";
ChartJS.defaults.color = "#64748b";

const RISK_STYLES = {
  low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  moderate: "bg-amber-50 text-amber-700 ring-amber-600/20",
  high: "bg-orange-50 text-orange-700 ring-orange-600/20",
  critical: "bg-red-50 text-red-700 ring-red-600/20",
};
const RISK_DOTS = { low: "bg-emerald-500", moderate: "bg-amber-500", high: "bg-orange-500", critical: "bg-red-500" };

export function RiskBadge({ level }) {
  if (!level) return <span className="text-slate-400">—</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ring-1 ring-inset ${RISK_STYLES[level] || "bg-slate-100 text-slate-700 ring-slate-300"}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${RISK_DOTS[level] || "bg-slate-400"}`} />
      {level}
    </span>
  );
}

export function Stat({ label, value, hint }) {
  return (
    <div className="card relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 to-cyan-400" />
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-3xl font-bold tabular-nums tracking-tight text-slate-900">{value ?? "—"}</div>
      {hint && <div className="mt-1.5 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Section({ title, children, action }) {
  return (
    <section className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <span className="h-4 w-1 rounded-full bg-gradient-to-b from-blue-600 to-cyan-400" />
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Table({ columns, rows, empty = "Nothing to show yet." }) {
  if (!rows?.length) {
    return <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-6 text-center text-sm text-slate-500">{empty}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-slate-500">
            {columns.map((c) => <th key={c.header} className="border-b border-slate-200 bg-slate-50/70 px-3 py-2.5 font-semibold first:rounded-tl-lg last:rounded-tr-lg">{c.header}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-blue-50/40">
              {columns.map((c) => <td key={c.header} className="px-3 py-3 text-slate-700">{c.render ? c.render(r) : r[c.key] ?? "—"}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const tooltip = { backgroundColor: "#0f172a", padding: 10, cornerRadius: 8, titleFont: { weight: "600" }, boxPadding: 4 };

export function TrendChart({ labels, series }) {
  const colors = ["#2563eb", "#06b6d4", "#1e3a8a"];
  return (
    <Line
      height={90}
      data={{
        labels,
        datasets: series.map((s, i) => ({
          label: s.label, data: s.data, borderColor: colors[i % 3], backgroundColor: `${colors[i % 3]}1f`, fill: true,
          tension: 0.35, borderWidth: 2.5, pointRadius: 3.5, pointHoverRadius: 6, pointBackgroundColor: "#fff", pointBorderColor: colors[i % 3], pointBorderWidth: 2,
        })),
      }}
      options={{
        plugins: { legend: { display: series.length > 1, position: "top", align: "end", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip },
        scales: { y: { min: 0, max: 100, grid: { color: "#eef2f7" }, border: { display: false } }, x: { grid: { display: false }, border: { display: false } } },
      }}
    />
  );
}

export function BarChart({ labels, data, label, color = "#2563eb", horizontal = false }) {
  const axis = { grid: { color: "#eef2f7" }, border: { display: false } };
  const off = { grid: { display: false }, border: { display: false } };
  return (
    <Bar
      height={90}
      data={{ labels, datasets: [{ label, data, backgroundColor: color, borderRadius: 8, maxBarThickness: 38 }] }}
      options={{
        indexAxis: horizontal ? "y" : "x",
        plugins: { legend: { display: false }, tooltip },
        scales: horizontal ? { x: axis, y: off } : { x: off, y: axis },
      }}
    />
  );
}

export function Error({ message }) {
  return message ? <div className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{message}</div> : null;
}

export const fmtDate = (s) => (s ? new Date(s).toLocaleDateString() : "—");
