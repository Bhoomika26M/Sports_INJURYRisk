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
    <div className="max-w-6xl mx-auto py-6 px-4 sm:px-6 space-y-6">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2 tracking-tight">
            <Users className="text-blue-600" size={22} />
            <span>Athletes Directory</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {user?.role === 'administrator'
              ? 'All registered athletes across all departments and programs.'
              : 'Athletes assigned to your roster for kinematic injury screening.'}
          </p>
        </div>

        <div className="w-full sm:w-64">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, sport, position..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-600 transition"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-3.5 rounded-xl border border-red-200 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white p-16 text-center text-slate-400 rounded-2xl border border-slate-200">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <span className="text-xs">Loading athlete roster...</span>
        </div>
      ) : filteredAthletes.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 shadow-xs">
          <Activity size={32} className="mx-auto text-slate-300 mb-2" />
          <h2 className="text-sm font-bold text-slate-700">No Athletes Found</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            {user?.role === 'administrator'
              ? 'No athlete physical profiles have been registered yet.'
              : 'No athletes are currently assigned to your monitoring roster.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAthletes.map(athlete => {
            const trainingIntensity = athlete.training_load?.intensity || 'Normal';
            const pastInjuriesCount = athlete.injury_history?.length || 0;

            return (
              <div
                key={athlete.id}
                className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-sm transition p-5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        Athlete #{athlete.id}
                      </span>
                      <h2 className="text-base font-bold text-slate-900 mt-0.5">
                        {athlete.name || athlete.sport_type || 'General Athlete'}
                      </h2>
                      <p className="text-xs text-blue-600 font-semibold">{athlete.position || athlete.sport_type || 'Player'}</p>
                    </div>

                    <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-bold border border-blue-200">
                      Load: {trainingIntensity}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-2.5 my-2 border-y border-slate-100 text-center text-xs">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Age</span>
                      <strong className="text-slate-800">{athlete.age || '—'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Height</span>
                      <strong className="text-slate-800">{athlete.height_cm ? `${athlete.height_cm}cm` : '—'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Weight</span>
                      <strong className="text-slate-800">{athlete.weight_kg ? `${athlete.weight_kg}kg` : '—'}</strong>
                    </div>
                  </div>

                  <div className="text-xs text-slate-500 mb-4">
                    <span className="font-semibold text-slate-600">Past Injuries: </span>
                    {pastInjuriesCount > 0 ? (
                      <span className="text-amber-600 font-medium">{pastInjuriesCount} recorded</span>
                    ) : (
                      <span className="text-emerald-600 font-medium">None reported</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                  <button
                    onClick={() => navigate(`/dashboard/athlete/${athlete.id}`)}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-3 rounded-xl text-xs transition shadow-xs"
                  >
                    View Screenings
                  </button>

                  {user?.role === 'administrator' ? (
                    <button
                      onClick={() => setAssignModal({ open: true, athleteId: athlete.id })}
                      className="p-2 border border-slate-200 hover:bg-slate-50 rounded-xl text-slate-600 transition"
                      title="Assign Staff"
                      aria-label="Assign Staff"
                    >
                      <UserPlus size={15} />
                    </button>
                  ) : (user?.role === 'coach' || user?.role === 'physiotherapist') ? (
                    <button
                      onClick={() => handleToggleSquad(athlete.id, isAthleteAssignedToMe(athlete))}
                      className={`p-2 border rounded-xl transition ${
                        isAthleteAssignedToMe(athlete)
                          ? 'border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-600'
                          : 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100'
                      }`}
                      title={isAthleteAssignedToMe(athlete) ? "Remove from Squad" : "+ Add to Squad"}
                      aria-label={isAthleteAssignedToMe(athlete) ? "Remove from Squad" : "Add to Squad"}
                    >
                      {isAthleteAssignedToMe(athlete) ? <UserMinus size={15} /> : <UserPlus size={15} />}
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
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <ShieldCheck className="text-blue-600" size={18} />
              <span>Assign Staff Member</span>
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Select a coach, physiotherapist, or sports scientist to grant monitoring access for Athlete #{assignModal.athleteId}.
            </p>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Select Staff</label>
              <select
                value={selectedStaffId}
                onChange={e => setSelectedStaffId(e.target.value)}
                className="w-full p-2.5 border border-slate-200 rounded-xl text-xs bg-white outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-600"
              >
                {allStaff.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.role.toUpperCase()}) &bull; {s.email}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setAssignModal({ open: false, athleteId: null })}
                className="px-3.5 py-1.5 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleAssignStaff}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition shadow-xs"
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
