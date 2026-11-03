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
  Database,
  Cpu,
  Search,
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
      <div className="max-w-6xl mx-auto py-24 px-4 text-center">
        <div className="w-10 h-10 border-3 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-300 font-medium">Querying platform governance telemetry & system health...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4 text-center">
        <div className="bg-rose-500/10 text-rose-300 p-5 rounded-2xl border border-rose-500/30 text-sm font-medium mb-4">
          {error}
        </div>
        <button
          onClick={fetchAdminData}
          className="bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-rose-600/25"
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
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 p-6 sm:p-7 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 shadow-xl">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-300 flex items-center justify-center shadow-sm">
              <ShieldAlert size={20} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">System Administration</h1>
            <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border bg-rose-500/15 text-rose-300 border-rose-500/30">
              Root Administrator
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Platform user access control, computer vision engine status, and database telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/athletes"
            className="bg-[#1a1b28] hover:bg-[#232435] text-slate-200 border border-white/10 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
          >
            <Users size={16} className="text-rose-400" /> Assign Coaches &amp; Staff
          </Link>
          <Link
            to="/profile"
            className="bg-[#1c1d2e] border border-white/10 hover:bg-[#25263a] text-slate-200 font-semibold text-xs sm:text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition"
          >
            <Shield size={16} className="text-slate-400" /> My Profile
          </Link>
        </div>
      </div>

      {/* 4 Governance Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Total Users */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Platform Users</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400 flex items-center justify-center">
              <Users size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-white">{total_users}</div>
            <span className="text-xs text-emerald-400 font-semibold block mt-1.5">
              {active_users} active &bull; {inactive_users} inactive
            </span>
          </div>
          <span className="text-xs text-slate-400">Across 5 distinct system roles</span>
        </div>

        {/* Athlete Profiles */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Athlete Profiles</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center">
              <Activity size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-indigo-400">{total_athletes}</div>
            <span className="text-xs text-indigo-300 font-medium block mt-1.5">
              {total_assignments} staff assignments
            </span>
          </div>
          <span className="text-xs text-slate-400">Physical screening profiles</span>
        </div>

        {/* Video Processed */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Video Pipeline</span>
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center">
              <Film size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-purple-400">{total_videos}</div>
            <span className="text-xs text-purple-300 font-medium block mt-1.5">
              {videos_breakdown?.completed || 0} completed &bull; {videos_breakdown?.processing || 0} processing
            </span>
          </div>
          <span className="text-xs text-slate-400">Pose tracking kinematics</span>
        </div>

        {/* Database Health */}
        <div className="bg-[#11121a] p-6 rounded-2xl border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">Database Latency</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <Server size={18} />
            </div>
          </div>
          <div className="my-3">
            <div className="text-3xl sm:text-4xl font-extrabold text-emerald-400">{system_health.db_latency_ms} ms</div>
            <span className="text-xs text-emerald-300 font-medium block mt-1.5">
              {system_health.database}
            </span>
          </div>
          <span className="text-xs text-slate-400">PostgreSQL Connection Pool</span>
        </div>
      </div>

      {/* Row 2: Role Distribution & System Infrastructure Monitoring */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Role Distribution */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl space-y-4">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
            <Users size={18} className="text-rose-400" />
            <span>Role Allocation Breakdown</span>
          </h2>
          <p className="text-xs text-slate-400">
            Current user distribution across institutional access levels.
          </p>

          <div className="space-y-2.5 pt-2 text-xs">
            {Object.entries(roles_breakdown || {}).map(([r, count]) => {
              const pct = Math.round((count / (total_users || 1)) * 100);
              return (
                <div key={r} className="p-3 bg-[#161724] rounded-xl border border-white/5 flex items-center justify-between">
                  <span className="capitalize font-semibold text-slate-200">{r.replace('_', ' ')}</span>
                  <div className="flex items-center gap-2.5">
                    <span className="text-slate-400 font-mono text-xs">{pct}%</span>
                    <span className="font-bold text-white bg-[#1e1f2f] px-2.5 py-0.5 rounded-lg border border-white/10">
                      {count}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Infrastructure Telemetry */}
        <div className="bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl lg:col-span-2 space-y-4">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
            <Cpu size={18} className="text-rose-400" />
            <span>Platform Infrastructure &amp; Subsystems</span>
          </h2>
          <p className="text-xs text-slate-400">
            Operational telemetry for biomechanics compute worker, database, and auth security.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 text-xs">
            <div className="p-4 rounded-xl border border-white/10 bg-[#161724] flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                <Database size={16} />
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block uppercase">Primary Database</span>
                <strong className="text-white font-bold block mt-0.5">{system_health.database}</strong>
                <span className="text-xs text-emerald-400 font-medium">Latency: {system_health.db_latency_ms} ms &bull; Connection Pool Active</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-white/10 bg-[#161724] flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400 flex items-center justify-center shrink-0">
                <Cpu size={16} />
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block uppercase">Computer Vision Pose Engine</span>
                <strong className="text-white font-bold block mt-0.5">{system_health.cv_engine}</strong>
                <span className="text-xs text-blue-400 font-medium">Bilateral Asymmetry &amp; Joint Flexion Tracking</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-white/10 bg-[#161724] flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shrink-0">
                <ShieldCheck size={16} />
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block uppercase">Injury Risk Model</span>
                <strong className="text-white font-bold block mt-0.5">{system_health.risk_engine}</strong>
                <span className="text-xs text-indigo-400 font-medium">Documented Weighted Risk Model (Page 6)</span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-white/10 bg-[#161724] flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400 flex items-center justify-center shrink-0">
                <Server size={16} />
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 block uppercase">Storage &amp; Authentication</span>
                <strong className="text-white font-bold block mt-0.5">{system_health.auth_service}</strong>
                <span className="text-xs text-purple-400 font-medium">{system_health.storage_status}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: User & Role Governance Console */}
      <div className="bg-[#11121a] rounded-2xl border border-white/10 shadow-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#141522]">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
              <Users size={20} className="text-rose-400" />
              <span>User Governance &amp; Access Management</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Directly assign roles, manage permissions, and update user account statuses.
            </p>
          </div>

          <div className="relative">
            <Search size={15} className="absolute left-3.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search user by name or email..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-rose-500 w-64"
            />
          </div>
        </div>

        {filteredUsers.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs sm:text-sm">
            <Users size={36} className="mx-auto mb-3 opacity-30 text-rose-400" />
            <p className="font-semibold text-white text-base">No users found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 font-semibold uppercase text-xs tracking-wider bg-[#171826]">
                  <th className="py-3.5 px-6">User</th>
                  <th className="py-3.5 px-4">Current Role</th>
                  <th className="py-3.5 px-4">Account Status</th>
                  <th className="py-3.5 px-4">Change Role</th>
                  <th className="py-3.5 px-6 text-right">Access Control</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {filteredUsers.map(u => {
                  return (
                    <tr key={u.id} className="hover:bg-white/5 transition">
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-slate-800 text-slate-300 font-bold flex items-center justify-center text-sm shrink-0 border border-white/10">
                            {u.full_name ? u.full_name[0] : u.email[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-white text-sm sm:text-base">{u.full_name || 'User'}</div>
                            <div className="text-xs text-slate-400">{u.email}</div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4">
                        <span className="capitalize font-semibold text-slate-200 bg-[#1e1f2f] px-2.5 py-1 rounded-lg border border-white/10 text-xs">
                          {u.role.replace('_', ' ')}
                        </span>
                      </td>

                      <td className="py-4 px-4">
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full inline-flex items-center gap-1.5 ${
                          u.is_active ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                          {u.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </td>

                      <td className="py-4 px-4">
                        <select
                          value={u.role}
                          disabled={updatingUser === u.id}
                          onChange={e => handleRoleChange(u.id, e.target.value)}
                          className="border border-white/10 rounded-xl px-2.5 py-1 text-xs bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-rose-500 font-medium"
                        >
                          <option value="athlete">Athlete</option>
                          <option value="coach">Coach</option>
                          <option value="physiotherapist">Physiotherapist</option>
                          <option value="sports_scientist">Sports Scientist</option>
                          <option value="administrator">Administrator</option>
                        </select>
                      </td>

                      <td className="py-4 px-6 text-right">
                        <button
                          onClick={() => handleStatusToggle(u.id, u.is_active)}
                          disabled={updatingUser === u.id}
                          className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition ${
                            u.is_active
                              ? 'border-white/10 text-slate-400 hover:bg-rose-500/15 hover:text-rose-300 hover:border-rose-500/30'
                              : 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-600 hover:text-white'
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

export default AdminDashboard;
