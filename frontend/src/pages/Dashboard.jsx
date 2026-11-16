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
    <div className="w-full space-y-6">
      {/* User Welcome Bar & Instant Actions */}
      <div className="w-full flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-5 sm:p-6 rounded-2xl shadow-sm border border-gray-100">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-[#FFDBCF] flex items-center justify-center text-[#BD4006] flex-shrink-0 shadow-sm font-display font-bold text-2xl">
            ⚡
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-[#141B2B]">
                Welcome back, {user?.full_name}
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#E9EDFF] text-[#141B2B] font-mono text-[11px] uppercase font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#BD4006]" />
                {user?.role?.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-[#594139] text-xs font-mono">
              <span className="flex items-center gap-1">
                <span>🟢 Node Status: Active 120Hz</span>
              </span>
              <span>•</span>
              <span>High-Performance Kinematic Hub</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to="/athletes"
            className="px-3.5 py-2 rounded-lg bg-[#F1F3FF] hover:bg-[#E9EDFF] text-[#141B2B] font-semibold text-xs transition-colors flex items-center gap-1.5 border border-[#E1BFB5]/30"
          >
            <span>👥 Manage Athletes</span>
          </Link>
          <Link
            to="/videos/upload"
            className="btn-primary py-2 px-4 shadow-sm text-xs flex items-center gap-1.5"
          >
            <span>📹 Upload Video</span>
          </Link>
        </div>
      </div>

      {/* Core Telemetry Metric Micro-Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* 1. Total Athletes */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-wider text-[#594139] font-semibold">
                Total Athletes
              </p>
              <h2 className="font-display text-3xl font-bold text-[#141B2B] mt-1">
                {loading ? '—' : stats.totalAthletes}
              </h2>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#ECFDF5] text-[#065F46] font-mono text-[11px] font-semibold">
              Roster Active
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-[#594139] text-xs font-mono">
            <span>Sport-Specific Kinematics</span>
            <span className="font-bold text-[#BD4006]">Managed</span>
          </div>
        </div>

        {/* 2. Total Videos Analyzed */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-wider text-[#594139] font-semibold">
                Videos Analyzed
              </p>
              <h2 className="font-display text-3xl font-bold text-[#141B2B] mt-1">
                {loading ? '—' : stats.processedVideos}
              </h2>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#ECFDF5] text-[#065F46] font-mono text-[11px] font-semibold">
              {stats.totalVideos > 0 ? `${Math.round((stats.processedVideos / stats.totalVideos) * 100)}% Done` : 'Ready'}
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between font-mono text-xs text-[#594139]">
            <span>MediaPipe BlazePose</span>
            <span className="font-semibold text-[#006C49]">33 Landmarks</span>
          </div>
        </div>

        {/* 3. Integrated Datasets */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-wider text-[#594139] font-semibold">
                Integrated Datasets
              </p>
              <div className="flex items-baseline gap-1 mt-1">
                <h2 className="font-display text-3xl font-bold text-[#141B2B]">
                  {loading ? '—' : stats.datasetsReady}
                </h2>
                <span className="text-[#594139] font-mono text-xs">benchmark sets</span>
              </div>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#FFFBEB] text-[#92400E] font-mono text-[11px] font-semibold">
              Calibrated
            </span>
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between font-mono text-xs text-[#594139]">
            <span>Biomech Normatives</span>
            <span className="font-semibold text-[#006C49]">Synchronized</span>
          </div>
        </div>

        {/* 4. Active In-flight Queue */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-wider text-[#594139] font-semibold">
                Telemetry Pipeline
              </p>
              <div className="flex items-center gap-2 mt-1">
                <h2 className="font-display text-3xl font-bold text-[#141B2B]">
                  {loading ? '—' : (stats.totalVideos - stats.processedVideos)}
                </h2>
                <span className="text-xs text-[#594139]">Pending Tasks</span>
              </div>
            </div>
            <span className="w-2.5 h-2.5 rounded-full bg-[#BD4006] animate-pulse mt-1" />
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between font-mono text-xs text-[#594139]">
            <span>YOLO11 Tracking</span>
            <span className="font-semibold text-[#BD4006]">ByteTrack Engaged</span>
          </div>
        </div>
      </div>

      {/* Feature Capabilities Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-display font-bold text-[#141B2B]">Biomechanical Feature Hub</h2>
          <span className="text-xs font-mono text-[#594139] uppercase">Platform Capabilities</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, index) => {
            const Content = (
              <div
                className={`p-5 rounded-2xl border transition-all h-full flex flex-col justify-between ${
                  feature.available
                    ? 'bg-white border-gray-200 shadow-sm hover:shadow-md hover:border-[#BD4006]/40 cursor-pointer'
                    : 'bg-[#F9F9FF] border-gray-200/60 opacity-80'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-2xl p-2 rounded-xl bg-[#F1F3FF]">{feature.icon}</span>
                    {feature.available ? (
                      <span className="badge-optimal text-[10px]">Active</span>
                    ) : (
                      <span className="badge-moderate text-[10px]">{feature.milestone || 'Planned'}</span>
                    )}
                  </div>
                  <h3 className="font-display font-bold text-base text-[#141B2B] mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-xs text-[#594139] leading-relaxed">
                    {feature.description}
                  </p>
                </div>
                {feature.available && (
                  <div className="mt-4 pt-2 flex items-center text-xs font-semibold text-[#BD4006]">
                    Launch Module →
                  </div>
                )}
              </div>
            );

            return feature.available && feature.link !== '#' ? (
              <Link key={index} to={feature.link}>
                {Content}
              </Link>
            ) : (
              <div key={index}>{Content}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
