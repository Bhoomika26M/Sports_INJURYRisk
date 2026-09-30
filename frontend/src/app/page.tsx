import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-app)" }}>
      <header className="app-header">
        <div className="flex items-center gap-3">
          <Link href="/login" className="flex items-center gap-3">
            <div className="circle-action-btn" style={{ width: 40, height: 40, fontSize: 20 }}>W</div>
            <span className="font-bold text-base" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>InjuryDetect</span>
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="pill-btn--primary">Sign In</Link>
          <Link href="/register" className="pill-btn--soft">Get Started</Link>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <section className="text-center max-w-3xl mx-auto">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6" style={{ color: "var(--text-primary)", letterSpacing: "-0.03em" }}>
            Sports Biomechanics & Injury Risk Intelligence
          </h1>
          <p className="text-lg mb-10 max-w-2xl mx-auto" style={{ color: "var(--text-secondary)", lineHeight: 1.7 }}>
            Movement screening, joint kinematics, and heuristic risk flags for athletes and coaches.
            Upload a video, get actionable insights — no black boxes, no false precision.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/register" className="pill-btn--primary text-lg px-8 py-4">Start Free</Link>
            <Link href="/login" className="pill-btn--soft text-lg px-8 py-4">Sign In</Link>
          </div>
        </section>

        <section className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="bento-card p-6">
            <div className="circle-action-btn mb-4" style={{ width: 48, height: 48, fontSize: 22 }}>📹</div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Upload & Analyze</h3>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Upload movement videos (squat, jump, landing, running, cutting). Get joint angles, LSI, and qualitative valgus flags in minutes.
            </p>
          </div>
          <div className="bento-card p-6">
            <div className="circle-action-btn mb-4" style={{ width: 48, height: 48, fontSize: 22 }}>📊</div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Transparent Risk Scoring</h3>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Heuristic composite: movement anomaly vs. population baseline, LSI asymmetry flag, prior injury, ACWR, fatigue. Every component visible.
            </p>
          </div>
          <div className="bento-card p-6">
            <div className="circle-action-btn mb-4" style={{ width: 48, height: 48, fontSize: 22 }}>🧠</div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>Actionable Recommendations</h3>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Rule-based corrective exercises mapped to flagged metrics — FIFA 11+, Copenhagen, Nordic, single-leg work. Priority-sorted.
            </p>
          </div>
        </section>

        <section className="mt-20 max-w-3xl mx-auto text-center">
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Built with honest science: no supervised injury prediction, no trained pose models, frontal-plane metrics are qualitative only.
            <br />See <a href="/docs/SCIENCE_CONSTRAINTS.md" className="underline" style={{ color: "var(--brand-dark)" }}>SCIENCE_CONSTRAINTS.md</a> for details.
          </p>
        </section>
      </main>

      <footer className="border-t py-8" style={{ borderColor: "var(--border-faint)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          InjuryDetect v1.0 — Sports Biomechanics & Injury Risk Intelligence
        </div>
      </footer>
    </div>
  );
}