"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function AthleteProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [athlete, setAthlete] = useState<any>(null);
  const [injuries, setInjuries] = useState<any[]>([]);
  const [trainingLoads, setTrainingLoads] = useState<any[]>([]);
  const [videos, setVideos] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { user } = useAuth();

  // Form states
  const [showInjuryForm, setShowInjuryForm] = useState(false);
  const [injuryForm, setInjuryForm] = useState({ injury_type: "", body_part: "", injury_date: "", severity: "" });
  
  const [showLoadForm, setShowLoadForm] = useState(false);
  const [loadForm, setLoadForm] = useState({ entry_date: "", duration_minutes: "", rpe: "", session_type: "" });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [athleteData, injuriesData, loadsData, videosData] = await Promise.all([
        apiClient.fetchWithAuth(`/athletes/${resolvedParams.id}`),
        apiClient.fetchWithAuth(`/athletes/${resolvedParams.id}/injuries`),
        apiClient.fetchWithAuth(`/athletes/${resolvedParams.id}/training-load`),
        apiClient.fetchWithAuth(`/videos?athlete_id=${resolvedParams.id}`)
      ]);
      setAthlete(athleteData);
      setInjuries(injuriesData.items || []);
      setTrainingLoads(loadsData.items || []);
      setVideos(videosData.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to load athlete data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [resolvedParams.id]);

  const handleAddInjury = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { ...injuryForm };
      if (!payload.severity) delete payload.severity;
      
      await apiClient.fetchWithAuth(`/athletes/${resolvedParams.id}/injuries`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setShowInjuryForm(false);
      setInjuryForm({ injury_type: "", body_part: "", injury_date: "", severity: "" });
      fetchData();
    } catch (err: any) {
      alert(err.message || "Failed to add injury");
    }
  };

  const handleAddLoad = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { entry_date: loadForm.entry_date };
      if (loadForm.duration_minutes) payload.duration_minutes = parseInt(loadForm.duration_minutes);
      if (loadForm.rpe) payload.rpe = parseInt(loadForm.rpe);
      if (loadForm.session_type) payload.session_type = loadForm.session_type;

      await apiClient.fetchWithAuth(`/athletes/${resolvedParams.id}/training-load`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setShowLoadForm(false);
      setLoadForm({ entry_date: "", duration_minutes: "", rpe: "", session_type: "" });
      fetchData();
    } catch (err: any) {
      alert(err.message || "Failed to add training load");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="neu-card p-6 rounded-2xl flex items-center gap-3 text-slate-700">
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-medium">Loading athlete profile...</span>
        </div>
      </div>
    );
  }

  if (error || !athlete) {
    return (
      <div className="neu-card rounded-2xl p-6 border-red-200 text-red-600 flex items-center gap-3">
        <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-medium">{error || "Athlete profile not found"}</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Profile Header Card */}
      <div 
        className="bg-white rounded-2xl p-6 sm:p-8 border-2 border-slate-300 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Link href="/athletes" className="text-xs font-black text-blue-600 hover:underline">
              ← Roster
            </Link>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs font-black uppercase tracking-wider text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              {athlete.sport_type}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
            {athlete.full_name || `Athlete #${athlete.id.slice(0, 8)}`}
          </h1>
          <p className="text-xs sm:text-sm font-semibold text-slate-600 mt-1 capitalize">
            {athlete.position ? `Position: ${athlete.position}` : "Athlete Profile"} • {athlete.date_of_birth}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/videos/upload"
            className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-black text-xs sm:text-sm px-5 py-3 rounded-xl shadow-lg shadow-blue-600/30 transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            <span>Upload Movement Video</span>
          </Link>
        </div>
      </div>

      {/* Biometrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6">
        <div 
          className="bg-white rounded-2xl p-5 text-center border-2 border-slate-300"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="text-xs font-black uppercase tracking-wider text-slate-600 mb-1">Height</div>
          <div className="text-2xl font-black text-slate-900">{athlete.height_cm ? `${athlete.height_cm} cm` : "N/A"}</div>
        </div>
        <div 
          className="bg-white rounded-2xl p-5 text-center border-2 border-slate-300"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="text-xs font-black uppercase tracking-wider text-slate-600 mb-1">Weight</div>
          <div className="text-2xl font-black text-slate-900">{athlete.weight_kg ? `${athlete.weight_kg} kg` : "N/A"}</div>
        </div>
        <div 
          className="bg-white rounded-2xl p-5 text-center border-2 border-slate-300"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="text-xs font-black uppercase tracking-wider text-slate-600 mb-1">Dominant Side</div>
          <div className="text-2xl font-black text-slate-900 capitalize">{athlete.dominant_side || "N/A"}</div>
        </div>
        <div 
          className="bg-white rounded-2xl p-5 text-center border-2 border-slate-300"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="text-xs font-black uppercase tracking-wider text-slate-600 mb-1">Status</div>
          <div className="text-2xl font-black text-emerald-600">Active</div>
        </div>
      </div>

      {/* Grid: Injuries & Training Load */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Injury History */}
        <div 
          className="bg-white rounded-2xl p-6 sm:p-7 border-2 border-slate-300 space-y-4 flex flex-col justify-between"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-red-50 border-2 border-red-200 flex items-center justify-center text-red-600">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="text-base font-black text-slate-900">Injury History</h3>
              </div>
              <button 
                onClick={() => setShowInjuryForm(!showInjuryForm)} 
                className="text-xs font-black text-blue-700 bg-blue-50 hover:bg-blue-100 border-2 border-blue-200 px-3 py-1.5 rounded-xl transition-all cursor-pointer"
              >
                {showInjuryForm ? "Cancel" : "+ Add Record"}
              </button>
            </div>

            {showInjuryForm && (
              <form onSubmit={handleAddInjury} className="mb-4 bg-slate-50 border-2 border-slate-300 p-4 rounded-xl space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <input 
                    required 
                    type="text" 
                    placeholder="Injury Type (e.g. ACL Sprain)" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={injuryForm.injury_type} 
                    onChange={e => setInjuryForm({...injuryForm, injury_type: e.target.value})} 
                  />
                  <input 
                    required 
                    type="text" 
                    placeholder="Body Part (e.g. Knee)" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={injuryForm.body_part} 
                    onChange={e => setInjuryForm({...injuryForm, body_part: e.target.value})} 
                  />
                  <input 
                    required 
                    type="date" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={injuryForm.injury_date} 
                    onChange={e => setInjuryForm({...injuryForm, injury_date: e.target.value})} 
                  />
                  <select 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={injuryForm.severity} 
                    onChange={e => setInjuryForm({...injuryForm, severity: e.target.value})}
                  >
                    <option value="">Severity (Optional)</option>
                    <option value="minor">Minor</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe</option>
                  </select>
                </div>
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-black px-4 py-2.5 rounded-xl shadow-md shadow-blue-600/30 cursor-pointer">
                  Save Injury Record
                </button>
              </form>
            )}

            {injuries.length === 0 ? (
              <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-6 text-center text-xs font-bold text-slate-500">
                No recorded prior injuries.
              </div>
            ) : (
              <div className="space-y-2.5">
                {injuries.map(inj => (
                  <div key={inj.id} className="p-3.5 rounded-xl bg-slate-50 border-2 border-slate-200 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-black text-slate-900">{inj.injury_type} • {inj.body_part}</div>
                      <div className="text-[11px] font-semibold text-slate-500 mt-0.5">{inj.injury_date}</div>
                    </div>
                    {inj.severity && (
                      <span className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full ${
                        inj.severity === 'severe' ? 'bg-red-100 text-red-800 border border-red-300' :
                        inj.severity === 'moderate' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                        'bg-blue-100 text-blue-800 border border-blue-300'
                      }`}>
                        {inj.severity}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Training Load */}
        <div 
          className="bg-white rounded-2xl p-6 sm:p-7 border-2 border-slate-300 space-y-4 flex flex-col justify-between"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-blue-50 border-2 border-blue-200 flex items-center justify-center text-blue-600">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h3 className="text-base font-black text-slate-900">Training Load (ACWR)</h3>
              </div>
              <button 
                onClick={() => setShowLoadForm(!showLoadForm)} 
                className="text-xs font-black text-blue-700 bg-blue-50 hover:bg-blue-100 border-2 border-blue-200 px-3 py-1.5 rounded-xl transition-all cursor-pointer"
              >
                {showLoadForm ? "Cancel" : "+ Add Session"}
              </button>
            </div>

            {showLoadForm && (
              <form onSubmit={handleAddLoad} className="mb-4 bg-slate-50 border-2 border-slate-300 p-4 rounded-xl space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <input 
                    required 
                    type="date" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={loadForm.entry_date} 
                    onChange={e => setLoadForm({...loadForm, entry_date: e.target.value})} 
                  />
                  <input 
                    type="text" 
                    placeholder="Session Type (e.g. Practice)" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={loadForm.session_type} 
                    onChange={e => setLoadForm({...loadForm, session_type: e.target.value})} 
                  />
                  <input 
                    type="number" 
                    placeholder="Duration (mins)" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={loadForm.duration_minutes} 
                    onChange={e => setLoadForm({...loadForm, duration_minutes: e.target.value})} 
                  />
                  <input 
                    type="number" 
                    min="1" 
                    max="10" 
                    placeholder="RPE (1-10)" 
                    className="p-2.5 bg-white text-xs font-semibold text-slate-900 rounded-lg border-2 border-slate-300 focus:border-blue-600 outline-none" 
                    value={loadForm.rpe} 
                    onChange={e => setLoadForm({...loadForm, rpe: e.target.value})} 
                  />
                </div>
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-black px-4 py-2.5 rounded-xl shadow-md shadow-blue-600/30 cursor-pointer">
                  Save Training Session
                </button>
              </form>
            )}

            {trainingLoads.length === 0 ? (
              <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-6 text-center text-xs font-bold text-slate-500">
                No recorded training sessions.
              </div>
            ) : (
              <div className="space-y-2.5">
                {trainingLoads.map(load => (
                  <div key={load.id} className="p-3.5 rounded-xl bg-slate-50 border-2 border-slate-200 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-black text-slate-900 capitalize">{load.session_type || 'Training Session'}</div>
                      <div className="text-[11px] font-semibold text-slate-500 mt-0.5">{load.entry_date}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-black text-slate-900">{load.duration_minutes ? `${load.duration_minutes}m` : ''}</div>
                      {load.rpe && <div className="text-[10px] text-blue-700 font-bold">RPE {load.rpe}/10</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Movement Videos Section */}
      <div 
        className="bg-white rounded-2xl p-6 sm:p-8 border-2 border-slate-300 space-y-4"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-purple-50 border-2 border-purple-200 flex items-center justify-center text-purple-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-base font-black text-slate-900">Analyzed Movement Videos</h3>
          </div>
          <Link 
            href="/videos/upload" 
            className="text-xs font-black text-blue-700 bg-blue-50 hover:bg-blue-100 border-2 border-blue-200 px-3.5 py-1.5 rounded-xl transition-all cursor-pointer"
          >
            + Upload New
          </Link>
        </div>

        {videos.length === 0 ? (
          <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-8 text-center text-xs font-bold text-slate-500">
            No video recordings analyzed yet for this athlete.
          </div>
        ) : (
          <div className="space-y-3">
            {videos.map(vid => (
              <div 
                key={vid.id} 
                className="p-4 rounded-xl bg-slate-50 border-2 border-slate-200 hover:border-blue-500 hover:bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all"
              >
                <div>
                  <Link 
                    href={vid.processing_status === 'completed' ? `/videos/${vid.id}/results` : `/videos/${vid.id}`}
                    className="text-sm font-black text-blue-700 hover:underline"
                  >
                    {vid.original_filename || "Video Recording"}
                  </Link>
                  <div className="text-xs font-semibold text-slate-500 mt-0.5 capitalize">
                    {vid.movement_type} • {new Date(vid.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[11px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full ${
                    vid.processing_status === 'completed' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                    vid.processing_status === 'failed' ? 'bg-red-100 text-red-800 border border-red-300' :
                    'bg-amber-100 text-amber-800 border border-amber-300'
                  }`}>
                    {vid.processing_status.replace('_', ' ')}
                  </span>
                  <Link
                    href={vid.processing_status === 'completed' ? `/videos/${vid.id}/results` : `/videos/${vid.id}`}
                    className="text-xs font-black text-blue-600 hover:text-blue-800"
                  >
                    View →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
