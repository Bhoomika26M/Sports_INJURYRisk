import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { Error, Section, Table } from "../components/ui.jsx";

const EMPTY = { full_name: "", sport_type: "", position: "", age: 20, height_cm: 175, weight_kg: 70, weekly_training_load: "" };

export default function Athletes() {
  const [athletes, setAthletes] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const load = () => api.get("/athletes").then(setAthletes).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const body = { ...form, age: +form.age, height_cm: +form.height_cm, weight_kg: +form.weight_kg };
    body.weekly_training_load = form.weekly_training_load === "" ? null : +form.weekly_training_load;
    if (!body.full_name) delete body.full_name;
    if (!body.position) delete body.position;
    try { await api.post("/athletes", body); setForm(EMPTY); load(); } catch (err) { setError(err.message); }
  };

  return (
    <>
      <h1 className="text-2xl font-semibold">Athletes</h1>
      <Error message={error} />
      <Section title="Athlete profiles">
        <Table
          columns={[
            { header: "Code", key: "athlete_code" },
            { header: "Name", render: (r) => <Link className="text-blue-600" to={`/athletes/${r.id}`}>{r.full_name}</Link> },
            { header: "Sport", key: "sport_type" }, { header: "Position", key: "position" }, { header: "Age", key: "age" },
          ]}
          rows={athletes}
        />
      </Section>
      <Section title="Register athlete">
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-3">
          <div><label className="label">Full name (blank = my name)</label><input className="input" value={form.full_name} onChange={set("full_name")} /></div>
          <div><label className="label">Sport</label><input className="input" required value={form.sport_type} onChange={set("sport_type")} /></div>
          <div><label className="label">Position</label><input className="input" value={form.position} onChange={set("position")} /></div>
          <div><label className="label">Age</label><input className="input" type="number" min="5" max="100" required value={form.age} onChange={set("age")} /></div>
          <div><label className="label">Height (cm)</label><input className="input" type="number" min="80" max="250" required value={form.height_cm} onChange={set("height_cm")} /></div>
          <div><label className="label">Weight (kg)</label><input className="input" type="number" min="20" max="250" required value={form.weight_kg} onChange={set("weight_kg")} /></div>
          <div><label className="label">Weekly training load (AU, optional)</label><input className="input" type="number" min="0" value={form.weekly_training_load} onChange={set("weekly_training_load")} /></div>
          <div className="flex items-end"><button className="btn">Register athlete</button></div>
        </form>
      </Section>
    </>
  );
}
