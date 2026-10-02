"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api, ApiError, uploadFile } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useAllAthletes, useMovementTypes, useVideo } from "@/lib/hooks";
import { athleteName, cameraLabel, canManageAthletes, formatBytes, processingFailureHelp } from "@/lib/format";
import type { UploadTicket } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Field } from "@/components/field";
import { Icon } from "@/components/icons";
import { EmptyState, ErrorState, Notice, PageSkeleton, Spinner } from "@/components/feedback";

const MAX_BYTES = 200 * 1024 * 1024;
const MIN_SECONDS = 2;
const MAX_SECONDS = 60;
const MIN_HEIGHT = 480;

type Probe = { duration: number; width: number; height: number };
type Phase =
  | { name: "form" }
  | { name: "uploading"; loaded: number; total: number; step: "sending" | "checking" }
  | { name: "analyzing"; videoId: string; startedAt: number }
  | { name: "failed"; message: string };

/** Read duration/resolution in the browser so we can reject bad clips *before* a 200 MB upload. */
function probeVideo(file: File): Promise<Probe | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    v.preload = "metadata";
    v.muted = true;
    let settled = false;
    const finish = (r: Probe | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      URL.revokeObjectURL(url);
      v.removeAttribute("src");
      v.load();
      resolve(r);
    };
    const timer = setTimeout(() => finish(null), 8000);
    v.onloadedmetadata = () =>
      finish(Number.isFinite(v.duration) ? { duration: v.duration, width: v.videoWidth, height: v.videoHeight } : null);
    v.onerror = () => finish(null); // e.g. a .mov codec the browser can't read — the server will check it
    v.src = url;
  });
}

