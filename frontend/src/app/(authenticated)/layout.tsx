"use client";

import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  const [unreadCount, setUnreadCount] = useState<number>(0);

  useEffect(() => {
    if (!user) return;
    apiClient.fetchWithAuth("/notifications?page_size=1").then((d: any) => setUnreadCount(d.unread_count || 0)).catch(() => {});
  }, [user, pathname]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-muted)" }}>
        <div className="bento-card p-6 flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24" style={{ color: "var(--brand-dark)" }}>
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
    { name: "Notifications", href: "/notifications", badge: unreadCount },
    { name: "Reports", href: "/reports" },
  ];

  const initials = user.full_name ? user.full_name.split(" ").map((p) => p.charAt(0)).join("").slice(0, 2).toUpperCase() : "U";
  const crumb = pathname === "/dashboard" ? "Home / Overview" : `Home ${pathname.replace(/\//g, " / ")}`;

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="circle-action-btn" style={{ width: 40, height: 40, fontSize: 20 }}>W</div>
            <span className="font-bold text-base" style={{ color: "var(--text-primary)", letterSpacing: "-0.02em" }}>InjuryDetect</span>
          </Link>
        </div>
        <nav className="flex flex-col gap-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}`));
            return (
              <Link key={item.name} href={item.href} className={`nav-item ${isActive ? "nav-item--active" : ""}`}>
                {item.name}
                {(item as any).badge > 0 && (
                  <span className="status-pill status-pill--danger" style={{ marginLeft: "auto" }}>
                    {(item as any).badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="app-main">
        <header className="app-header">
          <div className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>{crumb}</div>
          <div className="flex items-center gap-3">
            <Link href="/videos/upload" className="pill-btn--primary">Upload video</Link>
            <Link href="/reports" className="pill-btn--soft">Reports</Link>
            <div className="flex items-center gap-2 pill-btn--outline" style={{ cursor: "default" }}>
              <div
                className="flex items-center justify-center text-xs font-bold"
                style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--brand-primary)", color: "var(--brand-primary-fg)" }}
              >
                {initials}
              </div>
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{user.full_name}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{user.role.replace("_", " ")}</span>
            </div>
            <button onClick={() => logout()} title="Log out" className="pill-btn--outline">Log out</button>
          </div>
        </header>

        <main>
          <div className="content-canvas">{children}</div>
        </main>
      </div>
    </div>
  );
}