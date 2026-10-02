import type { ReactNode } from "react";
import { RISK, VIDEO_STATUS } from "@/lib/format";
import type { RiskCategory, VideoStatus } from "@/lib/types";

type Tone = "ok" | "info" | "warn" | "danger" | "muted";

export function Badge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: VideoStatus }) {
  const s = VIDEO_STATUS[status] ?? { label: status, tone: "muted" as const };
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

export function RiskBadge({ category }: { category: RiskCategory }) {
  const r = RISK[category];
  return <Badge tone={r?.tone ?? "muted"}>{r ? `${r.label} risk` : category}</Badge>;
}

export function Avatar({ text, size = 44 }: { text: string; size?: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-full bg-brand-tint text-sm font-semibold text-brand-dark"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {text}
    </span>
  );
}
