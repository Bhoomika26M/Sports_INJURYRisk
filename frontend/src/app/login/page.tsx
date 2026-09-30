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

  const demoAccounts = [
    { label: "Coach", email: "coach@demo.com", role: "Coach" },
    { label: "Physio", email: "physio@demo.com", role: "Physiotherapist" },
    { label: "Scientist", email: "scientist@demo.com", role: "Sports Scientist" },
    { label: "Athlete", email: "athlete@demo.com", role: "Athlete" },
    { label: "Admin", email: "admin@demo.com", role: "Administrator" },
  ];

  const fillDemo = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("demo123");
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await apiClient.fetchWithAuth("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      // Set inMemoryToken so immediate /auth/me fetch succeeds
      apiClient.setToken(data.access_token);

      // Fetch /me to get user details for context
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

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6" style={{ background: "var(--bg-muted)" }}>
      <div className="bento-card max-w-md w-full p-8 sm:p-10 space-y-6">
        {/* Brand Header */}
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

        {/* Quick Demo Login Chips */}
        <div className="grouped-row p-4">
          <div className="text-xs font-semibold uppercase mb-2.5 flex items-center justify-between" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
            <span>Quick Demo Login</span>
            <span className="status-pill status-pill--info">Click to fill</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {demoAccounts.map((acc) => {
              const isSelected = email === acc.email;
              return (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => fillDemo(acc.email)}
                  className={isSelected ? "pill-btn--primary" : "pill-btn--outline"}
                  style={{ fontSize: 12 }}
                >
                  {acc.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Login Form */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="status-pill status-pill--danger" style={{ padding: "12px 16px", fontSize: 13 }}>
              <span>{error}</span>
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
