"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { Icon } from "@/components/icons";

type Toast = { id: number; message: string; tone: "success" | "error" };

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  const push = useCallback(
    (tone: Toast["tone"], message: string) => {
      const id = nextId.current++;
      setToasts((t) => [...t.slice(-2), { id, message, tone }]);
      window.setTimeout(() => dismiss(id), tone === "error" ? 7000 : 4500);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({ success: (m) => push("success", m), error: (m) => push("error", m) }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tone === "error" ? "toast--error" : ""}`}>
            <Icon name={t.tone === "error" ? "alert" : "check"} className="mt-0.5 h-5 w-5 shrink-0" />
            <span className="flex-1">{t.message}</span>
            <button onClick={() => dismiss(t.id)} aria-label="Dismiss" className="-m-1 rounded-full p-1 opacity-70 hover:opacity-100">
              <Icon name="x" className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
