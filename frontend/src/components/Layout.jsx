import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const getRoleBadgeClass = (role) => {
    const roleClasses = {
      athlete: 'badge-athlete',
      coach: 'badge-coach',
      physiotherapist: 'badge-physiotherapist',
      sports_scientist: 'badge-sports-scientist',
      administrator: 'badge-administrator',
    };
    return roleClasses[role] || 'badge-athlete';
  };

  return (
    <div className="min-h-screen bg-surface">
      <nav className="bg-white shadow-sm border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-display font-bold text-text-primary">Kinetic Telemetry</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/dashboard"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/dashboard')
                      ? 'border-primary text-text-primary'
                      : 'border-transparent text-text-secondary hover:border-border-muted hover:text-text-primary'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/athletes"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/athletes')
                      ? 'border-primary text-text-primary'
                      : 'border-transparent text-text-secondary hover:border-border-muted hover:text-text-primary'
                  }`}
                >
                  Athletes
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-text-primary">{user?.full_name}</span>
                <span className={getRoleBadgeClass(user?.role)}>{user?.role}</span>
              </div>
              <Link
                to="/profile"
                className="text-sm text-text-secondary hover:text-text-primary"
              >
                Profile
              </Link>
              <button
                onClick={logout}
                className="text-sm text-error hover:text-error-light"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
