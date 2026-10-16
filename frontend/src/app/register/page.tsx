"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useHydrated } from "@/lib/hooks";
import { API_BASE_URL, ApiError } from "@/lib/api-client";
import type { Role } from "@/lib/types";
import { Field } from "@/components/field";
import { GoogleIcon, Icon } from "@/components/icons";
import { Logo } from "@/components/logo";
import { Modal } from "@/components/dialog";
import { Notice, Spinner } from "@/components/feedback";

const SHOW_GOOGLE = process.env.NEXT_PUBLIC_ENABLE_GOOGLE_LOGIN !== "false";

// "admin" is deliberately not offered here — admin accounts shouldn't be self-service.
const ROLES: { value: Exclude<Role, "admin">; label: string; hint: string }[] = [
  { value: "athlete", label: "Athlete", hint: "Upload your own movement videos" },
  { value: "coach", label: "Coach", hint: "Manage athletes and review results" },
  { value: "physiotherapist", label: "Physiotherapist", hint: "Follow rehab and flagged athletes" },
  { value: "sports_scientist", label: "Sports scientist", hint: "Explore baselines and analytics" },
];

export default function RegisterPage() {
  const router = useRouter();
  const { signUp } = useAuth();
  const hydrated = useHydrated();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role | null>(null);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [modalRole, setModalRole] = useState<Role | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [roleError, setRoleError] = useState<string | null>(null);

  function handleGoogleClick() {
    if (role) {
      // If user already clicked/selected a role, proceed directly without opening the modal
      window.location.href = `${API_BASE_URL}/auth/google?role=${encodeURIComponent(role)}`;
    } else {
      // Prompt modal to select a role first
      setModalRole(null);
      setRoleModalOpen(true);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!role) {
      setRoleError("Please choose your role before creating your account.");
      return;
    }
    setError(null);
    setEmailError(null);
    setRoleError(null);
    setBusy(true);
    try {
      await signUp({ email: email.trim(), password, full_name: fullName.trim(), role });
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.code === "DUPLICATE_EMAIL") {
        setEmailError("There's already an account with this email. Try signing in instead.");
      } else {
        setError(err instanceof Error ? err.message : "We couldn't create your account. Please try again.");
      }
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-wash px-4 py-10">
      <div className="card w-full max-w-lg p-8 sm:p-10">
        <div className="flex flex-col items-center text-center">
          <Logo href="/" />
          <h1 className="mt-7 text-[26px] font-bold tracking-tight text-ink">Create your account</h1>
          <p className="mt-1.5 text-ink-2">It takes less than a minute.</p>
        </div>

        <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
          {error && <Notice tone="danger">{error}</Notice>}

          <Field label="Full name">
            {(p) => <input {...p} name="name" autoComplete="name" autoFocus required className="input"
              placeholder="Alex Johnson" value={fullName} onChange={(e) => setFullName(e.target.value)} />}
          </Field>

          <Field label="Email" error={emailError}>
            {(p) => <input {...p} name="email" type="email" inputMode="email" autoComplete="email" required className="input"
              placeholder="you@example.com" value={email} onChange={(e) => { setEmail(e.target.value); setEmailError(null); }} />}
          </Field>

          <Field label="Password" hint="At least 8 characters.">
            {(p) => <input {...p} name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128}
              className="input" value={password} onChange={(e) => setPassword(e.target.value)} />}
          </Field>

          <fieldset>
            <div className="flex items-center justify-between">
              <legend className="mb-1.5 text-sm font-medium text-ink">I am a…</legend>
              {role && (
                <button
                  type="button"
                  onClick={() => setRole(null)}
                  className="text-xs text-ink-3 hover:text-ink underline"
                >
                  Clear selection
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {ROLES.map((r) => (
                <label key={r.value} className="choice !flex-col !items-start !gap-0.5 !py-3 cursor-pointer">
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={role === r.value}
                    onChange={() => {
                      setRole(r.value);
                      setRoleError(null);
                    }}
                    className="sr-only"
                  />
                  <span className="font-medium text-ink">{r.label}</span>
                  <span className="text-[13px] font-normal text-ink-3">{r.hint}</span>
                </label>
              ))}
            </div>
            {roleError && <p className="mt-1.5 text-sm font-medium text-danger">{roleError}</p>}
          </fieldset>

          <button type="submit" disabled={busy || !hydrated} className="btn btn-primary mt-1 w-full">
            {busy ? <Spinner className="h-4 w-4" /> : <Icon name="check" className="h-4 w-4" />}
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>

        {SHOW_GOOGLE && (
          <>
            <div className="my-6 flex items-center gap-3 text-sm text-ink-3">
              <span className="h-px flex-1 bg-hair" /> or <span className="h-px flex-1 bg-hair" />
            </div>
            <button
              type="button"
              onClick={handleGoogleClick}
              className="btn btn-outline flex w-full items-center justify-center gap-2.5 !py-2.5 font-medium shadow-xs"
            >
              <GoogleIcon className="h-5 w-5 shrink-0" />
              <span>
                {role
                  ? `Continue with Google as ${ROLES.find((r) => r.value === role)?.label}`
                  : "Continue with Google"}
              </span>
            </button>
          </>
        )}

        <Modal
          open={roleModalOpen}
          onClose={() => setRoleModalOpen(false)}
          title="Select your role"
          description="Choose how you will use the platform before continuing with Google."
        >
          <div className="mt-4 flex flex-col gap-5">
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {ROLES.map((r) => (
                <label
                  key={r.value}
                  className="choice !flex-col !items-start !gap-0.5 !py-3 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="modal_role"
                    value={r.value}
                    checked={modalRole === r.value}
                    onChange={() => setModalRole(r.value)}
                    className="sr-only"
                  />
                  <span className="font-medium text-ink">{r.label}</span>
                  <span className="text-[13px] font-normal text-ink-3">{r.hint}</span>
                </label>
              ))}
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-hair">
              <button
                type="button"
                onClick={() => setRoleModalOpen(false)}
                className="btn btn-ghost"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!modalRole}
                onClick={() => {
                  if (!modalRole) return;
                  setRole(modalRole);
                  setRoleModalOpen(false);
                  window.location.href = `${API_BASE_URL}/auth/google?role=${encodeURIComponent(modalRole)}`;
                }}
                className="btn btn-primary flex items-center gap-2"
              >
                <GoogleIcon className="h-4 w-4 shrink-0" />
                <span>
                  {modalRole
                    ? `Sign up as ${ROLES.find((r) => r.value === modalRole)?.label}`
                    : "Select a role"}
                </span>
              </button>
            </div>
          </div>
        </Modal>

        <p className="mt-7 text-center text-sm text-ink-2">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-brand-dark underline underline-offset-4">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
