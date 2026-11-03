import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navbar } from './components/Navbar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Activity } from 'lucide-react';

// Lazy loaded page components for optimal bundle splitting
const Login = lazy(() => import('./pages/Login').then(m => ({ default: m.Login })));
const Register = lazy(() => import('./pages/Register').then(m => ({ default: m.Register })));
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const AthleteDashboard = lazy(() => import('./pages/AthleteDashboard').then(m => ({ default: m.AthleteDashboard })));
const Profile = lazy(() => import('./pages/Profile').then(m => ({ default: m.Profile })));
const AthletesList = lazy(() => import('./pages/AthletesList').then(m => ({ default: m.AthletesList })));
const VideoUpload = lazy(() => import('./pages/VideoUpload').then(m => ({ default: m.VideoUpload })));
const DatasetsPage = lazy(() => import('./pages/DatasetsPage').then(m => ({ default: m.DatasetsPage })));

// Loading spinner fallback
const PageLoader = () => (
  <div className="min-h-[70vh] flex flex-col items-center justify-center gap-4 text-purple-400">
    <div className="w-12 h-12 rounded-2xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center animate-pulse">
      <Activity className="animate-spin" size={24} />
    </div>
    <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Loading AthletiQ...</span>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-[#07070a] text-slate-100 font-sans selection:bg-purple-600 selection:text-white flex flex-col">
            <Navbar />
            <main className="flex-1">
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  
                  {/* Protected Routes accessible by all roles */}
                  <Route 
                    path="/dashboard" 
                    element={
                      <ProtectedRoute>
                        <Dashboard />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/datasets" 
                    element={
                      <ProtectedRoute>
                        <DatasetsPage />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/profile" 
                    element={
                      <ProtectedRoute>
                        <Profile />
                      </ProtectedRoute>
                    } 
                  />

                  {/* Athlete specific routes */}
                  <Route 
                    path="/upload" 
                    element={
                      <ProtectedRoute allowedRoles={['athlete']}>
                        <VideoUpload />
                      </ProtectedRoute>
                    } 
                  />

                  {/* Staff & Admin specific routes */}
                  <Route 
                    path="/athletes" 
                    element={
                      <ProtectedRoute allowedRoles={['coach', 'physiotherapist', 'sports_scientist', 'administrator']}>
                        <AthletesList />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/dashboard/athlete/:athleteId" 
                    element={
                      <ProtectedRoute allowedRoles={['coach', 'physiotherapist', 'sports_scientist', 'administrator']}>
                        <AthleteDashboard />
                      </ProtectedRoute>
                    } 
                  />
                  <Route 
                    path="/admin/users" 
                    element={
                      <ProtectedRoute allowedRoles={['administrator']}>
                        <Profile />
                      </ProtectedRoute>
                    } 
                  />
                  
                  {/* Redirect root to dashboard */}
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  {/* Fallback 404 redirect */}
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </Suspense>
            </main>
          </div>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
