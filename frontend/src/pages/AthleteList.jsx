import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { athletesAPI } from '../services/api';

const AthleteList = () => {
  const { user } = useAuth();
  const [athletes, setAthletes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newAthlete, setNewAthlete] = useState({
    athlete_id: '',
    sport_type: '',
    position: '',
    age: '',
    height: '',
    weight: '',
    injury_history: '',
    training_load: '',
  });

  useEffect(() => {
    loadAthletes();
  }, []);

  const loadAthletes = async () => {
    try {
      const response = await athletesAPI.getAll();
      setAthletes(response.data);
    } catch (err) {
      setError('Failed to load athletes');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAthlete = async (e) => {
    e.preventDefault();
    try {
      await athletesAPI.create({
        ...newAthlete,
        age: parseInt(newAthlete.age),
        height: parseFloat(newAthlete.height),
        weight: parseFloat(newAthlete.weight),
      });
      setShowAddForm(false);
      setNewAthlete({
        athlete_id: '',
        sport_type: '',
        position: '',
        age: '',
        height: '',
        weight: '',
        injury_history: '',
        training_load: '',
      });
      loadAthletes();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create athlete');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this athlete?')) return;
    
    try {
      await athletesAPI.delete(id);
      loadAthletes();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete athlete');
    }
  };

  const canAddAthlete = ['administrator', 'coach', 'physiotherapist', 'sports_scientist'].includes(user?.role);
  const canDeleteAthlete = user?.role === 'administrator';

  if (loading) {
    return <div className="text-center py-8">Loading athletes...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Athletes</h1>
          <p className="mt-1 text-sm text-gray-500">Manage athlete profiles</p>
        </div>
        {canAddAthlete && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            {showAddForm ? 'Cancel' : 'Add Athlete'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {showAddForm && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Athlete</h3>
          <form onSubmit={handleAddAthlete} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Athlete ID *</label>
                <input
                  type="text"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.athlete_id}
                  onChange={(e) => setNewAthlete({ ...newAthlete, athlete_id: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Sport Type *</label>
                <input
                  type="text"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.sport_type}
                  onChange={(e) => setNewAthlete({ ...newAthlete, sport_type: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Position</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.position}
                  onChange={(e) => setNewAthlete({ ...newAthlete, position: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Age *</label>
                <input
                  type="number"
                  required
                  min="1"
                  max="99"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.age}
                  onChange={(e) => setNewAthlete({ ...newAthlete, age: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Height (cm) *</label>
                <input
                  type="number"
                  required
                  min="1"
                  step="0.1"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.height}
                  onChange={(e) => setNewAthlete({ ...newAthlete, height: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Weight (kg) *</label>
                <input
                  type="number"
                  required
                  min="1"
                  step="0.1"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.weight}
                  onChange={(e) => setNewAthlete({ ...newAthlete, weight: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Injury History</label>
                <textarea
                  rows="3"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.injury_history}
                  onChange={(e) => setNewAthlete({ ...newAthlete, injury_history: e.target.value })}
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">Training Load</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  value={newAthlete.training_load}
                  onChange={(e) => setNewAthlete({ ...newAthlete, training_load: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Add Athlete
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {athletes.length === 0 ? (
            <li className="px-4 py-8 text-center text-gray-500">
              No athletes found. {canAddAthlete ? 'Add your first athlete to get started.' : ''}
            </li>
          ) : (
            athletes.map((athlete) => (
              <li key={athlete.id}>
                <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/athletes/${athlete.id}`}
                        className="text-sm font-medium text-blue-600 truncate hover:text-blue-800"
                      >
                        {athlete.athlete_id}
                      </Link>
                      <p className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="truncate">{athlete.sport_type}</span>
                        {athlete.position && <span className="mx-2">•</span>}
                        {athlete.position && <span className="truncate">{athlete.position}</span>}
                      </p>
                    </div>
                    <div className="ml-4 flex-shrink-0 flex items-center space-x-2">
                      <span className="text-sm text-gray-500">{athlete.age} yrs</span>
                      <Link
                        to={`/athletes/${athlete.id}`}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        View
                      </Link>
                      {canDeleteAthlete && (
                        <button
                          onClick={() => handleDelete(athlete.id)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
};

export default AthleteList;
