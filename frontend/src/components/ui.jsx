import { Bar, Line } from "react-chartjs-2";
import {
  BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, Filler);

const RISK_STYLES = {
  low: "bg-emerald-100 text-emerald-800",
  moderate: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export function RiskBadge({ level }) {
  if (!level) return <span className="text-slate-400">—</span>;
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${RISK_STYLES[level] || "bg-slate-100"}`}>{level}</span>;
}

export function Stat({ label, value, hint }) {
  return (
    <div className="card">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-blue-700">{value ?? "—"}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Section({ title, children, action }) {
  return (
    <section className="card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-blue-900">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Table({ columns, rows, empty = "Nothing to show yet." }) {
  if (!rows?.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-blue-100 bg-blue-50/60 text-xs uppercase text-blue-900/70">
            {columns.map((c) => <th key={c.header} className="py-2 pr-4 font-medium">{c.header}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-blue-50 last:border-0 hover:bg-blue-50/40">
              {columns.map((c) => <td key={c.header} className="py-2 pr-4">{c.render ? c.render(r) : r[c.key] ?? "—"}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TrendChart({ labels, series }) {
  const colors = ["#2563eb", "#06b6d4", "#1e3a8a"];
  return (
    <Line
      height={90}
      data={{ labels, datasets: series.map((s, i) => ({ label: s.label, data: s.data, borderColor: colors[i % 3], backgroundColor: colors[i % 3], tension: 0.3 })) }}
      options={{ plugins: { legend: { display: series.length > 1 } }, scales: { y: { min: 0, max: 100 } } }}
    />
  );
}

export function BarChart({ labels, data, label, color = "#2563eb", horizontal = false }) {
  return (
    <Bar
      height={90}
      data={{ labels, datasets: [{ label, data, backgroundColor: color }] }}
      options={{ indexAxis: horizontal ? "y" : "x", plugins: { legend: { display: false } } }}
    />
  );
}

export function Error({ message }) {
  return message ? <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{message}</div> : null;
}

export const fmtDate = (s) => (s ? new Date(s).toLocaleDateString() : "—");
