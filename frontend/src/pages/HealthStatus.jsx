import React, { useState, useEffect } from 'react';
import { apiService } from '../api/client';
import { Activity, RefreshCw, CheckCircle2, XCircle, Database, Server } from 'lucide-react';

export default function HealthStatus() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [latency, setLatency] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await apiService.getHealth();
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealthData(data);
    } catch (err) {
      setError(err.message || 'Unable to connect to FastAPI backend');
      setHealthData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System & API Health</h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time diagnostics and backend connection validation.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-2 text-emerald-400 ${loading ? 'animate-spin' : ''}`} />
          Re-check
        </button>
      </div>

      {/* Connectivity Status Card */}
      <div className="glass-card rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                healthData?.status === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
              }`}
            >
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">FastAPI Application Service</h3>
              <p className="text-xs text-slate-400">Endpoint: GET /health</p>
            </div>
          </div>
          <div>
            {loading ? (
              <span className="px-3 py-1 text-xs rounded-full bg-slate-800 text-slate-400 animate-pulse">
                Probing...
              </span>
            ) : healthData ? (
              <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> ONLINE
              </span>
            ) : (
              <span className="px-3 py-1 text-xs font-bold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
                <XCircle className="w-3.5 h-3.5" /> OFFLINE
              </span>
            )}
          </div>
        </div>

        {/* Diagnostics Table */}
        {healthData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-500 block">Status:</span>
              <span className="text-sm font-semibold text-emerald-400">{healthData.status}</span>
            </div>
            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-500 block">Environment:</span>
              <span className="text-sm font-semibold text-slate-200">{healthData.environment}</span>
            </div>
            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-500 block">Version:</span>
              <span className="text-sm font-semibold text-slate-200">{healthData.version}</span>
            </div>
            <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-500 block">Latency:</span>
              <span className="text-sm font-semibold text-cyan-400">{latency} ms</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            <p className="font-semibold text-sm mb-1">Backend Connection Failed</p>
            <p>{error}</p>
            <p className="mt-2 text-slate-400">
              Ensure the backend is running via <code className="text-slate-300 bg-slate-900 px-1 py-0.5 rounded">docker compose up</code> or <code className="text-slate-300 bg-slate-900 px-1 py-0.5 rounded">uvicorn app.main:app</code>.
            </p>
          </div>
        )}

        {/* Raw Response Output */}
        {healthData && (
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Raw Response Payload:
            </span>
            <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-emerald-400/90 font-mono overflow-x-auto">
              {JSON.stringify(healthData, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
