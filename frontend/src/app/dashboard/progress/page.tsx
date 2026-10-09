"use client";

import { useEffect, useState } from "react";
import { getPerformanceRecords, createPerformanceRecord } from "@/lib/api";

interface RecordData {
  date: string;
  metric: string;
  value: number;
  unit: string;
}

export default function ProgressPage() {
  const [records, setRecords] = useState<RecordData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    metric: "",
    value: "",
    unit: ""
  });

  const loadRecords = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const data = await getPerformanceRecords(token);
      setRecords(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setTimeout(() => {
      loadRecords();
    }, 0);
  }, []);



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const payload = {
        ...formData,
        value: parseFloat(formData.value)
      };

      await createPerformanceRecord(token, payload);
      setShowForm(false);
      setFormData({ date: new Date().toISOString().split('T')[0], metric: "", value: "", unit: "" });
      loadRecords();
    } catch (err) {
      console.error("Failed to add performance record", err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Performance Tracking</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium text-sm shadow-lg shadow-indigo-500/20"
        >
          {showForm ? "Cancel" : "Add Record"}
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
                <label className="text-sm font-medium text-slate-300">Metric Name</label>
                <input required type="text" placeholder="e.g. Sprint Time, Jump Height" value={formData.metric} onChange={e => setFormData({ ...formData, metric: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Value</label>
                <input required type="number" step="0.01" placeholder="e.g. 10.5" value={formData.value} onChange={e => setFormData({ ...formData, value: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Unit</label>
                <input required type="text" placeholder="e.g. sec, cm, kg" value={formData.unit} onChange={e => setFormData({ ...formData, unit: e.target.value })} className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-xl focus:border-indigo-500 text-white" />
              </div>
            </div>
            <button type="submit" className="px-6 py-2 bg-white text-slate-900 font-bold rounded-xl mt-4">Save Record</button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-slate-400">Loading performance records...</div>
      ) : records.length === 0 ? (
        <div className="glass-panel p-8 text-center rounded-2xl text-slate-400">
          No performance records yet. Add one to start tracking your progress!
        </div>
      ) : (
        <div className="glass-panel p-6 rounded-2xl overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-3 px-4 font-medium text-sm">Date</th>
                <th className="py-3 px-4 font-medium text-sm">Metric</th>
                <th className="py-3 px-4 font-medium text-sm">Value</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="py-3 px-4 text-sm text-slate-300">{r.date}</td>
                  <td className="py-3 px-4 text-sm font-medium text-white">{r.metric}</td>
                  <td className="py-3 px-4 text-sm text-indigo-400 font-bold">{r.value} {r.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
