import { useState, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export const AthleteProfile = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState({
    sport_type: '',
    position: '',
    age: '',
    height_cm: '',
    weight_kg: '',
    injury_history: '',
    training_load: 'Medium',
  });
  const [exists, setExists] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/athletes/me');
        if (res.data) {
          // Parse JSON lists/dicts back to simple strings for the MVP form
          const injuries = res.data.injury_history?.map(i => i.description).join(', ') || '';
          const load = res.data.training_load?.intensity || 'Medium';
          
          setProfile({
            sport_type: res.data.sport_type || '',
            position: res.data.position || '',
            age: res.data.age || '',
            height_cm: res.data.height_cm || '',
            weight_kg: res.data.weight_kg || '',
            injury_history: injuries,
            training_load: load,
          });
          setExists(true);
        }
      } catch (err) {
        if (err.response?.status !== 404) {
          setError('Failed to load profile');
        }
      }
    };
    if (user?.role === 'athlete') fetchProfile();
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');

    // Format fields back to JSON schema expectations
    const injuriesArray = profile.injury_history
      ? profile.injury_history.split(',').map(i => ({ description: i.trim() })).filter(i => i.description)
      : [];

    const payload = {
      sport_type: profile.sport_type,
      position: profile.position,
      age: profile.age ? parseInt(profile.age, 10) : null,
      height_cm: profile.height_cm ? parseFloat(profile.height_cm) : null,
      weight_kg: profile.weight_kg ? parseFloat(profile.weight_kg) : null,
      injury_history: injuriesArray,
      training_load: { intensity: profile.training_load },
    };

    try {
      if (exists) {
        await api.put('/athletes/me', payload);
        setMessage('Profile updated successfully!');
      } else {
        await api.post('/athletes/me', payload);
        setExists(true);
        setMessage('Profile created successfully!');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile');
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto mb-10">
      <div className="bg-white p-8 rounded-lg shadow-md border border-gray-200">
        <h2 className="text-2xl font-bold mb-6 text-gray-800">My Athlete Profile</h2>
        {message && <div className="bg-green-50 text-green-700 p-3 rounded mb-4">{message}</div>}
        {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Sport Type</label>
              <input 
                type="text" 
                value={profile.sport_type}
                onChange={e => setProfile({...profile, sport_type: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Position</label>
              <input 
                type="text" 
                value={profile.position}
                onChange={e => setProfile({...profile, position: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Age</label>
              <input 
                type="number" 
                min="1"
                value={profile.age}
                onChange={e => setProfile({...profile, age: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Height (cm)</label>
              <input 
                type="number" 
                step="0.1"
                min="1"
                value={profile.height_cm}
                onChange={e => setProfile({...profile, height_cm: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Weight (kg)</label>
              <input 
                type="number" 
                step="0.1"
                min="1"
                value={profile.weight_kg}
                onChange={e => setProfile({...profile, weight_kg: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              />
            </div>
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2">Current Training Load</label>
              <select 
                value={profile.training_load}
                onChange={e => setProfile({...profile, training_load: e.target.value})}
                className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="Low">Low (Recovery)</option>
                <option value="Medium">Medium (Maintenance)</option>
                <option value="High">High (Peak Training)</option>
              </select>
            </div>
          </div>

          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Injury History (Comma separated)</label>
            <textarea 
              value={profile.injury_history}
              onChange={e => setProfile({...profile, injury_history: e.target.value})}
              placeholder="e.g. ACL tear (2022), Ankle sprain (2024)"
              className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500" 
              rows="3"
            />
          </div>
          
          <button type="submit" className="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded hover:bg-blue-700 transition">
            {exists ? 'Update Profile' : 'Create Profile'}
          </button>
        </form>
      </div>
    </div>
  );
};
