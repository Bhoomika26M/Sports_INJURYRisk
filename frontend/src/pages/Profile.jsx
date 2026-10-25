import { useState, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  User as UserIcon,
  Shield,
  Key,
  Save,
  CheckCircle,
  AlertCircle,
  Activity,
  Award,
  Stethoscope,
  Microscope,
  ShieldAlert,
  Users
} from 'lucide-react';

const ROLE_INFO = {
  athlete: {
    label: 'Athlete',
    icon: Activity,
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    description: 'Upload movement trials, track personal symmetry, and review corrective training recommendations.'
  },
  coach: {
    label: 'Coach',
    icon: Award,
    badge: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    description: 'Monitor roster biomechanics, team risk scores, and movement readiness indices for assigned athletes.'
  },
  physiotherapist: {
    label: 'Physiotherapist',
    icon: Stethoscope,
    badge: 'bg-teal-50 text-teal-700 border-teal-200',
    description: 'Analyze clinical movement anomalies, joint kinematic deviations, and track rehabilitation milestones.'
  },
  sports_scientist: {
    label: 'Sports Scientist',
    icon: Microscope,
    badge: 'bg-purple-50 text-purple-700 border-purple-200',
    description: 'Investigate bilateral symmetry, angular velocity variables, and kinetic biomechanical telemetry.'
  },
  administrator: {
    label: 'Administrator',
    icon: ShieldAlert,
    badge: 'bg-rose-50 text-rose-700 border-rose-200',
    description: 'System governance, user role administration, staff-athlete matching, and platform audit logs.'
  }
};

