"use client";

import { useSyncExternalStore } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { isInFlight } from "@/lib/format";
import type {
  Acwr, Athlete, Injury, MovementType, NotificationPage, Page, TrainingLoad, Video,
} from "@/lib/types";

export const POLL_MS = 2000;

export function useAthletes(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["athletes", { page, pageSize }],
    queryFn: () => api.get<Page<Athlete>>(`/athletes?page=${page}&page_size=${pageSize}`),
    placeholderData: (prev) => prev,
  });
}

/** Everyone the user can see (API max page size is 100) — for pickers and name lookups. */
export function useAllAthletes() {
  return useQuery({
    queryKey: ["athletes", "all"],
    queryFn: () => api.get<Page<Athlete>>("/athletes?page=1&page_size=100"),
  });
}

export function useAthlete(id: string) {
  return useQuery({ queryKey: ["athlete", id], queryFn: () => api.get<Athlete>(`/athletes/${id}`) });
}

export function useInjuries(id: string) {
  return useQuery({
    queryKey: ["athlete", id, "injuries"],
    queryFn: () => api.get<Page<Injury>>(`/athletes/${id}/injuries?page_size=100`),
  });
}

export function useTrainingLoad(id: string) {
  return useQuery({
    queryKey: ["athlete", id, "training"],
    queryFn: () => api.get<Page<TrainingLoad>>(`/athletes/${id}/training-load?page_size=100`),
  });
}

export function useAcwr(id: string) {
  return useQuery({ queryKey: ["athlete", id, "acwr"], queryFn: () => api.get<Acwr>(`/athletes/${id}/acwr`) });
}

export function useMovementTypes() {
  return useQuery({
    queryKey: ["movement-types"],
    queryFn: () => api.get<MovementType[]>("/videos/movement-types"),
    staleTime: 10 * 60_000,
  });
}

/** One video. Polls every 2s while it's still being uploaded/analyzed, then stops by itself. */
export function useVideo(id: string | null) {
  return useQuery({
    queryKey: ["video", id],
    queryFn: () => api.get<Video>(`/videos/${id}`),
    enabled: !!id,
    refetchInterval: (q) => {
      const v = q.state.data;
      if (q.state.status === "error") return v && isInFlight(v.processing_status) ? 5000 : false;
      return v && isInFlight(v.processing_status) ? POLL_MS : false;
    },
  });
}

export function useVideos(opts: { athleteId?: string; page?: number; pageSize?: number } = {}) {
  const { athleteId, page = 1, pageSize = 20 } = opts;
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (athleteId) qs.set("athlete_id", athleteId);
  return useQuery({
    queryKey: ["videos", { athleteId: athleteId ?? null, page, pageSize }],
    queryFn: () => api.get<Page<Video>>(`/videos?${qs.toString()}`),
    placeholderData: (prev) => prev,
    // keep the list fresh while anything on the page is still being analyzed
    refetchInterval: (q) => (q.state.data?.items.some((v) => isInFlight(v.processing_status)) ? 4000 : false),
  });
}

export function useNotifications(pageSize = 50) {
  return useQuery({
    queryKey: ["notifications", { pageSize }],
    queryFn: () => api.get<NotificationPage>(`/notifications?page_size=${pageSize}`),
  });
}

/** Tiny request powering the bell badge. */
export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => api.get<NotificationPage>("/notifications?page_size=1"),
    select: (d) => d.unread_count,
    refetchInterval: 60_000,
  });
}

const noopSubscribe = () => () => {};
/** False during SSR and until React has hydrated — used to keep forms from submitting natively (password in URL). */
export function useHydrated(): boolean {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}
