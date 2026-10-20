import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { videosAPI, athletesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

function VideoUpload() {
  const [athleteId, setAthleteId] = useState('');
  const [activityType, setActivityType] = useState('');
  const [videoFile, setVideoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [athletes, setAthletes] = useState([]);
  const { user } = useAuth();
  const navigate = useNavigate();

  const activityTypes = [
    'squat',
    'jump',
    'running',
    'walking',
    'lunges',
    'deadlift',
    'other'
  ];

  useEffect(() => {
    if (user) {
      fetchAthletes();
    }
  }, [user]);

  const fetchAthletes = async () => {
    try {
      let response;
      // If user is an athlete, fetch only their profile
      // If user is coach/therapist/admin/scientist, fetch all athletes
      if (user?.role === 'athlete') {
        response = await athletesAPI.getMe();
        setAthletes([response.data]);
        if (response.data) {
          setAthleteId(response.data.id);
        }
      } else {
        response = await athletesAPI.getAll();
        setAthletes(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch athletes:', err);
      setError('Failed to load athletes');
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
      if (!validTypes.includes(file.type)) {
        setError('Invalid file type. Please upload a video file (mp4, avi, mov, webm).');
        setVideoFile(null);
        return;
      }
      
      // Validate file size (500 MB limit)
      const maxSize = 500 * 1024 * 1024;
      if (file.size > maxSize) {
        setError('File too large. Maximum size is 500 MB.');
        setVideoFile(null);
        return;
      }
      
      setVideoFile(file);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!videoFile) {
      setError('Please select a video file');
      return;
    }
    
    if (!athleteId) {
      setError('Please select an athlete');
      return;
    }
    
    if (!activityType) {
      setError('Please select an activity type');
      return;
    }
    
    setUploading(true);
    setError('');
    
    try {
      const formData = new FormData();
      formData.append('athlete_id', athleteId);
      formData.append('activity_type', activityType);
      formData.append('video', videoFile);
      
      const response = await videosAPI.upload(formData);
      
      // Navigate to analysis page
      navigate(`/videos/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload video');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-10 p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-3xl font-bold mb-6">Upload Video</h1>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 font-bold mb-2">
            Athlete
          </label>
          <select
            value={athleteId}
            onChange={(e) => setAthleteId(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Select an athlete</option>
            {athletes.map((athlete) => (
              <option key={athlete.id} value={athlete.id}>
                {athlete.athlete_id} - {athlete.sport_type} ({athlete.position || 'N/A'})
              </option>
            ))}
          </select>
        </div>
        
        <div className="mb-4">
          <label className="block text-gray-700 font-bold mb-2">
            Activity Type
          </label>
          <select
            value={activityType}
            onChange={(e) => setActivityType(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Select activity type</option>
            {activityTypes.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>
        
        <div className="mb-4">
          <label className="block text-gray-700 font-bold mb-2">
            Video File
          </label>
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-msvideo,video/webm"
            onChange={handleFileChange}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <p className="text-sm text-gray-600 mt-1">
            Maximum file size: 500 MB. Supported formats: MP4, AVI, MOV, WebM
          </p>
        </div>
        
        {videoFile && (
          <div className="mb-4 p-3 bg-gray-100 rounded">
            <p className="text-sm">
              <strong>Selected file:</strong> {videoFile.name}
            </p>
            <p className="text-sm">
              <strong>Size:</strong> {(videoFile.size / (1024 * 1024)).toFixed(2)} MB
            </p>
          </div>
        )}
        
        <button
          type="submit"
          disabled={uploading}
          className="w-full bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
        >
          {uploading ? 'Uploading...' : 'Upload Video'}
        </button>
      </form>
    </div>
  );
}

export default VideoUpload;
