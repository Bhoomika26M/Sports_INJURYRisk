"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await apiClient.fetchWithAuth("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      apiClient.setToken(data.access_token);
      const userData = await apiClient.fetchWithAuth("/auth/me");
      login(data.access_token, userData);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to login. Please check your credentials.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/google`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6" style={{ background: "var(--bg-muted)" }}>
      <div className="bento-card max-w-md w-full p-8 sm:p-10 space-y-6">
        <div className="text-center">
          <div className="circle-action-btn mx-auto mb-3" style={{ width: 56, height: 56 }}>
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="font-bold tracking-tight" style={{ color: "var(--text-primary)", fontSize: 26, letterSpacing: "-0.02em" }}>
            InjuryDetect
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            Sports Biomechanics & Injury Risk Intelligence
          </p>
        </div>

        <div className="grouped-row p-4">
          <div className="text-xs font-semibold uppercase mb-2.5 flex items-center justify-between" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
            <span>Continue with Google</span>
            <span className="status-pill status-pill--info">OAuth2</span>
          </div>
          <button
            onClick={handleGoogleLogin}
            className="pill-btn--outline w-full justify-center"
            disabled={loading}
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="status-pill status-pill--danger" style={{ padding: "12px 16px", fontSize: 13 }}>
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Email Address
            </label>
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              className="field-input"
              placeholder="coach@demo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Password
            </label>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="field-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div className="pt-2">
            <button type="submit" disabled={loading} className="pill-btn--primary w-full justify-center" style={{ padding: "14px 22px", fontSize: 15 }}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </div>
        </form>

        <div className="text-center pt-4" style={{ borderTop: "1px solid var(--border-faint)" }}>
          <Link href="/register" className="text-xs font-semibold" style={{ color: "var(--brand-dark)" }}>
            Don&apos;t have an account? Register here
          </Link>
        </div>
      </div>
    </div>
  );
}