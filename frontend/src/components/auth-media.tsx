"use client";

import { useEffect, useState } from "react";
import { fetchAsObjectUrl } from "@/lib/api-client";
import { Icon } from "@/components/icons";
import { Spinner } from "@/components/feedback";

function useBlobUrl(path: string | null, attempt: number) {
  const key = `${path}|${attempt}`;
  const [result, setResult] = useState<{ key: string; url?: string; error?: string } | null>(null);

  useEffect(() => {
    if (!path) return;
    const ctrl = new AbortController();
    let created: string | undefined;
    fetchAsObjectUrl(path, ctrl.signal)
      .then((url) => {
        created = url;
        if (ctrl.signal.aborted) return URL.revokeObjectURL(url);
        setResult({ key, url });
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setResult({ key, error: e instanceof Error ? e.message : "Couldn't load the video." });
      });
    return () => {
      ctrl.abort();
      if (created) URL.revokeObjectURL(created);
    };
  }, [path, key]);

  const current = result?.key === key ? result : null;
  return { url: current?.url, error: current?.error, loading: !!path && !current };
}

/**
 * <video> can't attach an Authorization header, so we fetch the file with the
 * signed-in session and play it from a blob URL.
 */
export function AuthVideo({ path, label }: { path: string; label: string }) {
  const [attempt, setAttempt] = useState(0);
  const { url, error, loading } = useBlobUrl(path, attempt);

  if (loading) {
    return (
      <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 rounded-[16px] bg-surface text-ink-2" role="status">
        <Spinner className="h-6 w-6" />
        <span className="text-sm">Loading video…</span>
      </div>
    );
  }
  if (error || !url) {
    return (
      <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 rounded-[16px] bg-surface px-6 text-center" role="alert">
        <Icon name="alert" className="h-6 w-6 text-danger" />
        <p className="text-sm text-ink-2">{error ?? "Couldn't load the video."}</p>
        <button onClick={() => setAttempt((n) => n + 1)} className="btn btn-outline btn-sm">
          <Icon name="refresh" className="h-4 w-4" /> Try again
        </button>
      </div>
    );
  }
  return (
    <video
      src={url}
      controls
      playsInline
      preload="metadata"
      aria-label={label}
      className="aspect-video w-full rounded-[16px] bg-black"
    />
  );
}
