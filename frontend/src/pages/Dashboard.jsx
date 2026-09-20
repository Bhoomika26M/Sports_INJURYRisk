import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { athletesAPI, datasetsAPI } from '../services/api';

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalAthletes: 0,
    datasetsReady: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [athletesResponse, datasetsResponse] = await Promise.all([
          athletesAPI.getAll(),
          datasetsAPI.getAll(),
        ]);
        
        setStats({
          totalAthletes: athletesResponse.data.length,
          datasetsReady: datasetsResponse.data.filter(d => d.status === 'sample_integrated').length,
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
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Welcome back, {user?.full_name}. You are logged in as {user?.role}.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">👥</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Athletes
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {loading ? '...' : stats.totalAthletes}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">📁</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Datasets Integrated
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {loading ? '...' : stats.datasetsReady}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-3xl">🎯</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Current Milestone
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    1 - Foundation
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">System Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className={`bg-white overflow-hidden shadow rounded-lg ${
                !feature.available ? 'opacity-60' : ''
              }`}
            >
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <div className="text-4xl mr-3">{feature.icon}</div>
                  <h3 className="text-lg font-medium text-gray-900">{feature.title}</h3>
                </div>
                <p className="text-sm text-gray-500 mb-4">{feature.description}</p>
                {!feature.available ? (
                  <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
                    Coming in {feature.milestone}
                  </div>
                ) : feature.link !== '#' ? (
                  <Link
                    to={feature.link}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 hover:bg-blue-200"
                  >
                    Access
                  </Link>
                ) : (
                  <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    Available
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
