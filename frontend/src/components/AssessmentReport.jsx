import { useState, useEffect } from 'react';
import api from '../api/client';
import { ShieldAlert, CheckCircle2, BookOpen, Layers } from 'lucide-react';

export const AssessmentReport = ({ videoId }) => {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activity, setActivity] = useState('running');

  const fetchAssessment = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/assessment/${videoId}?activity=${activity}`);
      setAssessment(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load assessment');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessment();
  }, [videoId, activity]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <Layers size={18} className="text-purple-400" />
            <span>Movement Quality Assessment</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Evaluation against FIFA 11+ injury prevention clinical reference models.</p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <label className="text-xs font-semibold text-slate-300">Movement Pattern:</label>
          <select 
            value={activity} 
            onChange={(e) => setActivity(e.target.value)}
            className="text-xs border border-white/10 rounded-xl px-3 py-1.5 font-medium text-white bg-[#1c1d2e] outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="running">Running Gait</option>
            <option value="sprinting">Sprinting</option>
            <option value="squatting">Squatting</option>
            <option value="jumping">Jumping</option>
            <option value="landing">Drop Landing</option>
            <option value="cutting">Cutting / Change of Direction</option>
            <option value="throwing">Throwing</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-slate-400">Evaluating movement quality...</div>
      ) : error ? (
        <div className="p-4 bg-rose-500/10 text-rose-300 text-xs rounded-xl border border-rose-500/30">{error}</div>
      ) : assessment ? (
        <div className="space-y-4">
          {/* Clinical Reference Header */}
          <div className="flex items-center justify-between bg-[#161724] border border-white/5 px-4 py-3 rounded-xl text-xs text-white">
            <div className="flex items-center gap-2">
              <BookOpen size={16} className="text-purple-400 shrink-0" />
              <span className="font-semibold text-slate-300">Clinical Standard:</span>
              <span className="text-white font-medium">{assessment.clinical_reference || "FIFA 11+ / F-MARC Framework"}</span>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
              assessment.status === 'success' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 
              assessment.status === 'limited' ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' : 
              'bg-rose-500/15 text-rose-300 border border-rose-500/30'
            }`}>
              {assessment.status}
            </span>
          </div>

          <p className="text-xs text-slate-300 font-medium leading-relaxed">{assessment.summary}</p>

          {/* FIFA 11+ Clinical Benchmarks Comparison */}
          {assessment.fifa_benchmarks && Object.keys(assessment.fifa_benchmarks).length > 0 && (
            <div className="border border-white/5 rounded-xl p-4 bg-[#161724]">
              <span className="text-xs font-bold text-white block mb-3">
                Clinical Movement Benchmarks
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(assessment.fifa_benchmarks).map(([key, item]) => {
                  const isNormal = item.status === 'NORMAL';
                  const isBorderline = item.status === 'BORDERLINE';
                  return (
                    <div 
                      key={key} 
                      className={`p-3.5 rounded-xl border text-xs flex flex-col justify-between ${
                        isNormal ? 'bg-emerald-500/10 border-emerald-500/20 text-slate-200' : 
                        isBorderline ? 'bg-amber-500/10 border-amber-500/20 text-slate-200' : 
                        'bg-rose-500/10 border-rose-500/20 text-slate-200'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1.5">
                        <span className="font-bold capitalize text-white">{key.replace(/_/g, ' ')}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          isNormal ? 'bg-emerald-500/20 text-emerald-300' : 
                          isBorderline ? 'bg-amber-500/20 text-amber-300' : 
                          'bg-rose-500/20 text-rose-300'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                      <div className="text-xs text-slate-300 mt-1">
                        <p>Observed: <strong className="text-white">{item.observed_diff_deg ?? item.observed_lean_deg}°</strong> &bull; Target: {item.fifa_standard}</p>
                        {item.injury_correlation && (
                          <p className="text-slate-400 italic mt-0.5">{item.injury_correlation}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Warnings & Flags */}
          {assessment.flags && assessment.flags.length > 0 && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
              <h4 className="font-bold text-rose-300 text-xs mb-2 flex items-center gap-1.5">
                <ShieldAlert size={15} /> Kinematic Risk Indicators:
              </h4>
              <ul className="list-disc pl-4 text-xs text-rose-200 space-y-1">
                {assessment.flags.map((f, idx) => <li key={idx}>{f}</li>)}
              </ul>
            </div>
          )}
          
          {(!assessment.flags || assessment.flags.length === 0) && assessment.status === 'success' && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 p-3.5 rounded-xl text-xs flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
              <span>Optimal kinematics maintained. No significant biomechanical flags detected.</span>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default AssessmentReport;
