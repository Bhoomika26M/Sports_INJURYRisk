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
      <div className="p-12 text-center text-xs text-slate-500 bg-white rounded-2xl border border-slate-200 shadow-xs">
        <Activity className="w-8 h-8 mx-auto animate-spin text-teal-700 mb-2" />
        Loading dataset benchmarks...
      </div>
    );
  }

  const datasets = data?.datasets || [];
  const norms = data?.normative_benchmarks || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Database className="w-5 h-5 text-teal-700" />
            Sports Biomechanics Reference Datasets &amp; Normative Baselines
          </h2>
          <p className="text-xs text-slate-500">
            Published scientific literature benchmarks used to calibrate kinematic angle thresholds and epidemiological injury corridors.
          </p>
        </div>
        <span className="px-3 py-1 rounded-xl bg-teal-50 text-teal-800 border border-teal-200 text-xs font-bold font-mono">
          5 Reference Benchmarks
        </span>
      </div>

      {/* Honesty & Transparency Notice */}
      <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-start gap-3 text-xs text-slate-600">
        <Shield className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-800">Scientific Reference Disclosure: </span>
          The datasets below represent peer-reviewed academic benchmarks (Human3.6M, SportsPose, MPII, COCO, FIFA Surveillance) utilized strictly as normative distribution references for risk thresholds. Kinematix analyzes video using real-time computer vision without claiming custom local fine-tuning on these proprietary corpora.
        </div>
      </div>

      {/* 5 Dataset Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {datasets.map((d) => (
          <div
            key={d.id}
            className="bg-white p-5 rounded-2xl border border-slate-200 hover:border-slate-300 shadow-xs transition-colors space-y-3 flex flex-col justify-between"
          >
            <div className="space-y-2.5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">{d.name}</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                  {d.keypoints > 0 ? `${d.keypoints} Keypoints` : 'Epidemiology'}
                </span>
              </div>

              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 block">
                {d.category}
              </span>

              <p className="text-xs text-slate-600 leading-relaxed">{d.purpose}</p>

              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 block uppercase">Sample Drills:</span>
                <p className="text-[11px] text-slate-700">{(d.sample_activities || []).join(', ')}</p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500 space-y-1">
              <span className="text-slate-800 font-semibold block">Normative Benchmark:</span>
              <p className="text-[10px] text-slate-600">{d.normative_valgus_mean}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Normative Reference Thresholds Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-teal-700" />
          Clinical Normative Risk Corridor Benchmarks
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(norms).map(([key, val]) => (
            <div key={key} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <h4 className="text-xs font-bold text-slate-800 capitalize">
                {key.replace(/_/g, ' ')}
              </h4>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Optimal Zone:</span>
                  <span className="text-emerald-800 font-mono font-bold">{val.healthy_range || val.sweet_spot}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Risk Threshold:</span>
                  <span className="text-rose-700 font-mono font-bold">{val.high_risk || val.danger_zone}</span>
                </div>
              </div>
              <p className="text-[10px] text-slate-500 pt-1 border-t border-slate-200">{val.clinical_significance}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
