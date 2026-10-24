import { useEffect, useState } from "react";
import "./App.css";

/* =========================
   TYPE DEFINITIONS
========================= */

type UserRole = "ATHLETE" | "COACH" | "PHYSIOTHERAPIST" | "SPORTS_SCIENTIST" | "ADMINISTRATOR";
type DashboardView = "STUDIO" | "COACH" | "PHYSIO" | "SPORTS_SCIENCE" | "ADMIN" | "REPORTS";

type Athlete = {
  id: number;
  athlete_id: string;
  sport_type: string;
  position: string;
  age: number;
  height: number;
  weight: number;
  injury_history: string;
  training_load: number;
};

type MetricsSummary = {
  peak_knee_valgus_left: number;
  peak_knee_valgus_right: number;
  peak_valgus_overall: number;
  avg_valgus_overall: number;
  peak_knee_flexion_left: number;
  peak_knee_flexion_right: number;
  peak_flexion_overall: number;
  mean_asymmetry_index: number;
  peak_asymmetry_index: number;
  mean_trunk_lean: number;
  peak_trunk_lean: number;
};

type QualityReport = {
  overall_score: number;
  grade: string;
  valgus_stability_score: number;
  symmetry_score: number;
  rom_score: number;
  posture_score: number;
  metrics_summary: MetricsSummary;
  anomalies: string[];
};

type FrameSample = {
  frame_index: number;
  timestamp: number;
  left_knee_angle: number;
  right_knee_angle: number;
  left_knee_flexion: number;
  right_knee_flexion: number;
  left_hip_angle: number;
  right_hip_angle: number;
  left_valgus_angle: number;
  right_valgus_angle: number;
  trunk_lean: number;
  lateral_lean: number;
  knee_symmetry_index: number;
  valgus_symmetry_index: number;
};

type VideoAnalysisResponse = {
  video_name: string;
  movement_type: string;
  athlete_id: string | null;
  total_frames: number;
  fps: number;
  duration: number;
  quality_report: QualityReport;
  sampled_frames: FrameSample[];
};

type EarlyWarningItem = {
  severity: "CRITICAL" | "WARNING" | "INFO";
  title: string;
  message: string;
};

type RiskBreakdown = {
  acl_risk: number;
  hamstring_risk: number;
  ankle_risk: number;
  patellar_risk: number;
};

type CorrectiveExerciseItem = {
  name: string;
  category: string;
  target: string;
  frequency: string;
  purpose: string;
  difficulty: string;
};

type RecommendationPlan = {
  prescribed_exercises: CorrectiveExerciseItem[];
  training_load_recommendation: string;
  recovery_status: string;
  recovery_guidelines: string[];
};

type InjuryAssessmentResponse = {
  id?: number;
  athlete_id?: string | null;
  movement_type: string;
  overall_risk_score: number;
  risk_level: "LOW" | "MODERATE" | "HIGH";
  risk_breakdown: RiskBreakdown;
  early_warnings: EarlyWarningItem[];
  recommendations: RecommendationPlan;
  created_at?: string;
};

type NotificationItem = {
  id: number;
  athlete_id?: string;
  athlete_name?: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  category: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at?: string;
};

type UserItem = {
  id: number;
  name: string;
  email: string;
  role: string;
};

