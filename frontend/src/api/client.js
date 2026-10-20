const API_BASE = '/api';

const getStoredToken = () => {
  return localStorage.getItem('kinematix_token');
};

const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem('kinematix_token', token);
  } else {
    localStorage.removeItem('kinematix_token');
  }
};

const authHeaders = (headers = {}) => {
  const token = getStoredToken();
  const auth = token ? { Authorization: `Bearer ${token}` } : {};
  return {
    ...headers,
    ...auth
  };
};

export const api = {
  getStoredToken,
  setStoredToken,

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
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    if (data.access_token) {
      setStoredToken(data.access_token);
    }
    return data;
  },

  register: async ({ email, password, full_name, role }) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name, role })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    return data;
  },

  forgotPassword: async (email) => {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
  },

  resetPassword: async (token, newPassword) => {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Password reset failed');
    return data;
  },

  logout: async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: authHeaders()
      });
    } catch {
      // Ignore network errors on logout
    }
    setStoredToken(null);
    return { message: 'Logged out successfully' };
  },

  getCurrentUser: async () => {
    const token = getStoredToken();
    if (!token) return null;
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders()
    });
    if (!res.ok) {
      setStoredToken(null);
      return null;
    }
    return res.json();
  },

  getUsers: async () => {
    const res = await fetch(`${API_BASE}/auth/users`, {
      headers: authHeaders()
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to fetch users');
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
  },

  getAdminDashboard: async () => {
    const res = await fetch(`${API_BASE}/dashboards/admin`, {
      headers: authHeaders()
    });
    return res.json();
  },

  // Longitudinal Risk Trends
  getAthleteRiskTrends: async (athleteId) => {
    const res = await fetch(`${API_BASE}/injury_risk/athlete/${athleteId}/trends`);
    if (!res.ok) return { trends: [] };
    return res.json();
  },

  // Report Export URLs
  getPdfReportUrl: (videoId) => `${API_BASE}/reports/${videoId}/pdf`,
  getExcelReportUrl: (videoId) => `${API_BASE}/reports/${videoId}/excel`
};
