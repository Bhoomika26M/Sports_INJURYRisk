"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, ApiError } from "@/lib/api-client";
import { useVideo } from "@/lib/hooks";
import { breakdownLabel, classificationRows, humanize, LEVEL_TONE, metricLabel, movementLabel, RISK, SUB_SCORE_LABELS, wholeDegrees } from "@/lib/format";
import type { Biomechanics, InsufficientBaseline, Recommendation, RiskScore, Video, VideoQuality } from "@/lib/types";
import { BackLink } from "@/components/back-link";
import { PageHeader } from "@/components/page-header";
import { DownloadButton } from "@/components/download-button";
import { Icon } from "@/components/icons";
import { ErrorState, Notice, PageSkeleton } from "@/components/feedback";

type RiskResult =
  | { kind: "scored"; risk: RiskScore }
  | { kind: "insufficient"; info: InsufficientBaseline }
  | { kind: "unavailable"; message?: string };

const SERIES_COLORS = ["#163300", "#6bbf3a", "#2563eb", "#9333ea", "#ea580c", "#0891b2"];

const GRADE_TONE: Record<string, "ok" | "warn" | "danger" | "info"> = { good: "ok", fair: "warn", poor: "danger", unknown: "info" };

/** What the pipeline could actually measure on this clip. A score is never shown as more certain than that. */
function QualityNotes({ video, quality, caveat, baseline }: { video: Video; quality?: VideoQuality; caveat?: string | null; baseline?: RiskScore["baseline"] }) {
  const q = quality ?? video.analysis?.quality;
  const cav = caveat ?? video.coverage_caveat;
  const warns = q?.warnings ?? [];
  if (!cav && !warns.length && !baseline?.provisional && (!q || q.grade === "good")) return null;
  return (
    <section className="card-soft flex flex-col gap-3 p-6">
      <div className="flex flex-wrap items-center gap-2">
        {q && q.grade !== "unknown" && <span className={`badge badge-${GRADE_TONE[q.grade]}`}>Video quality: {q.grade}</span>}
        {video.detection_rate != null && <span className="badge badge-muted">Athlete tracked in {Math.round(video.detection_rate * 100)}% of frames</span>}
        {(video.person_count_detected ?? 0) > 1 && <span className="badge badge-muted">{video.person_count_detected} people in frame</span>}
      </div>
      {baseline?.provisional && <p className="text-sm text-ink-2">Compared against {baseline.videos} other videos. That is a small comparison group, so treat this score as provisional: it gets steadier as more videos are added.</p>}
      {cav && <p className="text-sm text-ink-2">{cav}</p>}
      {warns.length > 0 && <ul className="space-y-1 text-sm text-ink-2">{warns.map((w) => <li key={w.code}>• {w.message}</li>)}</ul>}
      {(q?.grade === "poor" || cav) && <p className="text-xs text-ink-3">Treat any score on this clip as provisional.</p>}
    </section>
  );
}

/** What the classifier saw in the clip, set against the labels it was uploaded with. Absent on videos processed before it existed. */
function ClassificationNotes({ video }: { video: Video }) {
  const view = classificationRows(video.analysis?.classification, video);
  if (!view) return null;
  const off = view.rows.filter((r) => r.same === false);
  return (
    <section className="card-soft flex flex-col gap-4 p-6">
      <h2 className="text-lg font-semibold text-ink">What the clip shows</h2>
      {view.auto && (
        <Notice tone="info">
          No labels were given, so the movement and camera angle were identified from the footage. That check is a heuristic that has not been validated on real clips: confirm them before relying on this video&apos;s measurements.
        </Notice>
      )}
      {off.length > 0 && (
        <Notice tone="warn">
          {off.map((r) => <p key={r.label}>{r.label} looks different from the label: the clip seems to show <b>{r.found}</b>, but it is labelled <b>{r.labelled}</b>.</p>)}
          <p>The measurements below follow the label, so check it before relying on them.</p>
        </Notice>
      )}
      <dl className="grid gap-3 sm:grid-cols-2">
        {view.rows.map((r) => (
          <div key={r.label} className="rounded-[12px] bg-white px-4 py-3">
            <dt className="text-xs text-ink-3">{r.label}</dt>
            <dd className="flex flex-wrap items-center gap-2 font-semibold text-ink">
              {r.found ?? "Couldn't tell"}
              {r.same === true && <span className="badge badge-ok">Matches the label</span>}
              {r.same === false && <span className="badge badge-warn">Differs from the label</span>}
              {r.same === null && r.suggests && <span className="badge badge-muted">Suggested instead of the label</span>}
            </dd>
            <p className="text-xs text-ink-3">{r.labelled ? `Labelled as ${r.labelled}` : "Identified from the footage"}</p>
          </div>
        ))}
      </dl>
    </section>
  );
}