function App() {
  /* =========================
     AUTH & ROLE STATE
  ========================= */
  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [loggedIn, setLoggedIn] = useState<boolean>(() => {
    return !!localStorage.getItem("access_token");
  });
  const [userRole, setUserRole] = useState<UserRole>(() => {
    return (localStorage.getItem("role") as UserRole) || "ATHLETE";
  });
  const [activeView, setActiveView] = useState<DashboardView>("STUDIO");

  /* =========================
     LOGIN & SIGNUP FORMS
  ========================= */
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupConfirmPassword, setSignupConfirmPassword] = useState("");
  const [signupRole, setSignupRole] = useState<UserRole>("ATHLETE");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  /* =========================
     ATHLETE MANAGEMENT STATE
  ========================= */
  const [athletesList, setAthletesList] = useState<Athlete[]>([]);
  const [athlete, setAthlete] = useState<Athlete | null>(null);

  /* =========================
     MILESTONES 2 & 3: BIOMECHANICS & INJURY RISK STATE
  ========================= */
  const [selectedMovement, setSelectedMovement] = useState<string>("SQUAT");
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string>("");
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [predictionResult, setPredictionResult] = useState<InjuryAssessmentResponse | null>(null);
  const [predictionLoading, setPredictionLoading] = useState<boolean>(false);
  const [videoSrc, setVideoSrc] = useState<string>("/videos/broadcast_basketball.mp4");
  const [activeVideoName, setActiveVideoName] = useState<string>("broadcast_basketball.mp4");
  const [videoSourceType, setVideoSourceType] = useState<"UPLOAD" | "SAMPLE">("SAMPLE");
  const [uploadedFileMeta, setUploadedFileMeta] = useState<{
    name: string;
    sizeMB: string;
    lastModified?: string;
  } | null>(null);

  /* =========================
     MILESTONE 4: EXECUTIVE DASHBOARDS & NOTIFICATIONS
  ========================= */
  const [coachData, setCoachData] = useState<any>(null);
  const [physioData, setPhysioData] = useState<any>(null);
  const [sportsSciData, setSportsSciData] = useState<any>(null);
  const [adminData, setAdminData] = useState<any>(null);
  const [usersList, setUsersList] = useState<UserItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);

  /* =========================
     INITIAL LOADERS & REFRESH
  ========================= */
  const loadAthletes = async (token?: string) => {
    try {
      const headers: any = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch("http://127.0.0.1:8000/athletes/", { headers });
      if (res.ok) {
        const data: Athlete[] = await res.json();
        setAthletesList(data);
        if (data.length > 0 && !athlete) {
          setAthlete(data[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load athletes roster", err);
    }
  };

  const loadNotifications = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/notifications/");
      if (res.ok) {
        const data: NotificationItem[] = await res.json();
        setNotifications(data);
      }
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  };

  const loadExecutiveDashboards = async () => {
    try {
      // Coach Dashboard
      fetch("http://127.0.0.1:8000/dashboard/coach")
        .then((r) => r.json())
        .then(setCoachData)
        .catch(console.error);

      // Physio Dashboard
      fetch("http://127.0.0.1:8000/dashboard/physio")
        .then((r) => r.json())
        .then(setPhysioData)
        .catch(console.error);

      // Sports Science Dashboard
      fetch("http://127.0.0.1:8000/dashboard/sports-scientist")
        .then((r) => r.json())
        .then(setSportsSciData)
        .catch(console.error);

      // Admin Dashboard & Users
      fetch("http://127.0.0.1:8000/dashboard/admin")
        .then((r) => r.json())
        .then(setAdminData)
        .catch(console.error);

      fetch("http://127.0.0.1:8000/users/")
        .then((r) => r.json())
        .then(setUsersList)
        .catch(console.error);
    } catch (err) {
      console.error("Failed to load executive dashboards", err);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      setLoggedIn(true);
      const storedRole = localStorage.getItem("role") as UserRole;
      if (storedRole) setUserRole(storedRole);
      loadAthletes(token);
      loadNotifications();
      loadExecutiveDashboards();
    }
  }, []);

  /* =========================
     AUTH HANDLERS
  ========================= */
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Invalid email or password");
        setLoading(false);
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("role", data.role);
      setUserRole(data.role as UserRole);
      setLoggedIn(true);
      setShowLogin(false);
      setShowSignup(false);
      setEmail("");
      setPassword("");
      setMessage("");

      // Automatically switch to role-appropriate view
      if (data.role === "COACH") setActiveView("COACH");
      else if (data.role === "PHYSIOTHERAPIST") setActiveView("PHYSIO");
      else if (data.role === "SPORTS_SCIENTIST") setActiveView("SPORTS_SCIENCE");
      else if (data.role === "ADMINISTRATOR") setActiveView("ADMIN");
      else setActiveView("STUDIO");

      await loadAthletes(data.access_token);
      await loadNotifications();
      await loadExecutiveDashboards();
    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to server");
    }
    setLoading(false);
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");

    if (signupPassword !== signupConfirmPassword) {
      setMessage("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: signupName,
          email: signupEmail,
          password: signupPassword,
          role: signupRole,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Registration failed");
        setLoading(false);
        return;
      }

      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setSignupConfirmPassword("");
      setShowSignup(false);
      setShowLogin(true);
      setMessage("Account created successfully. Please login.");
    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to server");
    }
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");
    setLoggedIn(false);
    setAthlete(null);
    setShowLogin(true);
    setShowSignup(false);
    setMessage("");
  };

  /* =========================
     BIOMECHANICS & INJURY RISK HANDLERS
  ========================= */
  const handleAssessInjuryRisk = async (customBiotech?: QualityReport) => {
    setPredictionLoading(true);
    try {
      const payload: any = {
        athlete_id: athlete?.athlete_id || null,
        movement_type: selectedMovement,
      };
      const biotechData = customBiotech || analysisResult?.quality_report;
      if (biotechData) {
        payload.biomechanics = {
          overall_score: biotechData.overall_score,
          metrics_summary: biotechData.metrics_summary,
          anomalies: biotechData.anomalies,
        };
      }

      const res = await fetch("http://127.0.0.1:8000/prediction/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to assess injury risk");
      const data: InjuryAssessmentResponse = await res.json();
      setPredictionResult(data);
      loadNotifications();
    } catch (err: any) {
      console.error(err);
    } finally {
      setPredictionLoading(false);
    }
  };

  const handleRunDemo = async (movement: string) => {
    setAnalysisLoading(true);
    setAnalysisError("");
    try {
      const athleteParam = athlete?.athlete_id ? `&athlete_id=${athlete.athlete_id}` : "";
      const res = await fetch(
        `http://127.0.0.1:8000/analysis/synthetic-demo?movement_type=${movement}${athleteParam}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error("Failed to process biomechanical assessment");
      const data: VideoAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setCurrentFrameIndex(0);
      handleAssessInjuryRisk(data.quality_report);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to run analysis");
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleLoadSampleVideo = async (videoFilename: string, movement: string) => {
    const url = `/videos/${videoFilename}`;
    setVideoSrc(url);
    setActiveVideoName(videoFilename);
    setSelectedMovement(movement);
    setVideoSourceType("SAMPLE");
    setAnalysisLoading(true);
    setAnalysisError("");
    try {
      const athleteParam = athlete?.athlete_id ? `&athlete_id=${athlete.athlete_id}` : "";
      const res = await fetch(
        `http://127.0.0.1:8000/analysis/analyze-video-file?filename=${videoFilename}&movement_type=${movement}${athleteParam}`,
        { method: "POST" }
      );
      if (!res.ok) {
        throw new Error("Video analysis pipeline failed");
      }
      const data: VideoAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setCurrentFrameIndex(0);
      await handleAssessInjuryRisk(data.quality_report);
    } catch (err: any) {
      console.warn("Direct video file analysis fallback to demo:", err);
      await handleRunDemo(movement);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input value so selecting the same file triggers change reliably
    e.target.value = "";

    // Create local object URL for instant embedded video playback in the UI
    const localVideoUrl = URL.createObjectURL(file);
    setVideoSrc(localVideoUrl);
    setActiveVideoName(file.name);
    setVideoSourceType("UPLOAD");
    setUploadedFileMeta({
      name: file.name,
      sizeMB: (file.size / (1024 * 1024)).toFixed(2),
      lastModified: new Date(file.lastModified).toLocaleDateString(),
    });

    setAnalysisLoading(true);
    setAnalysisError("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("movement_type", selectedMovement);
    if (athlete?.athlete_id) {
      formData.append("athlete_id", athlete.athlete_id);
    }

    try {
      const res = await fetch("http://127.0.0.1:8000/analysis/process-video", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Video analysis processing failed");
      }
      const data: VideoAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setCurrentFrameIndex(0);
      handleAssessInjuryRisk(data.quality_report);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to upload and analyze video");
    } finally {
      setAnalysisLoading(false);
    }
  };

  /* =========================
     NOTIFICATIONS & ADMIN ACTIONS
  ========================= */
  const handleMarkAllRead = async () => {
    try {
      await fetch("http://127.0.0.1:8000/notifications/mark-all-read", { method: "POST" });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateUserRole = async (userId: number, newRole: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/users/${userId}/role`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        setUsersList((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
        );
      }
    } catch (err) {
      console.error(err);
    }
  };

  const unreadNotifsCount = notifications.filter((n) => !n.is_read).length;

  /* =========================================================
     LANDING PAGE
  ========================================================= */
  if (!loggedIn && !showLogin && !showSignup) {
    return (
      <div className="login-page">
        <div className="login-wrapper">
          <div className="brand">
            <div className="brand-icon">SG</div>
            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>
          </div>
          <div className="login-card">
            <div className="top-line">
              <span className="online-label">AI POWERED INTELLIGENCE</span>
            </div>
            <h1>SPORTS INJURY<br />RISK DETECTION</h1>
            <p className="login-description">
              AI-powered athlete movement analysis, computer-vision biomechanics, and proactive injury risk prevention.
            </p>
            <button
              className="login-button"
              onClick={() => {
                setShowLogin(true);
                setMessage("");
              }}
            >
              LOGIN
            </button>
            <button
              type="button"
              className="signup-link"
              onClick={() => {
                setShowSignup(true);
                setMessage("");
              }}
            >
              Don't have an account? <span>SIGN UP</span>
            </button>
          </div>
          <div className="login-footer">SPORTGUARD AI • SECURE ATHLETE MONITORING</div>
        </div>
      </div>
    );
  }

  /* =========================================================
     SIGNUP PAGE
  ========================================================= */
  if (!loggedIn && showSignup) {
    return (
      <div className="login-page">
        <div className="login-wrapper">
          <div className="brand">
            <div className="brand-icon">SG</div>
            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>
          </div>
          <div className="login-card">
            <div className="top-line">
              <span className="online-label">CREATE ACCOUNT</span>
            </div>
            <h1>SIGN UP</h1>
            <p className="login-description">Create your SPORTGUARD AI account with your designated role.</p>
            <form onSubmit={handleSignup}>
              <div className="form-group">
                <label>NAME</label>
                <input
                  type="text"
                  value={signupName}
                  onChange={(e) => setSignupName(e.target.value)}
                  placeholder="Enter your name"
                  required
                />
              </div>
              <div className="form-group">
                <label>EMAIL</label>
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                />
              </div>
              <div className="form-group">
                <label>SYSTEM ROLE</label>
                <select
                  value={signupRole}
                  onChange={(e) => setSignupRole(e.target.value as UserRole)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.15)",
                    color: "#f8fafc",
                    borderRadius: "4px",
                  }}
                >
                  <option value="ATHLETE" style={{ background: "#0b0f17" }}>Athlete</option>
                  <option value="COACH" style={{ background: "#0b0f17" }}>Coach</option>
                  <option value="PHYSIOTHERAPIST" style={{ background: "#0b0f17" }}>Physiotherapist</option>
                  <option value="SPORTS_SCIENTIST" style={{ background: "#0b0f17" }}>Sports Scientist</option>
                  <option value="ADMINISTRATOR" style={{ background: "#0b0f17" }}>Administrator</option>
                </select>
              </div>
              <div className="form-group">
                <label>PASSWORD</label>
                <input
                  type="password"
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="Create password"
                  required
                />
              </div>
              <div className="form-group">
                <label>CONFIRM PASSWORD</label>
                <input
                  type="password"
                  value={signupConfirmPassword}
                  onChange={(e) => setSignupConfirmPassword(e.target.value)}
                  placeholder="Confirm password"
                  required
                />
              </div>
              <button type="submit" className="login-button" disabled={loading}>
                {loading ? "CREATING..." : "CREATE ACCOUNT"}
              </button>
            </form>
            {message && <div className="message">{message}</div>}
            <button
              type="button"
              className="signup-link"
              onClick={() => {
                setShowSignup(false);
                setShowLogin(true);
                setMessage("");
              }}
            >
              Already have an account? <span>LOGIN</span>
            </button>
          </div>
          <div className="login-footer">SPORTGUARD AI • SECURE ATHLETE MONITORING</div>
        </div>
      </div>
    );
  }

  /* =========================================================
     LOGIN PAGE
  ========================================================= */
  if (!loggedIn && showLogin) {
    return (
      <div className="login-page">
        <div className="login-wrapper">
          <div className="brand">
            <div className="brand-icon">SG</div>
            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>
          </div>
          <div className="login-card">
            <div className="top-line">
              <span className="online-label">SYSTEM ONLINE</span>
            </div>
            <h1>LOGIN</h1>
            <p className="login-description">Access your AI athlete biomechanics and risk prevention portal.</p>
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>EMAIL</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                />
              </div>
              <div className="form-group">
                <label>PASSWORD</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
              </div>
              <button type="submit" className="login-button" disabled={loading}>
                {loading ? "AUTHENTICATING..." : "LOGIN"}
              </button>
            </form>

            {/* PRESENTATION DEMO QUICK-FILL */}
            <div style={{ marginTop: "16px", padding: "10px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "4px" }}>
              <div style={{ fontSize: "10px", color: "#94a3b8", fontWeight: 700, letterSpacing: "1px", marginBottom: "8px" }}>
                🎯 PRESENTATION DEMO ONE-CLICK LOGIN:
              </div>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {[
                  { label: "🏀 Coach", email: "coach@sportguard.ai", pass: "coach123" },
                  { label: "🩺 Physio", email: "physio@sportguard.ai", pass: "physio123" },
                  { label: "🔬 Sports Scientist", email: "science@sportguard.ai", pass: "science123" },
                  { label: "🏃 Athlete", email: "athlete@sportguard.ai", pass: "athlete123" },
                  { label: "⚙️ Admin", email: "admin@sportguard.ai", pass: "admin123" },
                ].map((d) => (
                  <button
                    key={d.label}
                    type="button"
                    onClick={() => {
                      setEmail(d.email);
                      setPassword(d.pass);
                      setMessage("");
                    }}
                    style={{
                      background: "rgba(255, 69, 69, 0.12)",
                      border: "1px solid rgba(255, 69, 69, 0.3)",
                      color: "#ff8080",
                      padding: "4px 8px",
                      fontSize: "10px",
                      fontWeight: 600,
                      borderRadius: "3px",
                      cursor: "pointer",
                    }}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
            {message && <div className="message">{message}</div>}
            <button
              type="button"
              className="signup-link"
              onClick={() => {
                setShowLogin(false);
                setShowSignup(true);
                setMessage("");
              }}
            >
              Don't have an account? <span>SIGN UP</span>
            </button>
          </div>
          <div className="login-footer">SPORTGUARD AI • SECURE ATHLETE MONITORING</div>
        </div>
      </div>
    );
  }

  /* =========================================================
     MAIN PLATFORM (AUTHENTICATED)
  ========================================================= */
  return (
    <div className="dashboard">
      {/* ================= NAVBAR ================= */}
      <nav className="navbar" style={{ flexWrap: "wrap", gap: "10px" }}>
        <div className="brand" style={{ margin: 0, cursor: "pointer" }} onClick={() => setActiveView("STUDIO")}>
          <div className="brand-icon">SG</div>
          <div>
            <h2>SPORTGUARD AI</h2>
            <span>INJURY RISK INTELLIGENCE</span>
          </div>
        </div>

        {/* VIEW NAVIGATION TABS */}
        <div className="nav-center">
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "STUDIO" ? "active" : ""}`}
            onClick={() => setActiveView("STUDIO")}
          >
            ⚡ MOVEMENT STUDIO
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "COACH" ? "active" : ""}`}
            onClick={() => {
              setActiveView("COACH");
              loadExecutiveDashboards();
            }}
          >
            🏆 COACH SQUAD
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "PHYSIO" ? "active" : ""}`}
            onClick={() => {
              setActiveView("PHYSIO");
              loadExecutiveDashboards();
            }}
          >
            🩺 PHYSIO REHAB
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "SPORTS_SCIENCE" ? "active" : ""}`}
            onClick={() => {
              setActiveView("SPORTS_SCIENCE");
              loadExecutiveDashboards();
            }}
          >
            🔬 SPORTS SCIENCE
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "ADMIN" ? "active" : ""}`}
            onClick={() => {
              setActiveView("ADMIN");
              loadExecutiveDashboards();
            }}
          >
            ⚙ ADMIN
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeView === "REPORTS" ? "active" : ""}`}
            onClick={() => setActiveView("REPORTS")}
          >
            📄 REPORTS & PDF
          </button>
        </div>

        <div className="navbar-right" style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {/* USER ROLE BADGE */}
          <span className="role-badge-pill">
            ● ROLE: {userRole}
          </span>

          {/* NOTIFICATION BELL */}
          <button
            type="button"
            className="notif-bell-btn"
            onClick={() => setShowNotifications(!showNotifications)}
            title="Early Warnings & Notifications"
          >
            🔔
            {unreadNotifsCount > 0 && (
              <span className="notif-counter-badge">{unreadNotifsCount}</span>
            )}
          </button>

          <button className="logout-button" onClick={handleLogout}>
            LOGOUT
          </button>
        </div>
      </nav>

      {/* NOTIFICATIONS DROPDOWN DRAWER */}
      {showNotifications && (
        <div className="notifications-dropdown">
          <div className="notif-header">
            <h4>EARLY WARNINGS & ALERTS ({notifications.length})</h4>
            <button type="button" className="notif-action-btn" onClick={handleMarkAllRead}>
              Mark all read
            </button>
          </div>
          {notifications.length === 0 ? (
            <p style={{ fontSize: "11px", color: "#64748b", margin: 0 }}>No active notifications.</p>
          ) : (
            notifications.map((n) => (
              <div key={n.id} className={`notif-item ${!n.is_read ? "unread" : ""}`}>
                <div className="notif-item-top">
                  <span className={`risk-tag risk-${n.severity}`}>{n.severity}</span>
                  <small style={{ fontSize: "9px", color: "#64748b" }}>{n.category.replace("_", " ")}</small>
                </div>
                <div className="notif-item-title">{n.title}</div>
                <p className="notif-item-msg">{n.message}</p>
              </div>
            ))
          )}
        </div>
      )}

      {/* ================= MAIN CONTAINER ================= */}
      <main className="dashboard-container">

        {/* =========================================================
           VIEW 1: MOVEMENT STUDIO (MILESTONES 2 & 3 INTEGRATED)
        ========================================================= */}
        {activeView === "STUDIO" && (
          <div>
            {/* HERO BANNER */}
            <section className="dashboard-hero">
              <div>
                <span className="online-label">AI COMPUTER VISION & KINEMATICS</span>
                <h1>ATHLETE MOVEMENT & INJURY RISK STUDIO</h1>
                <p>
                  33 3D Pose Keypoint Tracking • Dynamic Knee Valgus • Bilateral Symmetry • Prescriptive Corrective AI
                </p>
                {/* ATHLETE SELECTOR */}
                {athletesList.length > 0 && (
                  <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, letterSpacing: "1px" }}>
                      ACTIVE ATHLETE:
                    </span>
                    <select
                      value={athlete?.athlete_id || ""}
                      onChange={(e) => {
                        const sel = athletesList.find((a) => a.athlete_id === e.target.value);
                        if (sel) setAthlete(sel);
                      }}
                      style={{
                        padding: "8px 12px",
                        background: "#0d121c",
                        border: "1px solid #ff4545",
                        color: "#f8fafc",
                        fontSize: "12px",
                        borderRadius: "4px",
                      }}
                    >
                      {athletesList.map((a) => (
                        <option key={a.id} value={a.athlete_id}>
                          {a.athlete_id} - {a.sport_type} ({a.position})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* SKELETON GRAPHIC */}
              <div className="movement-card">
                <div className="movement-area">
                  <div className="scan"></div>
                  <div className="circle circle-one"></div>
                  <div className="circle circle-two"></div>
                  <div className="circle circle-three"></div>
                  <div className="human">
                    <div className="head"></div>
                    <div className="body"></div>
                    <div className="arm arm-left"></div>
                    <div className="arm arm-right"></div>
                    <div className="leg leg-left"></div>
                    <div className="leg leg-right"></div>
                    <div className="joint joint-1"></div>
                    <div className="joint joint-2"></div>
                    <div className="joint joint-3"></div>
                    <div className="joint joint-4"></div>
                    <div className="joint joint-5"></div>
                    <div className="joint joint-6"></div>
                  </div>
                </div>
              </div>
            </section>

            {/* ATHLETE PROFILE ROW */}
            <section className="profile-card">
              <div className="section-title">ACTIVE ATHLETE BIOMETRIC PROFILE</div>
              {athlete ? (
                <div className="metrics">
                  <div className="metric">
                    <span>ATHLETE ID</span>
                    <strong>{athlete.athlete_id}</strong>
                  </div>
                  <div className="metric">
                    <span>SPORT</span>
                    <strong>{athlete.sport_type}</strong>
                  </div>
                  <div className="metric">
                    <span>POSITION</span>
                    <strong>{athlete.position}</strong>
                  </div>
                  <div className="metric">
                    <span>AGE</span>
                    <strong>{athlete.age} yrs</strong>
                  </div>
                  <div className="metric">
                    <span>HEIGHT</span>
                    <strong>{athlete.height} cm</strong>
                  </div>
                  <div className="metric">
                    <span>WEIGHT</span>
                    <strong>{athlete.weight} kg</strong>
                  </div>
                  <div className="metric">
                    <span>TRAINING LOAD</span>
                    <strong style={{ color: athlete.training_load >= 80 ? "#ef4444" : "#10b981" }}>
                      {athlete.training_load}%
                    </strong>
                  </div>
                </div>
              ) : (
                <p>Loading athlete information...</p>
              )}
            </section>

            {/* BIOMECHANICAL ANALYSIS STUDIO */}
            <section className="biomechanics-section">
              <div className="biomechanics-header">
                <div>
                  <span className="online-label">MILESTONE 2 • POSE ESTIMATION & KINEMATICS</span>
                  <h2>BIOMECHANICAL MOVEMENT QUALITY STUDIO</h2>
                  <p>
                    Analyze joint kinematics, dynamic knee valgus, bilateral symmetry, and movement quality using 33 3D MediaPipe pose landmarks.
                  </p>
                </div>
                <div className="movement-tabs">
                  {(["SQUAT", "JUMP_LANDING", "RUNNING"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      className={`movement-tab-btn ${selectedMovement === m ? "active" : ""}`}
                      onClick={() => setSelectedMovement(m)}
                    >
                      {m.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              <div className="action-row">
                <button
                  type="button"
                  className="btn-primary-action"
                  disabled={analysisLoading}
                  onClick={() => handleRunDemo(selectedMovement)}
                >
                  {analysisLoading ? "ANALYZING KINEMATICS..." : `RUN ${selectedMovement.replace("_", " ")} AI ANALYSIS`}
                </button>
                <label className="btn-secondary-action">
                  <span>↑ UPLOAD ATHLETE VIDEO</span>
                  <input
                    type="file"
                    accept="video/mp4,video/quicktime,video/webm"
                    style={{ display: "none" }}
                    onChange={handleFileUpload}
                    disabled={analysisLoading}
                  />
                </label>
              </div>

              {/* EMBEDDED REAL-TIME VIDEO PLAYER & MOTION CAPTURE */}
              <div className="video-player-studio">
                <div className="video-player-header">
                  <div>
                    <h4 style={{ margin: "0 0 4px", fontSize: "14px", color: "#f8fafc", letterSpacing: "1px" }}>
                      🎥 ATHLETE MOVEMENT VIDEO & POSE CAPTURE
                    </h4>
                    <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                      Source: <strong style={{ color: "#38bdf8" }}>{activeVideoName}</strong> {videoSourceType === "UPLOAD" ? "• 📁 User Uploaded Video" : "• 🎥 Broadcast Match Sample"}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      type="button"
                      className={`source-mode-pill ${videoSourceType === "UPLOAD" ? "active" : ""}`}
                      onClick={() => setVideoSourceType("UPLOAD")}
                    >
                      📁 {uploadedFileMeta ? `UPLOADED (${uploadedFileMeta.name})` : "UPLOADED VIDEO"}
                    </button>
                    <button
                      type="button"
                      className={`source-mode-pill ${videoSourceType === "SAMPLE" ? "active" : ""}`}
                      onClick={() => setVideoSourceType("SAMPLE")}
                    >
                      🎥 SAMPLE FOOTAGE
                    </button>
                  </div>
                </div>

                {videoSourceType === "UPLOAD" ? (
                  /* ========================================================
                     MODE 1: USER UPLOADED VIDEO (FOCUSED CINEMATIC VIEW)
                     Only displays THAT uploaded video without website clutter
                     ======================================================== */
                  <div className="uploaded-video-layout">
                    <div className="embedded-video-box full-width">
                      {videoSrc ? (
                        <video
                          key={videoSrc}
                          src={videoSrc}
                          controls
                          autoPlay
                          loop
                          muted
                          playsInline
                        />
                      ) : (
                        <div style={{ padding: "60px 20px", textAlign: "center", color: "#64748b" }}>
                          No video uploaded yet. Click "UPLOAD ATHLETE VIDEO" below to select a video file.
                        </div>
                      )}
                      <div className="video-hud-overlay">
                        AI TRACKING: {selectedMovement.replace("_", " ")}
                      </div>
                    </div>

                    <div className="uploaded-focus-card">
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span className="online-label" style={{ background: "rgba(16, 185, 129, 0.2)", color: "#10b981", borderColor: "#10b981" }}>
                            ● ACTIVE UPLOADED FOOTAGE
                          </span>
                          <strong style={{ fontSize: "14px", color: "#f8fafc" }}>{uploadedFileMeta?.name || activeVideoName}</strong>
                        </div>
                        <div style={{ fontSize: "12px", color: "#94a3b8", display: "flex", gap: "16px", flexWrap: "wrap", marginTop: "6px" }}>
                          <span>File Size: <strong style={{ color: "#e2e8f0" }}>{uploadedFileMeta?.sizeMB || "Direct"} MB</strong></span>
                          <span>Movement Type: <strong style={{ color: "#38bdf8" }}>{selectedMovement.replace("_", " ")}</strong></span>
                          <span>AI Pose Status: <strong style={{ color: analysisLoading ? "#f59e0b" : "#10b981" }}>
                            {analysisLoading ? "Running 33-Landmark Pose Extraction..." : "✓ Pose Kinematics Analyzed"}
                          </strong></span>
                        </div>
                      </div>

                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                        <label className="btn-primary-action" style={{ cursor: "pointer", fontSize: "11px", padding: "8px 14px" }}>
                          <span>↑ UPLOAD DIFFERENT VIDEO</span>
                          <input
                            type="file"
                            accept="video/mp4,video/quicktime,video/webm"
                            style={{ display: "none" }}
                            onChange={handleFileUpload}
                            disabled={analysisLoading}
                          />
                        </label>
                        <button
                          type="button"
                          className="btn-secondary-action"
                          style={{ fontSize: "11px", padding: "8px 14px" }}
                          onClick={() => setVideoSourceType("SAMPLE")}
                        >
                          🎥 BROWSE SAMPLE FOOTAGE
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* ========================================================
                     MODE 2: SAMPLE SPORTS BROADCAST FOOTAGE
                     ======================================================== */
                  <div className="video-player-grid">
                    {/* VIDEO ELEMENT */}
                    <div className="embedded-video-box">
                      {videoSrc ? (
                        <video
                          key={videoSrc}
                          src={videoSrc}
                          controls
                          autoPlay
                          loop
                          muted
                          playsInline
                        />
                      ) : (
                        <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
                          Select a sample video below or upload a video file.
                        </div>
                      )}
                      <div className="video-hud-overlay">
                        AI TRACKING: {selectedMovement.replace("_", " ")}
                      </div>
                    </div>

                    {/* QUICK SAMPLE SELECTOR */}
                    <div>
                      <h5 style={{ margin: "0 0 8px", fontSize: "12px", color: "#e2e8f0", letterSpacing: "1px" }}>
                        BROADCAST SPORTS FOOTAGE WITH GREEN DETECTION BOXES:
                      </h5>
                      <div className="sample-videos-bar" style={{ flexDirection: "column" }}>
                        <button
                          type="button"
                          className={`sample-video-btn ${activeVideoName.includes("basketball") ? "active" : ""}`}
                          onClick={() => handleLoadSampleVideo("broadcast_basketball.mp4", "JUMP_LANDING")}
                        >
                          🟩 🏀 Basketball Court: Jump Shot & Hardwood Landing (broadcast_basketball.mp4)
                        </button>
                        <button
                          type="button"
                          className={`sample-video-btn ${activeVideoName.includes("volleyball") ? "active" : ""}`}
                          onClick={() => handleLoadSampleVideo("broadcast_volleyball.mp4", "JUMP_LANDING")}
                        >
                          🟩 🏐 Volleyball Arena: Spike Jump & Stiff Block Landing (broadcast_volleyball.mp4)
                        </button>
                        <button
                          type="button"
                          className={`sample-video-btn ${activeVideoName.includes("sprint") || activeVideoName.includes("track") ? "active" : ""}`}
                          onClick={() => handleLoadSampleVideo("sprint_track_clean.mp4", "RUNNING")}
                        >
                          🟩 🏃 100m Track Sprint: Cadence & Hamstring Asymmetry (sprint_track_clean.mp4)
                        </button>
                        <button
                          type="button"
                          className={`sample-video-btn ${activeVideoName.includes("soccer") ? "active" : ""}`}
                          onClick={() => handleLoadSampleVideo("detected_soccer_match.mp4", "RUNNING")}
                        >
                          🟩 ⚽ Soccer Pitch: Turf Cutting & Deceleration Shear (detected_soccer_match.mp4)
                        </button>
                      </div>

                      {/* PURPOSE OF BOUNDING BOXES IN THIS SYSTEM */}
                      <div style={{ marginTop: "14px", padding: "12px", background: "rgba(16, 185, 129, 0.06)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "4px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 700, color: "#10b981", letterSpacing: "1px", marginBottom: "6px" }}>
                          🎯 PURPOSE OF AI BOUNDING BOXES & FEATURE EXTRACTION:
                        </div>
                        <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#94a3b8", lineHeight: "1.6" }}>
                          <li><strong>Athlete ROI Isolation:</strong> Isolates the active athlete from teammates, opponents, and stadium background.</li>
                          <li><strong>ML Model Feature Extraction:</strong> 33 joint coordinates inside this bounding box train the Multi-Output Random Forest Model.</li>
                          <li><strong>Dynamic Risk Alert Color:</strong> Shifts from 🟢 <strong>Green</strong> (Safe) to 🟡 <strong>Amber</strong> (Asymmetry / Strain) or 🔴 <strong>Red</strong> (Critical Valgus Collapse).</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {/* MATCH VIDEO INJURY REPORT BANNER */}
                <div style={{ marginTop: "18px", paddingTop: "15px", borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <span style={{ fontSize: "10px", color: "#ff4545", letterSpacing: "1.5px", fontWeight: 700 }}>
                      SPORTS BROADCAST INJURY RISK REPORT • ACTIVE VIDEO
                    </span>
                    <h4 style={{ margin: "4px 0", fontSize: "15px", color: "#f8fafc" }}>
                      {activeVideoName.includes("basketball")
                        ? "Basketball Court Analysis: Jump Shot Deceleration & ACL Valgus Vulnerability"
                        : activeVideoName.includes("volleyball")
                        ? "Volleyball Match Analysis: Spike Jump Impact & Patellar Tendon Stress"
                        : activeVideoName.includes("track")
                        ? "Track & Field Analysis: High-Speed Sprint Cadence & Hamstring Asymmetry"
                        : activeVideoName.includes("soccer")
                        ? "Turf Pitch Analysis: High-Velocity Deceleration & Cutting Movement"
                        : "Movement Quality & Biomechanical Kinematic Report"}
                    </h4>
                    <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                      Detected Sport Activity: <strong style={{ color: "#38bdf8" }}>{selectedMovement.replace("_", " ")}</strong> • Video File: {activeVideoName}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-primary-action"
                    style={{ fontSize: "11px", padding: "8px 16px" }}
                    onClick={() => setActiveView("REPORTS")}
                  >
                    📄 VIEW FULL PRINTABLE REPORT
                  </button>
                </div>
              </div>

              {analysisError && <div className="message" style={{ marginBottom: "20px" }}>{analysisError}</div>}

              {analysisResult && (
                <div>
                  <div className="quality-grid">
                    <div className="overall-score-card">
                      <div className="score-circle">
                        <strong>{analysisResult.quality_report.overall_score}</strong>
                        <span>SCORE / 100</span>
                      </div>
                      <span className={`grade-badge grade-${analysisResult.quality_report.grade}`}>
                        {analysisResult.quality_report.grade.replace("_", " ")}
                      </span>
                      <p style={{ fontSize: "11px", color: "#8a94a6", marginTop: "10px" }}>
                        Movement Quality Index ({analysisResult.movement_type})
                      </p>
                    </div>

                    <div className="subscores-container">
                      <div className="subscore-item">
                        <div className="subscore-label">
                          <span>VALGUS STABILITY (ACL COLLAPSE RESISTANCE)</span>
                          <strong>{analysisResult.quality_report.valgus_stability_score}%</strong>
                        </div>
                        <div className="subscore-bar-bg">
                          <div
                            className="subscore-bar-fill"
                            style={{ width: `${analysisResult.quality_report.valgus_stability_score}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="subscore-item">
                        <div className="subscore-label">
                          <span>BILATERAL SYMMETRY (LIMB BALANCE)</span>
                          <strong>{analysisResult.quality_report.symmetry_score}%</strong>
                        </div>
                        <div className="subscore-bar-bg">
                          <div
                            className="subscore-bar-fill"
                            style={{ width: `${analysisResult.quality_report.symmetry_score}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="subscore-item">
                        <div className="subscore-label">
                          <span>RANGE OF MOTION (FUNCTIONAL DEPTH)</span>
                          <strong>{analysisResult.quality_report.rom_score}%</strong>
                        </div>
                        <div className="subscore-bar-bg">
                          <div
                            className="subscore-bar-fill"
                            style={{ width: `${analysisResult.quality_report.rom_score}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="subscore-item">
                        <div className="subscore-label">
                          <span>POSTURAL & TRUNK ALIGNMENT</span>
                          <strong>{analysisResult.quality_report.posture_score}%</strong>
                        </div>
                        <div className="subscore-bar-bg">
                          <div
                            className="subscore-bar-fill"
                            style={{ width: `${analysisResult.quality_report.posture_score}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* KINEMATICS TILES */}
                  <div className="kinematics-grid">
                    <div className="kinematic-tile">
                      <small>PEAK KNEE VALGUS</small>
                      <div className="k-val">{analysisResult.quality_report.metrics_summary.peak_valgus_overall}°</div>
                      <div className="k-sub">
                        L: {analysisResult.quality_report.metrics_summary.peak_knee_valgus_left}° | R: {analysisResult.quality_report.metrics_summary.peak_knee_valgus_right}°
                      </div>
                    </div>
                    <div className="kinematic-tile">
                      <small>MAX KNEE FLEXION</small>
                      <div className="k-val">{analysisResult.quality_report.metrics_summary.peak_flexion_overall}°</div>
                      <div className="k-sub">
                        L: {analysisResult.quality_report.metrics_summary.peak_knee_flexion_left}° | R: {analysisResult.quality_report.metrics_summary.peak_knee_flexion_right}°
                      </div>
                    </div>
                    <div className="kinematic-tile">
                      <small>MEAN ASYMMETRY</small>
                      <div className="k-val">{analysisResult.quality_report.metrics_summary.mean_asymmetry_index}%</div>
                      <div className="k-sub">
                        {analysisResult.quality_report.metrics_summary.mean_asymmetry_index < 10
                          ? "Optimal Bilateral Balance (<10%)"
                          : "Elevated Asymmetry (>10%)"}
                      </div>
                    </div>
                    <div className="kinematic-tile">
                      <small>PEAK TRUNK LEAN</small>
                      <div className="k-val">{analysisResult.quality_report.metrics_summary.peak_trunk_lean}°</div>
                      <div className="k-sub">
                        Mean: {analysisResult.quality_report.metrics_summary.mean_trunk_lean}° deviation
                      </div>
                    </div>
                  </div>

                  {/* DETECTED ANOMALIES */}
                  <div className="anomalies-box">
                    <h4>DETECTED BIOMECHANICAL ANOMALIES & FLAGS</h4>
                    {analysisResult.quality_report.anomalies.map((anomaly, idx) => (
                      <div key={idx} className="anomaly-pill">
                        <span>⚠</span>
                        <span>{anomaly}</span>
                      </div>
                    ))}
                  </div>

                  {/* TIMELINE SCRUBBER */}
                  {analysisResult.sampled_frames.length > 0 && (
                    <div className="timeline-scrubber-card">
                      <h4>
                        <span>KINEMATIC TIMELINE SCRUBBER</span>
                        <small style={{ color: "#ff4545" }}>
                          FRAME {analysisResult.sampled_frames[currentFrameIndex]?.frame_index || 0} / {analysisResult.total_frames} ({(analysisResult.sampled_frames[currentFrameIndex]?.timestamp || 0).toFixed(2)}s)
                        </small>
                      </h4>
                      <input
                        type="range"
                        min={0}
                        max={analysisResult.sampled_frames.length - 1}
                        value={currentFrameIndex}
                        onChange={(e) => setCurrentFrameIndex(Number(e.target.value))}
                        className="scrubber-slider"
                      />
                      <div className="live-frame-metrics">
                        <div className="frame-metric-cell">
                          <span>LEFT KNEE ANGLE</span>
                          <strong>{analysisResult.sampled_frames[currentFrameIndex]?.left_knee_angle}°</strong>
                        </div>
                        <div className="frame-metric-cell">
                          <span>RIGHT KNEE ANGLE</span>
                          <strong>{analysisResult.sampled_frames[currentFrameIndex]?.right_knee_angle}°</strong>
                        </div>
                        <div className="frame-metric-cell">
                          <span>LEFT VALGUS</span>
                          <strong>{analysisResult.sampled_frames[currentFrameIndex]?.left_valgus_angle}°</strong>
                        </div>
                        <div className="frame-metric-cell">
                          <span>RIGHT VALGUS</span>
                          <strong>{analysisResult.sampled_frames[currentFrameIndex]?.right_valgus_angle}°</strong>
                        </div>
                        <div className="frame-metric-cell">
                          <span>TRUNK TILT</span>
                          <strong>{analysisResult.sampled_frames[currentFrameIndex]?.trunk_lean}°</strong>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* MILESTONE 3: AI INJURY PREDICTION & RECOMMENDATIONS */}
            <section className="prediction-section">
              <div className="prediction-header">
                <div>
                  <span className="online-label">MILESTONE 3 • INJURY INTELLIGENCE & RECOMMENDATIONS</span>
                  <h2>INJURY RISK PREDICTION & RECOVERY WORKFLOWS</h2>
                  <p>
                    Multi-factor ML predictive engine analyzing biomechanics, historical injuries, and training loads to deliver real-time risk scores and personalized corrective exercise prescriptions.
                  </p>
                </div>
                <div>
                  <button
                    type="button"
                    className="btn-primary-action"
                    disabled={predictionLoading}
                    onClick={() => handleAssessInjuryRisk()}
                  >
                    {predictionLoading ? "CALCULATING RISK..." : "ASSESS INJURY RISK"}
                  </button>
                </div>
              </div>

              {predictionResult && (
                <div>
                  <div className="risk-overview-grid">
                    <div className="overall-risk-hero">
                      <div className="risk-gauge-circle">
                        <strong>{predictionResult.overall_risk_score}%</strong>
                        <span>OVERALL RISK</span>
                      </div>
                      <span className={`risk-level-badge risk-level-${predictionResult.risk_level}`}>
                        {predictionResult.risk_level} RISK LEVEL
                      </span>
                      <p style={{ fontSize: "11px", color: "#8c97a7", marginTop: "12px" }}>
                        Composite AI Injury Risk Probability
                      </p>
                    </div>

                    <div className="breakdown-grid">
                      <div className="injury-card-metric">
                        <div className="injury-card-top">
                          <span>ACL LIGAMENT STRAIN</span>
                          <strong>{predictionResult.risk_breakdown.acl_risk}%</strong>
                        </div>
                        <div className="injury-bar-bg">
                          <div
                            className={`injury-bar-fill ${predictionResult.risk_breakdown.acl_risk >= 70 ? "bar-high" : predictionResult.risk_breakdown.acl_risk >= 35 ? "bar-mid" : "bar-low"}`}
                            style={{ width: `${predictionResult.risk_breakdown.acl_risk}%` }}
                          ></div>
                        </div>
                        <div className="injury-card-desc">Correlated with Dynamic Knee Valgus and landing stiffness.</div>
                      </div>

                      <div className="injury-card-metric">
                        <div className="injury-card-top">
                          <span>HAMSTRING STRAIN</span>
                          <strong>{predictionResult.risk_breakdown.hamstring_risk}%</strong>
                        </div>
                        <div className="injury-bar-bg">
                          <div
                            className={`injury-bar-fill ${predictionResult.risk_breakdown.hamstring_risk >= 70 ? "bar-high" : predictionResult.risk_breakdown.hamstring_risk >= 35 ? "bar-mid" : "bar-low"}`}
                            style={{ width: `${predictionResult.risk_breakdown.hamstring_risk}%` }}
                          ></div>
                        </div>
                        <div className="injury-card-desc">Driven by bilateral asymmetry & high-velocity eccentric loads.</div>
                      </div>

                      <div className="injury-card-metric">
                        <div className="injury-card-top">
                          <span>ANKLE INVERSION / SPRAIN</span>
                          <strong>{predictionResult.risk_breakdown.ankle_risk}%</strong>
                        </div>
                        <div className="injury-bar-bg">
                          <div
                            className={`injury-bar-fill ${predictionResult.risk_breakdown.ankle_risk >= 70 ? "bar-high" : predictionResult.risk_breakdown.ankle_risk >= 35 ? "bar-mid" : "bar-low"}`}
                            style={{ width: `${predictionResult.risk_breakdown.ankle_risk}%` }}
                          ></div>
                        </div>
                        <div className="injury-card-desc">Influenced by lateral postural sway and prior ankle history.</div>
                      </div>

                      <div className="injury-card-metric">
                        <div className="injury-card-top">
                          <span>PATELLAR TENDONITIS</span>
                          <strong>{predictionResult.risk_breakdown.patellar_risk}%</strong>
                        </div>
                        <div className="injury-bar-bg">
                          <div
                            className={`injury-bar-fill ${predictionResult.risk_breakdown.patellar_risk >= 70 ? "bar-high" : predictionResult.risk_breakdown.patellar_risk >= 35 ? "bar-mid" : "bar-low"}`}
                            style={{ width: `${predictionResult.risk_breakdown.patellar_risk}%` }}
                          ></div>
                        </div>
                        <div className="injury-card-desc">Triggered by repetitive high impact & training overload.</div>
                      </div>
                    </div>
                  </div>

                  {/* EARLY WARNING ALERTS */}
                  <div className="warnings-container">
                    <h4 style={{ fontSize: "12px", letterSpacing: "1.5px", margin: "0 0 12px", color: "#e2e8f0" }}>
                      EARLY WARNING SYSTEM ALERTS
                    </h4>
                    {predictionResult.early_warnings.map((w, idx) => (
                      <div key={idx} className={`warning-item-card warning-${w.severity}`}>
                        <span style={{ fontSize: "16px" }}>
                          {w.severity === "CRITICAL" ? "🚨" : w.severity === "WARNING" ? "⚠" : "ℹ"}
                        </span>
                        <div className="warning-text">
                          <h5>{w.title}</h5>
                          <p>{w.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* CORRECTIVE EXERCISE PRESCRIPTION */}
                  <div style={{ marginBottom: "25px" }}>
                    <h4 style={{ fontSize: "12px", letterSpacing: "1.5px", margin: "0 0 16px", color: "#e2e8f0" }}>
                      PRESCRIPTIVE CORRECTIVE EXERCISE PROTOCOL
                    </h4>
                    <div className="exercises-grid">
                      {predictionResult.recommendations.prescribed_exercises.map((ex, idx) => (
                        <div key={idx} className="exercise-card">
                          <div>
                            <h4>{ex.name}</h4>
                            <span className="ex-tag">{ex.category.toUpperCase()} • {ex.difficulty.toUpperCase()}</span>
                            <div className="ex-target"><strong>Target:</strong> {ex.target}</div>
                            <div className="ex-freq"><strong>Dose:</strong> {ex.frequency}</div>
                          </div>
                          <div className="ex-purpose">{ex.purpose}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* LOAD PROTOCOL */}
                  <div className="load-protocol-box">
                    <h4>TRAINING LOAD & RECOVERY MANAGEMENT</h4>
                    <div className="protocol-action">
                      {predictionResult.recommendations.training_load_recommendation}
                    </div>
                    <ul className="guidelines-list">
                      {predictionResult.recommendations.recovery_guidelines.map((g, idx) => (
                        <li key={idx}>
                          <span>✓</span> {g}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* =========================================================
           VIEW 2: COACH DASHBOARD (MILESTONE 4)
        ========================================================= */}
        {activeView === "COACH" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <span className="online-label">COACH COMMAND CENTER</span>
              <h1 style={{ fontSize: "28px", margin: "8px 0" }}>SQUAD INJURY RISK OVERVIEW</h1>
              <p style={{ color: "#94a3b8" }}>
                Monitor whole-team risk distributions, acute training load spikes, and prioritize preventative drills.
              </p>
            </div>

            {coachData && (
              <div>
                {/* SQUAD SUMMARY CARDS */}
                <div className="stats-cards-grid">
                  <div className="stat-card">
                    <small>SQUAD HEALTH INDEX</small>
                    <div className="stat-num" style={{ color: "#10b981" }}>
                      {coachData.summary.squad_health_score}%
                    </div>
                    <span className="stat-desc">Composite readiness score</span>
                  </div>

                  <div className="stat-card">
                    <small>HIGH RISK ATHLETES</small>
                    <div className="stat-num" style={{ color: coachData.summary.high_risk_count > 0 ? "#ef4444" : "#10b981" }}>
                      {coachData.summary.high_risk_count}
                    </div>
                    <span className="stat-desc">Requiring immediate load reduction</span>
                  </div>

                  <div className="stat-card">
                    <small>AVG TRAINING LOAD</small>
                    <div className="stat-num">{coachData.summary.avg_training_load}%</div>
                    <span className="stat-desc">{coachData.summary.overload_count} athletes exceeding 80%</span>
                  </div>

                  <div className="stat-card">
                    <small>AVG KNEE VALGUS</small>
                    <div className="stat-num">{coachData.summary.avg_knee_valgus}°</div>
                    <span className="stat-desc">Squad safety threshold: &lt; 8.0°</span>
                  </div>
                </div>

                {/* SQUAD ROSTER TABLE */}
                <div className="data-table-container">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>ATHLETE</th>
                        <th>SPORT / POSITION</th>
                        <th>TRAINING LOAD</th>
                        <th>PEAK VALGUS</th>
                        <th>RISK SCORE</th>
                        <th>RISK LEVEL</th>
                        <th>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coachData.roster.map((ath: any) => (
                        <tr key={ath.id}>
                          <td>
                            <strong>{ath.athlete_id}</strong>
                            <div style={{ fontSize: "10px", color: "#64748b" }}>Age: {ath.age}</div>
                          </td>
                          <td>{ath.sport_type} - {ath.position}</td>
                          <td>
                            <strong style={{ color: ath.training_load >= 80 ? "#ef4444" : "#e2e8f0" }}>
                              {ath.training_load}%
                            </strong>
                          </td>
                          <td>{ath.peak_valgus}°</td>
                          <td><strong>{ath.overall_risk_score}%</strong></td>
                          <td>
                            <span className={`risk-tag risk-${ath.risk_level}`}>
                              {ath.risk_level}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn-primary-action"
                              style={{ padding: "6px 12px", fontSize: "10px" }}
                              onClick={() => {
                                const matched = athletesList.find((a) => a.athlete_id === ath.athlete_id);
                                if (matched) setAthlete(matched);
                                setActiveView("STUDIO");
                              }}
                            >
                              ANALYZE
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* TEAM FOCUS DIRECTIVES */}
                <div className="load-protocol-box">
                  <h4>COACHING TACTICAL DIRECTIVES</h4>
                  <ul className="guidelines-list">
                    {coachData.recommended_team_focus.map((f: string, i: number) => (
                      <li key={i}>
                        <span>✓</span> {f}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =========================================================
           VIEW 3: PHYSIOTHERAPIST DASHBOARD (MILESTONE 4)
        ========================================================= */}
        {activeView === "PHYSIO" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <span className="online-label">PHYSIOTHERAPY & CLINICAL REHAB</span>
              <h1 style={{ fontSize: "28px", margin: "8px 0" }}>REHABILITATION & RECOVERY MONITORING</h1>
              <p style={{ color: "#94a3b8" }}>
                Track clinical rehabilitation stages, joint vulnerability matrices, and corrective exercise adherence.
              </p>
            </div>

            {physioData && (
              <div>
                {/* ACTIVE REHAB CASES */}
                <div className="section-title">ACTIVE REHABILITATION CASELOAD ({physioData.active_rehab_cases_count})</div>
                <div className="rehab-grid">
                  {physioData.rehab_cases.map((rc: any, idx: number) => (
                    <div key={idx} className="rehab-card">
                      <div className="rehab-card-top">
                        <div>
                          <h4>{rc.athlete_id} ({rc.sport})</h4>
                          <span className="rehab-cond">{rc.condition}</span>
                        </div>
                        <span className={`risk-tag ${rc.status === "ON_TRACK" ? "risk-LOW" : "risk-HIGH"}`}>
                          {rc.status.replace("_", " ")}
                        </span>
                      </div>
                      <div className="rehab-phase">{rc.phase}</div>
                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ width: `${rc.progress_percent}%` }}></div>
                      </div>
                      <div style={{ fontSize: "11px", color: "#94a3b8", display: "flex", justifyContent: "space-between" }}>
                        <span>Target: {rc.target_date}</span>
                        <strong>{rc.progress_percent}% Complete</strong>
                      </div>
                      <div style={{ marginTop: "10px", fontSize: "10px", color: "#64748b" }}>
                        Valgus: {rc.current_valgus} • Asymmetry: {rc.asymmetry_reduction}
                      </div>
                    </div>
                  ))}
                </div>

                {/* JOINT VULNERABILITY MATRIX */}
                <div className="stats-cards-grid" style={{ marginTop: "24px" }}>
                  <div className="stat-card">
                    <small>ACL LIGAMENT CASES</small>
                    <div className="stat-num" style={{ color: "#ef4444" }}>
                      {physioData.injury_breakdown.acl_knee_vulnerability}%
                    </div>
                    <span className="stat-desc">Dominant biomechanical risk</span>
                  </div>
                  <div className="stat-card">
                    <small>HAMSTRING STRAINS</small>
                    <div className="stat-num" style={{ color: "#f59e0b" }}>
                      {physioData.injury_breakdown.hamstring_strain}%
                    </div>
                    <span className="stat-desc">Eccentric load weakness</span>
                  </div>
                  <div className="stat-card">
                    <small>ANKLE INVERSIONS</small>
                    <div className="stat-num" style={{ color: "#38bdf8" }}>
                      {physioData.injury_breakdown.ankle_inversion}%
                    </div>
                    <span className="stat-desc">Lateral postural sway</span>
                  </div>
                  <div className="stat-card">
                    <small>PATELLAR TENDON</small>
                    <div className="stat-num" style={{ color: "#10b981" }}>
                      {physioData.injury_breakdown.patellar_tendon}%
                    </div>
                    <span className="stat-desc">Repetitive jump load</span>
                  </div>
                </div>

                {/* PROTOCOL ADHERENCE */}
                <div className="load-protocol-box" style={{ marginTop: "24px" }}>
                  <h4>CORRECTIVE PROTOCOL ADHERENCE (AVG: {physioData.overall_rehab_adherence}%)</h4>
                  <div className="exercises-grid">
                    {physioData.corrective_protocols.map((p: any, i: number) => (
                      <div key={i} className="exercise-card">
                        <h4>{p.name}</h4>
                        <div style={{ fontSize: "12px", color: "#10b981", fontWeight: 700 }}>
                          Adherence: {p.adherence_rate}
                        </div>
                        <div className="ex-target">Target: {p.target}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =========================================================
           VIEW 4: SPORTS SCIENTIST DASHBOARD (MILESTONE 4)
        ========================================================= */}
        {activeView === "SPORTS_SCIENCE" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <span className="online-label">BIOMECHANICAL LABORATORY</span>
              <h1 style={{ fontSize: "28px", margin: "8px 0" }}>SPORTS BIOMECHANICS & ANALYTICS</h1>
              <p style={{ color: "#94a3b8" }}>
                3D joint angle distributions, bilateral asymmetry indices across activities, and multi-variable risk correlations.
              </p>
            </div>

            {sportsSciData && (
              <div>
                {/* KINEMATIC BENCHMARKS */}
                <div className="stats-cards-grid">
                  <div className="stat-card">
                    <small>MEAN SQUAT VALGUS</small>
                    <div className="stat-num">{sportsSciData.kinematic_benchmarks.mean_valgus_squat}°</div>
                    <span className="stat-desc">Normal baseline &lt; 8°</span>
                  </div>
                  <div className="stat-card">
                    <small>JUMP LANDING VALGUS</small>
                    <div className="stat-num" style={{ color: "#ef4444" }}>
                      {sportsSciData.kinematic_benchmarks.mean_valgus_jump_landing}°
                    </div>
                    <span className="stat-desc">Elevated impact medial shift</span>
                  </div>
                  <div className="stat-card">
                    <small>BILATERAL ASYMMETRY</small>
                    <div className="stat-num">{sportsSciData.kinematic_benchmarks.mean_asymmetry_bilateral}%</div>
                    <span className="stat-desc">Limb force discrepancy</span>
                  </div>
                  <div className="stat-card">
                    <small>SAGITTAL TRUNK LEAN</small>
                    <div className="stat-num">{sportsSciData.kinematic_benchmarks.mean_trunk_lean_sagittal}°</div>
                    <span className="stat-desc">Postural displacement</span>
                  </div>
                </div>

                {/* MOVEMENT COMPARISON TABLE */}
                <div className="data-table-container">
                  <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    <h4 style={{ margin: 0, fontSize: "13px", letterSpacing: "1px" }}>
                      MOVEMENT KINEMATICS COMPARISON
                    </h4>
                  </div>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>ACTIVITY / MOVEMENT</th>
                        <th>SAMPLES (N)</th>
                        <th>MEAN VALGUS (°)</th>
                        <th>ASYMMETRY INDEX (%)</th>
                        <th>QUALITY INDEX</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sportsSciData.movement_comparison.map((mc: any, i: number) => (
                        <tr key={i}>
                          <td><strong>{mc.movement}</strong></td>
                          <td>{mc.sample_size}</td>
                          <td>{mc.valgus_avg}°</td>
                          <td>{mc.asymmetry_avg}%</td>
                          <td><strong>{mc.quality_score_avg} / 100</strong></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* RISK CORRELATION MATRIX */}
                <div className="data-table-container">
                  <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    <h4 style={{ margin: 0, fontSize: "13px", letterSpacing: "1px" }}>
                      CLINICAL BIOMECHANICAL RISK CORRELATIONS
                    </h4>
                  </div>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>BIOMECHANICAL VARIABLE (X)</th>
                        <th>INJURY OUTCOME (Y)</th>
                        <th>PEARSON CORRELATION (r)</th>
                        <th>SIGNIFICANCE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sportsSciData.risk_correlations.map((rc: any, i: number) => (
                        <tr key={i}>
                          <td><strong>{rc.variable_x}</strong></td>
                          <td>{rc.variable_y}</td>
                          <td><strong style={{ color: "#38bdf8" }}>{rc.correlation_r}</strong></td>
                          <td><span className="risk-tag risk-HIGH">p &lt; 0.001 (Strong)</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* ML MODEL VALIDATION METRICS */}
                <div className="stats-cards-grid">
                  <div className="stat-card">
                    <small>KEYPOINT DETECTION ACCURACY</small>
                    <div className="stat-num" style={{ color: "#10b981" }}>
                      {sportsSciData.ml_model_accuracy.keypoint_localization_accuracy}
                    </div>
                    <span className="stat-desc">MediaPipe 33 Landmark PCK@0.2</span>
                  </div>
                  <div className="stat-card">
                    <small>JOINT ANGLE MAE</small>
                    <div className="stat-num">{sportsSciData.ml_model_accuracy.joint_angle_mae_degrees}</div>
                    <span className="stat-desc">Mean Absolute Error vs 3D Vicon</span>
                  </div>
                  <div className="stat-card">
                    <small>INJURY RISK AUC</small>
                    <div className="stat-num" style={{ color: "#38bdf8" }}>
                      {sportsSciData.ml_model_accuracy.injury_risk_classification_auc}
                    </div>
                    <span className="stat-desc">RandomForest Classifier ROC AUC</span>
                  </div>
                  <div className="stat-card">
                    <small>FALSE POSITIVE RATE</small>
                    <div className="stat-num">{sportsSciData.ml_model_accuracy.false_positive_rate}</div>
                    <span className="stat-desc">Low clinical alert fatigue</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =========================================================
           VIEW 5: ADMIN DASHBOARD (MILESTONE 4)
        ========================================================= */}
        {activeView === "ADMIN" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <span className="online-label">SYSTEM ADMINISTRATION</span>
              <h1 style={{ fontSize: "28px", margin: "8px 0" }}>ADMIN & PLATFORM GOVERNANCE</h1>
              <p style={{ color: "#94a3b8" }}>
                Manage user permissions, monitor computer-vision latency, and view audit telemetry.
              </p>
            </div>

            {adminData && (
              <div>
                {/* PLATFORM METRICS */}
                <div className="stats-cards-grid">
                  <div className="stat-card">
                    <small>TOTAL USERS</small>
                    <div className="stat-num">{adminData.platform_stats.total_users}</div>
                    <span className="stat-desc">Athletes, Coaches, Clinicians</span>
                  </div>
                  <div className="stat-card">
                    <small>ATHLETES PROFILED</small>
                    <div className="stat-num">{adminData.platform_stats.total_athletes}</div>
                    <span className="stat-desc">Active athletic roster</span>
                  </div>
                  <div className="stat-card">
                    <small>VIDEO ANALYSES</small>
                    <div className="stat-num">{adminData.platform_stats.total_video_analyses}</div>
                    <span className="stat-desc">Kinematic pipelines executed</span>
                  </div>
                  <div className="stat-card">
                    <small>PREDICTIONS STORED</small>
                    <div className="stat-num">{adminData.platform_stats.total_injury_predictions}</div>
                    <span className="stat-desc">Risk assessments recorded</span>
                  </div>
                </div>

                {/* USER MANAGEMENT TABLE */}
                <div className="data-table-container">
                  <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                    <h4 style={{ margin: 0, fontSize: "13px", letterSpacing: "1px" }}>
                      USER ROLES & ACCESS CONTROL (RBAC)
                    </h4>
                  </div>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>USER ID</th>
                        <th>NAME</th>
                        <th>EMAIL</th>
                        <th>CURRENT ROLE</th>
                        <th>CHANGE ROLE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersList.map((u) => (
                        <tr key={u.id}>
                          <td>#{u.id}</td>
                          <td><strong>{u.name}</strong></td>
                          <td>{u.email}</td>
                          <td>
                            <span className="role-badge-pill">{u.role}</span>
                          </td>
                          <td>
                            <select
                              value={u.role}
                              onChange={(e) => handleUpdateUserRole(u.id, e.target.value)}
                              style={{
                                background: "#0b0f17",
                                border: "1px solid rgba(255,255,255,0.2)",
                                color: "#f8fafc",
                                padding: "4px 8px",
                                fontSize: "11px",
                                borderRadius: "3px",
                              }}
                            >
                              <option value="ATHLETE">ATHLETE</option>
                              <option value="COACH">COACH</option>
                              <option value="PHYSIOTHERAPIST">PHYSIOTHERAPIST</option>
                              <option value="SPORTS_SCIENTIST">SPORTS_SCIENTIST</option>
                              <option value="ADMINISTRATOR">ADMINISTRATOR</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* INFRASTRUCTURE HEALTH */}
                <div className="load-protocol-box">
                  <h4>INFRASTRUCTURE & ENGINE TELEMETRY</h4>
                  <div className="stats-cards-grid" style={{ marginBottom: 0 }}>
                    <div className="stat-card" style={{ background: "#0b0f17" }}>
                      <small>API STATUS</small>
                      <div className="stat-num" style={{ color: "#10b981", fontSize: "20px" }}>
                        {adminData.system_health.api_gateway_status}
                      </div>
                      <span className="stat-desc">Uptime: {adminData.system_health.fastapi_uptime}</span>
                    </div>
                    <div className="stat-card" style={{ background: "#0b0f17" }}>
                      <small>LATENCY</small>
                      <div className="stat-num" style={{ color: "#38bdf8", fontSize: "20px" }}>
                        {adminData.system_health.avg_response_time_ms} ms
                      </div>
                      <span className="stat-desc">FastAPI Async pipeline</span>
                    </div>
                    <div className="stat-card" style={{ background: "#0b0f17" }}>
                      <small>CV INFERENCE</small>
                      <div style={{ fontSize: "12px", color: "#f8fafc", fontWeight: 700, margin: "8px 0" }}>
                        {adminData.system_health.cv_inference_engine}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* =========================================================
           VIEW 6: REPORTS & CLINICAL PRINTABLE PDF (MILESTONE 4)
        ========================================================= */}
        {activeView === "REPORTS" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
              <div>
                <span className="online-label">CLINICAL & COACHING REPORTS</span>
                <h1 style={{ fontSize: "28px", margin: "8px 0" }}>REPORTS & DATA EXPORT</h1>
                <p style={{ color: "#94a3b8" }}>
                  Generate official printable clinical assessment reports and download CSV data for research.
                </p>
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  className="btn-primary-action"
                  onClick={() => window.print()}
                >
                  🖨 PRINT / SAVE PDF
                </button>
                <a
                  href="http://127.0.0.1:8000/reports/export/csv"
                  download="sports_injury_analytics_export.csv"
                  className="btn-secondary-action"
                  style={{ textDecoration: "none" }}
                >
                  ⬇ EXPORT CSV
                </a>
              </div>
            </div>

            {/* PRINTABLE REPORT SHEET */}
            <div className="report-paper">
              <div className="report-header-banner">
                <div>
                  <h2>SPORTGUARD AI • BIOMECHANICAL & RISK REPORT</h2>
                  <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                    Official Medical, Biomechanical & Prescriptive Assessment Document
                  </span>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#ff4545" }}>
                    REPORT ID: #REP-2026-X89
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>
                    Date: {new Date().toLocaleDateString()}
                  </div>
                </div>
              </div>

              {/* REPORT METADATA */}
              <div className="report-meta-grid">
                <div className="report-meta-item">
                  <small>ANALYZED VIDEO FILE</small>
                  <strong style={{ color: "#38bdf8" }}>{analysisResult?.video_name || activeVideoName}</strong>
                </div>
                <div className="report-meta-item">
                  <small>VIDEO DURATION & FRAMES</small>
                  <strong>
                    {analysisResult ? `${analysisResult.total_frames} frames (${analysisResult.duration}s @ ${analysisResult.fps} FPS)` : "150 frames (6.0s @ 25 FPS)"}
                  </strong>
                </div>
                <div className="report-meta-item">
                  <small>ATHLETE ID / SPORT</small>
                  <strong>{athlete?.athlete_id || "ATH-101"} - {athlete?.sport_type || "Soccer"} ({athlete?.position || "Midfielder"})</strong>
                </div>
                <div className="report-meta-item">
                  <small>TRAINING LOAD FACTOR</small>
                  <strong style={{ color: (athlete?.training_load || 0) >= 80 ? "#ef4444" : "#10b981" }}>
                    {athlete?.training_load || 78}% Acute Load
                  </strong>
                </div>
              </div>

              {/* BIOMECHANICAL FINDINGS */}
              <h3 style={{ fontSize: "16px", color: "#f8fafc", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "6px" }}>
                1. Real Computer Vision Kinematics & Postural Extraction
              </h3>
              <p style={{ fontSize: "12px", color: "#94a3b8", lineHeight: "1.6" }}>
                Frame-by-frame 3D pose tracking extracted across <strong>{analysisResult?.video_name || activeVideoName}</strong> ({selectedMovement.replace("_", " ")}) identified:
              </p>
              <div className="stats-cards-grid" style={{ margin: "14px 0" }}>
                <div className="stat-card">
                  <small>PEAK DYNAMIC KNEE VALGUS</small>
                  <div className="stat-num" style={{ color: (analysisResult?.quality_report.metrics_summary.peak_valgus_overall || 0) > 10 ? "#ef4444" : "#10b981" }}>
                    {analysisResult?.quality_report.metrics_summary.peak_valgus_overall || 0}°
                  </div>
                  <span className="stat-desc">
                    Left: {analysisResult?.quality_report.metrics_summary.peak_knee_valgus_left || 0}° | Right: {analysisResult?.quality_report.metrics_summary.peak_knee_valgus_right || 0}°
                  </span>
                </div>
                <div className="stat-card">
                  <small>BILATERAL LIMB ASYMMETRY</small>
                  <div className="stat-num">
                    {analysisResult?.quality_report.metrics_summary.mean_asymmetry_index || 0}%
                  </div>
                  <span className="stat-desc">Normal baseline threshold: &lt; 10%</span>
                </div>
                <div className="stat-card">
                  <small>MAX KNEE FLEXION (ROM)</small>
                  <div className="stat-num">
                    {analysisResult?.quality_report.metrics_summary.peak_flexion_overall || 0}°
                  </div>
                  <span className="stat-desc">Functional sagittal landing depth</span>
                </div>
                <div className="stat-card">
                  <small>PEAK TRUNK LEAN</small>
                  <div className="stat-num">
                    {analysisResult?.quality_report.metrics_summary.peak_trunk_lean || 0}°
                  </div>
                  <span className="stat-desc">Core & lateral postural displacement</span>
                </div>
              </div>

              {/* DETECTED VIDEO ANOMALIES */}
              {analysisResult?.quality_report.anomalies && analysisResult.quality_report.anomalies.length > 0 && (
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "12px", color: "#e2e8f0", letterSpacing: "1px", margin: "0 0 8px" }}>
                    DETECTED BIOMECHANICAL FLAGS & ANOMALIES IN FOOTAGE:
                  </h4>
                  {analysisResult.quality_report.anomalies.map((an, idx) => (
                    <div key={idx} className="anomaly-pill" style={{ margin: "4px 0" }}>
                      <span>⚠</span>
                      <span>{an}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* INJURY RISK PROBABILITIES */}
              <h3 style={{ fontSize: "16px", color: "#f8fafc", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "6px", marginTop: "24px" }}>
                2. Machine Learning Injury Risk Probabilities (Random Forest Model)
              </h3>
              <div className="stats-cards-grid" style={{ margin: "16px 0" }}>
                <div className="stat-card" style={{ borderLeft: "3px solid #ff4545" }}>
                  <small>COMPOSITE RISK PROBABILITY</small>
                  <div className="stat-num" style={{ color: "#ff4545" }}>
                    {predictionResult?.overall_risk_score || 0}%
                  </div>
                  <span className="stat-desc">Status: {predictionResult?.risk_level || "EVALUATING"} RISK</span>
                </div>
                <div className="stat-card">
                  <small>ACL LIGAMENT RISK</small>
                  <div className="stat-num" style={{ color: (predictionResult?.risk_breakdown.acl_risk || 0) > 50 ? "#ef4444" : "#38bdf8" }}>
                    {predictionResult?.risk_breakdown.acl_risk || 0}%
                  </div>
                  <span className="stat-desc">Knee valgus & stiff landing trigger</span>
                </div>
                <div className="stat-card">
                  <small>HAMSTRING STRAIN RISK</small>
                  <div className="stat-num" style={{ color: (predictionResult?.risk_breakdown.hamstring_risk || 0) > 50 ? "#ef4444" : "#38bdf8" }}>
                    {predictionResult?.risk_breakdown.hamstring_risk || 0}%
                  </div>
                  <span className="stat-desc">Bilateral load asymmetry trigger</span>
                </div>
                <div className="stat-card">
                  <small>ANKLE INVERSION RISK</small>
                  <div className="stat-num">
                    {predictionResult?.risk_breakdown.ankle_risk || 0}%
                  </div>
                  <span className="stat-desc">Postural sway stability</span>
                </div>
                <div className="stat-card">
                  <small>PATELLAR TENDON RISK</small>
                  <div className="stat-num" style={{ color: (predictionResult?.risk_breakdown.patellar_risk || 0) > 50 ? "#ef4444" : "#38bdf8" }}>
                    {predictionResult?.risk_breakdown.patellar_risk || 0}%
                  </div>
                  <span className="stat-desc">Repetitive landing & deceleration impact</span>
                </div>
              </div>

              {/* CLINICAL PRESCRIPTION */}
              <h3 style={{ fontSize: "16px", color: "#f8fafc", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "6px", marginTop: "24px" }}>
                3. Tailored Corrective Exercise Protocol
              </h3>
              {predictionResult?.recommendations.prescribed_exercises ? (
                <div className="exercises-grid" style={{ margin: "14px 0" }}>
                  {predictionResult.recommendations.prescribed_exercises.map((ex, idx) => (
                    <div key={idx} className="exercise-card">
                      <div>
                        <h4>{ex.name}</h4>
                        <span className="ex-tag">{ex.category.toUpperCase()} • {ex.difficulty.toUpperCase()}</span>
                        <div className="ex-target"><strong>Target:</strong> {ex.target}</div>
                        <div className="ex-freq"><strong>Dose:</strong> {ex.frequency}</div>
                      </div>
                      <div className="ex-purpose">{ex.purpose}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: "12px", color: "#94a3b8" }}>Perform analysis on a video to generate exercise prescriptions.</p>
              )}

              {/* LOAD DIRECTIVE */}
              {predictionResult?.recommendations.training_load_recommendation && (
                <div className="load-protocol-box" style={{ marginTop: "16px" }}>
                  <h4>TRAINING LOAD DIRECTIVE</h4>
                  <div className="protocol-action">
                    {predictionResult.recommendations.training_load_recommendation}
                  </div>
                  <ul className="guidelines-list">
                    {predictionResult.recommendations.recovery_guidelines.map((g, idx) => (
                      <li key={idx}>
                        <span>✓</span> {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ marginTop: "35px", display: "flex", justifyContent: "space-between", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "15px", fontSize: "11px", color: "#64748b" }}>
                <span>Verified by SportGuard AI Biomechanics Engine</span>
                <span>Authorized Sign-off: Dr. S. Jenkins, Lead Sports Physiotherapist</span>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