function UploadFlow() {
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const athletesQ = useAllAthletes();
  const movementsQ = useMovementTypes();

  const [athleteChoice, setAthleteChoice] = useState<string | null>(null);
  const [movement, setMovement] = useState("");
  const [viewChoice, setViewChoice] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [probe, setProbe] = useState<Probe | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [errors, setErrors] = useState<{ athlete?: string; movement?: string; file?: string }>({});
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>({ name: "form" });
  const [now, setNow] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const probeToken = useRef(0);

  const athletes = athletesQ.data?.items ?? [];
  const movements = movementsQ.data ?? [];

  // Smart defaults, derived (not copied into state): ?athlete_id=…, or the only athlete there is.
  const paramId = params.get("athlete_id");
  const defaultAthlete =
    athletes.find((a) => a.id === paramId)?.id ?? (athletes.length === 1 ? athletes[0].id : "");
  const athleteId = athleteChoice ?? defaultAthlete;

  const movementInfo = movements.find((m) => m.code === movement);
  const allowedViews = movementInfo?.camera_views ?? [];
  const view =
    viewChoice && allowedViews.includes(viewChoice)
      ? viewChoice
      : allowedViews.includes("sagittal") ? "sagittal" : (allowedViews[0] ?? "");

  // Warn before closing the tab mid-upload, and stop the transfer if we navigate away.
  const uploading = phase.name === "uploading";
  useEffect(() => {
    if (!uploading) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [uploading]);
  useEffect(() => () => abortRef.current?.abort(), []);

  // A ticking clock, only while analyzing, so we can reassure people if it's slow.
  const analyzing = phase.name === "analyzing";
  useEffect(() => {
    if (!analyzing) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [analyzing]);

  const videoQ = useVideo(phase.name === "analyzing" ? phase.videoId : null);

  async function acceptFile(f: File | undefined) {
    if (!f) return;
    setErrors((e) => ({ ...e, file: undefined }));
    const ext = f.name.toLowerCase();
    if (!ext.endsWith(".mp4") && !ext.endsWith(".mov")) {
      setFile(null); setProbe(null);
      return setFileError("That file type isn't supported. Please choose an .mp4 or .mov video.");
    }
    if (f.size > MAX_BYTES) {
      setFile(null); setProbe(null);
      return setFileError(`That file is ${formatBytes(f.size)}. Videos can be up to 200 MB.`);
    }
    const token = ++probeToken.current;
    setFileError(null);
    setFile(f);
    setProbe(null);
    const info = await probeVideo(f);
    if (token !== probeToken.current) return; // a newer file was chosen meanwhile
    if (info && (info.duration < MIN_SECONDS || info.duration > MAX_SECONDS)) {
      setFile(null);
      return setFileError(
        `This clip is ${Math.round(info.duration)} seconds long. Clips need to be between ${MIN_SECONDS} and ${MAX_SECONDS} seconds.`,
      );
    }
    setProbe(info);
  }

  function removeFile() {
    probeToken.current++;
    setFile(null); setProbe(null); setFileError(null);
  }

  function focusSection(id: string) {
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    el?.querySelector<HTMLElement>("select, input, button")?.focus({ preventScroll: true });
  }

  async function start(e: React.FormEvent) {
    e.preventDefault();
    if (phase.name !== "form") return;

    const next: typeof errors = {};
    if (!athleteId) next.athlete = "Choose who this video is for.";
    if (!movement) next.movement = "Pick the movement that was filmed.";
    if (!file) next.file = "Add a video to analyze.";
    setErrors(next);
    if (next.athlete) return focusSection("section-athlete");
    if (next.movement) return focusSection("section-movement");
    if (next.file || !file) return focusSection("section-file");

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setPhase({ name: "uploading", loaded: 0, total: file.size, step: "sending" });
    try {
      const ticket = await api.post<UploadTicket>("/videos/upload-url", {
        athlete_id: athleteId,
        movement_type: movement,
        camera_view: view,
        original_filename: file.name,
      });
      await uploadFile(ticket.upload_url, file, {
        signal: ctrl.signal,
        onProgress: (loaded, total) =>
          setPhase((p) => (p.name === "uploading" ? { ...p, loaded, total } : p)),
      });
      setPhase({ name: "uploading", loaded: file.size, total: file.size, step: "checking" });
      await api.post(`/videos/${ticket.video_id}/confirm-upload`);
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      setNow(Date.now());
      setPhase({ name: "analyzing", videoId: ticket.video_id, startedAt: Date.now() });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return setPhase({ name: "form" });
      const rejected = err instanceof ApiError && err.status === 400;
      if (rejected) removeFile(); // the server rejected this file and discarded it
      setPhase({ name: "failed", message: err instanceof Error ? err.message : "The upload didn't go through." });
    }
  }

  function reset() {
    abortRef.current = null;
    setFile(null); setProbe(null); setFileError(null); setErrors({});
    setPhase({ name: "form" });
  }

  /* ---------- loading / empty states ---------- */
  if (athletesQ.isPending || movementsQ.isPending) return <PageSkeleton rows={2} />;
  if (athletesQ.isError || movementsQ.isError) {
    const err = athletesQ.error ?? movementsQ.error;
    return (
      <ErrorState
        message={err instanceof Error ? err.message : "We couldn't load the upload form."}
        onRetry={() => { athletesQ.refetch(); movementsQ.refetch(); }}
      />
    );
  }
  if (athletes.length === 0) {
    return (
      <>
        <PageHeader title="New analysis" />
        {canManageAthletes(user?.role) ? (
          <EmptyState icon="users" title="Add an athlete first" action={{ label: "Add an athlete", href: "/athletes/new" }}>
            Videos are analyzed per athlete, so create a profile before uploading.
          </EmptyState>
        ) : user?.role === "athlete" ? (
          <EmptyState icon="users" title="Your profile isn't set up yet">
            Your coach needs to create or link your athlete profile before you can upload videos.
          </EmptyState>
        ) : (
          <EmptyState icon="users" title="No athletes to choose from yet">
            Once a coach adds athletes, you&apos;ll be able to upload their videos here.
          </EmptyState>
        )}
      </>
    );
  }

  /* ---------- uploading ---------- */
  if (phase.name === "uploading") {
    const pct = phase.total ? Math.round((phase.loaded / phase.total) * 100) : 0;
    const checking = phase.step === "checking";
    return (
      <>
        <PageHeader title="New analysis" />
        <div className="card mx-auto w-full max-w-xl p-8 text-center sm:p-10">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-tint text-brand-dark">
            {checking ? <Spinner className="h-6 w-6" /> : <Icon name="upload" className="h-6 w-6" />}
          </span>
          <h2 className="mt-5 text-xl font-semibold text-ink">{checking ? "Checking your video…" : "Uploading your video"}</h2>
          <p className="mt-1 text-ink-2" aria-live="polite">
            {checking ? "Making sure it's ready to analyze." : `${pct}% · ${formatBytes(phase.loaded)} of ${formatBytes(phase.total)}`}
          </p>
          <div className={`progress mt-6 ${checking ? "progress--indeterminate" : ""}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={checking ? undefined : pct} aria-label="Upload progress">
            <span style={{ width: `${checking ? 100 : pct}%` }} />
          </div>
          {!checking && (
            <button onClick={() => abortRef.current?.abort()} className="btn btn-ghost btn-sm mt-6">Cancel upload</button>
          )}
          <p className="mt-4 text-sm text-ink-3">Please keep this tab open until the upload finishes.</p>
        </div>
      </>
    );
  }

  /* ---------- analyzing / done / failed-processing ---------- */
  if (phase.name === "analyzing") {
    const v = videoQ.data;
    const elapsed = now ? (now - phase.startedAt) / 1000 : 0;

    if (v?.processing_status === "completed") {
      return (
        <>
          <PageHeader title="New analysis" />
          <div className="card mx-auto w-full max-w-xl p-8 text-center sm:p-10">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand text-brand-dark"><Icon name="check" className="h-7 w-7" /></span>
            <h2 className="mt-5 text-xl font-semibold text-ink">Your analysis is ready</h2>
            <p className="mt-1 text-ink-2">We measured the movement and put the results together.</p>
            <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
              <Link href={`/videos/${v.id}/results`} className="btn btn-primary">See results</Link>
              <button onClick={reset} className="btn btn-outline">Analyze another video</button>
            </div>
          </div>
        </>
      );
    }

    if (v?.processing_status === "failed") {
      return (
        <>
          <PageHeader title="New analysis" />
          <div className="card mx-auto w-full max-w-xl p-8 text-center sm:p-10" role="alert">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-danger-bg text-danger"><Icon name="alert" className="h-7 w-7" /></span>
            <h2 className="mt-5 text-xl font-semibold text-ink">We couldn&apos;t analyze this video</h2>
            <p className="mx-auto mt-2 max-w-md text-ink-2">{processingFailureHelp(v.error_code, v.error_message)}</p>
            <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
              <button onClick={reset} className="btn btn-primary">Try another video</button>
              <Link href="/videos" className="btn btn-outline">Go to videos</Link>
            </div>
          </div>
        </>
      );
    }

    const pct = v?.progress_pct ?? 0;
    return (
      <>
        <PageHeader title="New analysis" />
        <div className="card mx-auto w-full max-w-xl p-8 text-center sm:p-10">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-brand-tint text-brand-dark"><Spinner className="h-6 w-6" /></span>
          <h2 className="mt-5 text-xl font-semibold text-ink">Analyzing movement</h2>
          <p className="mt-1 text-ink-2" aria-live="polite">
            {pct > 0 ? `${pct}% complete` : "Getting started…"}
          </p>
          <div className={`progress mt-6 ${pct === 0 ? "progress--indeterminate" : ""}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct > 0 ? pct : undefined} aria-label="Analysis progress">
            <span style={{ width: `${Math.max(pct, 4)}%` }} />
          </div>
          {videoQ.isError && <div className="mt-5 text-left"><Notice tone="warn">We lost touch with the server for a moment. Still trying…</Notice></div>}
          {elapsed > 90 && pct === 0 && (
            <div className="mt-5 text-left"><Notice tone="info">This is taking longer than usual. You can leave this page — your video keeps processing and will appear under Videos.</Notice></div>
          )}
          <p className="mt-6 text-sm text-ink-3">
            This usually takes a minute or two. You can leave — find it any time under{" "}
            <Link href="/videos" className="font-medium text-brand-dark underline underline-offset-4">Videos</Link>.
          </p>
        </div>
      </>
    );
  }

  /* ---------- the form ---------- */
  return (
    <>
      <PageHeader title="New analysis" subtitle="Upload a short clip and we'll measure how the body moves." />

      <form onSubmit={start} noValidate className="card flex flex-col gap-9 p-6 sm:p-9">
        {phase.name === "failed" && <Notice tone="danger">{phase.message}</Notice>}

        <section id="section-athlete" className="flex flex-col gap-2">
          <Field label="Who is this video for?" error={errors.athlete}>
            {(p) => (
              <select {...p} className="input" value={athleteId}
                onChange={(e) => { setAthleteChoice(e.target.value); setErrors((x) => ({ ...x, athlete: undefined })); }}>
                <option value="">Choose an athlete…</option>
                {athletes.map((a) => (
                  <option key={a.id} value={a.id}>{athleteName(a)}</option>
                ))}
              </select>
            )}
          </Field>
        </section>

        <section id="section-movement">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">What movement was filmed?</legend>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
              {movements.map((m) => (
                <label key={m.code} className="choice">
                  <input type="radio" name="movement" value={m.code} checked={movement === m.code} className="sr-only"
                    onChange={() => { setMovement(m.code); setViewChoice(null); setErrors((x) => ({ ...x, movement: undefined })); }} />
                  {m.display_name}
                </label>
              ))}
            </div>
            {errors.movement && <p className="mt-2 text-sm text-danger">{errors.movement}</p>}
          </fieldset>
        </section>

        {allowedViews.length > 1 && (
          <section>
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-ink">Camera angle</legend>
              <div className="flex flex-wrap gap-2.5">
                {allowedViews.map((v) => (
                  <label key={v} className="choice">
                    <input type="radio" name="view" value={v} checked={view === v} className="sr-only" onChange={() => setViewChoice(v)} />
                    {cameraLabel(v)}
                  </label>
                ))}
              </div>
              <p className="mt-2 text-sm text-ink-3">
                {view === "frontal"
                  ? "Front view gives a visual alignment flag, not exact angles."
                  : "Side view gives the most reliable joint angles."}
              </p>
            </fieldset>
          </section>
        )}

        <section id="section-file" className="flex flex-col gap-3">
          <span className="text-sm font-medium text-ink">Your video</span>
          {!file ? (
            <label
              className="dropzone"
              data-active={dragging}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); acceptFile(e.dataTransfer.files?.[0]); }}
            >
              <input type="file" accept=".mp4,.mov,video/mp4,video/quicktime" className="sr-only"
                onChange={(e) => { acceptFile(e.target.files?.[0]); e.target.value = ""; }} />
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface text-ink-2"><Icon name="upload" className="h-6 w-6" /></span>
              <span className="font-semibold text-ink">Drop a video here, or tap to browse</span>
              <span className="text-sm text-ink-3">.mp4 or .mov · up to 200 MB · 2–60 seconds</span>
            </label>
          ) : (
            <div className="row !bg-brand-tint/60">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-brand-dark"><Icon name="film" /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-ink">{file.name}</p>
                <p className="text-sm text-ink-2">
                  {formatBytes(file.size)}
                  {probe && ` · ${Math.round(probe.duration)} s · ${probe.width}×${probe.height}`}
                </p>
              </div>
              <button type="button" onClick={removeFile} aria-label="Remove video" className="btn btn-ghost !h-10 !min-h-10 !w-10 !p-0"><Icon name="x" className="h-5 w-5" /></button>
            </div>
          )}
          {fileError && <Notice tone="danger">{fileError}</Notice>}
          {errors.file && !fileError && <p className="text-sm text-danger">{errors.file}</p>}
          {probe && probe.height < MIN_HEIGHT && (
            <Notice tone="warn">This video is a little low-resolution. Clips under {MIN_HEIGHT}p may be rejected — filming in HD works best.</Notice>
          )}
          <p className="text-sm text-ink-3">Tip: keep the whole body in frame, hold the camera steady, and film in good light.</p>
        </section>

        <button type="submit" className="btn btn-primary !min-h-[52px] w-full sm:w-fit sm:self-end sm:!px-10">
          Analyze video <Icon name="chevron-right" className="h-4 w-4" />
        </button>
      </form>
    </>
  );
}

export default function UploadVideoPage() {
  return (
    <Suspense fallback={<PageSkeleton rows={2} />}>
      <UploadFlow />
    </Suspense>
  );
}