function SubScores({ risk }: { risk: RiskScore }) {
  if (!risk.sub_scores) return null;
  return (
    <section className="flex flex-col gap-3">
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {Object.entries(risk.sub_scores).map(([k, v]) => (
          <li key={k} className="card-soft p-4" title={v.definition}>
            <p className="text-xs font-medium text-ink-3">{SUB_SCORE_LABELS[k] ?? humanize(k)}</p>
            <p className="mt-1 text-2xl font-bold text-ink">{v.score == null ? "—" : Math.round(v.score)}</p>
            <p className="text-[11px] text-ink-3">{v.score == null ? "not enough data" : `higher is ${v.higher_is}`}</p>
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-ink-3">
        *Efficiency is a proxy (asymmetry plus rep-to-rep consistency). True mechanical efficiency needs force or energy data a single camera cannot provide.
      </p>
    </section>
  );
}

function InjuryTypes({ risk }: { risk: RiskScore }) {
  if (!risk.injury_categories) return null;
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-ink">Where the pattern points</h2>
        <p className="mt-0.5 text-sm text-ink-3">Movement patterns the research links to common injury types. A flag to look closer, not a diagnosis.</p>
      </div>
      <ul className="grid gap-3 md:grid-cols-3">
        {Object.entries(risk.injury_categories).map(([k, c]) => (
          <li key={k} className="card-soft p-5">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-ink">{c.label}</h3>
              <span className={`badge badge-${LEVEL_TONE[c.level] ?? "muted"}`}>{c.level === "insufficient_data" ? "no data" : c.level}</span>
            </div>
            {c.drivers && c.drivers.length > 0 ? (
              <ul className="mt-3 space-y-1 text-sm text-ink-2">
                {c.drivers.slice(0, 3).map((d) => <li key={d.factor}>• {humanize(d.factor)}</li>)}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-ink-3">{c.level === "insufficient_data" ? "Not enough measurable signal for this clip." : "Nothing notable."}</p>
            )}
            {c.video_kinematics_used === false && <p className="mt-2 text-[11px] text-ink-3">Based on history and load only: no usable video signal.</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function MovementSummary({ risk }: { risk: RiskScore }) {
  const reps = risk.movement?.reps, gait = risk.movement?.gait;
  if (!reps && !gait) return null;
  const items: [string, string][] = [];
  if (reps) {
    items.push(["Repetitions", String(reps.n_reps)]);
    const t = reps.mean_rep_s ?? reps.mean_cycle_s;
    if (t != null) items.push(["Time per rep", `${t.toFixed(1)} s`]);
    if (reps.mean_descent_s != null && reps.mean_ascent_s != null) items.push(["Down / up", `${reps.mean_descent_s.toFixed(1)} s / ${reps.mean_ascent_s.toFixed(1)} s`]);
    if (reps.cv_pct != null) items.push(["Rep-to-rep variation", `${Math.round(reps.cv_pct)}%`]);
    if (reps.drift_pct != null) items.push(["Change over the set", `${reps.drift_pct > 0 ? "+" : ""}${Math.round(reps.drift_pct)}%`]);
  }
  if (gait) {
    items.push(["Steps counted", String(gait.n_steps)], ["Cadence", `${Math.round(gait.cadence_spm)} steps/min`]);
    if (gait.step_time_asymmetry_pct != null) items.push(["Step-time asymmetry", `${Math.round(gait.step_time_asymmetry_pct)}%`]);
  }
  return (
    <section className="card-soft p-6 sm:p-8">
      <h2 className="text-lg font-semibold text-ink">{gait ? "Gait" : "Repetitions"}</h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {items.map(([k, v]) => (
          <div key={k} className="rounded-[12px] bg-white px-4 py-3">
            <dt className="text-xs text-ink-3">{k}</dt><dd className="font-semibold text-ink">{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function ResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const videoQ = useVideo(id);
  const completed = videoQ.data?.processing_status === "completed";

  const bioQ = useQuery({
    queryKey: ["video", id, "biomechanics"],
    queryFn: () => api.get<Biomechanics>(`/videos/${id}/biomechanics`),
    enabled: completed,
  });

  const riskQ = useQuery({
    queryKey: ["video", id, "risk"],
    enabled: completed,
    queryFn: async (): Promise<RiskResult> => {
      try {
        const rs = await api.get<RiskScore | InsufficientBaseline>(`/videos/${id}/risk-score`);
        if ("status" in rs && rs.status === "insufficient_baseline_data") return { kind: "insufficient", info: rs };
        return { kind: "scored", risk: rs as RiskScore };
      } catch (e) {
        // "no validated metrics" (400/422), "still processing" (409) or "not found" (404) just mean there's
        // no score to show: say why instead of failing the page.
        if (e instanceof ApiError && [400, 404, 409, 422].includes(e.status)) return { kind: "unavailable", message: e.status === 404 ? undefined : e.message };
        throw e;
      }
    },
  });

  const scored = riskQ.data?.kind === "scored";
  const recsQ = useQuery({
    queryKey: ["video", id, "recommendations"],
    queryFn: () => api.get<Recommendation[]>(`/videos/${id}/recommendations`),
    enabled: scored,
  });

  const [picked, setPicked] = useState<string[] | null>(null);
  const fps = videoQ.data?.fps ?? null;

  const { validatedNames, qualitativeNames, chartData } = useMemo(() => {
    const frames = bioQ.data?.frames ?? [];
    const validated = new Set<string>();
    const qualitative = new Set<string>();
    const byFrame = new Map<number, Record<string, number>>();
    for (const f of frames) {
      if (f.confidence === "validated") {
        validated.add(f.metric_name);
        const row = byFrame.get(f.frame_number) ?? { t: fps ? f.frame_number / fps : f.frame_number };
        row[f.metric_name] = f.metric_value;
        byFrame.set(f.frame_number, row);
      } else {
        qualitative.add(f.metric_name); // never plotted or quoted as numbers — see SCIENCE_CONSTRAINTS
      }
    }
    return {
      validatedNames: [...validated],
      qualitativeNames: [...qualitative],
      chartData: [...byFrame.entries()].sort((a, b) => a[0] - b[0]).map(([, r]) => r),
    };
  }, [bioQ.data, fps]);

  if (videoQ.isPending) return <PageSkeleton rows={3} />;
  if (videoQ.isError) {
    return (
      <>
        <BackLink href="/videos">All videos</BackLink>
        <ErrorState message={videoQ.error.message} onRetry={() => videoQ.refetch()} />
      </>
    );
  }
  const video = videoQ.data;
  const back = <BackLink href={`/videos/${id}`}>Video</BackLink>;

  if (!completed) {
    return (
      <>
        <PageHeader back={back} title="Results" />
        <Notice tone="info">
          {video.processing_status === "failed"
            ? "This video couldn't be analyzed, so there are no results to show."
            : "This video is still being analyzed. Results will be here shortly."}{" "}
          <Link href={`/videos/${id}`} className="font-semibold underline underline-offset-4">View status</Link>
        </Notice>
      </>
    );
  }
  if (bioQ.isPending || riskQ.isPending) return <PageSkeleton rows={3} />;
  if (bioQ.isError || riskQ.isError) {
    const err = bioQ.error ?? riskQ.error;
    return (
      <>
        {back}
        <ErrorState message={err?.message ?? "We couldn't load the results."} onRetry={() => { bioQ.refetch(); riskQ.refetch(); }} />
      </>
    );
  }

  const bio = bioQ.data;
  const risk = riskQ.data;
  const defaults = validatedNames.filter((n) => n.includes("knee_flexion")).concat(validatedNames).slice(0, 2);
  const shown = (picked ?? [...new Set(defaults)]).filter((n) => validatedNames.includes(n));
  const keyNumbers = bio.summary.filter((s) => validatedNames.includes(s.metric_name));
  const lsi = bio.limb_symmetry_index;
  const hero =
    risk.kind === "scored"
      ? { low: "hero--green", moderate: "hero--blue", high: "hero--yellow", critical: "" }[risk.risk.risk_category]
      : "hero--blue";

  return (
    <>
      <PageHeader
        back={back}
        title={`${movementLabel(video.movement_type)} results`}
        actions={
          <>
            <DownloadButton path={`/videos/${id}/biomechanics/export.csv`} filename={`video-${id}.csv`} label="CSV" />
            {risk.kind === "scored" && (
              <>
                <DownloadButton path={`/videos/${id}/report.pdf`} filename={`report-${id}.pdf`} label="PDF" variant="soft" />
                <DownloadButton path={`/videos/${id}/report.xlsx`} filename={`report-${id}.xlsx`} label="Excel" />
              </>
            )}
          </>
        }
      />

      {/* ---------- Score ---------- */}
      {risk.kind === "scored" ? (
        <section
          className={`hero ${hero}`}
          style={risk.risk.risk_category === "critical" ? { background: "var(--danger-bg)", color: "var(--danger-fg)" } : undefined}
        >
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide opacity-80">Movement pattern score</p>
            <p className="mt-1 text-5xl font-bold tracking-tight">
              {Math.round(risk.risk.overall_score)}<span className="text-2xl font-semibold opacity-70"> / 100</span>
            </p>
            <p className="mt-2 max-w-md opacity-90">
              {`${RISK[risk.risk.risk_category].label} risk pattern. This flags movement worth a closer look — it isn't a prediction of injury.`}
            </p>
          </div>
          {Object.values(risk.risk.score_breakdown).some((b) => b.available) && (
            <ul className="w-full max-w-xs space-y-2.5 sm:w-72">
              {Object.entries(risk.risk.score_breakdown).filter(([, b]) => b.available).sort((a, b) => b[1].max - a[1].max).map(([k, b]) => (
                <li key={k}>
                  <div className="flex justify-between text-sm"><span>{breakdownLabel(k)}</span><span className="font-semibold">{Math.round(b.points)}/{b.max}</span></div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-black/10"><span className="block h-full rounded-full bg-current opacity-60" style={{ width: `${b.max ? (b.points / b.max) * 100 : 0}%` }} /></div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : risk.kind === "insufficient" ? (
        <Notice tone="info">
          {risk.info.unit === "athletes"
            ? `A score needs a comparison group of at least ${risk.info.need} different athletes. So far there are ${risk.info.have}. `
            : `A score needs enough similar videos to compare against (${risk.info.have} of ${risk.info.need} so far). `}
          Your measurements are below, and the score will appear once there&apos;s a baseline.
        </Notice>
      ) : (
        <Notice tone="info">{risk.message ? `${risk.message} ` : "There's no risk score for this video. "}The measurements are below.</Notice>
      )}

      <ClassificationNotes video={video} />

      <QualityNotes
        video={video}
        quality={risk.kind === "scored" ? risk.risk.quality : undefined}
        caveat={risk.kind === "scored" ? risk.risk.data_quality?.caveat : undefined}
        baseline={risk.kind === "scored" ? risk.risk.baseline : undefined}
      />
      {risk.kind === "scored" && <SubScores risk={risk.risk} />}

      {/* ---------- Key numbers ---------- */}
      {keyNumbers.length > 0 && (
        <section className="card-soft p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-ink">Key numbers</h2>
          <p className="mt-0.5 text-sm text-ink-3">Estimated from video — expect a few degrees of error.</p>
          <ul className="mt-5 grid gap-3 sm:grid-cols-2">
            {keyNumbers.map((s) => (
              <li key={s.metric_name} className="flex items-center justify-between rounded-[12px] bg-white px-4 py-3.5">
                <span className="font-medium text-ink">{metricLabel(s.metric_name)}</span>
                <span className="text-right text-sm text-ink-2">
                  Peak <b className="text-ink">{wholeDegrees(s.peak_value)}</b>
                  {s.range_of_motion != null && <> · Range <b className="text-ink">{wholeDegrees(s.range_of_motion)}</b></>}
                </span>
              </li>
            ))}
          </ul>
          {lsi != null && (
            <p className="mt-5 text-sm text-ink-2">
              <b className="text-ink">Left–right balance: {Math.round(lsi)}%.</b>{" "}
              Many programs use 90% as a rule of thumb, but that cutoff has documented limits — treat it as one signal, not a pass or fail.
            </p>
          )}
        </section>
      )}

      {/* ---------- Chart ---------- */}
      {validatedNames.length > 0 && (
        <section className="card p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-ink">Movement over time</h2>
          <p className="mt-0.5 text-sm text-ink-3">Pick what to show. Angles are in degrees.</p>
          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Metrics to show">
            {validatedNames.map((n) => {
              const on = shown.includes(n);
              return (
                <button key={n} aria-pressed={on}
                  onClick={() => setPicked(on ? shown.filter((x) => x !== n) : [...shown, n])}
                  className={`btn btn-sm ${on ? "btn-soft" : "btn-outline"}`}>
                  {on && <Icon name="check" className="h-3.5 w-3.5" />} {metricLabel(n)}
                </button>
              );
            })}
          </div>
          {shown.length === 0 ? (
            <p className="py-16 text-center text-ink-3">Choose a metric above to see it here.</p>
          ) : (
            <div className="mt-6 h-[300px] w-full" role="img" aria-label={`Line chart of ${shown.map(metricLabel).join(", ")} over time`}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
                  <CartesianGrid stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="t" tickFormatter={(t: number) => (fps ? `${t.toFixed(1)}s` : String(t))} tick={{ fill: "#64748b", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#e2e8f0" }} minTickGap={32} />
                  <YAxis tickFormatter={(v: number) => `${Math.round(v)}°`} tick={{ fill: "#64748b", fontSize: 12 }} tickLine={false} axisLine={false} width={48} />
                  <Tooltip
                    formatter={(v, name) => [wholeDegrees(Number(v)), metricLabel(String(name))]}
                    labelFormatter={(t) => (fps ? `${Number(t).toFixed(2)} s` : `Frame ${t}`)}
                    contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 8px 24px -8px rgba(15,23,42,.15)" }}
                  />
                  <Legend formatter={(n) => metricLabel(String(n))} iconType="circle" wrapperStyle={{ fontSize: 13 }} />
                  {shown.map((n) => (
                    <Line key={n} type="monotone" dataKey={n} stroke={SERIES_COLORS[validatedNames.indexOf(n) % SERIES_COLORS.length]} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      )}

      {/* ---------- Visual checks (qualitative only — no numbers by design) ---------- */}
      {qualitativeNames.length > 0 && (
        <section className="card-soft flex flex-col gap-3 p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-ink">Visual checks</h2>
          <p className="text-ink-2">
            Knee alignment from the front view is best judged by eye. From a single camera it can only be flagged, not measured as an angle, so we don&apos;t show a number.
          </p>
          <Link href={`/videos/${id}`} className="btn btn-outline btn-sm w-fit"><Icon name="play" className="h-4 w-4" /> Watch the tracked video</Link>
        </section>
      )}

      {risk.kind === "scored" && <InjuryTypes risk={risk.risk} />}
      {risk.kind === "scored" && <MovementSummary risk={risk.risk} />}

      {/* ---------- Recommendations ---------- */}
      {recsQ.data && recsQ.data.length > 0 && (
        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-ink">Suggested next steps</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {[...recsQ.data].sort((a, b) => a.priority - b.priority).map((r, i) => (
              <li key={`${r.title}-${i}`} className="card-soft p-6">
                <span className="badge badge-muted">{humanize(r.category)}</span>
                <h3 className="mt-3 font-semibold text-ink">{r.title}</h3>
                <p className="mt-1 text-sm text-ink-2">{r.description}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {risk.kind === "scored" && (
        <details className="rounded-[16px] bg-surface px-5 py-4 text-sm text-ink-2">
          <summary className="cursor-pointer font-semibold text-ink">How this score works</summary>
          <p className="mt-3">{risk.risk.methodology_note}</p>
        </details>
      )}
    </>
  );
}
