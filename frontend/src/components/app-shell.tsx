"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useUnreadCount } from "@/lib/hooks";
import { initials, roleLabel } from "@/lib/format";
import { Icon, type IconName } from "@/components/icons";
import { Logo } from "@/components/logo";
import { Avatar } from "@/components/badges";
import { Spinner } from "@/components/feedback";

type NavItem = { label: string; href: string; icon: IconName; match: (p: string) => boolean };

function navFor(role: string): NavItem[] {
  const under = (base: string) => (p: string) => p === base || p.startsWith(`${base}/`);
  return [
    { label: "Home", href: "/dashboard", icon: "home", match: under("/dashboard") },
    { label: role === "athlete" ? "Profile" : "Athletes", href: "/athletes", icon: "users", match: under("/athletes") },
    { label: "Videos", href: "/videos", icon: "video", match: (p) => under("/videos")(p) && p !== "/videos/upload" },
    { label: "Reports", href: "/reports", icon: "file", match: under("/reports") },
  ];
}

function routeTitle(p: string): string {
  if (p.startsWith("/dashboard")) return "Home";
  if (p === "/athletes") return "Athletes";
  if (p === "/athletes/new") return "New athlete";
  if (p.startsWith("/athletes/")) return "Athlete";
  if (p === "/videos") return "Videos";
  if (p === "/videos/upload") return "New analysis";
  if (p.endsWith("/results")) return "Results";
  if (p.startsWith("/videos/")) return "Video";
  if (p.startsWith("/notifications")) return "Notifications";
  if (p.startsWith("/reports")) return "Reports";
  return "InjuryDetect";
}

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  return (
    <div className="relative" ref={wrapRef}>
      <button
        ref={btnRef}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        className="flex items-center gap-2 rounded-full p-1 pr-2 hover:bg-surface"
      >
        <Avatar text={initials(user.full_name)} size={40} />
        <Icon name="chevron-down" className="hidden h-4 w-4 text-ink-3 sm:block" />
      </button>
      {open && (
        <div className="popover" role="menu">
          <div className="px-3 py-2.5">
            <p className="truncate font-semibold text-ink">{user.full_name}</p>
            <p className="truncate text-sm text-ink-3">{user.email}</p>
            <p className="mt-1.5"><span className="badge badge-muted">{roleLabel(user.role)}</span></p>
          </div>
          <div className="my-1 border-t border-faint" />
          <button
            role="menuitem"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await logout();
            }}
            className="flex min-h-11 w-full items-center gap-3 rounded-[12px] px-3 text-left text-sm font-medium text-ink-2 hover:bg-surface hover:text-ink disabled:opacity-60"
          >
            {busy ? <Spinner className="h-4 w-4" /> : <Icon name="logout" className="h-4 w-4" />} Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function Bell() {
  const { data: unread = 0 } = useUnreadCount();
  const pathname = usePathname();
  return (
    <Link
      href="/notifications"
      aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
      aria-current={pathname.startsWith("/notifications") ? "page" : undefined}
      className="relative flex h-11 w-11 items-center justify-center rounded-full text-ink-2 hover:bg-surface hover:text-ink aria-[current=page]:bg-surface"
    >
      <Icon name="bell" />
      {unread > 0 && (
        <span className="absolute right-1 top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-danger px-1 text-[11px] font-bold leading-none text-white">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, pathname, router]);

  const title = routeTitle(pathname);
  useEffect(() => {
    document.title = `${title} · InjuryDetect`;
  }, [title]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-wash text-ink-2" role="status">
        <Logo compact href="/" />
        <Spinner className="h-6 w-6" />
        <span className="text-sm">Getting things ready…</span>
      </div>
    );
  }

  const nav = navFor(user.role);

  return (
    <div className="flex min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:rounded-full focus:bg-brand focus:px-5 focus:py-3 focus:font-semibold focus:text-brand-dark"
      >
        Skip to content
      </a>

      <aside className="sidebar" aria-label="Main">
        <div className="px-2 pb-6"><Logo /></div>
        <nav className="flex flex-col gap-1">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} className="nav-item" aria-current={item.match(pathname) ? "page" : undefined}>
              <Icon name={item.icon} className="h-5 w-5" /> {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="topbar">
          <div className="flex min-w-0 items-center gap-3">
            <div className="lg:hidden"><Logo compact /></div>
            <span className="truncate text-[15px] font-semibold text-ink-2">{title}</span>
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <Link href="/videos/upload" className="btn btn-primary btn-sm hidden sm:inline-flex">
              <Icon name="plus" className="h-4 w-4" /> New analysis
            </Link>
            <Bell />
            <UserMenu />
          </div>
        </header>

        <main id="main" className="mx-auto flex w-full max-w-[1120px] flex-1 flex-col gap-8 px-5 pb-32 pt-8 lg:px-10 lg:pb-24 lg:pt-10">
          {children}
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Main">
        {nav.slice(0, 2).map((item) => (
          <Link key={item.href} href={item.href} aria-current={item.match(pathname) ? "page" : undefined}>
            <span className="bn-icon"><Icon name={item.icon} className="h-5 w-5" /></span>{item.label}
          </Link>
        ))}
        <Link href="/videos/upload" aria-current={pathname === "/videos/upload" ? "page" : undefined}>
          <span className="bn-icon !bg-brand !text-brand-dark"><Icon name="plus" className="h-5 w-5" /></span>Analyze
        </Link>
        {nav.slice(2).map((item) => (
          <Link key={item.href} href={item.href} aria-current={item.match(pathname) ? "page" : undefined}>
            <span className="bn-icon"><Icon name={item.icon} className="h-5 w-5" /></span>{item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
