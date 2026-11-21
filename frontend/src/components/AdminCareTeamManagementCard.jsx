import React, { useState, useEffect } from 'react';
import { usersAPI } from '../services/api';

const AdminCareTeamManagementCard = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'coach',
  });
  const [message, setMessage] = useState({ text: '', type: '' });

  const loadUsers = async () => {
    try {
      setLoading(true);
      const res = await usersAPI.getAll({ limit: 100 });
      setUsers(res.data || []);
    } catch (err) {
      console.error('Failed to load users for admin:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password || !form.full_name) {
      setMessage({ text: 'Please fill in all required fields.', type: 'error' });
      return;
    }
    try {
      setCreating(true);
      setMessage({ text: '', type: '' });
      await usersAPI.create(form);
      setMessage({
        text: `Successfully provisioned ${form.full_name} as ${form.role.replace(/_/g, ' ')}!`,
        type: 'success',
      });
      setForm({
        full_name: '',
        email: '',
        password: '',
        role: 'coach',
      });
      await loadUsers();
    } catch (err) {
      setMessage({
        text: err.response?.data?.detail || 'Failed to create user account.',
        type: 'error',
      });
    } finally {
      setCreating(false);
    }
  };

  const roleBadge = (role) => {
    const map = {
      athlete: 'bg-blue-100 text-blue-800 border-blue-200',
      coach: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      physiotherapist: 'bg-purple-100 text-purple-800 border-purple-200',
      sports_scientist: 'bg-cyan-100 text-cyan-800 border-cyan-200',
      administrator: 'bg-orange-100 text-orange-800 border-orange-200',
    };
    return (
      <span
        className={`px-2 py-0.5 rounded-full text-[11px] font-mono uppercase font-semibold border ${
          map[role] || 'bg-gray-100 text-gray-700 border-gray-200'
        }`}
      >
        {role?.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-orange-50/50 to-transparent">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#BD4006] text-white flex items-center justify-center font-bold text-lg shadow-sm">
            🛡️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-lg font-bold text-[#141B2B]">
                Care Team Users Management
              </h2>
              <span className="px-2 py-0.5 rounded bg-orange-100 text-[#BD4006] text-[10px] font-mono font-bold uppercase tracking-wider">
                Admin Oversight
              </span>
            </div>
            <p className="text-xs text-[#594139] mt-0.5">
              Provision and manage specialized clinical roles (Coaches, Physiotherapists, Sports Scientists) with audit logging.
            </p>
          </div>
        </div>
        <button
          onClick={loadUsers}
          disabled={loading}
          className="text-xs text-[#BD4006] hover:underline font-semibold flex items-center gap-1 self-start sm:self-auto"
        >
          🔄 Refresh Users
        </button>
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Status Message */}
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

        {/* Creation Form */}
        <div className="bg-[#F9F9FF] p-4 sm:p-5 rounded-xl border border-gray-200/70">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#BD4006] mb-3 flex items-center gap-1.5">
            <span>➕</span> Provision New Role Account
          </h3>
          <form onSubmit={handleCreateUser} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Dr. Jordan Hayes"
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Email Address *
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="physio@athletics.org"
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Password *
              </label>
              <input
                type="password"
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••"
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono uppercase text-[#594139] font-medium mb-1">
                Account Role *
              </label>
              <div className="flex gap-2">
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#BD4006] bg-white font-medium"
                >
                  <option value="coach">Coach</option>
                  <option value="physiotherapist">Physiotherapist</option>
                  <option value="sports_scientist">Sports Scientist</option>
                  <option value="administrator">Administrator</option>
                </select>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-[#BD4006] hover:bg-[#A33605] text-white text-xs font-bold rounded-lg transition-colors whitespace-nowrap shadow-sm disabled:opacity-50"
                >
                  {creating ? 'Saving...' : 'Create'}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* User Roster Table */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#594139]">
              Registered System Accounts ({users.length})
            </h3>
            <span className="text-[11px] font-mono text-gray-500">Security Audit Trail Active</span>
          </div>

          <div className="overflow-x-auto border border-gray-200 rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50/80 border-b border-gray-200 text-[#594139] font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Email</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-gray-400 font-mono">
                      Loading user accounts...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-gray-400 font-mono">
                      No accounts registered.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50/60 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-[#141B2B]">
                        {u.full_name}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-gray-600">
                        {u.email}
                      </td>
                      <td className="py-2.5 px-3">
                        {roleBadge(u.role)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 text-[11px] font-mono ${
                            u.is_active ? 'text-emerald-700' : 'text-gray-400'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              u.is_active ? 'bg-emerald-500' : 'bg-gray-300'
                            }`}
                          />
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-gray-400 text-[11px]">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
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

export default AdminCareTeamManagementCard;