export const Profile = () => {
  const { user, updateProfile, changePassword } = useAuth();
  const [activeTab, setActiveTab] = useState('account');

  // Account details form
  const [accountForm, setAccountForm] = useState({
    full_name: '',
    bio: '',
    phone_number: '',
    organization: '',
    specialization: ''
  });
  const [accountSuccess, setAccountSuccess] = useState('');
  const [accountError, setAccountError] = useState('');
  const [accountSaving, setAccountSaving] = useState(false);

  // Password change form
  const [pwdForm, setPwdForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [pwdSuccess, setPwdSuccess] = useState('');
  const [pwdError, setPwdError] = useState('');
  const [pwdSaving, setPwdSaving] = useState(false);

  // Athlete physical profile (for athlete role)
  const [athleteProfile, setAthleteProfile] = useState({
    sport_type: '',
    position: '',
    age: '',
    height_cm: '',
    weight_kg: '',
    injury_history: '',
    training_load: 'Medium',
    coach_id: '',
    physiotherapist_id: ''
  });
  const [availableStaff, setAvailableStaff] = useState({ coaches: [], physiotherapists: [] });
  const [athleteExists, setAthleteExists] = useState(false);
  const [athleteSuccess, setAthleteSuccess] = useState('');
  const [athleteError, setAthleteError] = useState('');
  const [athleteSaving, setAthleteSaving] = useState(false);

  // Admin user directory
  const [usersList, setUsersList] = useState([]);
  const [adminSearch, setAdminSearch] = useState('');
  const [adminRoleFilter, setAdminRoleFilter] = useState('');
  const [adminLoading, setAdminLoading] = useState(false);

  const fetchAthleteProfile = async () => {
    try {
      const res = await api.get('/athletes/me');
      if (res.data) {
        const injuries = res.data.injury_history?.map(i => i.description || i.type || '').filter(Boolean).join(', ') || '';
        const load = res.data.training_load?.intensity || 'Medium';
        setAthleteProfile({
          sport_type: res.data.sport_type || '',
          position: res.data.position || '',
          age: res.data.age || '',
          height_cm: res.data.height_cm || '',
          weight_kg: res.data.weight_kg || '',
          injury_history: injuries,
          training_load: load,
          coach_id: res.data.coach?.id ? String(res.data.coach.id) : '',
          physiotherapist_id: res.data.physiotherapist?.id ? String(res.data.physiotherapist.id) : ''
        });
        setAthleteExists(true);
      }
    } catch (_err) {
      // Profile might not exist yet
    }
  };

  const fetchStaff = async () => {
    try {
      const res = await api.get('/users/staff');
      setAvailableStaff(res.data);
    } catch (_err) {
      // ignore
    }
  };

  const fetchUsers = async () => {
    try {
      setAdminLoading(true);
      let url = '/users/?limit=100';
      if (adminRoleFilter) url += `&role=${adminRoleFilter}`;
      if (adminSearch) url += `&search=${encodeURIComponent(adminSearch)}`;
      const res = await api.get(url);
      setUsersList(res.data);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      setAccountForm({
        full_name: user.full_name || '',
        bio: user.bio || '',
        phone_number: user.phone_number || '',
        organization: user.organization || '',
        specialization: user.specialization || ''
      });

      if (user.role === 'athlete') {
        fetchAthleteProfile();
        fetchStaff();
      }

      if (user.role === 'administrator') {
        fetchUsers();
      }
    }
  }, [user]);

  const handleAccountSubmit = async (e) => {
    e.preventDefault();
    try {
      setAccountSaving(true);
      setAccountError('');
      setAccountSuccess('');
      await updateProfile(accountForm);
      setAccountSuccess('Profile updated successfully!');
    } catch (err) {
      setAccountError(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setAccountSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (pwdForm.new_password !== pwdForm.confirm_password) {
      return setPwdError('New passwords do not match');
    }
    if (pwdForm.new_password.length < 6) {
      return setPwdError('Password must be at least 6 characters long');
    }
    try {
      setPwdSaving(true);
      setPwdError('');
      setPwdSuccess('');
      await changePassword(pwdForm.current_password, pwdForm.new_password);
      setPwdSuccess('Password changed successfully!');
      setPwdForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      setPwdError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setPwdSaving(false);
    }
  };

  const handleAthleteSubmit = async (e) => {
    e.preventDefault();
    setAthleteSuccess('');
    setAthleteError('');
    setAthleteSaving(true);

    const injuriesArray = athleteProfile.injury_history
      ? athleteProfile.injury_history.split(',').map(i => ({ description: i.trim() })).filter(i => i.description)
      : [];

    const payload = {
      sport_type: athleteProfile.sport_type,
      position: athleteProfile.position,
      age: athleteProfile.age ? parseInt(athleteProfile.age, 10) : null,
      height_cm: athleteProfile.height_cm ? parseFloat(athleteProfile.height_cm) : null,
      weight_kg: athleteProfile.weight_kg ? parseFloat(athleteProfile.weight_kg) : null,
      injury_history: injuriesArray,
      training_load: { intensity: athleteProfile.training_load },
      coach_id: athleteProfile.coach_id ? parseInt(athleteProfile.coach_id, 10) : null,
      physiotherapist_id: athleteProfile.physiotherapist_id ? parseInt(athleteProfile.physiotherapist_id, 10) : null,
    };

    try {
      if (athleteExists) {
        await api.put('/athletes/me', payload);
        setAthleteSuccess('Physical metrics updated successfully!');
      } else {
        await api.post('/athletes/me', payload);
        setAthleteExists(true);
        setAthleteSuccess('Physical profile initialized successfully!');
      }
    } catch (err) {
      setAthleteError(err.response?.data?.detail || 'Failed to save athlete metrics');
    } finally {
      setAthleteSaving(false);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await api.put(`/users/${userId}/role`, { role: newRole });
      fetchUsers();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user role');
    }
  };

  const handleToggleStatus = async (userId, currentStatus) => {
    try {
      const targetUser = usersList.find(u => u.id === userId);
      await api.put(`/users/${userId}/role`, { role: targetUser.role, is_active: !currentStatus });
      fetchUsers();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update user status');
    }
  };

  const currentRoleMeta = ROLE_INFO[user?.role] || ROLE_INFO.athlete;
  const RoleIcon = currentRoleMeta.icon;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 sm:px-6 space-y-6">
      {/* Profile Header */}
      <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 font-black text-xl border border-blue-200">
            {user?.full_name ? user.full_name[0].toUpperCase() : user?.email[0].toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">{user?.full_name || 'My Account'}</h1>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border flex items-center gap-1 ${currentRoleMeta.badge}`}>
                <RoleIcon size={12} /> {currentRoleMeta.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{user?.email}</p>
            {user?.organization && (
              <p className="text-[11px] text-slate-400 font-medium">{user.organization}</p>
            )}
          </div>
        </div>

        <div className="text-right text-xs text-slate-400 hidden sm:block">
          <div>Member since: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</div>
          <div>Account ID: #{user?.id}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('account')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
            activeTab === 'account' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <UserIcon size={14} /> Personal Details
        </button>

        {user?.role === 'athlete' && (
          <button
            onClick={() => setActiveTab('athlete')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'athlete' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Activity size={14} /> Athlete Physical Profile
          </button>
        )}

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
            activeTab === 'security' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Key size={14} /> Security
        </button>

        <button
          onClick={() => setActiveTab('roles')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
            activeTab === 'roles' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Shield size={14} /> Permissions Matrix
        </button>

        {user?.role === 'administrator' && (
          <button
            onClick={() => setActiveTab('admin')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'admin' ? 'bg-rose-600 text-white shadow-xs' : 'text-rose-700 bg-rose-50 hover:bg-rose-100'
            }`}
          >
            <Users size={14} /> User Governance
          </button>
        )}
      </div>

      {/* Tab 1: Account Details */}
      {activeTab === 'account' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6">
          <h2 className="text-base font-bold text-slate-900 mb-1">Account Information</h2>
          <p className="text-xs text-slate-500 mb-5">Manage your contact details and professional identity</p>

          {accountSuccess && (
            <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 p-3 rounded-xl mb-4 text-xs border border-emerald-200">
              <CheckCircle size={16} /> {accountSuccess}
            </div>
          )}
          {accountError && (
            <div className="flex items-center gap-2 bg-red-50 text-red-700 p-3 rounded-xl mb-4 text-xs border border-red-200">
              <AlertCircle size={16} /> {accountError}
            </div>
          )}

          <form onSubmit={handleAccountSubmit} className="space-y-4 max-w-xl">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={accountForm.full_name}
                  onChange={e => setAccountForm({ ...accountForm, full_name: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="w-full p-2.5 border border-slate-200 rounded-xl bg-slate-50 text-slate-400 text-xs cursor-not-allowed"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Organization / Club</label>
                <input
                  type="text"
                  placeholder="e.g. National Athletics Federation"
                  value={accountForm.organization}
                  onChange={e => setAccountForm({ ...accountForm, organization: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number</label>
                <input
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  value={accountForm.phone_number}
                  onChange={e => setAccountForm({ ...accountForm, phone_number: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Specialization / Focus Area</label>
              <input
                type="text"
                placeholder="e.g. Lower Extremity Biomechanics & ACL Prevention"
                value={accountForm.specialization}
                onChange={e => setAccountForm({ ...accountForm, specialization: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Professional Bio</label>
              <textarea
                rows={3}
                placeholder="Summary of experience, sports background, or clinical focus..."
                value={accountForm.bio}
                onChange={e => setAccountForm({ ...accountForm, bio: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={accountSaving}
              className="flex items-center gap-1.5 bg-blue-600 text-white font-semibold py-2 px-4 rounded-xl hover:bg-blue-700 transition shadow-xs disabled:opacity-50 text-xs"
            >
              <Save size={14} />
              {accountSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Athlete Biomechanical Profile */}
      {activeTab === 'athlete' && user?.role === 'athlete' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6">
          <h2 className="text-base font-bold text-slate-900 mb-1">Athlete Physical Profile</h2>
          <p className="text-xs text-slate-500 mb-5">Biometric and physical attributes used by the injury risk engine</p>

          {athleteSuccess && (
            <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 p-3 rounded-xl mb-4 text-xs border border-emerald-200">
              <CheckCircle size={16} /> {athleteSuccess}
            </div>
          )}
          {athleteError && (
            <div className="flex items-center gap-2 bg-red-50 text-red-700 p-3 rounded-xl mb-4 text-xs border border-red-200">
              <AlertCircle size={16} /> {athleteError}
            </div>
          )}

          <form onSubmit={handleAthleteSubmit} className="space-y-4 max-w-xl">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Primary Sport</label>
                <input
                  type="text"
                  placeholder="e.g. Football / Soccer"
                  value={athleteProfile.sport_type}
                  onChange={e => setAthleteProfile({ ...athleteProfile, sport_type: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Position / Discipline</label>
                <input
                  type="text"
                  placeholder="e.g. Striker / Forward"
                  value={athleteProfile.position}
                  onChange={e => setAthleteProfile({ ...athleteProfile, position: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Age (Years)</label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  placeholder="24"
                  value={athleteProfile.age}
                  onChange={e => setAthleteProfile({ ...athleteProfile, age: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Height (cm)</label>
                <input
                  type="number"
                  step="0.5"
                  placeholder="182"
                  value={athleteProfile.height_cm}
                  onChange={e => setAthleteProfile({ ...athleteProfile, height_cm: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="76.5"
                  value={athleteProfile.weight_kg}
                  onChange={e => setAthleteProfile({ ...athleteProfile, weight_kg: e.target.value })}
                  className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Current Training Load</label>
              <select
                value={athleteProfile.training_load}
                onChange={e => setAthleteProfile({ ...athleteProfile, training_load: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs bg-white"
              >
                <option value="Low">Low (Maintenance / Active Recovery)</option>
                <option value="Medium">Medium (Regular In-Season Training)</option>
                <option value="High">High (Intense Pre-Season / High Match Load)</option>
                <option value="Exhaustive">Exhaustive (Tournament Overload)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Past Injury History</label>
              <textarea
                rows={2}
                placeholder="Comma-separated: Right Ankle Sprain (2024), Left Knee Strain (2025)..."
                value={athleteProfile.injury_history}
                onChange={e => setAthleteProfile({ ...athleteProfile, injury_history: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
              />
            </div>

            <div className="pt-3 border-t border-slate-100">
              <span className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-2.5">
                Assigned Coaching & Medical Staff
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Head Coach</label>
                  <select
                    value={athleteProfile.coach_id || ''}
                    onChange={e => setAthleteProfile({ ...athleteProfile, coach_id: e.target.value })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs bg-white"
                  >
                    <option value="">-- No Coach Assigned --</option>
                    {availableStaff.coaches?.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.full_name} ({c.email}){c.organization ? ` &bull; ${c.organization}` : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Physiotherapist</label>
                  <select
                    value={athleteProfile.physiotherapist_id || ''}
                    onChange={e => setAthleteProfile({ ...athleteProfile, physiotherapist_id: e.target.value })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs bg-white"
                  >
                    <option value="">-- No Physiotherapist Assigned --</option>
                    {availableStaff.physiotherapists?.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.full_name} ({p.email}){p.specialization ? ` &bull; ${p.specialization}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={athleteSaving}
              className="flex items-center gap-1.5 bg-blue-600 text-white font-semibold py-2 px-4 rounded-xl hover:bg-blue-700 transition shadow-xs disabled:opacity-50 text-xs"
            >
              <Save size={14} />
              {athleteSaving ? 'Saving...' : athleteExists ? 'Update Metrics' : 'Create Profile'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 3: Security & Password */}
      {activeTab === 'security' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6">
          <h2 className="text-base font-bold text-slate-900 mb-1">Security & Authentication</h2>
          <p className="text-xs text-slate-500 mb-5">Change password to protect your biometric account</p>

          {pwdSuccess && (
            <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 p-3 rounded-xl mb-4 text-xs border border-emerald-200">
              <CheckCircle size={16} /> {pwdSuccess}
            </div>
          )}
          {pwdError && (
            <div className="flex items-center gap-2 bg-red-50 text-red-700 p-3 rounded-xl mb-4 text-xs border border-red-200">
              <AlertCircle size={16} /> {pwdError}
            </div>
          )}

          <form onSubmit={handlePasswordSubmit} className="space-y-3.5 max-w-sm">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Current Password</label>
              <input
                type="password"
                value={pwdForm.current_password}
                onChange={e => setPwdForm({ ...pwdForm, current_password: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">New Password</label>
              <input
                type="password"
                value={pwdForm.new_password}
                onChange={e => setPwdForm({ ...pwdForm, new_password: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm New Password</label>
              <input
                type="password"
                value={pwdForm.confirm_password}
                onChange={e => setPwdForm({ ...pwdForm, confirm_password: e.target.value })}
                className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-600 outline-none text-xs"
                required
              />
            </div>

            <button
              type="submit"
              disabled={pwdSaving}
              className="flex items-center gap-1.5 bg-blue-600 text-white font-semibold py-2 px-4 rounded-xl hover:bg-blue-700 transition shadow-xs disabled:opacity-50 text-xs"
            >
              <Key size={14} />
              {pwdSaving ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      )}

      {/* Tab 4: Roles & Permissions Matrix */}
      {activeTab === 'roles' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6 space-y-5">
          <div>
            <h2 className="text-base font-bold text-slate-900 mb-0.5">Role-Based Access Control (RBAC) Matrix</h2>
            <p className="text-xs text-slate-500">Security tiers and role privileges across the platform</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(ROLE_INFO).map(([key, info]) => {
              const Icon = info.icon;
              const isMyRole = user?.role === key;
              return (
                <div
                  key={key}
                  className={`p-4 rounded-2xl border transition ${
                    isMyRole ? 'border-blue-600 bg-blue-50/40 shadow-xs' : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <Icon size={16} className={isMyRole ? 'text-blue-600' : 'text-slate-500'} />
                      <span className="font-bold text-xs text-slate-900">{info.label}</span>
                    </div>
                    {isMyRole && (
                      <span className="text-[10px] bg-blue-600 text-white font-bold px-2 py-0.5 rounded-full">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">{info.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 5: Admin User Governance */}
      {activeTab === 'admin' && user?.role === 'administrator' && (
        <div className="bg-white rounded-2xl shadow-xs border border-slate-200 p-6 space-y-5">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">User Governance & Access Control</h2>
              <p className="text-xs text-slate-500">Manage registered accounts and role authorizations</p>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Search user..."
                value={adminSearch}
                onChange={e => setAdminSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchUsers()}
                className="p-1.5 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-100 w-full sm:w-48"
              />
              <select
                value={adminRoleFilter}
                onChange={e => {
                  setAdminRoleFilter(e.target.value);
                  setTimeout(fetchUsers, 50);
                }}
                className="p-1.5 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-100 bg-white"
              >
                <option value="">All Roles</option>
                <option value="athlete">Athlete</option>
                <option value="coach">Coach</option>
                <option value="physiotherapist">Physiotherapist</option>
                <option value="sports_scientist">Sports Scientist</option>
                <option value="administrator">Administrator</option>
              </select>
            </div>
          </div>

          {adminLoading ? (
            <div className="p-8 text-center text-slate-400 text-xs">Loading accounts directory...</div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="min-w-full divide-y divide-slate-100 text-xs">
                <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-4 text-left">User</th>
                    <th className="py-2.5 px-4 text-left">Current Role</th>
                    <th className="py-2.5 px-4 text-left">Status</th>
                    <th className="py-2.5 px-4 text-left">Modify Role</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {usersList.map(u => {
                    const roleInfo = ROLE_INFO[u.role] || ROLE_INFO.athlete;
                    return (
                      <tr key={u.id} className="hover:bg-slate-50/60">
                        <td className="py-2.5 px-4">
                          <div className="font-semibold text-slate-900">{u.full_name || 'No Name'}</div>
                          <div className="text-[11px] text-slate-400">{u.email}</div>
                        </td>
                        <td className="py-2.5 px-4">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${roleInfo.badge}`}>
                            {roleInfo.label}
                          </span>
                        </td>
                        <td className="py-2.5 px-4">
                          {u.is_active ? (
                            <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-bold">Active</span>
                          ) : (
                            <span className="text-[10px] text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full font-bold">Inactive</span>
                          )}
                        </td>
                        <td className="py-2.5 px-4">
                          <select
                            value={u.role}
                            onChange={e => handleRoleChange(u.id, e.target.value)}
                            className="text-xs p-1 border border-slate-200 rounded-lg bg-white outline-none"
                          >
                            <option value="athlete">Athlete</option>
                            <option value="coach">Coach</option>
                            <option value="physiotherapist">Physiotherapist</option>
                            <option value="sports_scientist">Sports Scientist</option>
                            <option value="administrator">Administrator</option>
                          </select>
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          <button
                            onClick={() => handleToggleStatus(u.id, u.is_active)}
                            className={`text-xs px-2.5 py-1 rounded-lg font-semibold border transition ${
                              u.is_active ? 'border-rose-200 text-rose-600 hover:bg-rose-50' : 'border-emerald-200 text-emerald-600 hover:bg-emerald-50'
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
      )}
    </div>
  );
};
