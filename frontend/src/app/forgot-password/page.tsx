"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { Field } from "@/components/field";
import { Logo } from "@/components/logo";
import { Notice, Spinner } from "@/components/feedback";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !email) return;
    setError(null);
    setBusy(true);

    try {
      await api.post("/auth/password/forgot", { email: email.trim() });
      setSent(true);
      setBusy(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-wash px-4 py-10">
      <div className="card w-full max-w-md p-8 sm:p-10">
        <div className="flex flex-col items-center text-center">
          <Logo href="/" />
          <h1 className="mt-7 text-[26px] font-bold tracking-tight text-ink">Reset password</h1>
          <p className="mt-1.5 text-sm text-ink-2">
            Enter your email and we&apos;ll send a 6-digit verification code.
          </p>
        </div>

        {sent ? (
          <div className="mt-8 flex flex-col gap-5">
            <Notice tone="info">
              If an account exists for <strong>{email}</strong>, a 6-digit verification code has been dispatched.
              Check your inbox or developer console.
            </Notice>
            <button
              type="button"
              onClick={() => router.push(`/reset-password?email=${encodeURIComponent(email)}`)}
              className="btn btn-primary w-full cursor-pointer"
            >
              Enter Verification Code
            </button>
            <p className="text-center text-xs text-ink-3">
              Didn&apos;t receive it?{" "}
              <button
                type="button"
                onClick={() => setSent(false)}
                className="font-semibold text-brand-dark hover:underline"
              >
                Try again
              </button>
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
            {error && <Notice tone="danger">{error}</Notice>}

            <Field label="Email address">
              {(p) => (
                <input
                  {...p}
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  autoFocus
                  required
                  className="input"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              )}
            </Field>

            <button type="submit" disabled={busy} className="btn btn-primary w-full cursor-pointer">
              {busy && <Spinner className="h-4 w-4" />}
              {busy ? "Sending code…" : "Send verification code"}
            </button>
          </form>
        )}

        <p className="mt-7 text-center text-sm text-ink-2">
          Remember your password?{" "}
          <Link href="/login" className="font-semibold text-brand-dark underline underline-offset-4">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
