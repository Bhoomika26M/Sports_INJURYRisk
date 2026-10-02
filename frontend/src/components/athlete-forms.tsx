"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { humanize, todayISO } from "@/lib/format";
import type { Athlete, Injury, TrainingLoad } from "@/lib/types";
import { Field } from "@/components/field";
import { Modal } from "@/components/dialog";
import { Notice, Spinner } from "@/components/feedback";
import { useToast } from "@/components/toast";

const SPORTS = ["basketball", "soccer", "track", "volleyball", "tennis", "baseball", "football", "swimming", "other"];

function SubmitRow({ busy, label, onCancel }: { busy: boolean; label: string; onCancel?: () => void }) {
  return (
    <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
      {onCancel && <button type="button" onClick={onCancel} disabled={busy} className="btn btn-outline">Cancel</button>}
      <button type="submit" disabled={busy} className="btn btn-primary">
        {busy && <Spinner className="h-4 w-4" />} {label}
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ athlete */

export function AthleteForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: Athlete;
  submitLabel: string;
  onSubmit: (body: Record<string, unknown>) => Promise<void>;
  onCancel?: () => void;
}) {
  const [sport, setSport] = useState(initial?.sport_type ?? "");
  const [position, setPosition] = useState(initial?.position ?? "");
  const [dob, setDob] = useState(initial?.date_of_birth ?? "");
  const [height, setHeight] = useState(initial?.height_cm?.toString() ?? "");
  const [weight, setWeight] = useState(initial?.weight_kg?.toString() ?? "");
  const [side, setSide] = useState(initial?.dominant_side ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // keep a stored sport (e.g. "track and field") selectable even if it isn't in the short list
  const sports = sport && !SPORTS.includes(sport) ? [sport, ...SPORTS] : SPORTS;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await onSubmit({
        sport_type: sport,
        position: position.trim() || null,
        date_of_birth: dob,
        height_cm: height ? Number(height) : null,
        weight_kg: weight ? Number(weight) : null,
        dominant_side: side || null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't save that. Please try again.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-5">
      {error && <Notice tone="danger">{error}</Notice>}
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Sport">
          {(p) => (
            <select {...p} required className="input" value={sport} onChange={(e) => setSport(e.target.value)}>
              <option value="">Choose a sport…</option>
              {sports.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
            </select>
          )}
        </Field>
        <Field label="Position" optional>
          {(p) => <input {...p} className="input" maxLength={100} placeholder="e.g. Guard" value={position} onChange={(e) => setPosition(e.target.value)} />}
        </Field>
        <Field label="Date of birth">
          {(p) => <input {...p} type="date" required className="input" max={todayISO()} value={dob} onChange={(e) => setDob(e.target.value)} />}
        </Field>
        <Field label="Dominant side" optional>
          {(p) => (
            <select {...p} className="input" value={side} onChange={(e) => setSide(e.target.value as "left" | "right" | "")}>
              <option value="">Not sure</option>
              <option value="left">Left</option>
              <option value="right">Right</option>
            </select>
          )}
        </Field>
        <Field label="Height (cm)" optional>
          {(p) => <input {...p} type="number" inputMode="decimal" min={50} max={300} step="any" className="input" value={height} onChange={(e) => setHeight(e.target.value)} />}
        </Field>
        <Field label="Weight (kg)" optional>
          {(p) => <input {...p} type="number" inputMode="decimal" min={20} max={200} step="any" className="input" value={weight} onChange={(e) => setWeight(e.target.value)} />}
        </Field>
      </div>
      <SubmitRow busy={busy} label={submitLabel} onCancel={onCancel} />
    </form>
  );
}

export function EditAthleteModal({ athlete, open, onClose }: { athlete: Athlete; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  return (
    <Modal open={open} onClose={onClose} title="Edit profile">
      <AthleteForm
        initial={athlete}
        submitLabel="Save changes"
        onCancel={onClose}
        onSubmit={async (body) => {
          await api.put(`/athletes/${athlete.id}`, body);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["athlete", athlete.id] }),
            queryClient.invalidateQueries({ queryKey: ["athletes"] }),
          ]);
          toast.success("Profile updated.");
          onClose();
        }}
      />
    </Modal>
  );
}

/* ------------------------------------------------------------------ injury */

