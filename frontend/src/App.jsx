import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import LoadingSpinner from './components/LoadingSpinner';

// Public pages
import Login from './pages/Login';
import Register from './pages/Register';

// Protected pages
import UploadVideo from './pages/UploadVideo';
import AthleteList from './pages/AthleteList';
import HealthStatus from './pages/HealthStatus';

// Role dashboards
import AthleteDashboard from './pages/dashboards/AthleteDashboard';
import CoachDashboard from './pages/dashboards/CoachDashboard';
import PhysioDashboard from './pages/dashboards/PhysioDashboard';
import ScientistDashboard from './pages/dashboards/ScientistDashboard';
import AdminDashboard from './pages/dashboards/AdminDashboard';

// ─── Role-based redirect ────────────────────────────────────────────────────
const ROLE_HOME = {
  athlete:          '/dashboard/athlete',
  coach:            '/dashboard/coach',
  physiotherapist:  '/dashboard/physiotherapist',
  sports_scientist: '/dashboard/scientist',
  admin:            '/dashboard/admin',
};

function RoleRedirect() {
  const { user } = useAuth();
  return <Navigate to={ROLE_HOME[user?.role] ?? '/dashboard/athlete'} replace />;
}

// ─── Shared page shell (navbar + main + footer) ─────────────────────────────
function AppShell({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <footer className="border-t border-slate-900 py-5 text-center text-xs text-slate-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>InjuryGuard • Sports Injury Risk Detection</span>
          <span>FastAPI + React · Pose Estimation &amp; Biomechanics</span>
        </div>
      </footer>
    </div>
  );
}

// ─── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <Routes>
      {/* ── Public (no navbar) ─────────────────────────────── */}
      <Route path="/login"    element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* ── All authenticated routes (require login) ─────── */}
      <Route element={<ProtectedRoute />}>

        {/* Root → role-specific dashboard */}
        <Route path="/" element={<AppShell><RoleRedirect /></AppShell>} />

        {/* Role dashboards (role-gated) */}
        <Route element={<ProtectedRoute allowedRoles={['athlete']} />}>
          <Route path="/dashboard/athlete" element={<AppShell><AthleteDashboard /></AppShell>} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['coach']} />}>
          <Route path="/dashboard/coach" element={<AppShell><CoachDashboard /></AppShell>} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['physiotherapist']} />}>
          <Route path="/dashboard/physiotherapist" element={<AppShell><PhysioDashboard /></AppShell>} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['sports_scientist']} />}>
          <Route path="/dashboard/scientist" element={<AppShell><ScientistDashboard /></AppShell>} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="/dashboard/admin" element={<AppShell><AdminDashboard /></AppShell>} />
        </Route>

        {/* Shared protected pages (all roles) */}
        <Route path="/upload"   element={<AppShell><UploadVideo /></AppShell>} />
        <Route path="/athletes" element={<AppShell><AthleteList /></AppShell>} />
        <Route path="/health"   element={<AppShell><HealthStatus /></AppShell>} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
