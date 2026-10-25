import React, { useState, useEffect } from 'react';
import api from '../api/client';
import AnomalyTimeline from './AnomalyTimeline';

export const AnomalyReport = ({ videoId, videoRef }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        setLoading(true);
        const res = await api.get(`/anomaly/${videoId}`);
        setData(res.data);
      } catch (err) {
        setError("Failed to load anomaly data.");
      } finally {
        setLoading(false);
      }
    };
    if (videoId) {
      fetchAnomalies();
    }
  }, [videoId]);

  if (loading) return <div className="mt-4 p-4 text-gray-500">Loading anomalies...</div>;
  if (error) return <div className="mt-4 p-4 text-red-500">{error}</div>;
  if (!data) return null;

  const handleSeek = (timeInSeconds) => {
    if (videoRef && videoRef.current) {
      videoRef.current.currentTime = timeInSeconds;
      videoRef.current.play().catch(e => console.log("Playback error:", e));
    }
  };

  return <AnomalyTimeline anomalies={data.events} onSeek={handleSeek} />;
};
