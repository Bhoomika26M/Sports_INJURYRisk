import type { ReactNode } from "react";
import Link from "next/link";
import { Icon, type IconName } from "@/components/icons";

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

/** Gentle placeholder for a whole page while its first data loads. */
export function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-6" role="status" aria-label="Loading">
      <Skeleton className="h-9 w-56" />
      <Skeleton className="h-28 w-full !rounded-[24px]" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full !rounded-[16px]" />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-[72px] w-full !rounded-[16px]" />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  title = "Something went wrong",
}: {
  message: string;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center" role="alert">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-bg text-danger">
        <Icon name="alert" className="h-6 w-6" />
      </span>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="max-w-md text-ink-2">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-outline mt-2">
          <Icon name="refresh" className="h-4 w-4" /> Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon = "info",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children?: ReactNode;
  action?: { label: string; href: string };
}) {
  return (
    <div className="card-soft flex flex-col items-center gap-3 px-6 py-14 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white text-ink-2 shadow-[var(--shadow-diffuse)]">
        <Icon name={icon} className="h-6 w-6" />
      </span>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {children && <p className="max-w-md text-ink-2">{children}</p>}
      {action && (
        <Link href={action.href} className="btn btn-primary mt-2">
          {action.label}
        </Link>
      )}
    </div>
  );
}

/** Inline, non-blocking message inside a form or card. */
export function Notice({
  tone = "info",
  children,
}: {
  tone?: "info" | "warn" | "danger" | "ok";
  children: ReactNode;
}) {
  const styles = {
    info: "bg-info-bg text-info",
    warn: "bg-warn-bg text-warn",
    danger: "bg-danger-bg text-danger",
    ok: "bg-brand-tint text-brand-dark",
  }[tone];
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={`flex items-start gap-3 rounded-[16px] px-4 py-3 text-sm ${styles}`}>
      <Icon name={tone === "ok" ? "check" : tone === "info" ? "info" : "alert"} className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{children}</div>
    </div>
  );
}
