"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";

export default function AddAthletePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    sport_type: "",
    position: "",
    date_of_birth: "",
    height_cm: "",
    weight_kg: "",
    dominant_side: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const payload: any = {
        sport_type: formData.sport_type,
        date_of_birth: formData.date_of_birth,
      };

      if (formData.position) payload.position = formData.position;
      if (formData.height_cm) payload.height_cm = parseFloat(formData.height_cm);
      if (formData.weight_kg) payload.weight_kg = parseFloat(formData.weight_kg);
      if (formData.dominant_side) payload.dominant_side = formData.dominant_side;

      await apiClient.fetchWithAuth("/athletes", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push("/athletes");
    } catch (err: any) {
      setError(err.message || "Failed to create athlete");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-2">
        <Link href="/athletes" className="text-xs font-semibold text-blue-600 hover:underline">
          ← Back to Athletes
        </Link>
      </div>

      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
          Register New Athlete
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Add an athlete to your roster to track kinematics baselines and movement risk assessments.
        </p>
      </div>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-4 rounded-xl flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      <form 
        onSubmit={handleSubmit} 
        className="bg-white rounded-2xl p-6 sm:p-8 border-2 border-slate-300 space-y-5"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        <div>
          <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
            Sport Discipline *
          </label>
          <input
            type="text"
            name="sport_type"
            required
            value={formData.sport_type}
            onChange={handleChange}
            className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
            placeholder="e.g. Basketball, Soccer, Sprinting"
          />
        </div>

        <div>
          <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
            Position / Role
          </label>
          <input
            type="text"
            name="position"
            value={formData.position}
            onChange={handleChange}
            className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
            placeholder="e.g. Point Guard, Midfielder, Sprinter"
          />
        </div>

        <div>
          <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
            Date of Birth *
          </label>
          <input
            type="date"
            name="date_of_birth"
            required
            value={formData.date_of_birth}
            onChange={handleChange}
            className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
              Height (cm)
            </label>
            <input
              type="number"
              step="0.1"
              name="height_cm"
              value={formData.height_cm}
              onChange={handleChange}
              placeholder="e.g. 185"
              className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
              Weight (kg)
            </label>
            <input
              type="number"
              step="0.1"
              name="weight_kg"
              value={formData.weight_kg}
              onChange={handleChange}
              placeholder="e.g. 80"
              className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm placeholder-slate-400 focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black text-slate-700 uppercase tracking-wider mb-2">
            Dominant Side
          </label>
          <select
            name="dominant_side"
            value={formData.dominant_side}
            onChange={handleChange}
            className="w-full px-4 py-3 rounded-xl bg-slate-50 border-2 border-slate-300 text-slate-900 font-bold text-sm focus:bg-white focus:border-blue-600 focus:outline-none transition-all"
          >
            <option value="">Select Dominant Side...</option>
            <option value="right">Right</option>
            <option value="left">Left</option>
            <option value="bilateral">Bilateral / Both</option>
          </select>
        </div>

        <div className="pt-4 flex items-center justify-end gap-3">
          <Link
            href="/athletes"
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs sm:text-sm px-5 py-3 rounded-xl border-2 border-slate-300 transition-all cursor-pointer shadow-xs"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-black text-xs sm:text-sm px-6 py-3 rounded-xl shadow-lg shadow-blue-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            {loading ? "Registering..." : "Register Athlete"}
          </button>
        </div>
      </form>
    </div>
  );
}
