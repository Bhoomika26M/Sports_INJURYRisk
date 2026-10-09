"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUserFromToken } from "@/lib/auth";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, AreaChart, Area } from 'recharts';

export default function DashboardHome() {
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);

  useEffect(() => {
    const user = getUserFromToken();
    if (user) {
      setTimeout(() => setUser(user), 0);
    }
  }, []);

  if (!user) return null;

  switch (user.role) {
    case "Athlete":
      return <AthleteDashboard />;
    case "Physiotherapist":
      return <PhysioDashboard />;
    case "Sports Scientist":
      return <ScientistDashboard />;
    case "Administrator":
      return <AdminDashboard />;
    case "Coach":
    default:
      return <CoachDashboard />;
  }
}

function AthleteDashboard() {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<any[]>([]);

  useEffect(() => {
    const fetchAnalyses = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        // Fetch Analyses
        const { getAnalyses } = await import("@/lib/api");
        const data = await getAnalyses(token);
        setAnalyses(data);

        // Fetch Notifications
        const notifRes = await fetch("http://localhost:8000/notifications", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (notifRes.ok) {
          const notifData = await notifRes.json();
          setNotifications(notifData);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalyses();
  }, []);

  const handleExportPDF = () => {
    const token = localStorage.getItem("token");
    window.open(`http://localhost:8000/export/pdf?token=${token}`, "_blank");
  };

  const handleExportCSV = () => {
    const token = localStorage.getItem("token");
    window.open(`http://localhost:8000/export/csv?token=${token}`, "_blank");
  };

  const avgRiskScore = analyses.length > 0
    ? Math.round(analyses.reduce((acc, curr) => acc + curr.risk_score, 0) / analyses.length)
    : 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-white">Athlete Intelligence Dashboard</h2>
          <p className="text-slate-400 text-sm mt-1">AI-Powered Biomechanics & Injury Prediction</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportPDF} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors border border-slate-700">Export PDF</button>
          <button onClick={handleExportCSV} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors border border-slate-700">Export CSV</button>
        </div>
      </div>

      {notifications.length > 0 && (
        <div className="flex flex-col gap-2">
          {notifications.map(notif => (
            <div key={notif.id} className={`p-4 rounded-xl border ${notif.type === 'alert' ? 'bg-rose-500/10 border-rose-500/30 text-rose-300' : 'bg-amber-500/10 border-amber-500/30 text-amber-300'}`}>
              <strong>{notif.title}</strong>: {notif.message}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Average Risk Score</div>
          <div className={`text-3xl font-bold ${avgRiskScore > 30 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {avgRiskScore} / 100
          </div>
          <div className="text-xs text-slate-400 mt-2">Based on {analyses.length} recent analyses</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Total Videos Analyzed</div>
          <div className="text-3xl font-bold text-white">{analyses.length}</div>
          <div className="text-xs text-slate-400 mt-2">Historical movement assessment</div>
        </div>
        <Link href="/dashboard/upload" className="glass-panel p-6 rounded-2xl border-indigo-500/30 bg-indigo-500/5 hover:bg-indigo-500/10 transition-colors cursor-pointer flex flex-col items-center justify-center text-indigo-400 hover:text-indigo-300">
          <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span className="font-medium">Run New Analysis</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="glass-panel rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-6">Biomechanics Reports & Movement Anomalies</h3>
          {loading ? (
            <div className="text-slate-400 text-center py-12">Loading analysis history...</div>
          ) : analyses.length === 0 ? (
            <div className="text-slate-400 text-center py-12">No video analysis found. Upload a video to generate your first report.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {analyses.map((analysis) => {
                const flags = JSON.parse(analysis.injury_probabilities || "[]");
                return (
                  <div key={analysis.id} className="bg-slate-900/50 p-6 rounded-xl border border-slate-800 hover:border-slate-700 transition-colors flex flex-col">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="text-white font-medium">{analysis.activity}</div>
                        <div className="text-xs text-slate-400">{new Date(analysis.created_at).toLocaleDateString()}</div>
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-bold ${analysis.risk_score > 30 ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {analysis.risk_score} Risk
                      </div>
                    </div>
                    <div className="space-y-2 flex-1 mb-4">
                      <div className="text-xs font-semibold text-slate-500 uppercase">Anomalies & Flags</div>
                      {flags.map((f: string, i: number) => (
                        <div key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="text-rose-400 shrink-0">•</span> <span>{f}</span>
                        </div>
                      ))}
                      {flags.length === 0 && <div className="text-sm text-slate-400">No anomalies detected.</div>}
                    </div>
                    <div className="pt-4 border-t border-slate-800/50">
                      <div className="text-xs font-semibold text-slate-500 uppercase mb-1">Corrective Recommendation</div>
                      <div className="text-sm text-indigo-300 bg-indigo-500/10 p-3 rounded-lg border border-indigo-500/20">
                        {analysis.corrective_recommendation || "Maintain current training program."}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PhysioDashboard() {
  const data = [
    { name: 'Mon', injuries: 1, recoveries: 2 },
    { name: 'Tue', injuries: 0, recoveries: 1 },
    { name: 'Wed', injuries: 2, recoveries: 0 },
    { name: 'Thu', injuries: 1, recoveries: 3 },
    { name: 'Fri', injuries: 0, recoveries: 2 },
    { name: 'Sat', injuries: 3, recoveries: 1 },
    { name: 'Sun', injuries: 0, recoveries: 4 },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Active Injuries</div>
          <div className="text-3xl font-bold text-white">4</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Rehab Plans Active</div>
          <div className="text-3xl font-bold text-white">12</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Cleared to Play</div>
          <div className="text-3xl font-bold text-emerald-400">2 This Week</div>
        </div>
      </div>
      <div className="glass-panel rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-6">Injury vs Recovery Trends</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
              <Legend />
              <Bar dataKey="injuries" fill="#f43f5e" name="New Injuries" radius={[4, 4, 0, 0]} />
              <Bar dataKey="recoveries" fill="#10b981" name="Recoveries" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function ScientistDashboard() {
  const fatigueData = [
    { day: 'Day 1', load: 60, fatigue: 40 },
    { day: 'Day 2', load: 80, fatigue: 55 },
    { day: 'Day 3', load: 40, fatigue: 30 },
    { day: 'Day 4', load: 95, fatigue: 85 },
    { day: 'Day 5', load: 85, fatigue: 75 },
    { day: 'Day 6', load: 50, fatigue: 45 },
    { day: 'Day 7', load: 100, fatigue: 90 },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Team Fatigue Index</div>
          <div className="text-3xl font-bold text-amber-400">Elevated</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Workload Spikes</div>
          <div className="text-3xl font-bold text-rose-400">3 Players</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Reports Generated</div>
          <div className="text-3xl font-bold text-white">14</div>
        </div>
      </div>
      <div className="glass-panel rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-6">Training Load vs Fatigue Overlay</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={fatigueData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
              <Legend />
              <Line type="monotone" dataKey="load" stroke="#8b5cf6" strokeWidth={3} name="Training Load" />
              <Line type="monotone" dataKey="fatigue" stroke="#f59e0b" strokeWidth={3} name="Fatigue Index" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function AdminDashboard() {
  const platformUsage = [
    { name: 'Week 1', users: 150, analyses: 300 },
    { name: 'Week 2', users: 180, analyses: 450 },
    { name: 'Week 3', users: 210, analyses: 500 },
    { name: 'Week 4', users: 245, analyses: 620 },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Total Users</div>
          <div className="text-3xl font-bold text-white">245</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Active Teams</div>
          <div className="text-3xl font-bold text-white">8</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">System Health</div>
          <div className="text-3xl font-bold text-emerald-400">99.9%</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Storage Used</div>
          <div className="text-3xl font-bold text-white">1.2 TB</div>
        </div>
      </div>
      <div className="glass-panel rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-6">Platform Usage Overview</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={platformUsage}>
              <defs>
                <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorAnalyses" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
              <Legend />
              <Area type="monotone" dataKey="users" stroke="#3b82f6" fillOpacity={1} fill="url(#colorUsers)" name="Active Users" />
              <Area type="monotone" dataKey="analyses" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorAnalyses)" name="Analyses Run" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function CoachDashboard() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Team Overall Risk Score</div>
          <div className="text-3xl font-bold text-white flex items-end gap-2">
            28<span className="text-lg text-green-400">/ 100</span>
          </div>
          <div className="text-xs text-green-400 mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>
            -12% from last week
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">High Risk Athletes</div>
          <div className="text-3xl font-bold text-white">
            2
          </div>
          <div className="text-xs text-rose-400 mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
            +1 since yesterday
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl">
          <div className="text-sm font-medium text-slate-400 mb-1">Videos Analyzed</div>
          <div className="text-3xl font-bold text-white">
            143
          </div>
          <div className="text-xs text-indigo-400 mt-2 flex items-center gap-1">
            <span>Last 7 days</span>
          </div>
        </div>

        <Link href="/dashboard/upload" className="glass-panel p-6 rounded-2xl border-indigo-500/30 bg-indigo-500/5 cursor-pointer hover:bg-indigo-500/10 transition-colors group">
          <div className="h-full flex flex-col items-center justify-center text-indigo-400 group-hover:text-indigo-300">
            <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="font-medium">Upload New Video</span>
          </div>
        </Link>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Column - Athletes List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white">Athlete Risk Assessment</h3>
              <button className="text-sm text-indigo-400 hover:text-indigo-300 font-medium">View All</button>
            </div>

            <div className="space-y-4">
              {/* Athlete Item 1 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">MS</div>
                  <div>
                    <div className="font-medium text-white">Michael Smith</div>
                    <div className="text-xs text-slate-400">Point Guard • Knee Valgus Detected</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-rose-400">84/100 Risk</div>
                    <div className="text-xs text-slate-500">Critical</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-rose-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-rose-500 rounded-full" style={{ height: '84%' }}></div>
                  </div>
                </div>
              </div>

              {/* Athlete Item 2 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">DJ</div>
                  <div>
                    <div className="font-medium text-white">David Johnson</div>
                    <div className="text-xs text-slate-400">Shooting Guard • Minor Fatigue</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-amber-400">42/100 Risk</div>
                    <div className="text-xs text-slate-500">Moderate</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-amber-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-amber-500 rounded-full" style={{ height: '42%' }}></div>
                  </div>
                </div>
              </div>

              {/* Athlete Item 3 */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300">EW</div>
                  <div>
                    <div className="font-medium text-white">Ethan Williams</div>
                    <div className="text-xs text-slate-400">Power Forward • Optimal Form</div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm font-bold text-emerald-400">12/100 Risk</div>
                    <div className="text-xs text-slate-500">Low</div>
                  </div>
                  <div className="w-2 h-10 rounded-full bg-emerald-500/20 relative">
                    <div className="absolute bottom-0 w-full bg-emerald-500 rounded-full" style={{ height: '12%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Breakdown */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-6">Recent Video Analysis</h3>

            <div className="aspect-video bg-slate-900 rounded-xl relative overflow-hidden group mb-4 border border-slate-800">
              {/* Fake Video Thumbnail / AI Overlay */}
              <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1546519638-68e109498ffc?q=80&w=2090&auto=format&fit=crop')] bg-cover bg-center opacity-40 mix-blend-luminosity"></div>

              {/* Simulated skeleton overlay */}
              <div className="absolute top-[20%] left-[45%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[40%] left-[40%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[40%] left-[50%] w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <div className="absolute top-[60%] left-[38%] w-2 h-2 bg-rose-500 rounded-full animate-pulse shadow-[0_0_10px_#f43f5e]"></div>

              {/* Connecting lines simulated */}
              <div className="absolute top-[21%] left-[45%] w-[1px] h-[20%] bg-green-400/50 transform -rotate-12 origin-top"></div>

              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950/40">
                <button className="w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center text-white shadow-lg hover:bg-indigo-500 transition-colors cursor-pointer z-10">
                  <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4l12 6-12 6z" /></svg>
                </button>
              </div>

              {/* Status Badge */}
              <div className="absolute top-3 right-3 px-2.5 py-1 bg-rose-500/20 border border-rose-500/50 text-rose-400 text-xs font-bold rounded-lg backdrop-blur-sm">
                Anomaly Detected
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Athlete</span>
                <span className="text-white font-medium">Michael Smith</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Movement</span>
                <span className="text-white font-medium">Squat Jump</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Issue Found</span>
                <span className="text-rose-400 font-medium">Valgus Collapse (Left)</span>
              </div>

              <button className="w-full mt-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors border border-slate-700">
                View Detailed Report
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
