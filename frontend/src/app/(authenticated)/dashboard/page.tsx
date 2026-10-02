"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { PageSkeleton } from "@/components/feedback";

const ROLE_HOME: Record<string, string> = {
  athlete: "/dashboard/athlete",
  coach: "/dashboard/coach",
  physiotherapist: "/dashboard/physio",
  sports_scientist: "/dashboard/scientist",
  admin: "/dashboard/admin",
};

export default function DashboardRouter() {
  const router = useRouter();
  const { user } = useAuth();
  useEffect(() => {
    if (user) router.replace(ROLE_HOME[user.role] ?? "/dashboard/athlete");
  }, [user, router]);
  return <PageSkeleton rows={2} />;
}
