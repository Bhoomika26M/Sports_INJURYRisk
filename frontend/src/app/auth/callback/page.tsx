"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Spinner } from "@/components/feedback";

// Landing page after Google sign-in. The backend has already set the httpOnly refresh cookie on the
// redirect that brought the browser here. AuthProvider's bootstrap exchanges that cookie for an
// in-memory access token (POST /auth/refresh) and loads /auth/me; this page just waits for the result.
// No token is ever in the URL, and nothing is written to localStorage.
export default function OAuthCallbackPage() {
  const { restore } = useAuth();
  const router = useRouter();

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const user = await restore();
        if (!active) return;
        if (user) {
          router.replace("/dashboard");
        } else {
          router.replace("/login?error=oauth_session_failed");
        }
      } catch {
        if (!active) return;
        router.replace("/login?error=oauth_session_failed");
      }
    })();
    return () => {
      active = false;
    };
  }, [restore, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-wash px-4">
      <div className="card flex w-full max-w-md flex-col items-center gap-3 p-10 text-center">
        <Spinner className="h-5 w-5" />
        <p className="text-sm font-bold text-ink">Completing sign-in&hellip;</p>
      </div>
    </div>
  );
}