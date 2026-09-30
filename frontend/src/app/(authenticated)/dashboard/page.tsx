"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const ROLE_HOME: Record<string, string> = {
  athlete: "/dashboard/athlete",
  coach: "/dashboard/coach",
  physiotherapist: "/dashboard/physio",
  sports_scientist: "/dashboard/scientist",
  admin: "/dashboard/admin",
};

export default function DashboardRouter() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace(ROLE_HOME[user.role] || "/dashboard/athlete");
    }
  }, [loading, user, router]);

  return <div className="bento-card p-6">Loading dashboard…</div>;
}
