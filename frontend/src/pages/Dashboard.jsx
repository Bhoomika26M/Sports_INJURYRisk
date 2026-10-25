import { useAuth } from '../context/AuthContext';
import { AthleteDashboard } from './AthleteDashboard';
import { CoachDashboard } from './dashboards/CoachDashboard';
import { PhysiotherapistDashboard } from './dashboards/PhysiotherapistDashboard';
import { SportsScientistDashboard } from './dashboards/SportsScientistDashboard';
import { AdminDashboard } from './dashboards/AdminDashboard';

export const Dashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="max-w-6xl mx-auto py-20 px-4 text-center">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500 font-medium">Authenticating dashboard session...</p>
      </div>
    );
  }

  switch (user.role) {
    case 'athlete':
      return <AthleteDashboard />;
    case 'coach':
      return <CoachDashboard />;
    case 'physiotherapist':
      return <PhysiotherapistDashboard />;
    case 'sports_scientist':
      return <SportsScientistDashboard />;
    case 'administrator':
      return <AdminDashboard />;
    default:
      return <CoachDashboard />;
  }
};