export function InjuryModal({ athleteId, open, onClose }: { athleteId: string; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [type, setType] = useState("");
  const [part, setPart] = useState("");
  const [date, setDate] = useState("");
  const [recovered, setRecovered] = useState("");
  const [severity, setSeverity] = useState("");
  const [notes, setNotes] = useState("");
  const [dateError, setDateError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.post<Injury>(`/athletes/${athleteId}/injuries`, {
        injury_type: type.trim(),
        body_part: part.trim(),
        injury_date: date,
        recovery_date: recovered || null,
        severity: severity || null,
        notes: notes.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["athlete", athleteId, "injuries"] });
      toast.success("Injury added.");
      onClose();
    },
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (recovered && recovered < date) return setDateError("Recovery can't be before the injury date.");
    setDateError(null);
    save.mutate();
  }

  return (
    <Modal open={open} onClose={onClose} title="Add an injury" description="Past injuries help put movement results in context.">
      <form onSubmit={submit} className="flex flex-col gap-5">
        {save.isError && <Notice tone="danger">{save.error.message}</Notice>}
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="What happened?">
            {(p) => <input {...p} required maxLength={255} className="input" placeholder="e.g. Ankle sprain" value={type} onChange={(e) => setType(e.target.value)} />}
          </Field>
          <Field label="Body part">
            {(p) => <input {...p} required maxLength={100} className="input" placeholder="e.g. Left ankle" value={part} onChange={(e) => setPart(e.target.value)} />}
          </Field>
          <Field label="Injury date">
            {(p) => <input {...p} type="date" required max={todayISO()} className="input" value={date} onChange={(e) => setDate(e.target.value)} />}
          </Field>
          <Field label="Recovered on" optional error={dateError}>
            {(p) => <input {...p} type="date" min={date || undefined} max={todayISO()} className="input" value={recovered} onChange={(e) => setRecovered(e.target.value)} />}
          </Field>
        </div>
        <Field label="Severity" optional>
          {(p) => (
            <select {...p} className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">Not specified</option>
              <option value="minor">Minor</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          )}
        </Field>
        <Field label="Notes" optional>
          {(p) => <textarea {...p} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />}
        </Field>
        <SubmitRow busy={save.isPending} label="Add injury" onCancel={onClose} />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------- training load */

export function TrainingModal({ athleteId, open, onClose }: { athleteId: string; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [date, setDate] = useState(todayISO);
  const [sessionType, setSessionType] = useState("");
  const [minutes, setMinutes] = useState("");
  const [rpe, setRpe] = useState("");
  const [notes, setNotes] = useState("");

  const save = useMutation({
    mutationFn: () =>
      api.post<TrainingLoad>(`/athletes/${athleteId}/training-load`, {
        entry_date: date,
        session_type: sessionType.trim() || null,
        duration_minutes: minutes ? Number(minutes) : null,
        rpe: rpe ? Number(rpe) : null,
        notes: notes.trim() || null,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["athlete", athleteId, "training"] }),
        queryClient.invalidateQueries({ queryKey: ["athlete", athleteId, "acwr"] }),
      ]);
      toast.success("Session logged.");
      onClose();
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Log a training session" description="Duration × effort (RPE) gives the session load.">
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="flex flex-col gap-5">
        {save.isError && <Notice tone="danger">{save.error.message}</Notice>}
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Date">
            {(p) => <input {...p} type="date" required max={todayISO()} className="input" value={date} onChange={(e) => setDate(e.target.value)} />}
          </Field>
          <Field label="Session type" optional>
            {(p) => <input {...p} maxLength={100} className="input" placeholder="e.g. Strength" value={sessionType} onChange={(e) => setSessionType(e.target.value)} />}
          </Field>
          <Field label="Duration (minutes)">
            {(p) => <input {...p} type="number" inputMode="numeric" required min={1} max={1440} className="input" value={minutes} onChange={(e) => setMinutes(e.target.value)} />}
          </Field>
          <Field label="Effort (RPE 1–10)" hint="How hard it felt, 10 is maximal.">
            {(p) => (
              <select {...p} required className="input" value={rpe} onChange={(e) => setRpe(e.target.value)}>
                <option value="">Choose…</option>
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            )}
          </Field>
        </div>
        <Field label="Notes" optional>
          {(p) => <textarea {...p} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />}
        </Field>
        <SubmitRow busy={save.isPending} label="Log session" onCancel={onClose} />
      </form>
    </Modal>
  );
}
