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
          <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Layers size={18} className="text-blue-600" />
            <span>Movement Quality Assessment</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">Evaluation against FIFA 11+ injury prevention clinical reference models.</p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <label className="text-xs font-semibold text-slate-600">Movement Pattern:</label>
          <select 
            value={activity} 
            onChange={(e) => setActivity(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 bg-white outline-none focus:ring-2 focus:ring-blue-100"
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
        <div className="p-6 text-center text-xs text-slate-400">Evaluating movement quality...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200">{error}</div>
      ) : assessment ? (
        <div className="space-y-4">
          {/* Clinical Reference Header */}
          <div className="flex items-center justify-between bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-xl text-xs text-slate-800">
            <div className="flex items-center gap-2">
              <BookOpen size={15} className="text-blue-600 shrink-0" />
              <span className="font-semibold">Clinical Standard:</span>
              <span className="text-slate-600">{assessment.clinical_reference || "FIFA 11+ / F-MARC Framework"}</span>
            </div>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
              assessment.status === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 
              assessment.status === 'limited' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 
              'bg-rose-50 text-rose-700 border border-rose-200'
            }`}>
              {assessment.status}
            </span>
          </div>

          <p className="text-xs text-slate-700 font-medium leading-relaxed">{assessment.summary}</p>

          {/* FIFA 11+ Clinical Benchmarks Comparison */}
          {assessment.fifa_benchmarks && Object.keys(assessment.fifa_benchmarks).length > 0 && (
            <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50">
              <span className="text-xs font-bold text-slate-800 block mb-2.5">
                Clinical Movement Benchmarks
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {Object.entries(assessment.fifa_benchmarks).map(([key, item]) => {
                  const isNormal = item.status === 'NORMAL';
                  const isBorderline = item.status === 'BORDERLINE';
                  return (
                    <div 
                      key={key} 
                      className={`p-3 rounded-xl border text-xs flex flex-col justify-between ${
                        isNormal ? 'bg-emerald-50/50 border-emerald-200 text-emerald-950' : 
                        isBorderline ? 'bg-amber-50/50 border-amber-200 text-amber-950' : 
                        'bg-rose-50/50 border-rose-200 text-rose-950'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-bold capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          isNormal ? 'bg-emerald-100 text-emerald-800' : 
                          isBorderline ? 'bg-amber-100 text-amber-800' : 
                          'bg-rose-100 text-rose-800'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-600 mt-1">
                        <p>Observed: <strong>{item.observed_diff_deg ?? item.observed_lean_deg}°</strong> &bull; Target: {item.fifa_standard}</p>
                        {item.injury_correlation && (
                          <p className="text-slate-500 italic mt-0.5">{item.injury_correlation}</p>
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
            <div className="p-3.5 bg-rose-50/70 border border-rose-200 rounded-xl">
              <h4 className="font-bold text-rose-800 text-xs mb-1.5 flex items-center gap-1.5">
                <ShieldAlert size={14} /> Kinematic Risk Indicators:
              </h4>
              <ul className="list-disc pl-4 text-xs text-rose-700 space-y-1">
                {assessment.flags.map((f, idx) => <li key={idx}>{f}</li>)}
              </ul>
            </div>
          )}
          
          {(!assessment.flags || assessment.flags.length === 0) && assessment.status === 'success' && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-xl text-xs flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              <span>Optimal kinematics maintained. No significant biomechanical flags detected.</span>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
