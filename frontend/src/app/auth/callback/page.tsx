"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

// Landing page after Google sign-in. The backend has already set the httpOnly refresh cookie on the
// redirect that brought the browser here. AuthProvider's bootstrap exchanges that cookie for an
// in-memory access token (POST /auth/refresh) and loads /auth/me; this page just waits for the result.
// No token is ever in the URL, and nothing is written to localStorage.
export default function OAuthCallbackPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/dashboard" : "/login?error=oauth_session_failed");
  }, [loading, user, router]);

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-muted)" }}>
      <div className="bento-card p-6 text-sm font-bold" style={{ color: "var(--text-primary)" }}>
        Completing sign-in…
      </div>
    </div>
  );
}
