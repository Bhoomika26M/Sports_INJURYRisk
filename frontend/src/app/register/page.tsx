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
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8" style={{ background: "var(--bg-muted)" }}>
      <div className="bento-card max-w-md w-full p-8 sm:p-10 space-y-7">
        <div className="text-center">
          <div className="circle-action-btn mx-auto mb-3" style={{ width: 56, height: 56 }}>+</div>
          <h2 className="font-bold tracking-tight" style={{ color: "var(--text-primary)", fontSize: 26, letterSpacing: "-0.02em" }}>
            Create Account
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
            Register to access kinematics data & risk assessments
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="status-pill status-pill--danger" style={{ padding: "12px 16px", fontSize: 13 }}>
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Full Name
            </label>
            <input name="fullName" type="text" required className="field-input" placeholder="Alex Johnson" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Email Address
            </label>
            <input name="email" type="email" autoComplete="email" required className="field-input" placeholder="athlete@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Password (min 4 characters)
            </label>
            <input name="password" type="password" autoComplete="new-password" required minLength={4} className="field-input" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Account Role
            </label>
            <select name="role" className="field-input" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="athlete">Athlete</option>
              <option value="coach">Coach</option>
              <option value="physiotherapist">Physiotherapist</option>
              <option value="sports_scientist">Sports Scientist</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div className="pt-2">
            <button type="submit" disabled={loading} className="pill-btn--primary w-full justify-center">
              {loading ? "Registering..." : "Create Account"}
            </button>
          </div>
        </form>

        <div className="text-center pt-2">
          <Link href="/login" className="text-xs font-semibold" style={{ color: "var(--brand-dark)" }}>
            Already have an account? Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
