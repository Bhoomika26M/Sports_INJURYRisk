"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useAthletes } from "@/lib/hooks";
import { athleteName, canManageAthletes, humanize, initials } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { Avatar } from "@/components/badges";
import { Icon } from "@/components/icons";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/feedback";

const PAGE_SIZE = 20;

export default function AthletesPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const q = useAthletes(page, PAGE_SIZE);
  const canManage = canManageAthletes(user?.role);

  // An athlete only ever sees themselves — skip the pointless one-row list.
  const only = user?.role === "athlete" && q.data?.items.length === 1 ? q.data.items[0].id : null;
  useEffect(() => {
    if (only) router.replace(`/athletes/${only}`);
  }, [only, router]);

  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title={user?.role === "athlete" ? "Your profile" : "Athletes"}
        subtitle={user?.role === "athlete" ? undefined : "Everyone you're keeping an eye on."}
        actions={canManage && <Link href="/athletes/new" className="btn btn-primary"><Icon name="plus" className="h-4 w-4" /> Add athlete</Link>}
      />

      {q.isPending || only ? (
        <ListSkeleton />
      ) : q.isError ? (
        <ErrorState message={q.error.message} onRetry={() => q.refetch()} />
      ) : total === 0 ? (
        canManage ? (
          <EmptyState icon="users" title="No athletes yet" action={{ label: "Add your first athlete", href: "/athletes/new" }}>
            Create a profile to start uploading and analyzing videos.
          </EmptyState>
        ) : user?.role === "athlete" ? (
          <EmptyState icon="users" title="Your profile isn't set up yet">Your coach needs to create or link your athlete profile.</EmptyState>
        ) : (
          <EmptyState icon="users" title="No athletes to show yet">Athletes will appear here once a coach adds them.</EmptyState>
        )
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {q.data.items.map((a) => (
              <li key={a.id}>
                <Link href={`/athletes/${a.id}`} className="row">
                  <Avatar text={initials(athleteName(a))} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-ink">{athleteName(a)}</p>
                    <p className="truncate text-sm text-ink-3">
                      {humanize(a.sport_type)}{a.position ? ` · ${a.position}` : ""}{a.age != null ? ` · ${a.age} years` : ""}
                    </p>
                  </div>
                  <Icon name="chevron-right" className="h-5 w-5 text-ink-3" />
                </Link>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="flex items-center justify-between">
              <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><Icon name="chevron-left" className="h-4 w-4" /> Previous</button>
              <span className="text-sm text-ink-3">Page {page} of {pages}</span>
              <button className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next <Icon name="chevron-right" className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}
    </>
  );
}
