import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { athletesAPI, datasetsAPI, videosAPI } from '../services/api';

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalAthletes: 0,
    datasetsReady: 0,
    totalVideos: 0,
    processedVideos: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [athletesResponse, datasetsResponse, videosResponse] = await Promise.all([
          athletesAPI.getAll(),
          datasetsAPI.getAll(),
          videosAPI.getAll().catch(() => ({ data: [] })),
        ]);
        
        setStats({
          totalAthletes: athletesResponse.data.length,
          datasetsReady: datasetsResponse.data.filter(d => d.status === 'sample_integrated').length,
          totalVideos: videosResponse.data.length,
          processedVideos: videosResponse.data.filter(v => v.processing_status === 'completed').length,
        });
      } catch (error) {
        console.error('Failed to load stats:', error);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  const features = [
    {
      title: 'Athlete Management',
      description: 'Create and manage athlete profiles with sport-specific information',
      icon: '👥',
      link: '/athletes',
      available: true,
    },
    {
      title: 'Video Upload',
      description: 'Upload sports movement videos for analysis',
      icon: '📹',
      link: '/videos/upload',
      available: true,
    },
    {
      title: 'Movement Analysis',
      description: 'Analyze athlete movement patterns using pose estimation',
      icon: '🏃',
      link: '#',
      available: false,
      milestone: 'Milestone 2',
    },
    {
      title: 'Biomechanical Assessment',
      description: 'Calculate joint angles and movement metrics',
      icon: '📊',
      link: '#',
      available: false,
      milestone: 'Milestone 2',
    },
    {
      title: 'Injury Risk Prediction',
      description: 'AI-powered injury risk scoring and prediction',
      icon: '⚠️',
      link: '#',
      available: false,
      milestone: 'Milestone 3',
    },
    {
      title: 'Dataset Integration',
      description: 'Integrated pose estimation datasets for model training',
      icon: '📁',
      link: '#',
      available: true,
    },
    {
      title: 'Recommendation Engine',
      description: 'Personalized corrective exercise recommendations',
      icon: '💡',
      link: '#',
      available: false,
      milestone: 'Milestone 3',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Welcome back, {user?.full_name}. You are logged in as {user?.role}.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="micro-card">
          <div className="micro-card-header">Total Athletes</div>
          <div className="micro-card-value">{loading ? '...' : stats.totalAthletes}</div>
          <div className="micro-card-delta">Athletes in system</div>
        </div>

        <div className="micro-card">
          <div className="micro-card-header">Total Videos</div>
          <div className="micro-card-value">{loading ? '...' : stats.totalVideos}</div>
          <div className="micro-card-delta">Videos uploaded</div>
        </div>

        <div className="micro-card">
          <div className="micro-card-header">Processed Videos</div>
          <div className="micro-card-value">{loading ? '...' : stats.processedVideos}</div>
          <div className="micro-card-delta">Analyses completed</div>
        </div>

        <div className="micro-card">
          <div className="micro-card-header">Current Milestone</div>
          <div className="micro-card-value">2</div>
          <div className="micro-card-delta">Video Analysis</div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-display font-semibold text-text-primary mb-4">System Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className={`card p-6 ${!feature.available ? 'opacity-60' : ''}`}
            >
              <div className="flex items-center mb-4">
                <div className="text-4xl mr-3">{feature.icon}</div>
                <h3 className="text-lg font-display font-semibold text-text-primary">{feature.title}</h3>
              </div>
              <p className="text-sm text-text-secondary mb-4">{feature.description}</p>
              {!feature.available ? (
                <div className="badge-moderate">
                  Coming in {feature.milestone}
                </div>
              ) : feature.link !== '#' ? (
                <Link
                  to={feature.link}
                  className="btn-secondary inline-flex items-center"
                >
                  Access
                </Link>
              ) : (
                <div className="badge-optimal">
                  Available
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
