"use client";

import { useEffect, useState } from "react";
import { getAthleteProfile, createAthleteProfile, updateAthleteProfile } from "@/lib/api";

interface ProfileData {
  user_id: number;
  sport_type: string;
  position: string;
  age: number;
  height: number;
  weight: number;
  injury_history: string;
  training_load: string;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    sport_type: "",
    position: "",
    age: "",
    height: "",
    weight: "",
    injury_history: "",
    training_load: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadProfile = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const data = await getAthleteProfile(token);
      if (data) {
        setProfile(data);
        setFormData({
          sport_type: data.sport_type || "",
          position: data.position || "",
          age: data.age?.toString() || "",
          height: data.height?.toString() || "",
          weight: data.weight?.toString() || "",
          injury_history: data.injury_history || "",
          training_load: data.training_load || "",
        });
      } else {
        setIsEditing(true); // Auto-edit if no profile exists
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(() => {
      loadProfile();
    }, 0);
  }, []);



  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("No token found");

      const payload = {
        ...formData,
        age: parseInt(formData.age, 10),
        height: parseFloat(formData.height),
        weight: parseFloat(formData.weight),
      };

      if (profile) {
        const updated = await updateAthleteProfile(token, payload);
        setProfile(updated);
        setSuccess("Profile updated successfully!");
      } else {
        const created = await createAthleteProfile(token, payload);
        setProfile(created);
        setSuccess("Profile created successfully!");
      }
      setIsEditing(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading profile...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Athlete Profile Management</h2>
          <p className="text-slate-400 text-sm mt-1">Manage your physical assessment records and training profiles.</p>
        </div>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium text-sm shadow-lg shadow-indigo-500/20"
          >
            Edit Profile
          </button>
        )}
      </div>

      {error && <div className="p-4 rounded-xl bg-rose-500/20 border border-rose-500/50 text-rose-400 text-sm font-medium">{error}</div>}
      {success && <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-sm font-medium">{success}</div>}

      <div className="glass-panel p-8 rounded-2xl">
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <h3 className="text-lg font-bold text-white mb-4 border-b border-slate-800 pb-2">Athlete Information</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Sport Type</label>
                <input
                  required type="text" name="sport_type" value={formData.sport_type} onChange={handleChange} placeholder="e.g. Basketball, Soccer"
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Position</label>
                <input
                  required type="text" name="position" value={formData.position} onChange={handleChange} placeholder="e.g. Point Guard, Striker"
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all"
                />
              </div>
            </div>

            <h3 className="text-lg font-bold text-white mt-8 mb-4 border-b border-slate-800 pb-2 pt-4">Physical Assessment Records</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Age</label>
                <input
                  required type="number" name="age" value={formData.age} onChange={handleChange} placeholder="Years"
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Height (cm)</label>
                <input
                  required type="number" step="0.1" name="height" value={formData.height} onChange={handleChange} placeholder="e.g. 185"
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Weight (kg)</label>
                <input
                  required type="number" step="0.1" name="weight" value={formData.weight} onChange={handleChange} placeholder="e.g. 80.5"
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all"
                />
              </div>
            </div>

            <h3 className="text-lg font-bold text-white mt-8 mb-4 border-b border-slate-800 pb-2 pt-4">Training & History</h3>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300">Injury History Management</label>
              <textarea
                name="injury_history" value={formData.injury_history} onChange={handleChange} rows={3} placeholder="Describe any past injuries, surgeries, or chronic conditions..."
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all resize-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300">Training Profile & Load Management</label>
              <textarea
                name="training_load" value={formData.training_load} onChange={handleChange} rows={3} placeholder="Describe current training load, frequency, intensity..."
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 placeholder:text-slate-600 outline-none transition-all resize-none"
              />
            </div>

            <div className="flex gap-4 pt-6 mt-6 border-t border-slate-800">
              <button
                type="submit" disabled={saving}
                className="px-6 py-3 bg-white text-slate-900 hover:bg-slate-200 transition-colors font-bold rounded-xl shadow-lg shadow-white/10 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Profile"}
              </button>
              {profile && (
                <button
                  type="button" onClick={() => setIsEditing(false)}
                  className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors font-medium rounded-xl border border-slate-700"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        ) : (
          <div className="space-y-8">
            {!profile ? (
              <div className="text-slate-400">No profile found. Please create one.</div>
            ) : (
              <>
                <div>
                  <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-4">Athlete Information</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                      <div className="text-sm text-slate-500">Athlete ID</div>
                      <div className="text-lg font-medium text-white">#{profile.user_id}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500">Sport Type</div>
                      <div className="text-lg font-medium text-white">{profile.sport_type}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500">Position</div>
                      <div className="text-lg font-medium text-white">{profile.position}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500">Age</div>
                      <div className="text-lg font-medium text-white">{profile.age} yrs</div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-4">Physical Assessment Records</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                      <div className="text-sm text-slate-500">Height</div>
                      <div className="text-lg font-medium text-white">{profile.height} cm</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-500">Weight</div>
                      <div className="text-lg font-medium text-white">{profile.weight} kg</div>
                    </div>
                    <div className="col-span-2">
                      <div className="text-sm text-slate-500">Performance Tracking</div>
                      <div className="text-emerald-400 font-medium flex items-center gap-2 mt-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        Active monitoring enabled
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider mb-4">Training & History</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-800">
                      <div className="text-sm text-slate-500 mb-2">Injury History Management</div>
                      <div className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                        {profile.injury_history || "No injury history recorded."}
                      </div>
                    </div>
                    <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-800">
                      <div className="text-sm text-slate-500 mb-2">Training Profile Management</div>
                      <div className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                        {profile.training_load || "No training load data recorded."}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
