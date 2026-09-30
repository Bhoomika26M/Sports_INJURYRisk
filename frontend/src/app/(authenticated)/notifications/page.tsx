"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

type Note = {
  id: string;
  type: string;
  title: string;
  body: string;
  read_at: string | null;
  related_athlete_id: string | null;
  created_at: string;
};

export default function NotificationsPage() {
  const [items, setItems] = useState<Note[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const d = await apiClient.fetchWithAuth("/notifications?page_size=50");
      setItems(d.items);
      setUnread(d.unread_count);
    } catch (e: any) {
      setError(e.message || "Failed to load notifications");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const markRead = async (id: string) => {
    await apiClient.fetchWithAuth(`/notifications/${id}/read`, { method: "POST" });
    load();
  };

  if (error) return <div className="status-pill status-pill--danger">{error}</div>;

  return (
    <div>
      <section className="bento-hero bento-hero--blue">
        <div>
          <h2 className="bento-hero__title">Notifications</h2>
          <p className="bento-hero__subtitle">{unread} unread — high-risk alerts, training warnings, assessment updates.</p>
        </div>
      </section>
      <div className="bento-card" style={{ marginTop: 40, padding: "8px 0" }}>
        {items.length === 0 && <div className="drawer-item text-sm" style={{ color: "var(--text-secondary)" }}>No notifications yet.</div>}
        {items.map((n) => (
          <div key={n.id} className="drawer-item">
            <div style={{ flex: 1 }}>
              <div className="flex items-center gap-2">
                <span className="status-pill status-pill--info">{n.type.replace("_", " ")}</span>
                {!n.read_at && <span className="status-pill status-pill--danger">unread</span>}
              </div>
              <h3 className="font-semibold mt-1" style={{ color: "var(--text-primary)", fontSize: 16 }}>{n.title}</h3>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{n.body}</p>
            </div>
            {!n.read_at && (
              <button onClick={() => markRead(n.id)} className="pill-btn--outline">Mark read</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
