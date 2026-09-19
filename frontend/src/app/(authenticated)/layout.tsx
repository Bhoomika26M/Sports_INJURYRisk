"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <div 
          className="bg-white p-6 rounded-2xl border-2 border-slate-200 flex items-center gap-3 text-slate-800"
          style={{ boxShadow: "6px 6px 16px rgba(148, 163, 184, 0.25), -6px -6px 16px rgba(255, 255, 255, 0.9)" }}
        >
          <svg className="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm font-bold">Loading session...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const navigation = [
    { name: "Dashboard", href: "/dashboard" },
    { name: "Athletes", href: "/athletes" },
    { name: "Upload Video", href: "/videos/upload" },
  ];

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#edf2f7" }}>
      {/* High-Contrast Sleek Header */}
      <header className="sticky top-0 z-30 bg-white border-b-2 border-slate-300" style={{ boxShadow: "0 4px 14px rgba(148, 163, 184, 0.2)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link href="/dashboard" className="flex items-center gap-3 group">
                <div 
                  className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/30 group-hover:bg-blue-700 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div className="flex flex-col">
                  <span className="font-black text-lg tracking-tight text-slate-900 leading-tight">
                    Injury<span className="text-blue-600">Detect</span>
                  </span>
                  <span className="text-[10px] font-extrabold text-slate-500 tracking-wider uppercase">
                    Biomechanics Lab
                  </span>
                </div>
              </Link>

              {/* Nav links */}
              <nav className="hidden sm:flex items-center gap-1.5">
                {navigation.map((item) => {
                  const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}`));
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold tracking-wide transition-all ${
                        isActive
                          ? "bg-blue-600 text-white shadow-md shadow-blue-600/25"
                          : "text-slate-700 hover:text-slate-900 hover:bg-slate-100 border border-transparent"
                      }`}
                    >
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Right side user info & logout */}
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-extrabold text-slate-900 leading-tight">{user.full_name}</div>
                <div className="text-[10px] font-bold text-blue-700 uppercase tracking-wider bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded inline-block mt-0.5">
                  {user.role.replace("_", " ")}
                </div>
              </div>

              <div 
                className="w-9 h-9 rounded-xl bg-slate-800 text-white flex items-center justify-center text-xs font-black uppercase shadow-sm"
              >
                {user.full_name ? user.full_name.charAt(0) : "U"}
              </div>

              <button
                onClick={() => logout()}
                title="Log out"
                className="w-9 h-9 rounded-xl bg-white hover:bg-red-50 text-slate-500 hover:text-red-600 border-2 border-slate-300 hover:border-red-300 transition-colors flex items-center justify-center cursor-pointer shadow-xs"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
