import React from 'react';
import { useAuth } from '../context/AuthContext';

const Profile = () => {
  const { user } = useAuth();

  if (!user) {
    return <div className="text-center py-8">Loading profile...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">User Profile</h1>
        <p className="mt-1 text-sm text-gray-500">Your account information</p>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Account Information</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">Personal details and account settings</p>
        </div>
        <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-8 sm:grid-cols-2">
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Full Name</dt>
              <dd className="mt-1 text-sm text-gray-900">{user.full_name}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Email</dt>
              <dd className="mt-1 text-sm text-gray-900">{user.email}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Role</dt>
              <dd className="mt-1 text-sm text-gray-900 capitalize">{user.role.replace('_', ' ')}</dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Account Status</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {user.is_active ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    Inactive
                  </span>
                )}
              </dd>
            </div>
            <div className="sm:col-span-1">
              <dt className="text-sm font-medium text-gray-500">Member Since</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {new Date(user.created_at).toLocaleDateString()}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Role Permissions</h3>
        <div className="space-y-3">
          {user.role === 'athlete' && (
            <div className="text-sm text-gray-600">
              <strong>Athlete:</strong> View and update your own athlete profile, view your own data.
            </div>
          )}
          {user.role === 'coach' && (
            <div className="text-sm text-gray-600">
              <strong>Coach:</strong> View athlete profiles, manage athlete information.
            </div>
          )}
          {user.role === 'physiotherapist' && (
            <div className="text-sm text-gray-600">
              <strong>Physiotherapist:</strong> View athlete profiles, access injury-related information.
            </div>
          )}
          {user.role === 'sports_scientist' && (
            <div className="text-sm text-gray-600">
              <strong>Sports Scientist:</strong> View athlete profiles and analysis-ready information.
            </div>
          )}
          {user.role === 'administrator' && (
            <div className="text-sm text-gray-600">
              <strong>Administrator:</strong> Full system access, user management, athlete management.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Profile;
