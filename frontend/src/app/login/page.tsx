"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useHydrated } from "@/lib/hooks";
import { API_BASE_URL } from "@/lib/api-client";
import { safeNext } from "@/lib/nav";
import { Field } from "@/components/field";
import { Icon } from "@/components/icons";
import { Logo } from "@/components/logo";
import { Notice, Spinner } from "@/components/feedback";

const DEMO_PASSWORD = "demo123";
const DEMO_ACCOUNTS = [
  { label: "Coach", email: "coach@demo.com" },
  { label: "Athlete", email: "athlete@demo.com" },
  { label: "Physio", email: "physio@demo.com" },
  { label: "Scientist", email: "scientist@demo.com" },
  { label: "Admin", email: "admin@demo.com" },
];
const SHOW_DEMO = process.env.NODE_ENV !== "production";
const SHOW_GOOGLE = process.env.NEXT_PUBLIC_ENABLE_GOOGLE_LOGIN === "true";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const { user, signIn } = useAuth();
  const hydrated = useHydrated();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Already signed in? Skip the form.
  useEffect(() => {
    if (user) router.replace(next);
  }, [user, next, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't sign you in. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-wash px-4 py-10">
      <div className="card w-full max-w-md p-8 sm:p-10">
        <div className="flex flex-col items-center text-center">
          <Logo href="/" />
          <h1 className="mt-7 text-[26px] font-bold tracking-tight text-ink">Welcome back</h1>
          <p className="mt-1.5 text-ink-2">Sign in to keep screening movement.</p>
        </div>

        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
          {error && <Notice tone="danger">{error}</Notice>}

          <Field label="Email">
            {(p) => (
              <input {...p} name="email" type="email" inputMode="email" autoComplete="email" autoFocus required
                className="input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            )}
          </Field>

          <Field label="Password">
            {(p) => (
              <div className="relative">
                <input {...p} name="password" type={showPw ? "text" : "password"} autoComplete="current-password" required
                  className="input !pr-12" value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" onClick={() => setShowPw((s) => !s)}
                  aria-label={showPw ? "Hide password" : "Show password"} aria-pressed={showPw}
                  className="absolute right-1.5 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full text-ink-3 hover:bg-surface hover:text-ink">
                  <Icon name={showPw ? "eye-off" : "eye"} className="h-5 w-5" />
                </button>
              </div>
            )}
          </Field>

          <button type="submit" disabled={busy || !hydrated} className="btn btn-primary mt-1 w-full">
            {busy && <Spinner className="h-4 w-4" />} {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {SHOW_GOOGLE && (
          <>
            <div className="my-6 flex items-center gap-3 text-sm text-ink-3">
              <span className="h-px flex-1 bg-hair" /> or <span className="h-px flex-1 bg-hair" />
            </div>
            <a href={`${API_BASE_URL}/auth/google`} className="btn btn-outline w-full">Continue with Google</a>
          </>
        )}

        {SHOW_DEMO && (
          <div className="mt-7 rounded-[16px] bg-surface p-4">
            <p className="text-sm font-medium text-ink">Try a demo account</p>
            <p className="mt-0.5 text-sm text-ink-3">Fills the form for you. Development only.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button key={a.email} type="button" className="btn btn-outline btn-sm"
                  onClick={() => { setEmail(a.email); setPassword(DEMO_PASSWORD); setError(null); }}>
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <p className="mt-7 text-center text-sm text-ink-2">
          New here?{" "}
          <Link href="/register" className="font-semibold text-brand-dark underline underline-offset-4">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
