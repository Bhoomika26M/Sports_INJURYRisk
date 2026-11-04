import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Error, Section } from "./ui.jsx";

// Lets the athlete (or an administrator) choose which coach, physiotherapist or
// sports scientist can see this athlete's data.
export default function ShareBox({ athleteId }) {
  const [people, setPeople] = useState([]);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const load = () => api.get(`/athletes/${athleteId}/access`).then(setPeople).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [athleteId]);

  const share = async (e) => {
    e.preventDefault();
    setError(""); setInfo("");
    try {
      await api.post(`/athletes/${athleteId}/access`, { email });
      setEmail(""); setInfo("Shared."); load();
    } catch (err) { setError(err.message); }
  };
  const remove = async (userId) => {
    setError(""); setInfo("");
    try { await api.del(`/athletes/${athleteId}/access/${userId}`); load(); } catch (err) { setError(err.message); }
  };

  return (
    <Section title="Shared with">
      <p className="mb-3 text-sm text-slate-500">People listed here can see this athlete's videos and results. Coaches and physiotherapists can also add data; sports scientists can only view.</p>
      <Error message={error} />
      {info && <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-700">{info}</div>}
      {people.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-4 text-center text-sm text-slate-500">Not shared with anyone yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {people.map((p) => (
            <li key={p.user_id} className="flex items-center justify-between py-2.5 text-sm">
              <span><span className="font-medium text-slate-900">{p.full_name}</span> <span className="text-slate-500">{p.email} · {p.access_role.replace("_", " ")}</span></span>
              <button type="button" className="font-medium text-red-600 hover:text-red-700" onClick={() => remove(p.user_id)}>Remove</button>
            </li>
          ))}
        </ul>
      )}
      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={share}>
        <input className="input" type="email" required placeholder="Email of a coach, physiotherapist or sports scientist" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button className="btn sm:w-32">Share</button>
      </form>
    </Section>
  );
}
