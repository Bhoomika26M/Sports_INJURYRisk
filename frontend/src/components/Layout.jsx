import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">Sports Injury Risk Detection</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/dashboard"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/dashboard')
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/athletes"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/athletes')
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`}
                >
                  Athletes
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user?.full_name} ({user?.role})
              </span>
              <Link
                to="/profile"
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Profile
              </Link>
              <button
                onClick={logout}
                className="text-sm text-red-600 hover:text-red-800"
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
