import { useId, type ReactNode } from "react";

type ControlProps = { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean };

/** Label + control + hint/error, wired up for screen readers. */
export function Field({
  label,
  hint,
  error,
  optional,
  children,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  optional?: boolean;
  children: (props: ControlProps) => ReactNode;
}) {
  const id = useId();
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {optional && <span className="ml-1.5 font-normal text-ink-3">optional</span>}
      </label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {error ? (
        <p id={`${id}-err`} className="text-sm text-danger">{error}</p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-ink-3">{hint}</p>
      ) : null}
    </div>
  );
}
