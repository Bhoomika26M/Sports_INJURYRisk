"use client";

import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";

type TeamOverview = {
  total_athletes: number;
  total_videos: number;
  videos_completed: number;
  videos_failed: number;
  videos_processing: number;
  avg_risk_score: number | null;
  high_risk_count: number;
  critical_risk_count: number;
  low_risk_count: number;
  moderate_risk_count: number;
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<TeamOverview | null>(null);

  useEffect(() => {
    apiClient.fetchWithAuth("/analytics/team-overview").then(setOverview).catch(() => {});
  }, []);

  if (!user) return null;

  const flagged = overview ? overview.high_risk_count + overview.critical_risk_count : 0;

  return (
    <div>
      <section className="bento-hero bento-hero--yellow">
        <div>
          <span className="status-pill status-pill--muted">{user.role.replace("_", " ")}</span>
          <h2 className="bento-hero__title" style={{ marginTop: 12 }}>Welcome, {user.full_name}</h2>
          <p className="bento-hero__subtitle">Movement screening, joint kinematics, and heuristic risk flags — calm review, no black boxes.</p>
          <div className="flex items-center gap-3" style={{ marginTop: 20 }}>
            <Link href="/videos/upload" className="pill-btn--primary">Upload video</Link>
            <Link href="/athletes" className="pill-btn--soft">View athletes</Link>
          </div>
        </div>
        <div className="circle-action-btn" aria-hidden>+</div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6" style={{ marginTop: 40 }}>
        <div className="bento-account-card">
          <span className="bento-account-card__label">Athletes monitored</span>
          <span className="bento-account-card__amount">{overview ? overview.total_athletes : "—"}</span>
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>Across all sports in your scope.</span>
        </div>
        <div className="bento-account-card">
          <span className="bento-account-card__label">Average risk score</span>
          <span className="bento-account-card__amount">{overview && overview.avg_risk_score !== null ? overview.avg_risk_score : "—"}</span>
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {overview ? `${overview.videos_completed}/${overview.total_videos} videos completed · ${flagged} high/critical` : "Waiting for first scored video."}
          </span>
        </div>
      </section>

      <section style={{ marginTop: 40 }}>
        <h3 className="text-xl font-semibold" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: 16 }}>Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link href="/videos/upload" className="dashed-action-card">
            <div className="dashed-action-card__icon-wrapper"><span>+</span></div>
            <div className="dashed-action-card__content">
              <span className="dashed-action-card__title">Analyze movement video</span>
              <span className="dashed-action-card__desc">Upload squat, jump, or cutting clips. Joint angles, LSI, and qualitative valgus flags.</span>
            </div>
            <span className="chevron">›</span>
          </Link>
          <Link href="/athletes" className="dashed-action-card">
            <div className="dashed-action-card__icon-wrapper"><span>◔</span></div>
            <div className="dashed-action-card__content">
              <span className="dashed-action-card__title">Athlete profiles & history</span>
              <span className="dashed-action-card__desc">Injury records, training load, baseline kinematics, and risk history.</span>
            </div>
            <span className="chevron">›</span>
          </Link>
        </div>
      </section>
    </div>
  );
}
