import React, { useState, useEffect } from 'react';
import { athletesAPI, invitationsAPI } from '../services/api';

const AdminAthleteAccessCard = () => {
  const [athletes, setAthletes] = useState([]);
  const [professionals, setProfessionals] = useState([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState('');
  const [selectedProId, setSelectedProId] = useState('');
  const [notes, setNotes] = useState('');
  const [existingGrants, setExistingGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [grantsLoading, setGrantsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // Initial load: all athletes and active professional staff
  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const [athRes, proRes] = await Promise.all([
          athletesAPI.getAll(),
          invitationsAPI.getProfessionals(),
        ]);
        const athList = athRes.data || [];
        setAthletes(athList);
        setProfessionals(proRes.data || []);

        if (athList.length > 0) {
          setSelectedAthleteId(athList[0].id.toString());
        }
      } catch (err) {
        console.error('Failed to initialize AdminAthleteAccessCard:', err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // When selected athlete changes, load their access grants
  const loadGrantsForAthlete = async (athleteId) => {
    if (!athleteId) return;
    try {
      setGrantsLoading(true);
      const res = await invitationsAPI.getAthleteInvitations(athleteId);
      setExistingGrants(res.data || []);
    } catch (err) {
      console.error('Failed to load grants:', err);
      setExistingGrants([]);
    } finally {
      setGrantsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAthleteId) {
      loadGrantsForAthlete(selectedAthleteId);
    }
  }, [selectedAthleteId]);

  const handleGrantAccess = async (e) => {
    e.preventDefault();
    if (!selectedAthleteId || !selectedProId) {
      setMessage({ text: 'Please select both an Athlete and a Professional.', type: 'error' });
      return;
    }

    try {
      setSubmitting(true);
      setMessage({ text: '', type: '' });
      await invitationsAPI.invite(parseInt(selectedAthleteId), {
        professional_user_id: parseInt(selectedProId),
        notes: notes || 'Admin assigned care team access',
      });
      setMessage({
        text: 'Access granted successfully! The athlete and professional have been notified.',
        type: 'success',
      });
      setSelectedProId('');
      setNotes('');
      await loadGrantsForAthlete(selectedAthleteId);
    } catch (err) {
      setMessage({
        text: err.response?.data?.detail || 'Failed to grant access.',
        type: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (invitationId, proName) => {
    if (!confirm(`Are you sure you want to revoke access for ${proName}?`)) {
      return;
    }
    try {
      setGrantsLoading(true);
      setMessage({ text: '', type: '' });
      await invitationsAPI.revoke(parseInt(selectedAthleteId), invitationId);
      setMessage({ text: `Access revoked for ${proName}.`, type: 'success' });
      await loadGrantsForAthlete(selectedAthleteId);
    } catch (err) {
      setMessage({
        text: err.response?.data?.detail || 'Failed to revoke access.',
        type: 'error',
      });
    } finally {
      setGrantsLoading(false);
    }
  };

  const selectedAthleteObj = athletes.find((a) => a.id.toString() === selectedAthleteId);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-orange-50/50 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#BD4006] text-white flex items-center justify-center font-bold text-lg shadow-sm">
            🔗
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-lg font-bold text-[#141B2B]">
                Manual Athlete Access Grants
              </h2>
              <span className="px-2 py-0.5 rounded bg-orange-100 text-[#BD4006] text-[10px] font-mono font-bold uppercase tracking-wider">
                Direct Assignment
              </span>
            </div>
            <p className="text-xs text-[#594139] mt-0.5">
              Administratively link care team members (Coaches, Physios, Scientists) to specific athletes. Athletes are notified instantly.
            </p>
          </div>
        </div>
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Status Alert */}
        {message.text && (
          <div
            className={`p-3 rounded-xl text-xs font-medium border flex items-center justify-between ${
              message.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-red-50 text-red-800 border-red-200'
            }`}
          >
            <span>{message.text}</span>
            <button
              onClick={() => setMessage({ text: '', type: '' })}
              className="font-bold ml-2 text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        )}

        {/* Grant Form */}
        <div className="bg-[#F9F9FF] p-4 sm:p-5 rounded-xl border border-gray-200/70">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#BD4006] mb-3 flex items-center gap-1.5">
            <span>⚡</span> Grant Athlete Permissions
          </h3>
          <form onSubmit={handleGrantAccess} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Select Athlete *
              </label>
              <select
                value={selectedAthleteId}
                onChange={(e) => setSelectedAthleteId(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white font-medium"
              >
                {athletes.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name || a.athlete_id} ({a.sport || 'Athlete'})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Select Care Team Member *
              </label>
              <select
                value={selectedProId}
                onChange={(e) => setSelectedProId(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white font-medium"
              >
                <option value="">-- Choose Coach / Physio / Scientist --</option>
                {professionals.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name} ({p.role.replace(/_/g, ' ')})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Clinical Context / Notes
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Lead Sprint Coach"
                  className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white"
                />
                <button
                  type="submit"
                  disabled={submitting || !selectedProId}
                  className="px-4 py-2 bg-[#BD4006] hover:bg-[#A33605] text-white text-xs font-bold rounded-lg transition-colors whitespace-nowrap shadow-sm disabled:opacity-50"
                >
                  {submitting ? 'Granting...' : 'Grant'}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Current Permissions Roster for the Selected Athlete */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#594139]">
              Active Care Team for {selectedAthleteObj?.name || selectedAthleteObj?.athlete_id || 'Athlete'} ({existingGrants.length})
            </h3>
            <span className="text-[11px] font-mono text-gray-500">Live Permissions</span>
          </div>

          <div className="overflow-x-auto border border-gray-200 rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50/80 border-b border-gray-200 text-[#594139] font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Professional</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Notes</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {grantsLoading ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-gray-400 font-mono">
                      Loading care team permissions...
                    </td>
                  </tr>
                ) : existingGrants.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-gray-400 font-mono">
                      No professionals currently assigned to this athlete.
                    </td>
                  </tr>
                ) : (
                  existingGrants.map((g) => (
                    <tr key={g.id} className="hover:bg-gray-50/60 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-[#141B2B]">
                        {g.professional?.full_name || 'Staff Member'}
                        <div className="text-[10px] text-gray-400 font-mono font-normal">
                          {g.professional?.email}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] uppercase">
                        {g.invited_role?.replace(/_/g, ' ')}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase ${
                            g.status === 'accepted'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {g.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-gray-500 text-[11px] italic max-w-xs truncate">
                        {g.notes || '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => handleRevoke(g.id, g.professional?.full_name || 'user')}
                          className="px-2.5 py-1 text-[11px] font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors"
                        >
                          Revoke Access
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminAthleteAccessCard;
