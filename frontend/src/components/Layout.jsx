import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

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

  const link = ({ isActive }) => `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-white/20 text-white" : "text-blue-100 hover:bg-white/10 hover:text-white"}`;
  return (
    <div className="min-h-screen">
      <header className="bg-gradient-to-r from-blue-800 via-blue-700 to-blue-500 shadow-md">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight text-white">InjuryRisk AI</Link>
          <nav className="flex flex-1 gap-1">
            <NavLink to="/" end className={link}>Dashboard</NavLink>
            <NavLink to="/athletes" className={link}>Athletes</NavLink>
            {user.role === "administrator" && <NavLink to="/admin" className={link}>Admin</NavLink>}
          </nav>
          <Link to="/notifications" className="relative text-sm text-blue-100 hover:text-white">
            Alerts
            {unread > 0 && <span className="ml-1 rounded-full bg-red-600 px-1.5 text-xs text-white">{unread}</span>}
          </Link>
          <span className="hidden text-sm text-blue-100 sm:block">{user.full_name} · {user.role.replace("_", " ")}</span>
          <button className="btn-secondary" onClick={() => { logout(); navigate("/login"); }}>Sign out</button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">{children}</main>
    </div>
  );
}
