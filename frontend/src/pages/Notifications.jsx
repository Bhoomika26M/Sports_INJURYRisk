import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Error, fmtDate, Section } from "../components/ui.jsx";

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const load = () => api.get("/notifications").then(setItems).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Alerts &amp; notifications</h1>
        <button className="btn-secondary" onClick={() => api.post("/notifications/read-all").then(load)}>Mark all read</button>
      </div>
      <Error message={error} />
      <Section title="Latest">
        {items.length === 0 && <p className="text-sm text-slate-500">No notifications.</p>}
        <ul className="divide-y">
          {items.map((n) => (
            <li key={n.id} className={`py-3 ${n.is_read ? "opacity-60" : ""}`}>
              <div className="flex justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold">{n.title}</div>
                  <div className="text-sm text-slate-600">{n.message}</div>
                  <div className="text-xs text-slate-400">{fmtDate(n.created_at)} · {n.type.replace(/_/g, " ")}{n.athlete_id && <> · <Link className="text-blue-600" to={`/athletes/${n.athlete_id}`}>athlete</Link></>}</div>
                </div>
                {!n.is_read && <button className="btn-secondary h-8" onClick={() => api.post(`/notifications/${n.id}/read`).then(load)}>Read</button>}
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
