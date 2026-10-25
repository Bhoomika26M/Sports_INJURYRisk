import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Lightbulb, ShieldCheck } from 'lucide-react';

export const RecommendationPanel = ({ videoId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        setLoading(true);
        const res = await api.get(`/recommendations/${videoId}`);
        setData(res.data);
      } catch (err) {
        setError("Failed to load recommendations.");
      } finally {
        setLoading(false);
      }
    };
    if (videoId) {
      fetchRecommendations();
    }
  }, [videoId]);

  if (loading) return <div className="p-6 text-center text-xs text-slate-400">Loading corrective plan...</div>;
  if (error) return <div className="p-4 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200">{error}</div>;
  if (!data) return null;

  const { recommendations, disclaimer } = data;

  const getActionBadge = (actionType) => {
    switch (actionType) {
      case 'consult_professional':
        return <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Clinical Consult</span>;
      case 'technique_review':
        return <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Technique Review</span>;
      case 'educational':
        return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Conditioning</span>;
      default:
        return <span className="bg-slate-50 text-slate-700 border border-slate-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">General Practice</span>;
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Lightbulb size={18} className="text-amber-500" />
          <span>Biomechanical Recommendations</span>
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">Evidence-based corrective exercises and movement drills.</p>
      </div>

      {disclaimer && (
        <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 flex items-start gap-2">
          <ShieldCheck size={15} className="text-amber-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{disclaimer}</p>
        </div>
      )}

      {recommendations.length === 0 ? (
        <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs">
          No specific kinematic corrective alerts generated. Movement pattern is within acceptable tolerances.
        </div>
      ) : (
        <div className="space-y-3">
          {recommendations.map((rec, index) => (
            <div key={index} className="p-4 border border-slate-200 rounded-xl bg-white shadow-xs hover:border-slate-300 transition">
              <div className="flex justify-between items-start gap-2 mb-2">
                <h4 className="font-bold text-xs text-slate-900">{rec.title}</h4>
                {getActionBadge(rec.action_type)}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">{rec.description}</p>
              
              <div className="bg-slate-50 rounded-lg p-2.5 text-[11px] text-slate-500 space-y-1 border border-slate-100">
                <p><strong className="text-slate-700">Trigger Finding:</strong> {rec.triggering_finding}</p>
                <p><strong className="text-slate-700">Clinical Rationale:</strong> {rec.rationale}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
