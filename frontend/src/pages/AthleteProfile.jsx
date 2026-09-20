import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { athletesAPI } from '../services/api';

const AthleteProfile = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [athlete, setAthlete] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    loadAthlete();
  }, [id]);

  const loadAthlete = async () => {
    try {
      const response = await athletesAPI.getById(id);
      setAthlete(response.data);
      setEditForm(response.data);
    } catch (err) {
      setError('Failed to load athlete profile');
      if (err.response?.status === 404) {
        setError('Athlete not found');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await athletesAPI.update(id, editForm);
      setEditing(false);
      loadAthlete();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update athlete');
    }
  };

  const canEdit = user?.role === 'athlete' ? athlete?.user_id === user?.id : true;

  if (loading) {
    return <div className="text-center py-8">Loading athlete profile...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
        <Link to="/athletes" className="ml-4 text-blue-600 hover:text-blue-800">
          Back to Athletes
        </Link>
      </div>
    );
  }

  if (!athlete) {
    return <div className="text-center py-8">Athlete not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <Link to="/athletes" className="text-blue-600 hover:text-blue-800 text-sm">
            ← Back to Athletes
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">{athlete.athlete_id}</h1>
          <p className="mt-1 text-sm text-gray-500">Athlete Profile</p>
        </div>
        {canEdit && (
          <button
            onClick={() => setEditing(!editing)}
            className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            {editing ? 'Cancel' : 'Edit Profile'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {editing ? (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Edit Athlete Profile</h3>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Sport Type</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.sport_type}
                  onChange={(e) => setEditForm({ ...editForm, sport_type: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Position</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.position}
                  onChange={(e) => setEditForm({ ...editForm, position: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Age</label>
                <input
                  type="number"
                  min="1"
                  max="99"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.age}
                  onChange={(e) => setEditForm({ ...editForm, age: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Height (cm)</label>
                <input
                  type="number"
                  min="1"
                  step="0.1"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.height}
                  onChange={(e) => setEditForm({ ...editForm, height: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Weight (kg)</label>
                <input
                  type="number"
                  min="1"
                  step="0.1"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.weight}
                  onChange={(e) => setEditForm({ ...editForm, weight: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Training Load</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.training_load}
                  onChange={(e) => setEditForm({ ...editForm, training_load: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Injury History</label>
                <textarea
                  rows="3"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={editForm.injury_history}
                  onChange={(e) => setEditForm({ ...editForm, injury_history: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Save Changes
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Athlete Information</h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">Personal details and sport information</p>
          </div>
          <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
            <dl className="grid grid-cols-1 gap-x-4 gap-y-8 sm:grid-cols-2">
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Athlete ID</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.athlete_id}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Sport Type</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.sport_type}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Position</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.position || 'N/A'}</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Age</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.age} years</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Height</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.height} cm</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Weight</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.weight} kg</dd>
              </div>
              <div className="sm:col-span-1">
                <dt className="text-sm font-medium text-gray-500">Training Load</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.training_load || 'N/A'}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Injury History</dt>
                <dd className="mt-1 text-sm text-gray-900">{athlete.injury_history || 'No injury history recorded'}</dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Analysis Status</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Movement Analysis</h4>
              <p className="text-sm text-gray-500">Pose estimation and movement pattern analysis</p>
            </div>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
              Coming in Milestone 2
            </span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Biomechanical Assessment</h4>
              <p className="text-sm text-gray-500">Joint angle calculations and movement metrics</p>
            </div>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
              Coming in Milestone 2
            </span>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Injury Risk Prediction</h4>
              <p className="text-sm text-gray-500">AI-powered risk scoring and prediction</p>
            </div>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
              Coming in Milestone 3
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AthleteProfile;
