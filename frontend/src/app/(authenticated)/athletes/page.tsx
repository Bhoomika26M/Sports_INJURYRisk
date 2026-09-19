"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type Athlete = {
  id: string;
  full_name?: string | null;
  sport_type: string;
  position: string | null;
  date_of_birth: string;
  height_cm: number | null;
  weight_kg: number | null;
  dominant_side: string | null;
};

export default function AthletesPage() {
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { user } = useAuth();

  useEffect(() => {
    const fetchAthletes = async () => {
      try {
        const data = await apiClient.fetchWithAuth("/athletes");
        setAthletes(data.items || []);
      } catch (err: any) {
        setError(err.message || "Failed to load athletes");
      } finally {
        setLoading(false);
      }
    };

    fetchAthletes();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="neu-card p-6 rounded-2xl flex items-center gap-3 text-slate-700">
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-medium">Loading athlete roster...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="neu-card rounded-2xl p-6 border-red-200 text-red-600 flex items-center gap-3">
        <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-medium">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
            Athletes Roster
          </h1>
          <p className="text-xs sm:text-sm font-medium text-slate-600 mt-1">
            Registered roster members, baseline movement kinematics, and training load tracking.
          </p>
        </div>
        {user?.role !== "athlete" && (
          <Link
            href="/athletes/new"
            className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-black text-xs sm:text-sm px-5 py-3 rounded-xl shadow-lg shadow-blue-600/30 transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add Athlete</span>
          </Link>
        )}
      </div>

      {athletes.length === 0 ? (
        <div 
          className="bg-white rounded-2xl p-12 text-center text-slate-600 font-bold border-2 border-slate-300"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          No athletes found in the system.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {athletes.map((athlete) => (
            <Link
              key={athlete.id}
              href={`/athletes/${athlete.id}`}
              className="bg-white rounded-2xl p-6 border-2 border-slate-300 hover:border-blue-500 transition-all group flex flex-col justify-between cursor-pointer"
              style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <h3 className="text-base font-black text-slate-900 group-hover:text-blue-600 transition-colors">
                      {athlete.full_name || `Athlete #${athlete.id.slice(0, 8)}`}
                    </h3>
                    <div className="text-xs font-black text-blue-700 uppercase tracking-wider capitalize mt-0.5">
                      {athlete.sport_type} {athlete.position ? `· ${athlete.position}` : ""}
                    </div>
                  </div>
                  <span className="text-[11px] font-black text-emerald-800 bg-emerald-100 border border-emerald-300 px-2.5 py-0.5 rounded-full">
                    Active
                  </span>
                </div>

                <div className="space-y-2 pt-3 border-t-2 border-slate-100 text-xs">
                  <div className="flex justify-between">
                    <span className="font-bold text-slate-600">Date of Birth</span>
                    <span className="font-black text-slate-900">{athlete.date_of_birth}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-bold text-slate-600">Height / Weight</span>
                    <span className="font-black text-slate-900">
                      {athlete.height_cm ? `${athlete.height_cm} cm` : "N/A"} / {athlete.weight_kg ? `${athlete.weight_kg} kg` : "N/A"}
                    </span>
                  </div>
                  {athlete.dominant_side && (
                    <div className="flex justify-between">
                      <span className="font-bold text-slate-600">Dominant Side</span>
                      <span className="font-black text-slate-900 capitalize">{athlete.dominant_side}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-5 pt-3 border-t-2 border-slate-100 flex items-center justify-between text-xs font-black text-blue-600 group-hover:translate-x-1 transition-transform">
                <span>View Full Profile & History</span>
                <span>→</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
