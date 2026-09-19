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

      // Immediately fetch /me to get user details for context
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
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6" style={{ backgroundColor: "#edf2f7" }}>
      <div 
        className="max-w-md w-full bg-white rounded-2xl border-2 border-slate-300 p-8 sm:p-10 space-y-6"
        style={{ boxShadow: "8px 8px 24px rgba(148, 163, 184, 0.4), -8px -8px 24px rgba(255, 255, 255, 0.95)" }}
      >
        {/* Brand Header */}
        <div className="text-center">
          <div className="w-14 h-14 rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-500/30 flex items-center justify-center mx-auto mb-3">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Injury<span className="text-blue-600">Detect</span>
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-1">
            Sports Biomechanics & Injury Risk Intelligence
          </p>
        </div>

        {/* Quick Demo Login Chips */}
        <div className="bg-slate-50 rounded-xl p-4 border-2 border-slate-200">
          <div className="text-xs font-extrabold uppercase tracking-wider text-slate-600 mb-2.5 flex items-center justify-between">
            <span>Quick Demo Login</span>
            <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              CLICK TO FILL
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {demoAccounts.map((acc) => {
              const isSelected = email === acc.email;
              return (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => fillDemo(acc.email)}
                  className={`text-xs px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                    isSelected
                      ? "bg-blue-600 border-2 border-blue-600 text-white shadow-md shadow-blue-600/30"
                      : "bg-white hover:bg-slate-100 text-slate-700 border-2 border-slate-300 hover:border-slate-400 shadow-xs"
                  }`}
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
            <div className="bg-red-50 border-2 border-red-300 text-red-800 text-sm px-4 py-3 rounded-xl flex items-center gap-2.5 font-semibold">
              <svg className="w-5 h-5 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Email Address
            </label>
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-semibold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
              placeholder="coach@demo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-semibold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-6 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-extrabold text-base rounded-xl shadow-lg shadow-blue-600/30 transition-all focus:outline-none focus:ring-4 focus:ring-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing in...
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </div>
        </form>

        <div className="text-center pt-1 border-t border-slate-200">
          <Link href="/register" className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline">
            Don't have an account? Register here
          </Link>
        </div>
      </div>
    </div>
  );
}
