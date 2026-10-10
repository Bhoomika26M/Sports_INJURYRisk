import React, { useState } from 'react';
import { Users, Plus, ShieldAlert, Heart, Calendar, Activity, ChevronRight, Check } from 'lucide-react';
import { api } from '../api/client';

export default function AthleteManagement({ athletes, onRefreshAthletes, onSelectAthlete, selectedAthleteId }) {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [injuryModalOpen, setInjuryModalOpen] = useState(false);
  const [targetAthlete, setTargetAthlete] = useState(null);

  // Form states
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newSport, setNewSport] = useState('Football');
  const [newPosition, setNewPosition] = useState('');
  const [newAge, setNewAge] = useState(22);
  const [newHeight, setNewHeight] = useState(180);
  const [newWeight, setNewWeight] = useState(75);
  const [newLoad, setNewLoad] = useState(14);
  const [newAcwr, setNewAcwr] = useState(1.15);

  // Injury form
  const [injuryName, setInjuryName] = useState('');
  const [bodyPart, setBodyPart] = useState('Right Knee (ACL)');
  const [yearDate, setYearDate] = useState('2025');
  const [severity, setSeverity] = useState('Moderate');
  const [status, setStatus] = useState('Vulnerable');

  const handleCreateAthlete = async (e) => {
    e.preventDefault();
    try {
      await api.createAthlete({
        athlete_code: newCode,
        name: newName,
        sport_type: newSport,
        position: newPosition,
        age: Number(newAge),
        height: Number(newHeight),
        weight: Number(newWeight),
        training_load: Number(newLoad),
        acwr: Number(newAcwr),
        injury_history: [],
        physical_assessment: {}
      });
      setCreateModalOpen(false);
      onRefreshAthletes();
    } catch (err) {
      alert(err.message || 'Creation failed');
    }
  };

  const handleAddInjury = async (e) => {
    e.preventDefault();
    if (!targetAthlete) return;
    try {
      await api.addInjuryRecord(targetAthlete.id, {
        injury_name: injuryName,
        body_part: bodyPart,
        year_or_date: yearDate,
        severity: severity,
        status: status
      });
      setInjuryModalOpen(false);
      onRefreshAthletes();
    } catch (err) {
      alert(err.message || 'Failed to log injury');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-cyan-400" />
            Athlete Profile & Longitudinal Health Records
          </h2>
          <p className="text-xs text-slate-400">
            Milestone 1 Athlete Profile Management: physical assessment tracking, injury history, and training loads.
          </p>
        </div>

        <button
          onClick={() => setCreateModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Athlete</span>
        </button>
      </div>

      {/* Athlete Cards Roster */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {athletes.map((ath) => {
          const isSelected = selectedAthleteId === ath.id;
          return (
            <div
              key={ath.id}
              className={`p-5 rounded-2xl border transition-all space-y-4 flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-900 border-cyan-500 shadow-xl shadow-cyan-500/10'
                  : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      {ath.name}
                      {isSelected && <span className="text-[10px] font-mono text-cyan-400 font-semibold bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800">Active</span>}
                    </h3>
                    <p className="text-xs text-slate-400">{ath.sport_type} • {ath.position || 'Athlete'}</p>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                    {ath.athlete_code}
                  </span>
                </div>

                {/* Physical metrics */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">Age / Ht</span>
                    <span className="font-bold text-white font-mono">{ath.age}y / {ath.height}cm</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">Weight</span>
                    <span className="font-bold text-white font-mono">{ath.weight} kg</span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                    <span className="text-[9px] text-slate-400 block uppercase">ACWR Ratio</span>
                    <span className={`font-bold font-mono ${ath.acwr > 1.4 ? 'text-rose-400' : 'text-cyan-400'}`}>
                      {ath.acwr}
                    </span>
                  </div>
                </div>

                {/* Injury History Badges */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-slate-400">Injury History:</span>
                    <button
                      onClick={() => {
                        setTargetAthlete(ath);
                        setInjuryModalOpen(true);
                      }}
                      className="text-[10px] text-cyan-400 hover:underline flex items-center gap-0.5"
                    >
                      <Plus className="w-3 h-3" /> Log Injury
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {(ath.injury_history || []).length > 0 ? (
                      ath.injury_history.map((h, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-950 text-slate-300 border border-slate-800"
                        >
                          {h.injury_name} ({h.severity})
                        </span>
                      ))
                    ) : (
                      <span className="text-[10px] text-slate-500 italic">No prior surgeries recorded</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">Weekly Load: {ath.training_load} hrs</span>
                <button
                  onClick={() => onSelectAthlete(ath.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    isSelected
                      ? 'bg-cyan-500 text-slate-950 font-bold'
                      : 'bg-slate-800 hover:bg-slate-750 text-slate-300'
                  }`}
                >
                  {isSelected ? 'Selected' : 'Select Athlete'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Register Athlete Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" /> Register New Athlete Profile
              </h3>
              <button onClick={() => setCreateModalOpen(false)} className="text-slate-400 hover:text-white text-xs font-mono">✕</button>
            </div>

            <form onSubmit={handleCreateAthlete} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Athlete ID</label>
                  <input
                    type="text"
                    placeholder="e.g. ATH-106"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Full Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Jordan Miller"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Sport Type</label>
                  <select
                    value={newSport}
                    onChange={(e) => setNewSport(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                  >
                    <option value="Football">Football</option>
                    <option value="Basketball">Basketball</option>
                    <option value="Track & Field">Track & Field</option>
                    <option value="Tennis">Tennis</option>
                    <option value="Rugby">Rugby</option>
                    <option value="Volleyball">Volleyball</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Position / Discipline</label>
                  <input
                    type="text"
                    placeholder="e.g. Winger"
                    value={newPosition}
                    onChange={(e) => setNewPosition(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Age</label>
                  <input
                    type="number"
                    value={newAge}
                    onChange={(e) => setNewAge(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Height (cm)</label>
                  <input
                    type="number"
                    value={newHeight}
                    onChange={(e) => setNewHeight(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Weight (kg)</label>
                  <input
                    type="number"
                    value={newWeight}
                    onChange={(e) => setNewWeight(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Training Load (hrs/wk)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newLoad}
                    onChange={(e) => setNewLoad(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">ACWR Ratio</label>
                  <input
                    type="number"
                    step="0.05"
                    value={newAcwr}
                    onChange={(e) => setNewAcwr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white"
                >
                  Save Athlete Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Injury Modal */}
      {injuryModalOpen && targetAthlete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" /> Log Injury Record for {targetAthlete.name}
              </h3>
              <button onClick={() => setInjuryModalOpen(false)} className="text-slate-400 hover:text-white text-xs font-mono">✕</button>
            </div>

            <form onSubmit={handleAddInjury} className="space-y-3">
              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Injury Diagnosis Name</label>
                <input
                  type="text"
                  placeholder="e.g. Lateral Meniscus Tear / Hamstring Strain"
                  value={injuryName}
                  onChange={(e) => setInjuryName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Anatomical Body Part</label>
                  <input
                    type="text"
                    value={bodyPart}
                    onChange={(e) => setBodyPart(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Year / Season</label>
                  <input
                    type="text"
                    value={yearDate}
                    onChange={(e) => setYearDate(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Severity</label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                  >
                    <option value="Mild">Mild (Grade I)</option>
                    <option value="Moderate">Moderate (Grade II)</option>
                    <option value="Severe">Severe (Grade III)</option>
                    <option value="Surgical">Surgical Intervention</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Current Clinical Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                  >
                    <option value="Fully Recovered">Fully Recovered</option>
                    <option value="Ongoing Rehab">Ongoing Rehab</option>
                    <option value="Vulnerable">Vulnerable / Asymmetric Deficit</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setInjuryModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white"
                >
                  Save Injury Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
