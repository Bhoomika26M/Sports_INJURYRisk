"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useAcwr, useAthlete, useInjuries, useTrainingLoad, useVideos } from "@/lib/hooks";
import {
  athleteName, canManageAthletes, formatDate, formatDateTime, humanize, initials, movementLabel,
} from "@/lib/format";
import { EditAthleteModal, InjuryModal, TrainingModal } from "@/components/athlete-forms";
import { BackLink } from "@/components/back-link";
import { Avatar, Badge, StatusBadge } from "@/components/badges";
import { ConfirmDialog } from "@/components/dialog";
import { EmptyState, ErrorState, ListSkeleton, PageSkeleton } from "@/components/feedback";
import { Icon } from "@/components/icons";
import { useToast } from "@/components/toast";

type Tab = "videos" | "injuries" | "training";
type Pending = { kind: "athlete" } | { kind: "injury"; id: string } | { kind: "training"; id: string } | null;

export default function AthleteDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const canManage = canManageAthletes(user?.role); // coach/admin: edit profile, remove injuries/sessions
  const isAdmin = user?.role === "admin"; // the API only lets admins delete an athlete

  const athleteQ = useAthlete(id);
  const acwrQ = useAcwr(id);
  const injuriesQ = useInjuries(id);
  const trainingQ = useTrainingLoad(id);
  const videosQ = useVideos({ athleteId: id, pageSize: 50 });

  const [tab, setTab] = useState<Tab>("videos");
  const [modal, setModal] = useState<"edit" | "injury" | "training" | null>(null);
  const [pending, setPending] = useState<Pending>(null);

  const remove = useMutation({
    mutationFn: async (p: NonNullable<Pending>) => {
      if (p.kind === "athlete") return api.del(`/athletes/${id}`);
      return api.del(`/athletes/${id}/${p.kind === "injury" ? "injuries" : "training-load"}/${p.id}`);
    },
    onSuccess: async (_d, p) => {
      if (p.kind === "athlete") {
        await queryClient.invalidateQueries({ queryKey: ["athletes"] });
        toast.success("Athlete deleted.");
        router.replace("/athletes");
        return;
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["athlete", id, p.kind === "injury" ? "injuries" : "training"] }),
        queryClient.invalidateQueries({ queryKey: ["athlete", id, "acwr"] }),
      ]);
      toast.success(p.kind === "injury" ? "Injury removed." : "Session removed.");
      setPending(null);
    },
    onError: (e) => {
      setPending(null);
      toast.error(e instanceof Error ? e.message : "That didn't work. Please try again.");
    },
  });

  if (athleteQ.isPending) return <PageSkeleton rows={3} />;
  if (athleteQ.isError) {
    const notFound = athleteQ.error instanceof ApiError && athleteQ.error.status === 404;
    return (
      <>
        <BackLink href="/athletes">Athletes</BackLink>
        <ErrorState
          title={notFound ? "Athlete not found" : "Couldn't load this athlete"}
          message={notFound ? "They may have been removed, or you may not have access." : athleteQ.error.message}
          onRetry={notFound ? undefined : () => athleteQ.refetch()}
        />
      </>
    );
  }

  const a = athleteQ.data;
  const name = athleteName(a);
  const acwr = acwrQ.data;
  const tabs: [Tab, string][] = [["videos", "Videos"], ["injuries", "Injuries"], ["training", "Training"]];

  return (
    <>
      {user?.role !== "athlete" && <BackLink href="/athletes">Athletes</BackLink>}

      {/* ---------- Header ---------- */}
      <section className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <Avatar text={initials(name)} size={64} />
          <div className="min-w-0">
            <h1 className="truncate text-[28px] font-bold leading-tight tracking-tight text-ink">{name}</h1>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone="ok">{humanize(a.sport_type)}</Badge>
              {a.position && <Badge>{a.position}</Badge>}
              {a.age != null && <Badge>{a.age} years</Badge>}
              {a.dominant_side && <Badge>{humanize(a.dominant_side)}-sided</Badge>}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link href={`/videos/upload?athlete_id=${a.id}`} className="btn btn-primary"><Icon name="upload" className="h-4 w-4" /> Analyze video</Link>
          {canManage && (
            <>
              <button onClick={() => setModal("edit")} className="btn btn-outline"><Icon name="edit" className="h-4 w-4" /> Edit</button>
              {isAdmin && (
                <button onClick={() => setPending({ kind: "athlete" })} aria-label="Delete athlete" className="btn btn-ghost text-danger hover:!bg-danger-bg"><Icon name="trash" className="h-4 w-4" /></button>
              )}
            </>
          )}
        </div>
      </section>

      {/* ---------- At a glance ---------- */}
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="card-soft p-6">
          <p className="stat-label">Height</p>
          <span className="stat-value">{a.height_cm ? `${Math.round(a.height_cm)} cm` : "—"}</span>
        </div>
        <div className="card-soft p-6">
          <p className="stat-label">Weight</p>
          <span className="stat-value">{a.weight_kg ? `${Math.round(a.weight_kg)} kg` : "—"}</span>
        </div>
        <div className="card-soft p-6">
          <p className="stat-label">Training load balance</p>
          {acwrQ.isPending ? (
            <span className="stat-value text-ink-4">…</span>
          ) : acwr?.acwr != null ? (
            <>
              <span className="stat-value">{acwr.acwr.toFixed(2)}</span>
              <p className="mt-1.5"><Badge tone={acwr.flagged ? "warn" : "ok"}>{acwr.flagged ? "Above usual range" : "In usual range"}</Badge></p>
            </>
          ) : (
            <p className="mt-2 text-sm text-ink-2">{acwr?.message ?? "Log a few weeks of sessions to see this."}</p>
          )}
        </div>
      </section>

      {/* ---------- Tabs ---------- */}
      <section className="flex flex-col gap-5">
        <div className="tabs" role="tablist" aria-label="Athlete details">
          {tabs.map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} className="tab" onClick={() => setTab(key)}>{label}</button>
          ))}
        </div>

        {tab === "videos" && (
          videosQ.isPending ? <ListSkeleton rows={2} /> :
          videosQ.isError ? <ErrorState message={videosQ.error.message} onRetry={() => videosQ.refetch()} /> :
          videosQ.data.items.length === 0 ? (
            <EmptyState icon="video" title="No videos yet" action={{ label: "Analyze a video", href: `/videos/upload?athlete_id=${a.id}` }}>
              Upload a short clip to see how {a.full_name ? a.full_name.split(" ")[0] : "this athlete"} moves.
            </EmptyState>
          ) : (
            <ul className="flex flex-col gap-3">
              {videosQ.data.items.map((v) => (
                <li key={v.id}>
                  <Link href={`/videos/${v.id}`} className="row">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-ink-2"><Icon name="film" /></span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-ink">{movementLabel(v.movement_type)}</p>
                      <p className="text-sm text-ink-3">{formatDateTime(v.created_at)}</p>
                    </div>
                    <StatusBadge status={v.processing_status} />
                  </Link>
                </li>
              ))}
            </ul>
          )
        )}

        {tab === "injuries" && (
          <>
            <div className="flex justify-end"><button onClick={() => setModal("injury")} className="btn btn-soft btn-sm"><Icon name="plus" className="h-4 w-4" /> Add injury</button></div>
            {injuriesQ.isPending ? <ListSkeleton rows={2} /> :
             injuriesQ.isError ? <ErrorState message={injuriesQ.error.message} onRetry={() => injuriesQ.refetch()} /> :
             injuriesQ.data.items.length === 0 ? (
              <EmptyState icon="info" title="No injuries recorded">That&apos;s great. If something comes up, add it here for context.</EmptyState>
             ) : (
              <ul className="flex flex-col gap-3">
                {injuriesQ.data.items.map((inj) => (
                  <li key={inj.id} className="row !items-start">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-ink">{inj.injury_type} <span className="font-normal text-ink-3">· {inj.body_part}</span></p>
                      <p className="text-sm text-ink-3">
                        {formatDate(inj.injury_date)} → {inj.recovery_date ? formatDate(inj.recovery_date) : "ongoing"}
                      </p>
                      {inj.notes && <p className="mt-1.5 text-sm text-ink-2">{inj.notes}</p>}
                    </div>
                    {inj.severity && <Badge tone={inj.severity === "severe" ? "danger" : inj.severity === "moderate" ? "warn" : "muted"}>{humanize(inj.severity)}</Badge>}
                    {canManage && <button onClick={() => setPending({ kind: "injury", id: inj.id })} aria-label={`Remove ${inj.injury_type}`} className="btn btn-ghost !h-9 !min-h-9 !w-9 !p-0"><Icon name="trash" className="h-4 w-4" /></button>}
                  </li>
                ))}
              </ul>
             )}
          </>
        )}

        {tab === "training" && (
          <>
            <div className="flex justify-end"><button onClick={() => setModal("training")} className="btn btn-soft btn-sm"><Icon name="plus" className="h-4 w-4" /> Log session</button></div>
            {trainingQ.isPending ? <ListSkeleton rows={2} /> :
             trainingQ.isError ? <ErrorState message={trainingQ.error.message} onRetry={() => trainingQ.refetch()} /> :
             trainingQ.data.items.length === 0 ? (
              <EmptyState icon="clock" title="No sessions logged">Log sessions to track training load over time.</EmptyState>
             ) : (
              <ul className="flex flex-col gap-3">
                {trainingQ.data.items.map((t) => (
                  <li key={t.id} className="row">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-ink">{t.session_type || "Training session"}</p>
                      <p className="text-sm text-ink-3">
                        {formatDate(t.entry_date)}
                        {t.duration_minutes != null && ` · ${t.duration_minutes} min`}
                        {t.rpe != null && ` · effort ${t.rpe}/10`}
                      </p>
                    </div>
                    {t.session_load != null && <Badge>Load {Math.round(t.session_load)}</Badge>}
                    {canManage && <button onClick={() => setPending({ kind: "training", id: t.id })} aria-label="Remove this session" className="btn btn-ghost !h-9 !min-h-9 !w-9 !p-0"><Icon name="trash" className="h-4 w-4" /></button>}
                  </li>
                ))}
              </ul>
             )}
          </>
        )}
      </section>

      <EditAthleteModal athlete={a} open={modal === "edit"} onClose={() => setModal(null)} />
      <InjuryModal athleteId={id} open={modal === "injury"} onClose={() => setModal(null)} />
      <TrainingModal athleteId={id} open={modal === "training"} onClose={() => setModal(null)} />

      <ConfirmDialog
        open={pending !== null}
        onClose={() => setPending(null)}
        onConfirm={() => pending && remove.mutate(pending)}
        busy={remove.isPending}
        title={pending?.kind === "athlete" ? "Delete this athlete?" : pending?.kind === "injury" ? "Remove this injury?" : "Remove this session?"}
        message={pending?.kind === "athlete"
          ? "Their profile, videos, injuries and training history will be removed for good."
          : "This will be removed from their history. It can't be undone."}
        confirmLabel={pending?.kind === "athlete" ? "Delete athlete" : "Remove"}
      />
    </>
  );
}
