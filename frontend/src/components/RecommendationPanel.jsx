import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  Lightbulb, 
  ShieldCheck, 
  Dumbbell, 
  Sparkles, 
  RotateCcw, 
  HeartPulse, 
  Clock, 
  Target,
  SlidersHorizontal 
} from 'lucide-react';

export const RecommendationPanel = ({ videoId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeCategory, setActiveCategory] = useState('all');

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

  const categories = [
    { id: 'all', label: 'All Items', count: recommendations?.length || 0 },
    { id: 'exercise', label: 'Exercises', count: recommendations?.filter(r => r.category === 'exercise').length || 0 },
    { id: 'mobility', label: 'Mobility', count: recommendations?.filter(r => r.category === 'mobility').length || 0 },
    { id: 'strengthening', label: 'Strengthening', count: recommendations?.filter(r => r.category === 'strengthening').length || 0 },
    { id: 'recovery', label: 'Recovery', count: recommendations?.filter(r => r.category === 'recovery').length || 0 },
    { id: 'training_modification', label: 'Training Mods', count: recommendations?.filter(r => r.category === 'training_modification').length || 0 },
  ];

  const filteredRecs = (recommendations || []).filter(rec => {
    if (activeCategory === 'all') return true;
    return rec.category === activeCategory;
  });

  const getActionBadge = (actionType, category) => {
    if (category === 'strengthening') {
      return <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Strengthening</span>;
    }
    if (category === 'mobility') {
      return <span className="bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Mobility</span>;
    }
    if (category === 'exercise') {
      return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Exercise</span>;
    }
    if (category === 'recovery') {
      return <span className="bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Recovery</span>;
    }
    if (category === 'training_modification') {
      return <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Training Mod</span>;
    }
    switch (actionType) {
      case 'consult_professional':
        return <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Clinical Consult</span>;
      case 'technique_review':
        return <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Technique Review</span>;
      default:
        return <span className="bg-slate-50 text-slate-700 border border-slate-200 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">General Practice</span>;
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Lightbulb size={18} className="text-amber-500" />
          <span>Corrective Recommendation Engine</span>
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Targeted evidence-based corrective exercises, mobility drills, strengthening protocols, recovery, and training modifications.
        </p>
      </div>

      {disclaimer && (
        <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 flex items-start gap-2">
          <ShieldCheck size={15} className="text-amber-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{disclaimer}</p>
        </div>
      )}

      {/* Category Filter Pills */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              activeCategory === cat.id
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            <span>{cat.label}</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              activeCategory === cat.id ? 'bg-blue-700 text-white' : 'bg-slate-200 text-slate-700'
            }`}>
              {cat.count}
            </span>
          </button>
        ))}
      </div>

      {filteredRecs.length === 0 ? (
        <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs">
          No recommendations found in this category.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredRecs.map((rec, index) => (
            <div key={rec.id || index} className="p-4 border border-slate-200 rounded-xl bg-white shadow-xs hover:border-slate-300 transition">
              <div className="flex justify-between items-start gap-2 mb-2">
                <h4 className="font-bold text-xs text-slate-900">{rec.title}</h4>
                {getActionBadge(rec.action_type, rec.category)}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">{rec.description}</p>

              {/* Protocol Badges (Target Region, Sets/Reps, Frequency) */}
              {(rec.target_region || rec.sets_and_reps || rec.frequency) && (
                <div className="flex flex-wrap items-center gap-2 mb-2.5">
                  {rec.target_region && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md">
                      <Target size={11} className="text-slate-500" />
                      {rec.target_region}
                    </span>
                  )}
                  {rec.sets_and_reps && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md border border-blue-100">
                      <Dumbbell size={11} className="text-blue-500" />
                      {rec.sets_and_reps}
                    </span>
                  )}
                  {rec.frequency && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-md border border-emerald-100">
                      <Clock size={11} className="text-emerald-500" />
                      {rec.frequency}
                    </span>
                  )}
                </div>
              )}
              
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
export default RecommendationPanel;
