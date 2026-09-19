"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="space-y-8">
      {/* Welcome Hero Banner Card */}
      <div 
        className="bg-white rounded-2xl p-6 sm:p-8 border-2 border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6"
        style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.25), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
      >
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-black uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full">
              {user.role.replace("_", " ")}
            </span>
            <span className="text-xs font-bold text-slate-500">Biomechanics Portal v1.0</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
            Welcome, {user.full_name}
          </h1>
          <p className="mt-1.5 text-sm font-medium text-slate-600 max-w-xl leading-relaxed">
            Computer vision-based biomechanics screening, joint angle kinematics, and scientific risk flagging.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/videos/upload"
            className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-extrabold text-xs sm:text-sm px-5 py-3 rounded-xl shadow-lg shadow-blue-600/30 transition-all flex items-center gap-2 cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            <span>Upload Video</span>
          </Link>
          <Link
            href="/athletes"
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs sm:text-sm px-5 py-3 rounded-xl border-2 border-slate-300 transition-all cursor-pointer shadow-xs"
          >
            View Athletes
          </Link>
        </div>
      </div>

      {/* Metrics Row (3 High-Contrast Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div 
          className="bg-white rounded-2xl p-6 border-2 border-slate-300 flex flex-col justify-between"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="flex items-center justify-between text-slate-700 mb-3">
            <span className="text-xs font-black uppercase tracking-wider text-slate-600">Demo Athletes</span>
            <div className="w-10 h-10 rounded-xl bg-blue-50 border-2 border-blue-200 flex items-center justify-center text-blue-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-black text-slate-900">3</div>
          <div className="text-xs font-bold text-slate-600 mt-2">Basketball, Soccer, Track</div>
        </div>

        <div 
          className="bg-white rounded-2xl p-6 border-2 border-slate-300 flex flex-col justify-between"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="flex items-center justify-between text-slate-700 mb-3">
            <span className="text-xs font-black uppercase tracking-wider text-slate-600">Pose Pipeline</span>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center text-emerald-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-black text-slate-900">Active</div>
          <div className="text-xs font-bold text-slate-600 mt-2">MediaPipe Pose + YOLOv8 worker</div>
        </div>

        <div 
          className="bg-white rounded-2xl p-6 border-2 border-slate-300 flex flex-col justify-between"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
        >
          <div className="flex items-center justify-between text-slate-700 mb-3">
            <span className="text-xs font-black uppercase tracking-wider text-slate-600">Methodology</span>
            <div className="w-10 h-10 rounded-xl bg-purple-50 border-2 border-purple-200 flex items-center justify-center text-purple-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
          </div>
          <div className="text-4xl font-black text-slate-900">Heuristic</div>
          <div className="text-xs font-bold text-slate-600 mt-2">Validated biomechanics rules</div>
        </div>
      </div>

      {/* Quick Action Tiles (High Contrast with Rich Shadows) */}
      <div>
        <h2 className="text-xs font-black uppercase tracking-wider text-slate-600 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            href="/videos/upload"
            className="bg-white rounded-2xl p-6 border-2 border-slate-300 hover:border-blue-500 transition-all flex items-start gap-4 group cursor-pointer"
            style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
          >
            <div className="w-12 h-12 rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/30 flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-blue-600 transition-colors">
                Analyze Movement Video
              </h3>
              <p className="text-xs text-slate-600 font-medium mt-1 leading-relaxed">
                Upload squat, deadlift, or jump movement recordings. Compute joint angles, limb symmetry index (LSI), and qualitative frontal-plane knee valgus flags.
              </p>
            </div>
          </Link>

          <Link
            href="/athletes"
            className="bg-white rounded-2xl p-6 border-2 border-slate-300 hover:border-indigo-500 transition-all flex items-start gap-4 group cursor-pointer"
            style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.38), -6px -6px 16px rgba(255, 255, 255, 0.95)" }}
          >
            <div className="w-12 h-12 rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-500/30 flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-indigo-600 transition-colors">
                Athlete Profiles & History
              </h3>
              <p className="text-xs text-slate-600 font-medium mt-1 leading-relaxed">
                Review athlete injury records, Acute:Chronic Workload Ratios (ACWR), baseline movement kinematics, and historical risk scoring reports.
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
