import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Logo } from "./AuthShell.jsx";

const ICONS = {
  dashboard: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z",
  athletes: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z",
  alerts: "M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0",
  admin: "M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z",
};

function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name]} />
    </svg>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const load = () => api.get("/notifications/unread-count").then((d) => setUnread(d.unread)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  const items = [
    { to: "/", label: "Dashboard", icon: "dashboard", end: true },
    { to: "/athletes", label: "Athletes", icon: "athletes" },
    { to: "/notifications", label: "Alerts", icon: "alerts", badge: unread },
    ...(user.role === "administrator" ? [{ to: "/admin", label: "Admin", icon: "admin" }] : []),
  ];
  const link = ({ isActive }) =>
    `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? "bg-white/15 text-white shadow-inner" : "text-blue-100/80 hover:bg-white/10 hover:text-white"}`;
  const initials = user.full_name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const signOut = () => { logout(); navigate("/login"); };
  const Badge = ({ n }) => (n > 0 ? <span className="ml-auto rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold text-white">{n}</span> : null);

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col bg-gradient-to-b from-slate-900 via-blue-950 to-blue-900 p-4 shadow-xl lg:flex">
        <Link to="/" className="mb-8 flex items-center gap-3 px-2 pt-2">
          <Logo />
          <span className="text-lg font-bold tracking-tight text-white">InjuryRisk AI</span>
        </Link>
        <nav className="flex-1 space-y-1">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className={link}>
              <Icon name={i.icon} />
              {i.label}
              <Badge n={i.badge} />
            </NavLink>
          ))}
        </nav>
        <div className="rounded-2xl bg-white/10 p-3">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-gradient-to-br from-blue-400 to-cyan-300 text-sm font-bold text-slate-900">{initials}</span>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-white">{user.full_name}</div>
              <div className="truncate text-xs capitalize text-blue-200">{user.role.replace("_", " ")}</div>
            </div>
          </div>
          <button onClick={signOut} className="mt-3 w-full rounded-lg bg-white/10 py-2 text-sm font-medium text-white transition hover:bg-white/20">Sign out</button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 bg-gradient-to-r from-slate-900 via-blue-950 to-blue-800 shadow-md lg:hidden">
        <div className="flex items-center gap-3 px-4 py-3">
          <Logo size={30} />
          <span className="flex-1 font-bold tracking-tight text-white">InjuryRisk AI</span>
          <button onClick={signOut} className="rounded-lg bg-white/10 px-3 py-1.5 text-sm font-medium text-white">Sign out</button>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
          {items.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className={link}>
              {i.label}
              <Badge n={i.badge} />
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 lg:ml-64 lg:max-w-none lg:px-10 lg:py-8">{children}</main>
    </div>
  );
}
