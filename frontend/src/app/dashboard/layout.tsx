"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUserFromToken } from "@/lib/auth";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchedUser = getUserFromToken();
    if (!fetchedUser) {
      router.push("/");
    } else {
      setUser(fetchedUser);
    }
  }, [router]);

  if (!user) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Loading...</div>;
  }

  const getNavLinks = (role: string) => {
    switch (role) {
      case "Athlete":
        return [
          { name: "My Overview", href: "/dashboard" },
          { name: "Profile", href: "/dashboard/profile" },
          { name: "My Fitness", href: "/dashboard/fitness" },
          { name: "Training Plans", href: "/dashboard/training" },
          { name: "Progress", href: "/dashboard/progress" },
        ];
      case "Coach":
        return [
          { name: "Team Overview", href: "/dashboard" },
          { name: "Player Monitoring", href: "#" },
          { name: "Training Assignments", href: "#" },
          { name: "Workload Alerts", href: "#" },
        ];
      case "Physiotherapist":
        return [
          { name: "Injury Dashboard", href: "/dashboard" },
          { name: "Rehab Plans", href: "#" },
          { name: "Recovery Status", href: "#" },
          { name: "Return-to-Play", href: "#" },
        ];
      case "Sports Scientist":
        return [
          { name: "Performance Analytics", href: "/dashboard" },
          { name: "Metrics Comparison", href: "#" },
          { name: "Fatigue Trends", href: "#" },
          { name: "Reports", href: "#" },
        ];
      case "Administrator":
        return [
          { name: "Platform Overview", href: "/dashboard" },
          { name: "User Management", href: "#" },
          { name: "Team Config", href: "#" },
          { name: "System Settings", href: "#" },
        ];
      default:
        return [{ name: "Overview", href: "/dashboard" }];
    }
  };

  const navLinks = getNavLinks(user.role);

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-950/50 hidden md:flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <span className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-pink-500">
            SportsAI
          </span>
        </div>

        <nav className="flex-1 py-6 px-4 space-y-2 overflow-y-auto">
          {navLinks.map((link, idx) => (
            <Link key={idx} href={link.href} className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors ${idx === 0 ? 'bg-indigo-600/10 text-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}>
              {idx === 0 && (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              )}
              {idx !== 0 && (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              )}
              {link.name}
            </Link>
          ))}
          <Link href="/dashboard/settings" className="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 rounded-xl font-medium transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </Link>
        </nav>

        <div className="p-6 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-pink-500 flex items-center justify-center text-white font-bold">
              {user.email.substring(0, 2).toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <div className="text-sm font-medium text-slate-200 truncate">{user.email}</div>
              <div className="text-xs text-slate-500">{user.role}</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-16 flex items-center justify-between px-8 border-b border-slate-800 bg-slate-950/50 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-xl font-semibold capitalize">{user.role} Dashboard</h2>
          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-400 hover:text-slate-200 transition-colors relative">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-pink-500 rounded-full border-2 border-slate-950"></span>
            </button>
            <button onClick={() => { localStorage.removeItem("token"); router.push("/"); }} className="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors">
              Log Out
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-8 relative">
          <div className="absolute top-0 right-0 w-[40%] h-[40%] bg-indigo-500/10 blur-[100px] pointer-events-none" />
          {children}
        </div>
      </main>
    </div>
  );
}
