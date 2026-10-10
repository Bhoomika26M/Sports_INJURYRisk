const API_BASE = '/api';

export const api = {
  // Health
  getHealth: async () => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Auth
  login: async (email, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Login failed');
    return res.json();
  },

  getCurrentUser: async (token) => {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return res.json();
  },

  // Athletes
  getAthletes: async () => {
    const res = await fetch(`${API_BASE}/athletes`);
    return res.json();
  },

  getAthlete: async (id) => {
    const res = await fetch(`${API_BASE}/athletes/${id}`);
    return res.json();
  },

  createAthlete: async (data) => {
    const res = await fetch(`${API_BASE}/athletes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  addInjuryRecord: async (athleteId, injuryData) => {
    const res = await fetch(`${API_BASE}/athletes/${athleteId}/injuries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(injuryData)
    });
    return res.json();
  },

  // Videos
  getVideos: async (athleteId = null) => {
    const url = athleteId ? `${API_BASE}/videos?athlete_id=${athleteId}` : `${API_BASE}/videos`;
    const res = await fetch(url);
    return res.json();
  },

  getVideo: async (id) => {
    const res = await fetch(`${API_BASE}/videos/${id}`);
    return res.json();
  },

  generateSampleVideo: async (movementType, athleteId = 1) => {
    const res = await fetch(`${API_BASE}/videos/generate_sample?movement_type=${encodeURIComponent(movementType)}&athlete_id=${athleteId}`, {
      method: 'POST'
    });
    return res.json();
  },

  uploadVideo: async (formData) => {
    const res = await fetch(`${API_BASE}/videos/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
    return res.json();
  },

  // Biomechanics
  runAnalysis: async (videoId) => {
    const res = await fetch(`${API_BASE}/biomechanics/analyze/${videoId}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Analysis failed');
    return res.json();
  },

  getBiomechanics: async (videoId) => {
    const res = await fetch(`${API_BASE}/biomechanics/${videoId}`);
    if (!res.ok) return null;
    return res.json();
  },

  // Injury Risk
  getInjuryRisk: async (videoId) => {
    const res = await fetch(`${API_BASE}/injury_risk/${videoId}`);
    if (!res.ok) return null;
    return res.json();
  },

  // Datasets
  getDatasets: async () => {
    const res = await fetch(`${API_BASE}/datasets`);
    return res.json();
  },

  // Dashboards
  getCoachDashboard: async () => {
    const res = await fetch(`${API_BASE}/dashboards/coach`);
    return res.json();
  },

  getPhysioDashboard: async () => {
    const res = await fetch(`${API_BASE}/dashboards/physiotherapist`);
    return res.json();
  },

  getScientistDashboard: async () => {
    const res = await fetch(`${API_BASE}/dashboards/sports_scientist`);
    return res.json();
  }
};
