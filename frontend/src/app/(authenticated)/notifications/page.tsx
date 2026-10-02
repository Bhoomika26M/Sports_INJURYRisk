"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useNotifications } from "@/lib/hooks";
import { timeAgo } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { Icon } from "@/components/icons";
import { EmptyState, ErrorState, ListSkeleton, Spinner } from "@/components/feedback";
import { useToast } from "@/components/toast";

export default function NotificationsPage() {
  const q = useNotifications();
  const queryClient = useQueryClient();
  const toast = useToast();

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });
  const onError = (e: unknown) => toast.error(e instanceof Error ? e.message : "That didn't work. Please try again.");

  const markOne = useMutation({ mutationFn: (id: string) => api.post(`/notifications/${id}/read`), onSuccess: refresh, onError });
  const markAll = useMutation({
    mutationFn: () => api.post("/notifications/read-all"),
    onSuccess: async () => { await refresh(); toast.success("All caught up."); },
    onError,
  });

  const unread = q.data?.unread_count ?? 0;

  return (
    <>
      <PageHeader
        title="Notifications"
        subtitle={q.data ? (unread > 0 ? `${unread} unread` : "You're all caught up.") : undefined}
        actions={unread > 0 && (
          <button onClick={() => markAll.mutate()} disabled={markAll.isPending} className="btn btn-outline btn-sm">
            {markAll.isPending ? <Spinner className="h-4 w-4" /> : <Icon name="check" className="h-4 w-4" />} Mark all as read
          </button>
        )}
      />

      {q.isPending ? (
        <ListSkeleton />
      ) : q.isError ? (
        <ErrorState message={q.error.message} onRetry={() => q.refetch()} />
      ) : q.data.items.length === 0 ? (
        <EmptyState icon="bell" title="Nothing yet">We&apos;ll let you know here when something needs your attention.</EmptyState>
      ) : (
        <ul className="flex flex-col gap-3">
          {q.data.items.map((n) => {
            const isUnread = !n.read_at;
            return (
              <li key={n.id} className={`row !items-start ${isUnread ? "!bg-brand-tint/60" : ""}`}>
                <span className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${isUnread ? "bg-white text-brand-dark" : "bg-white text-ink-3"}`}>
                  <Icon name="bell" className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`text-ink ${isUnread ? "font-semibold" : "font-medium"}`}>{n.title}</p>
                  <p className="mt-0.5 text-sm text-ink-2">{n.body}</p>
                  <p className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-3">
                    {timeAgo(n.created_at)}
                    {n.related_athlete_id && (
                      <Link href={`/athletes/${n.related_athlete_id}`} className="font-medium text-brand-dark underline underline-offset-4">View athlete</Link>
                    )}
                  </p>
                </div>
                {isUnread && (
                  <button onClick={() => markOne.mutate(n.id)} disabled={markOne.isPending && markOne.variables === n.id}
                    aria-label={`Mark "${n.title}" as read`} className="btn btn-ghost btn-sm shrink-0">
                    {markOne.isPending && markOne.variables === n.id ? <Spinner className="h-4 w-4" /> : "Mark read"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
