/**
 * ProtectedRoute
 *
 * Wraps a route so that:
 *  1. Unauthenticated users are redirected to /login
 *  2. Optionally, users with roles NOT in `allowedRoles` get a 403 page
 */
import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';

export default function ProtectedRoute({ allowedRoles }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <LoadingSpinner />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 text-slate-100 gap-4">
        <span className="text-6xl">🚫</span>
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-slate-400">Your role <strong className="text-emerald-400">{user.role}</strong> is not permitted here.</p>
      </div>
    );
  }

  return <Outlet />;
}
