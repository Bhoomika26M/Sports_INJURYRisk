import React, { useState, useEffect } from 'react';
import { Database, CheckCircle2, Shield, Activity, BookOpen, Layers } from 'lucide-react';
import { api } from '../api/client';

export default function DatasetsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDatasets() {
      try {
        const res = await api.getDatasets();
        setData(res);
      } catch (err) {
        console.error('Failed to load datasets:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchDatasets();
  }, []);

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-slate-400">
        <Activity className="w-8 h-8 mx-auto animate-spin text-cyan-400 mb-2" />
        Loading dataset benchmarks...
      </div>
    );
  }

  const datasets = data?.datasets || [];
  const norms = data?.normative_benchmarks || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Sports Biomechanics Datasets & Clinical Normative Baselines
          </h2>
          <p className="text-xs text-slate-400">
            Milestone 1 reference collection used to calibrate computer vision pose tracking and epidemiological injury boundaries.
          </p>
        </div>
        <span className="px-3 py-1 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-bold font-mono">
          5 Reference Datasets Integrated
        </span>
      </div>

      {/* 5 Dataset Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {datasets.map((d) => (
          <div
            key={d.id}
            className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all space-y-3 flex flex-col justify-between"
          >
            <div className="space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-bold text-white">{d.name}</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-cyan-400 border border-slate-800 shrink-0">
                  {d.keypoints > 0 ? `${d.keypoints} Keypoints` : 'Epidemiology'}
                </span>
              </div>

              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400 block">
                {d.category}
              </span>

              <p className="text-xs text-slate-300 leading-relaxed">{d.purpose}</p>

              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Sample Drills:</span>
                <p className="text-[11px] text-slate-300">{(d.sample_activities || []).join(', ')}</p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
              <span className="text-cyan-400 font-semibold block">Normative Benchmark:</span>
              <p className="text-[10px] text-slate-300">{d.normative_valgus_mean}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Normative Reference Thresholds Table */}
      <div className="bg-slate-900/70 p-5 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-cyan-400" />
          Clinical Normative Risk Corridor Benchmarks
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(norms).map(([key, val]) => (
            <div key={key} className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
              <h4 className="text-xs font-bold text-slate-200 capitalize">
                {key.replace(/_/g, ' ')}
              </h4>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Optimal Zone:</span>
                  <span className="text-emerald-400 font-mono font-bold">{val.healthy_range || val.sweet_spot}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Risk Threshold:</span>
                  <span className="text-rose-400 font-mono font-bold">{val.high_risk || val.danger_zone}</span>
                </div>
              </div>
              <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-800/80">{val.clinical_significance}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
