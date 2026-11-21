import React, { useState, useEffect } from 'react';
import { invitationsAPI } from '../services/api';

const AthleteAccessCard = ({ athleteId, isOwner }) => {
  const [invitations, setInvitations] = useState([]);
  const [professionals, setProfessionals] = useState([]);
  const [selectedProId, setSelectedProId] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ text: '', type: '' });

  useEffect(() => {
    if (athleteId) {
      loadData();
    }
  }, [athleteId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [invRes, proRes] = await Promise.all([
        invitationsAPI.getAthleteInvitations(athleteId),
        isOwner ? invitationsAPI.getProfessionals() : Promise.resolve({ data: [] }),
      ]);
      setInvitations(invRes.data || []);
      setProfessionals(proRes.data || []);
    } catch (err) {
      console.error('Failed to load access authorizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendInvite = async (e) => {
    e.preventDefault();
    if (!selectedProId) return;

    try {
      setActionLoading(true);
      setStatusMessage({ text: '', type: '' });
      await invitationsAPI.invite(athleteId, {
        professional_user_id: parseInt(selectedProId),
        notes: notes || undefined,
      });
      setStatusMessage({ text: 'Invitation sent successfully!', type: 'success' });
      setSelectedProId('');
      setNotes('');
      await loadData();
    } catch (err) {
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to send invitation',
        type: 'error',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevoke = async (invitationId, name) => {
    if (!confirm(`Are you sure you want to withdraw access for ${name}? They will immediately lose access to your profile and video telemetry.`)) {
      return;
    }

    try {
      setActionLoading(true);
      setStatusMessage({ text: '', type: '' });
      await invitationsAPI.revoke(athleteId, invitationId);
      setStatusMessage({ text: `Access revoked for ${name}.`, type: 'info' });
      await loadData();
    } catch (err) {
      setStatusMessage({
        text: err.response?.data?.detail || 'Failed to revoke access',
        type: 'error',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const activeConnections = invitations.filter((i) => i.status === 'accepted');
  const pendingInvitations = invitations.filter((i) => i.status === 'pending');
  const historyInvitations = invitations.filter((i) => ['rejected', 'revoked'].includes(i.status));

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-orange-50/40 via-white to-blue-50/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-[#FFDBCF] text-[#BD4006] text-lg">🛡️</span>
            <div>
              <h3 className="font-display font-bold text-lg text-[#141B2B]">
                Care Team & Access Permissions
              </h3>
              <p className="text-xs text-[#594139] mt-0.5">
                Invite coaches, physiotherapists, or sports scientists. You retain full control to withdraw access at any time.
              </p>
            </div>
          </div>
        </div>
        <span className="self-start sm:self-auto px-2.5 py-1 rounded-full bg-[#E9EDFF] text-[#141B2B] text-xs font-mono font-semibold">
          {activeConnections.length} Active Pro{activeConnections.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="p-6 space-y-6">
        {/* Status Alert */}
        {statusMessage.text && (
          <div
            className={`px-4 py-3 rounded-xl text-xs font-medium border flex items-center justify-between ${
              statusMessage.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : statusMessage.type === 'error'
                ? 'bg-rose-50 text-rose-800 border-rose-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}
          >
            <span>{statusMessage.text}</span>
            <button
              onClick={() => setStatusMessage({ text: '', type: '' })}
              className="text-gray-400 hover:text-gray-600 ml-3"
            >
              ✕
            </button>
          </div>
        )}

        {/* Invite Form (only shown if user is the athlete owner) */}
        {isOwner && (
          <form
            onSubmit={handleSendInvite}
            className="p-4 rounded-xl bg-[#F9F9FF] border border-gray-200/80 space-y-3"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[#141B2B]">
                Send Invite to Coach, Therapist, or Sports Scientist
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-[11px] font-mono text-[#594139] uppercase mb-1">
                  Select Professional
                </label>
                <select
                  required
                  value={selectedProId}
                  onChange={(e) => setSelectedProId(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#BD4006] focus:border-[#BD4006] outline-none"
                >
                  <option value="">-- Choose Coach or Physiotherapist --</option>
                  {professionals.map((pro) => (
                    <option key={pro.id} value={pro.id}>
                      {pro.full_name} ({pro.email}) — [{pro.role.replace(/_/g, ' ')}]
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#594139] uppercase mb-1">
                  Optional Note
                </label>
                <input
                  type="text"
                  placeholder="e.g. For rehab monitoring"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#BD4006] focus:border-[#BD4006] outline-none"
                />
              </div>
            </div>

            <div className="flex justify-end pt-1">
              <button
                type="submit"
                disabled={actionLoading || !selectedProId}
                className="btn-primary text-xs py-2 px-4 shadow-sm flex items-center gap-1.5 disabled:opacity-50"
              >
                <span>✉️</span>
                <span>{actionLoading ? 'Sending...' : 'Send Access Invitation'}</span>
              </button>
            </div>
          </form>
        )}

        {/* Current Care Team / Connections List */}
        <div className="space-y-4">
          <h4 className="text-xs font-mono uppercase text-[#594139] font-semibold tracking-wider">
            Connected Professionals & Access Status
          </h4>

          {loading ? (
            <div className="text-center py-6 text-xs text-gray-500">
              Loading permissions...
            </div>
          ) : invitations.length === 0 ? (
            <div className="text-center py-6 px-4 bg-gray-50 rounded-xl border border-dashed border-gray-200 text-xs text-gray-500">
              No care team invitations or connections yet. Use the invite form above to add your coach or physiotherapist.
            </div>
          ) : (
            <div className="divide-y divide-gray-100 border border-gray-100 rounded-xl overflow-hidden bg-white">
              {/* Active Connections */}
              {activeConnections.map((inv) => (
                <div
                  key={inv.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-emerald-50/20 hover:bg-emerald-50/40 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="p-2 rounded-lg bg-emerald-100 text-emerald-800 text-sm">
                      ✓
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-[#141B2B]">
                          {inv.professional?.full_name || 'Professional'}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-mono uppercase font-bold">
                          Active Access
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {inv.professional?.email} • {inv.invited_role?.replace(/_/g, ' ')}
                      </p>
                      {inv.notes && (
                        <p className="text-xs text-gray-400 italic mt-0.5">"{inv.notes}"</p>
                      )}
                    </div>
                  </div>

                  {isOwner && (
                    <button
                      onClick={() =>
                        handleRevoke(inv.id, inv.professional?.full_name || 'this professional')
                      }
                      disabled={actionLoading}
                      className="px-3 py-1.5 rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 text-xs font-semibold transition-colors flex items-center gap-1 self-start sm:self-auto"
                      title="Withdraw profile and video telemetry access"
                    >
                      <span>Withdraw Access</span>
                    </button>
                  )}
                </div>
              ))}

              {/* Pending Invitations */}
              {pendingInvitations.map((inv) => (
                <div
                  key={inv.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-amber-50/20 hover:bg-amber-50/40 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="p-2 rounded-lg bg-amber-100 text-amber-800 text-sm">
                      ⏳
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-[#141B2B]">
                          {inv.professional?.full_name || 'Professional'}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-mono uppercase font-bold">
                          Pending Response
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {inv.professional?.email} • {inv.invited_role?.replace(/_/g, ' ')}
                      </p>
                    </div>
                  </div>

                  {isOwner && (
                    <button
                      onClick={() =>
                        handleRevoke(inv.id, inv.professional?.full_name || 'this professional')
                      }
                      disabled={actionLoading}
                      className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 text-xs font-semibold transition-colors self-start sm:self-auto"
                    >
                      Cancel Invite
                    </button>
                  )}
                </div>
              ))}

              {/* History / Revoked / Declined */}
              {historyInvitations.map((inv) => (
                <div
                  key={inv.id}
                  className="p-4 flex items-center justify-between gap-3 bg-gray-50/60 opacity-70"
                >
                  <div className="flex items-center gap-3">
                    <span className="p-1.5 rounded-lg bg-gray-200 text-gray-600 text-xs">
                      ✕
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-xs text-[#141B2B]">
                          {inv.professional?.full_name || 'Professional'}
                        </span>
                        <span className="px-2 py-0.2 rounded-full bg-gray-200 text-gray-700 text-[9px] font-mono uppercase">
                          {inv.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-500">
                        {inv.professional?.email} ({inv.invited_role?.replace(/_/g, ' ')})
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AthleteAccessCard;
