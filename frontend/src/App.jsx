import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navbar } from './components/Navbar';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { AthleteDashboard } from './pages/AthleteDashboard';
import { Profile } from './pages/Profile';
import { AthletesList } from './pages/AthletesList';
import { VideoUpload } from './pages/VideoUpload';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
          <Navbar />
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
              element={<Navigate to="/dashboard" replace />} 
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
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
