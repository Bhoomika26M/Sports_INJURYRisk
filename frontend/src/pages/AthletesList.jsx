import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Users, Activity, UserPlus, UserMinus, Search, ShieldCheck, AlertCircle } from 'lucide-react';

export const AthletesList = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [athletes, setAthletes] = useState([]);
  const [allStaff, setAllStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [assignModal, setAssignModal] = useState({ open: false, athleteId: null });
  const [selectedStaffId, setSelectedStaffId] = useState('');

  useEffect(() => {
    fetchAthletes();
    if (user?.role === 'administrator') {
      fetchStaffList();
    }
  }, [user]);

  const fetchAthletes = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/athletes/');
      setAthletes(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load athletes list');
    } finally {
      setLoading(false);
    }
  };

  const fetchStaffList = async () => {
    try {
      const res = await api.get('/users/?limit=100');
      const staffOnly = res.data.filter(u =>
        ['coach', 'physiotherapist', 'sports_scientist', 'administrator'].includes(u.role)
      );
      setAllStaff(staffOnly);
      if (staffOnly.length > 0) setSelectedStaffId(staffOnly[0].id);
    } catch (err) {
      console.error('Failed to load staff list:', err);
    }
  };

  const handleAssignStaff = async () => {
    if (!selectedStaffId || !assignModal.athleteId) return;
    try {
      await api.post(`/athletes/${assignModal.athleteId}/assign?staff_id=${selectedStaffId}`);
      setAssignModal({ open: false, athleteId: null });
      fetchAthletes();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to assign staff member');
    }
  };

  const isAthleteAssignedToMe = (a) => {
    if (!user) return false;
    if (a.assigned_staff?.some(s => s.id === user.id)) return true;
    if (a.coach?.id === user.id) return true;
    if (a.physiotherapist?.id === user.id) return true;
    return false;
  };

  const handleToggleSquad = async (athleteId, isAssigned) => {
    try {
      if (isAssigned) {
        await api.delete(`/athletes/${athleteId}/assign/${user.id}`);
      } else {
        await api.post(`/athletes/${athleteId}/assign?staff_id=${user.id}`);
      }
      fetchAthletes();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update squad roster');
    }
  };

  const filteredAthletes = athletes.filter(a => {
    const query = search.toLowerCase();
    return (
      (a.sport_type && a.sport_type.toLowerCase().includes(query)) ||
      (a.position && a.position.toLowerCase().includes(query)) ||
      (a.name && a.name.toLowerCase().includes(query)) ||
      String(a.id).includes(query)
    );
  });

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 bg-[#11121a] p-6 sm:p-7 rounded-2xl border border-white/10 shadow-xl">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-3 tracking-tight">
            <Users className="text-purple-400" size={24} />
            <span>Athletes Directory</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            {user?.role === 'administrator'
              ? 'All registered athletes across all sports programs and departments.'
              : 'Athletes in the organization available for kinematic screening and monitoring.'}
          </p>
        </div>

        <div className="w-full sm:w-72">
          <div className="relative">
            <Search size={15} className="absolute left-3.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, sport, position..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 text-rose-300 p-4 rounded-xl border border-rose-500/30 text-xs sm:text-sm flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-[#11121a] p-20 text-center text-slate-400 rounded-2xl border border-white/10">
          <div className="w-8 h-8 border-3 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <span className="text-xs sm:text-sm font-medium">Loading athlete roster...</span>
        </div>
      ) : filteredAthletes.length === 0 ? (
        <div className="bg-[#11121a] p-16 text-center rounded-2xl border border-white/10 shadow-xl">
          <Activity size={36} className="mx-auto text-slate-500 mb-3" />
          <h2 className="text-base font-bold text-white">No Athletes Found</h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-sm mx-auto">
            {user?.role === 'administrator'
              ? 'No athlete physical profiles have been registered yet.'
              : 'No athletes match your search query.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredAthletes.map(athlete => {
            const trainingIntensity = athlete.training_load?.intensity || 'Normal';
            const pastInjuriesCount = athlete.injury_history?.length || 0;

            return (
              <div
                key={athlete.id}
                className="bg-[#11121a] rounded-2xl border border-white/10 shadow-lg hover:border-purple-500/40 transition p-6 flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                        Athlete #{athlete.id}
                      </span>
                      <h2 className="text-lg font-bold text-white mt-0.5">
                        {athlete.name || athlete.sport_type || 'General Athlete'}
                      </h2>
                      <p className="text-xs text-purple-400 font-semibold">{athlete.position || athlete.sport_type || 'Player'}</p>
                    </div>

                    <span className="text-xs bg-purple-500/15 text-purple-300 px-2.5 py-1 rounded-full font-bold border border-purple-500/30">
                      Load: {trainingIntensity}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-3 my-3 border-y border-white/5 text-center text-xs">
                    <div>
                      <span className="text-slate-400 text-xs block">Age</span>
                      <strong className="text-white text-sm">{athlete.age || '—'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 text-xs block">Height</span>
                      <strong className="text-white text-sm">{athlete.height_cm ? `${athlete.height_cm}cm` : '—'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 text-xs block">Weight</span>
                      <strong className="text-white text-sm">{athlete.weight_kg ? `${athlete.weight_kg}kg` : '—'}</strong>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 mb-4">
                    <span className="font-semibold text-slate-300">Past Injuries: </span>
                    {pastInjuriesCount > 0 ? (
                      <span className="text-amber-400 font-medium">{pastInjuriesCount} recorded</span>
                    ) : (
                      <span className="text-emerald-400 font-medium">None reported</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-3 border-t border-white/5">
                  <button
                    onClick={() => navigate(`/dashboard/athlete/${athlete.id}`)}
                    className="flex-1 bg-purple-600 hover:bg-purple-500 text-white font-semibold py-2.5 px-3 rounded-xl text-xs sm:text-sm transition shadow-md shadow-purple-600/20"
                  >
                    View Kinematics
                  </button>

                  {user?.role === 'administrator' ? (
                    <button
                      onClick={() => setAssignModal({ open: true, athleteId: athlete.id })}
                      className="p-2.5 border border-white/10 hover:bg-white/10 rounded-xl text-slate-300 transition"
                      title="Assign Staff"
                      aria-label="Assign Staff"
                    >
                      <UserPlus size={16} />
                    </button>
                  ) : (user?.role === 'coach' || user?.role === 'physiotherapist') ? (
                    <button
                      onClick={() => handleToggleSquad(athlete.id, isAthleteAssignedToMe(athlete))}
                      className={`p-2.5 border rounded-xl transition ${
                        isAthleteAssignedToMe(athlete)
                          ? 'border-white/10 text-slate-400 hover:bg-rose-500/15 hover:text-rose-300 hover:border-rose-500/30'
                          : 'border-purple-500/30 bg-purple-500/15 text-purple-300 hover:bg-purple-600 hover:text-white'
                      }`}
                      title={isAthleteAssignedToMe(athlete) ? "Remove from Squad" : "+ Add to Squad"}
                      aria-label={isAthleteAssignedToMe(athlete) ? "Remove from Squad" : "Add to Squad"}
                    >
                      {isAthleteAssignedToMe(athlete) ? <UserMinus size={16} /> : <UserPlus size={16} />}
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Staff Assignment Modal */}
      {assignModal.open && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="bg-[#11121a] rounded-2xl shadow-2xl max-w-md w-full p-6 sm:p-7 border border-white/10">
            <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <ShieldCheck className="text-purple-400" size={20} />
              <span>Assign Staff Member</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Select a coach, physiotherapist, or sports scientist to grant monitoring access for Athlete #{assignModal.athleteId}.
            </p>

            <div className="mb-5">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Select Staff</label>
              <select
                value={selectedStaffId}
                onChange={e => setSelectedStaffId(e.target.value)}
                className="w-full p-2.5 border border-white/10 rounded-xl text-xs sm:text-sm bg-[#1c1d2e] text-white outline-none focus:ring-2 focus:ring-purple-500"
              >
                {allStaff.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.role.toUpperCase()}) &bull; {s.email}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setAssignModal({ open: false, athleteId: null })}
                className="px-4 py-2 border border-white/10 rounded-xl text-xs font-semibold text-slate-300 hover:bg-white/5 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleAssignStaff}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold transition shadow-md shadow-purple-600/20"
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AthletesList;
