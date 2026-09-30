"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useRouter } from "next/navigation";

export default function NewAthletePage() {
  const [form, setForm] = useState({
    sport_type: "",
    position: "",
    date_of_birth: "",
    height_cm: "",
    weight_kg: "",
    dominant_side: "right",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await apiClient.fetchWithAuth("/athletes", {
        method: "POST",
        body: JSON.stringify({
          sport_type: form.sport_type,
          position: form.position || null,
          date_of_birth: form.date_of_birth,
          height_cm: form.height_cm ? parseFloat(form.height_cm) : null,
          weight_kg: form.weight_kg ? parseFloat(form.weight_kg) : null,
          dominant_side: form.dominant_side,
        }),
      });
      router.push("/athletes");
    } catch (e: any) {
      setError(e.message || "Failed to create athlete");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>New Athlete</h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Create a new athlete profile.</p>
      </div>

      <form className="bento-card p-6 space-y-5" onSubmit={handleSubmit}>
        {error && <div className="status-pill status-pill--danger">{error}</div>}

        <div>
          <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
            Sport Type
          </label>
          <select className="field-input" value={form.sport_type} onChange={e => setForm({...form, sport_type: e.target.value})} required>
            <option value="">Select sport</option>
            <option value="basketball">Basketball</option>
            <option value="soccer">Soccer</option>
            <option value="track">Track & Field</option>
            <option value="volleyball">Volleyball</option>
            <option value="tennis">Tennis</option>
            <option value="baseball">Baseball</option>
            <option value="football">Football</option>
            <option value="swimming">Swimming</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
            Position (optional)
          </label>
          <input className="field-input" placeholder="e.g., Point Guard, Striker" value={form.position} onChange={e => setForm({...form, position: e.target.value})} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Date of Birth
            </label>
            <input type="date" className="field-input" value={form.date_of_birth} onChange={e => setForm({...form, date_of_birth: e.target.value})} required />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Dominant Side
            </label>
            <select className="field-input" value={form.dominant_side} onChange={e => setForm({...form, dominant_side: e.target.value})} required>
              <option value="left">Left</option>
              <option value="right">Right</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Height (cm)
            </label>
            <input type="number" step="0.1" min="50" max="300" className="field-input" placeholder="185.5" value={form.height_cm} onChange={e => setForm({...form, height_cm: e.target.value})} />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase mb-1.5" style={{ color: "var(--text-muted)", letterSpacing: "0.05em" }}>
              Weight (kg)
            </label>
            <input type="number" step="0.1" min="20" max="200" className="field-input" placeholder="82.0" value={form.weight_kg} onChange={e => setForm({...form, weight_kg: e.target.value})} />
          </div>
        </div>

        <div className="pt-2">
          <button type="submit" disabled={loading} className="pill-btn--primary w-full justify-center">
            {loading ? "Creating..." : "Create Athlete"}
          </button>
        </div>
      </form>
    </div>
  );
}