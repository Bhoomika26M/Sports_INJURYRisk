import type { ReactNode } from "react";

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card-soft p-6">
      <p className="stat-label">{label}</p>
      <span className="stat-value">{value}</span>
      {hint && <p className="mt-1 text-sm text-ink-3">{hint}</p>}
    </div>
  );
}
