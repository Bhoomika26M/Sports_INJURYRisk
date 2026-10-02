import Link from "next/link";
import { Icon, type IconName } from "@/components/icons";
import { Logo } from "@/components/logo";

const FEATURES: { icon: IconName; title: string; body: string }[] = [
  { icon: "upload", title: "Upload a short clip", body: "Squats, jumps, landings, running or cutting. A phone video is all you need." },
  { icon: "activity", title: "See how the body moves", body: "Joint angles and left-right balance, measured from video and shown plainly." },
  { icon: "chart", title: "Understand the signals", body: "A transparent score where every part is visible, plus simple next steps." },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-5">
        <Logo href="/" />
        <nav className="flex items-center gap-2" aria-label="Account">
          <Link href="/login" className="btn btn-ghost btn-sm">Sign in</Link>
          <Link href="/register" className="btn btn-primary btn-sm">Get started</Link>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-5">
        <section className="mx-auto max-w-2xl py-16 text-center sm:py-24">
          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-ink sm:text-[52px]">
            Movement screening, made simple
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-ink-2">
            Upload a short video and get clear movement insights for athletes — no black boxes, no false precision.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/register" className="btn btn-primary !min-h-[52px] !px-8 !text-base">Create a free account</Link>
            <Link href="/login" className="btn btn-soft !min-h-[52px] !px-8 !text-base">Sign in</Link>
          </div>
        </section>

        <section className="grid gap-5 pb-16 sm:grid-cols-3" aria-label="How it works">
          {FEATURES.map((f) => (
            <div key={f.title} className="card-soft p-7">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-brand-dark shadow-[var(--shadow-diffuse)]">
                <Icon name={f.icon} className="h-6 w-6" />
              </span>
              <h2 className="mt-5 text-lg font-semibold text-ink">{f.title}</h2>
              <p className="mt-1.5 text-ink-2">{f.body}</p>
            </div>
          ))}
        </section>

        <p className="mx-auto max-w-xl pb-16 text-center text-sm text-ink-3">
          Built on honest science: scores flag movement patterns worth a closer look, they don&apos;t predict injuries,
          and front-view knee alignment is shown as a visual flag, never an exact angle.
        </p>
      </main>

      <footer className="border-t border-faint py-6 text-center text-sm text-ink-3">InjuryDetect</footer>
    </div>
  );
}
