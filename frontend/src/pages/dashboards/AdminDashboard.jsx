import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import {
  ShieldAlert,
  Users,
  ShieldCheck,
  Server,
  Film,
  Activity,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu,
  UserCheck,
  UserX,
  Search,
  ExternalLink,
  ChevronRight,
  Shield
} from 'lucide-react';

export const AdminDashboard = () => {
  const [adminSummary, setAdminSummary] = useState(null);
  const [usersList, setUsersList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [updatingUser, setUpdatingUser] = useState(null);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      setError('');
      const [sumRes, usersRes] = await Promise.all([
        api.get('/dashboard/admin-summary'),
        api.get('/users/?limit=50')
      ]);
      setAdminSummary(sumRes.data);
      setUsersList(usersRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load administrative governance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    try {
      setUpdatingUser(userId);
      await api.post(`/users/${userId}/role?role=${newRole}`);
      await fetchAdminData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user role');
    } finally {
      setUpdatingUser(null);
    }
  };

  const handleStatusToggle = async (userId, currentActive) => {
    try {
      setUpdatingUser(userId);
      await api.post(`/users/${userId}/status?is_active=${!currentActive}`);
      await fetchAdminData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user status');
    } finally {
      setUpdatingUser(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-3 border-rose-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Querying platform governance telemetry & system health...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4 text-center">
        <div className="bg-red-50 text-red-700 p-4 rounded-2xl border border-red-200 text-xs font-medium mb-3">
          {error}
        </div>
        <button
          onClick={fetchAdminData}
          className="bg-rose-600 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:bg-rose-700 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!adminSummary) return null;

  const {
    total_users,
    active_users,
    inactive_users,
    roles_breakdown,
    total_athletes,
    total_videos,
    videos_breakdown,
    total_assignments,
    system_health
  } = adminSummary;

  const filteredUsers = usersList.filter(u => {
    const q = search.toLowerCase();
    return (
      (u.full_name && u.full_name.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q)) ||
      (u.role && u.role.toLowerCase().includes(q))
    );
  });

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-700 flex items-center justify-center">
              <ShieldAlert size={18} />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">System Administration & Governance</h1>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border bg-rose-50 text-rose-700 border-rose-200">
              Root Administrator
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Platform user access control, computer vision engine status, and database telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/profile"
            className="bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition"
          >
            <Shield size={14} /> Full Governance Console
          </Link>
        </div>
      </div>

      {/* 4 Governance Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Users */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Platform Users</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Users size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{total_users}</div>
            <span className="text-[11px] text-emerald-600 font-semibold block mt-1">
              {active_users} active &bull; {inactive_users} inactive
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Across 5 distinct system roles</span>
        </div>

        {/* Athlete Profiles */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Athlete Profiles</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Activity size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-indigo-700">{total_athletes}</div>
            <span className="text-[11px] text-indigo-600 font-semibold block mt-1">
              {total_assignments} staff assignments
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Biometric physical records</span>
        </div>

        {/* Video Processed */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Video Pipeline</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <Film size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-slate-900">{total_videos}</div>
            <span className="text-[11px] text-purple-600 font-semibold block mt-1">
              {videos_breakdown?.completed || 0} completed &bull; {videos_breakdown?.processing || 0} in progress
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Pose tracking kinematics</span>
        </div>

        {/* Database Health */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Database Latency</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Server size={16} />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-black text-emerald-600">{system_health.db_latency_ms} ms</div>
            <span className="text-[11px] text-emerald-700 font-semibold block mt-1">
              {system_health.database}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Local persistent volume</span>
        </div>
      </div>

      {/* Row 2: Role Distribution & System Infrastructure Monitoring */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Role Distribution */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Users size={16} className="text-rose-600" />
            <span>Role Allocation Breakdown</span>
          </h2>
          <p className="text-xs text-slate-500">
            Current user distribution across institutional access levels.
          </p>

          <div className="space-y-2.5 pt-2 text-xs">
            {Object.entries(roles_breakdown || {}).map(([r, count]) => {
              const pct = Math.round((count / (total_users || 1)) * 100);
              return (
                <div key={r} className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="capitalize font-semibold text-slate-800">{r.replace('_', ' ')}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[11px]">{pct}%</span>
                    <span className="font-bold text-slate-900 bg-white px-2 py-0.5 rounded-lg border border-slate-200">
                      {count}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Infrastructure Telemetry */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs lg:col-span-2 space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Cpu size={16} className="text-rose-600" />
            <span>Platform Infrastructure & Subsystem Status</span>
          </h2>
          <p className="text-xs text-slate-500">
            Operational telemetry for biomechanics compute worker, PostgreSQL database, and auth security.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 text-xs">
            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                <Database size={16} />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Primary Database</span>
                <strong className="text-slate-900 font-bold block mt-0.5">{system_health.database}</strong>
                <span className="text-[11px] text-emerald-600 font-medium">Latency: {system_health.db_latency_ms} ms &bull; Connection Pool Active</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                <Cpu size={16} />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Computer Vision Pose Engine</span>
                <strong className="text-slate-900 font-bold block mt-0.5">{system_health.cv_engine}</strong>
                <span className="text-[11px] text-blue-600 font-medium">Bilateral Asymmetry & Joint Flexion Tracking</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                <ShieldCheck size={16} />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Injury Risk Model</span>
                <strong className="text-slate-900 font-bold block mt-0.5">{system_health.risk_engine}</strong>
                <span className="text-[11px] text-indigo-600 font-medium">Evidence-Based Clinical Movement Thresholds</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                <Server size={16} />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Storage & Authentication</span>
                <strong className="text-slate-900 font-bold block mt-0.5">{system_health.auth_service}</strong>
                <span className="text-[11px] text-purple-600 font-medium">{system_health.storage_status}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: User & Role Governance Console */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/40">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users size={18} className="text-rose-600" />
              <span>User Governance & Access Management</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Directly assign roles, revoke permissions, and modify user activity status.
            </p>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search user by name or email..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs bg-white outline-none focus:ring-2 focus:ring-rose-100 focus:border-rose-600 w-60"
            />
          </div>
        </div>

        {filteredUsers.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Users size={32} className="mx-auto mb-2 opacity-40" />
            <p className="font-semibold text-slate-700 text-sm">No users found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold uppercase text-[10px] tracking-wider bg-slate-50/70">
                  <th className="py-3 px-5">User</th>
                  <th className="py-3 px-4">Current Role</th>
                  <th className="py-3 px-4">Account Status</th>
                  <th className="py-3 px-4">Change Role</th>
                  <th className="py-3 px-5 text-right">Access Control</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.map(u => {
                  return (
                    <tr key={u.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-5">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-xs shrink-0">
                            {u.full_name ? u.full_name[0] : u.email[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900">{u.full_name || 'Named User'}</div>
                            <div className="text-[11px] text-slate-400">{u.email}</div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="capitalize font-semibold text-slate-800 bg-slate-100 px-2 py-0.5 rounded-md text-[11px]">
                          {u.role.replace('_', ' ')}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          u.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                          {u.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <select
                          value={u.role}
                          disabled={updatingUser === u.id}
                          onChange={e => handleRoleChange(u.id, e.target.value)}
                          className="border border-slate-200 rounded-lg p-1 text-xs bg-white outline-none focus:ring-2 focus:ring-rose-100 font-medium"
                        >
                          <option value="athlete">Athlete</option>
                          <option value="coach">Coach</option>
                          <option value="physiotherapist">Physiotherapist</option>
                          <option value="sports_scientist">Sports Scientist</option>
                          <option value="administrator">Administrator</option>
                        </select>
                      </td>

                      <td className="py-3.5 px-5 text-right">
                        <button
                          onClick={() => handleStatusToggle(u.id, u.is_active)}
                          disabled={updatingUser === u.id}
                          className={`text-xs font-semibold px-2.5 py-1.5 rounded-lg border transition ${
                            u.is_active
                              ? 'border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200'
                              : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
