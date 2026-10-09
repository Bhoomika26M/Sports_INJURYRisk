"use client";

import { useEffect, useState } from "react";
import { getPhysicalAssessments, createPhysicalAssessment } from "@/lib/api";

interface Assessment {
  id: number;
  date: string;
  test_name: string;
  score: number;
  notes: string;
}

export default function FitnessPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    test_name: "",
    score: "",
    notes: ""
  });

  const loadAssessments = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const data = await getPhysicalAssessments(token);
      setAssessments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(() => {
      loadAssessments();
    }, 0);
  }, []);



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const payload = {
        ...formData,
        score: parseFloat(formData.score)
      };

      await createPhysicalAssessment(token, payload);
      setShowForm(false);
      setFormData({ date: new Date().toISOString().split('T')[0], test_name: "", score: "", notes: "" });
      loadAssessments();
    } catch (err) {
      console.error("Failed to add assessment", err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Physical Assessment Records</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium text-sm shadow-lg shadow-indigo-500/20"
        >
          {showForm ? "Cancel" : "Add Assessment"}
        </button>
      </div>

      {showForm && (
        <div className="glass-panel p-6 rounded-2xl mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Date</label>
                <input required type="date" value={formData.date} onChange={e => setFormData({ ...formData, date: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Test Name</label>
                <input required type="text" placeholder="e.g. Vo2 Max, 1RM Squat" value={formData.test_name} onChange={e => setFormData({ ...formData, test_name: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Score</label>
                <input required type="number" step="0.01" placeholder="e.g. 50.5" value={formData.score} onChange={e => setFormData({ ...formData, score: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Notes</label>
                <input type="text" placeholder="Optional notes" value={formData.notes} onChange={e => setFormData({ ...formData, notes: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
            </div>
            <button type="submit" className="px-6 py-2 bg-white text-slate-900 font-bold rounded-xl mt-4">Save Assessment</button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-slate-400">Loading assessments...</div>
      ) : assessments.length === 0 ? (
        <div className="glass-panel p-8 text-center rounded-2xl text-slate-400">
          No physical assessments recorded yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {assessments.map(a => (
            <div key={a.id} className="glass-panel p-6 rounded-2xl border border-slate-800">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-bold text-white">{a.test_name}</h3>
                <span className="text-xs text-slate-400">{a.date}</span>
              </div>
              <div className="text-3xl font-extrabold text-indigo-400 mb-2">{a.score}</div>
              {a.notes && <p className="text-sm text-slate-500">{a.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
