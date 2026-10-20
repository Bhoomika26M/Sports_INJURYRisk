import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Error, Section } from "../components/ui.jsx";

const ROLES = ["athlete", "coach", "physiotherapist", "sports_scientist", "administrator"];

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "coach" });
  const load = () => api.get("/users").then(setUsers).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);
  const patch = (id, body) => api.patch(`/users/${id}`, body).then(load).catch((e) => setError(e.message));

  return (
    <>
      <h1 className="text-2xl font-semibold">User management</h1>
      <Error message={error} />
      <Section title="Users">
        <table className="w-full text-left text-sm">
          <thead><tr className="border-b text-xs uppercase text-slate-500"><th className="py-2">Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b last:border-0">
                <td className="py-2">{u.full_name}</td><td>{u.email}</td>
                <td><select className="input w-auto py-1" value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select></td>
                <td><input type="checkbox" checked={u.is_active} onChange={(e) => patch(u.id, { is_active: e.target.checked })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <Section title="Create user">
        <form className="grid gap-3 sm:grid-cols-5" onSubmit={(e) => { e.preventDefault(); api.post("/users/admin-create", form).then(() => { setForm({ ...form, email: "", full_name: "", password: "" }); load(); }).catch((er) => setError(er.message)); }}>
          <input className="input" placeholder="Full name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <input className="input" type="email" placeholder="Email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="input" type="password" minLength={8} placeholder="Password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select>
          <button className="btn">Create</button>
        </form>
      </Section>
    </>
  );
}
