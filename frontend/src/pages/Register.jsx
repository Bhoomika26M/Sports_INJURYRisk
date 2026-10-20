import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Error } from "../components/ui.jsx";

const ROLES = ["athlete", "coach", "physiotherapist", "sports_scientist"];

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "athlete" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/register", form);
      await login(form.email, form.password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold text-blue-800">Create account</h1>
        <Error message={error} />
        <div><label className="label">Full name</label><input className="input" required minLength={2} value={form.full_name} onChange={set("full_name")} /></div>
        <div><label className="label">Email</label><input className="input" type="email" required value={form.email} onChange={set("email")} /></div>
        <div><label className="label">Password (min 8 characters)</label><input className="input" type="password" required minLength={8} value={form.password} onChange={set("password")} /></div>
        <div>
          <label className="label">Role</label>
          <select className="input" value={form.role} onChange={set("role")}>
            {ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
          </select>
        </div>
        <button className="btn w-full">Register</button>
        <p className="text-center text-sm text-slate-500">Have an account? <Link className="text-blue-600" to="/login">Sign in</Link></p>
      </form>
    </div>
  );
}
