"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient, ApiError } from "@/lib/api-client";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("athlete");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await apiClient.fetchWithAuth("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName, role }),
      });

      // Redirect to login after successful registration
      router.push("/login");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to register");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-100">
      <div className="max-w-md w-full neu-card rounded-2xl p-8 sm:p-10 space-y-7">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl neu-flat text-blue-600 mb-3">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-slate-900">
            Create Account
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Register to access kinematics data & risk assessments
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
              <svg className="w-4 h-4 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Full Name
            </label>
            <input
              name="fullName"
              type="text"
              required
              className="w-full px-3.5 py-2.5 rounded-xl neu-inset text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              placeholder="Alex Johnson"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Email Address
            </label>
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              className="w-full px-3.5 py-2.5 rounded-xl neu-inset text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              placeholder="athlete@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Password (min 4 characters)
            </label>
            <input
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={4}
              className="w-full px-3.5 py-2.5 rounded-xl neu-inset text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
              Account Role
            </label>
            <select
              name="role"
              className="w-full px-3.5 py-2.5 rounded-xl neu-inset text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="athlete">Athlete</option>
              <option value="coach">Coach</option>
              <option value="physiotherapist">Physiotherapist</option>
              <option value="sports_scientist">Sports Scientist</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 neu-button-primary rounded-xl text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              {loading ? "Registering..." : "Create Account"}
            </button>
          </div>
        </form>

        <div className="text-center pt-2">
          <Link href="/login" className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline">
            Already have an account? Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
