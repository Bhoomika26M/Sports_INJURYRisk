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

  if (loading) {
    return (
      <div className="p-8 text-center text-xs sm:text-sm text-slate-400">
        <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        Loading corrective exercise plan...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-rose-500/10 text-rose-300 text-xs sm:text-sm rounded-xl border border-rose-500/30">
        {error}
      </div>
    );
  }

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
      return <span className="bg-purple-500/15 text-purple-300 border border-purple-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Strengthening</span>;
    }
    if (category === 'mobility') {
      return <span className="bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Mobility</span>;
    }
    if (category === 'exercise') {
      return <span className="bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Exercise</span>;
    }
    if (category === 'recovery') {
      return <span className="bg-teal-500/15 text-teal-300 border border-teal-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Recovery</span>;
    }
    if (category === 'training_modification') {
      return <span className="bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Training Mod</span>;
    }
    switch (actionType) {
      case 'consult_professional':
        return <span className="bg-rose-500/15 text-rose-300 border border-rose-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Clinical Consult</span>;
      case 'technique_review':
        return <span className="bg-blue-500/15 text-blue-300 border border-blue-500/30 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Technique Review</span>;
      default:
        return <span className="bg-zinc-800 text-slate-300 border border-white/10 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">General Drill</span>;
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <Lightbulb size={20} className="text-amber-400" />
          <span>Corrective Recommendation Engine</span>
        </h3>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Targeted evidence-based corrective exercises, mobility drills, strengthening protocols, and training modifications.
        </p>
      </div>

      {disclaimer && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 text-xs sm:text-sm text-amber-200 flex items-start gap-2.5">
          <ShieldCheck size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{disclaimer}</p>
        </div>
      )}

      {/* Category Filter Pills */}
      <div className="flex flex-wrap gap-2 pt-1">
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            className={`px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition flex items-center gap-2 ${
              activeCategory === cat.id
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/25'
                : 'bg-[#181926] text-slate-300 hover:bg-[#232436] border border-white/5'
            }`}
          >
            <span>{cat.label}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${
              activeCategory === cat.id ? 'bg-purple-800 text-white' : 'bg-white/10 text-slate-300'
            }`}>
              {cat.count}
            </span>
          </button>
        ))}
      </div>

      {filteredRecs.length === 0 ? (
        <div className="p-8 text-center text-slate-400 bg-[#141522] rounded-xl border border-dashed border-white/10 text-xs sm:text-sm">
          No recommendations found in this category.
        </div>
      ) : (
        <div className="space-y-3.5">
          {filteredRecs.map((rec, index) => (
            <div key={rec.id || index} className="p-4 sm:p-5 border border-white/10 rounded-xl bg-[#141522] hover:border-purple-500/40 transition">
              <div className="flex justify-between items-start gap-3 mb-2.5">
                <h4 className="font-bold text-sm sm:text-base text-white">{rec.title}</h4>
                {getActionBadge(rec.action_type, rec.category)}
              </div>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-3.5">{rec.description}</p>

              {/* Protocol Badges (Target Region, Sets/Reps, Frequency) */}
              {(rec.target_region || rec.sets_and_reps || rec.frequency) && (
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  {rec.target_region && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold bg-[#1c1d2e] text-slate-300 border border-white/5 px-2.5 py-1 rounded-lg">
                      <Target size={13} className="text-purple-400" />
                      {rec.target_region}
                    </span>
                  )}
                  {rec.sets_and_reps && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2.5 py-1 rounded-lg">
                      <Dumbbell size={13} className="text-purple-400" />
                      {rec.sets_and_reps}
                    </span>
                  )}
                  {rec.frequency && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
                      <Clock size={13} className="text-emerald-400" />
                      {rec.frequency}
                    </span>
                  )}
                </div>
              )}
              
              <div className="bg-[#1a1b2b] rounded-xl p-3 text-xs text-slate-300 space-y-1.5 border border-white/5">
                <p><strong className="text-white">Trigger Finding:</strong> {rec.triggering_finding}</p>
                <p><strong className="text-white">Clinical Rationale:</strong> {rec.rationale}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecommendationPanel;
