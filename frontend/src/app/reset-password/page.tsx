"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import { Field } from "@/components/field";
import { Logo } from "@/components/logo";
import { Notice, Spinner } from "@/components/feedback";
import { Icon } from "@/components/icons";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState(searchParams?.get("email") || "");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setBusy(true);

    try {
      await api.post("/auth/password/reset", {
        email: email.trim(),
        code: code.trim(),
        new_password: newPassword,
      });
      setSuccess(true);
      setBusy(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed. Please check the code.");
      setBusy(false);
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-wash px-4 py-10">
        <div className="card w-full max-w-md p-8 sm:p-10 text-center flex flex-col items-center">
          <Logo href="/" />
          <div className="mt-6 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
            <Icon name="check" className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-[24px] font-bold text-ink">Password reset complete</h1>
          <p className="mt-2 text-sm text-ink-2">
            Your password has been securely updated. Prior active sessions have been revoked.
          </p>
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="btn btn-primary mt-6 w-full cursor-pointer"
          >
            Sign in with new password
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-wash px-4 py-10">
      <div className="card w-full max-w-md p-8 sm:p-10">
        <div className="flex flex-col items-center text-center">
          <Logo href="/" />
          <h1 className="mt-7 text-[26px] font-bold tracking-tight text-ink">Enter reset code</h1>
          <p className="mt-1.5 text-sm text-ink-2">
            Provide the 6-digit code and choose a new password.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
          {error && <Notice tone="danger">{error}</Notice>}

          <Field label="Email address">
            {(p) => (
              <input
                {...p}
                type="email"
                inputMode="email"
                autoComplete="email"
                required
                className="input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            )}
          </Field>

          <Field label="6-Digit Verification Code">
            {(p) => (
              <input
                {...p}
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                autoFocus
                required
                className="input font-mono tracking-widest text-center text-lg"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            )}
          </Field>

          <Field label="New password">
            {(p) => (
              <div className="relative">
                <input
                  {...p}
                  type={showPw ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  className="input !pr-12"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((s) => !s)}
                  aria-label={showPw ? "Hide password" : "Show password"}
                  className="absolute right-1.5 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full text-ink-3 hover:bg-surface hover:text-ink cursor-pointer"
                >
                  <Icon name={showPw ? "eye-off" : "eye"} className="h-5 w-5" />
                </button>
              </div>
            )}
          </Field>

          <button type="submit" disabled={busy} className="btn btn-primary w-full cursor-pointer mt-2">
            {busy && <Spinner className="h-4 w-4" />}
            {busy ? "Updating password…" : "Reset password"}
          </button>
        </form>

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

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
