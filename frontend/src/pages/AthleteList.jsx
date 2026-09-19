import React, { useState } from 'react';
import { Search, UserPlus, AlertCircle, CheckCircle, ShieldAlert } from 'lucide-react';

export default function AthleteList() {
  const [searchTerm, setSearchTerm] = useState('');

  const athletes = [
    {
      id: 'ath-1',
      name: 'Marcus Sterling',
      sport: 'Basketball',
      team: 'Varsity Men',
      dominantLeg: 'Right',
      riskTier: 'HIGH',
      riskScore: 84,
      injuries: ['ACL Reconstruction (2024)', 'Ankle Sprain (2025)'],
      lastScreened: '2026-09-15',
    },
    {
      id: 'ath-2',
      name: 'Elena Rostova',
      sport: 'Soccer',
      team: 'Premier Women',
      dominantLeg: 'Right',
      riskTier: 'MODERATE',
      riskScore: 56,
      injuries: ['Hamstring Strain (Grade 1)'],
      lastScreened: '2026-09-12',
    },
    {
      id: 'ath-3',
      name: 'Devon Vance',
      sport: 'Track & Field',
      team: 'Sprints',
      dominantLeg: 'Left',
      riskTier: 'LOW',
      riskScore: 18,
      injuries: ['None recorded'],
      lastScreened: '2026-09-10',
    },
    {
      id: 'ath-4',
      name: 'Sophia Chen',
      sport: 'Volleyball',
      team: 'Varsity Women',
      dominantLeg: 'Right',
      riskTier: 'LOW',
      riskScore: 24,
      injuries: ['Patellar Tendinopathy (Resolved)'],
      lastScreened: '2026-09-08',
    },
  ];

  const filtered = athletes.filter((a) =>
    a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.sport.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.team.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Athlete Profiles & Rosters</h1>
          <p className="text-slate-400 text-sm mt-1">
            Anthropometrics, prior injury records, and longitudinal movement screening profiles.
          </p>
        </div>
        <button className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold border border-slate-700 transition-colors">
          <UserPlus className="w-4 h-4 mr-1.5 text-emerald-400" />
          Add Athlete
        </button>
      </div>

      {/* Search Input */}
      <div className="glass-card rounded-2xl p-4">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by athlete name, sport, or squad..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-900/60 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </div>
      </div>

      {/* Athlete Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((athlete) => {
          const isHigh = athlete.riskTier === 'HIGH';
          const isMod = athlete.riskTier === 'MODERATE';
          const badgeColor = isHigh
            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            : isMod
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';

          return (
            <div key={athlete.id} className="glass-card p-5 rounded-2xl space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-white text-base">{athlete.name}</h3>
                  <p className="text-xs text-slate-400">
                    {athlete.sport} • {athlete.team}
                  </p>
                </div>
                <span className={`px-2.5 py-1 text-xs font-bold rounded-full border ${badgeColor}`}>
                  {athlete.riskTier} ({athlete.riskScore})
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Dominant Limb:</span>
                  <span className="font-medium text-slate-200">{athlete.dominantLeg}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Last Assessment:</span>
                  <span className="font-medium text-slate-200">{athlete.lastScreened}</span>
                </div>
              </div>

              <div>
                <span className="text-xs text-slate-500 block mb-1 font-semibold uppercase tracking-wider">
                  Injury History:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {athlete.injuries.map((inj, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-xs border border-slate-700"
                    >
                      {inj}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
