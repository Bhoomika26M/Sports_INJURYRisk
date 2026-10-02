import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
  back,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  back?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4">
      {back}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-[28px] font-bold leading-tight tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-1.5 max-w-2xl text-ink-2">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
