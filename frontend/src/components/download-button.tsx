"use client";

import { useState } from "react";
import { ApiError, downloadFile } from "@/lib/api-client";
import { Icon } from "@/components/icons";
import { Spinner } from "@/components/feedback";
import { useToast } from "@/components/toast";

function friendly(e: unknown): string {
  if (e instanceof ApiError && e.status === 404 && /not yet scored/i.test(e.message)) {
    return "This report isn't ready yet — a risk score needs enough similar videos to compare against.";
  }
  return e instanceof Error ? e.message : "The download didn't work. Please try again.";
}

/** Authenticated file download with its own loading state and error toast. */
export function DownloadButton({
  path,
  filename,
  label,
  variant = "outline",
  small = true,
}: {
  path: string;
  filename: string;
  label: string;
  variant?: "outline" | "soft" | "primary";
  small?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function run() {
    setBusy(true);
    try {
      await downloadFile(path, filename);
    } catch (e) {
      toast.error(friendly(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <button onClick={run} disabled={busy} className={`btn btn-${variant} ${small ? "btn-sm" : ""}`}>
      {busy ? <Spinner className="h-4 w-4" /> : <Icon name="download" className="h-4 w-4" />}
      {label}
    </button>
  );
}
