import type { Role, VideoStatus, RiskCategory } from "@/lib/types";

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateFmt.format(d);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateTimeFmt.format(d);
}

export function timeAgo(iso: string, now: number = Date.now()): string {
  const diff = Math.max(0, now - new Date(iso).getTime());
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "Just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} day${day === 1 ? "" : "s"} ago`;
  return formatDate(iso);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  return `${Math.round(seconds)} s`;
}

export function humanize(s: string): string {
  const t = s.replace(/_/g, " ").trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  return name.split(/\s+/).filter(Boolean).map((p) => p[0]).join("").slice(0, 2).toUpperCase() || "?";
}

export function firstName(name: string | null | undefined): string {
  return name?.trim().split(/\s+/)[0] || "there";
}

const ROLE_LABELS: Record<Role, string> = {
  athlete: "Athlete",
  coach: "Coach",
  physiotherapist: "Physiotherapist",
  sports_scientist: "Sports scientist",
  admin: "Admin",
};
export const roleLabel = (r: string) => ROLE_LABELS[r as Role] ?? humanize(r);

export const CAN_MANAGE_ATHLETES: Role[] = ["coach", "admin"];
export const canManageAthletes = (role: string | undefined) => !!role && CAN_MANAGE_ATHLETES.includes(role as Role);

const CAMERA_LABELS: Record<string, string> = {
  sagittal: "Side view",
  frontal: "Front view",
  other: "Other angle",
};
export const cameraLabel = (v: string) => CAMERA_LABELS[v] ?? humanize(v);

export const movementLabel = (code: string) => humanize(code);

/** "knee_flexion_angle_left" → "Left knee flexion" */
export function metricLabel(name: string): string {
  const side = name.endsWith("_left") ? "Left" : name.endsWith("_right") ? "Right" : "";
  const base = name
    .replace(/_(left|right)$/, "")
    .replace(/_(angle|deviation)$/, "")
    .replace(/_/g, " ")
    .trim();
  if (base === "knee valgus") return side ? `${side} knee alignment` : "Knee alignment";
  return side ? `${side} ${base}` : humanize(base);
}

/** Sagittal angles are estimates with real error — always whole degrees (docs/SCIENCE_CONSTRAINTS.md). */
export const wholeDegrees = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v)}°`);

export const VIDEO_STATUS: Record<VideoStatus, { label: string; tone: "ok" | "info" | "warn" | "danger" | "muted" }> = {
  pending_upload: { label: "Waiting for upload", tone: "muted" },
  uploaded: { label: "Queued", tone: "info" },
  processing: { label: "Analyzing", tone: "info" },
  completed: { label: "Ready", tone: "ok" },
  failed: { label: "Needs attention", tone: "danger" },
};

export const isInFlight = (s: VideoStatus) => s === "uploaded" || s === "processing" || s === "pending_upload";

export const RISK: Record<RiskCategory, { label: string; tone: "ok" | "info" | "warn" | "danger"; rank: number }> = {
  low: { label: "Low", tone: "ok", rank: 0 },
  moderate: { label: "Moderate", tone: "info", rank: 1 },
  high: { label: "High", tone: "warn", rank: 2 },
  critical: { label: "Critical", tone: "danger", rank: 3 },
};

/** Friendly explanations for the error codes the processing worker can set. */
export function processingFailureHelp(code: string | null, fallback: string | null): string {
  switch (code) {
    case "no_person_detected":
      return "We couldn't find a person in this clip. Make sure the athlete is fully in frame and the camera stays still.";
    case "low_detection_quality":
      return fallback ?? "We couldn't track the body reliably. Try better lighting and keep the whole body in view.";
    case "storage_error":
      return "We couldn't read the uploaded file. Please upload the video again.";
    default:
      return fallback ?? "Something went wrong while analyzing this video. Please try uploading it again.";
  }
}

/** Athlete names come from a linked user account; UI-created profiles have none, so fall back gracefully. */
export function athleteName(a: { full_name: string | null; sport_type: string; age: number | null }): string {
  if (a.full_name) return a.full_name;
  return `${humanize(a.sport_type)} athlete${a.age != null ? `, ${a.age}` : ""}`;
}

/** Today as YYYY-MM-DD in the user's local timezone (for <input type="date"> max/defaults). */
export function todayISO(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

const BREAKDOWN_LABELS: Record<string, string> = {
  movement_anomaly: "Movement pattern",
  asymmetry_flag: "Left–right balance",
  prior_injury_flag: "Past injury",
  acwr_flag: "Training load",
  fatigue_flag: "Fatigue",
};
export const breakdownLabel = (key: string) => BREAKDOWN_LABELS[key] ?? humanize(key);
