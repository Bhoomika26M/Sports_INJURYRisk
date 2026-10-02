"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { Icon } from "@/components/icons";
import { Spinner } from "@/components/feedback";

/**
 * Modal built on the native <dialog> element: focus is trapped, Esc closes,
 * the page behind is inert, and focus returns to the trigger — all for free.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose(); // click on the backdrop
      }}
    >
      {open && (
        <div className="p-6 sm:p-8">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h2 id={titleId} className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
              {description && <p className="mt-1 text-sm text-ink-2">{description}</p>}
            </div>
            <button onClick={onClose} aria-label="Close" className="btn btn-ghost -mr-2 -mt-2 !min-h-10 !w-10 !p-0">
              <Icon name="x" className="h-5 w-5" />
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Delete",
  busy = false,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
}) {
  return (
    <Modal open={open} onClose={busy ? () => {} : onClose} title={title}>
      <p className="-mt-2 text-ink-2">{message}</p>
      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button onClick={onClose} disabled={busy} className="btn btn-outline">Cancel</button>
        <button onClick={onConfirm} disabled={busy} className="btn btn-danger">
          {busy && <Spinner className="h-4 w-4" />} {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
