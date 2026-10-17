import { useEffect, useState } from "react";
import "./App.css";

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

function App() {
  /* =========================
     LOGIN / SIGNUP STATE
  ========================= */

  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);

  const [loggedIn, setLoggedIn] = useState<boolean>(() => {
    return !!localStorage.getItem("access_token");
  });

  /* =========================
     LOGIN STATE
  ========================= */

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  /* =========================
     SIGNUP STATE
  ========================= */

  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupConfirmPassword, setSignupConfirmPassword] = useState("");

  /* =========================
     COMMON STATE
  ========================= */

  const [message, setMessage] = useState("");
  const [athlete, setAthlete] = useState<Athlete | null>(null);
  const [loading, setLoading] = useState(false);

  /* =========================
     MILESTONE 2: BIOMECHANICS & POSE ANALYSIS STATE
  ========================= */
  const [selectedMovement, setSelectedMovement] = useState<string>("SQUAT");
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string>("");
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);

  /* =========================
     LOAD ATHLETE
  ========================= */

  const loadAthlete = async (token: string) => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/athletes/1",
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to load athlete");
      }

      const data = await response.json();
      setAthlete(data);
    } catch (error) {
      console.error(error);
    }
  };

  /* =========================
     CHECK TOKEN ON PAGE LOAD
  ========================= */

  useEffect(() => {
  const token = localStorage.getItem("access_token");

  if (token) {
    setLoggedIn(true);
    setShowLogin(false);
    setShowSignup(false);

    loadAthlete(token);

    // Remove login page from the current history position
    window.history.replaceState(
      { protected: true },
      "",
      window.location.href
    );
  }
}, []);

  /* =========================
     PROTECTED ROUTE / BACK BUTTON
  ========================= */

  useEffect(() => {
    const handlePopState = () => {
    const token = localStorage.getItem("access_token");

    if (token) {
      setLoggedIn(true);
      setShowLogin(false);
      setShowSignup(false);

      window.history.pushState(
        { protected: true },
        "",
        window.location.href
      );
    }
  };

  window.addEventListener("popstate", handlePopState);

  return () => {
    window.removeEventListener("popstate", handlePopState);
  };
}, []);

  /* =========================
     LOGIN
  ========================= */

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email,
            password: password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Invalid email or password");
        setLoading(false);
        return;
      }

      /* Store JWT token */

      localStorage.setItem(
        "access_token",
        data.access_token
      );

      localStorage.setItem(
        "role",
        data.role
      );

      /* Update login state */

      setLoggedIn(true);
      setShowLogin(false);
      setShowSignup(false);

      setEmail("");
      setPassword("");
      setMessage("");

      /* Prevent returning to login */

      window.history.pushState(
  { protected: true },
  "",
  window.location.href
);

      /* Load athlete */

      await loadAthlete(data.access_token);

    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to server");
    }

    setLoading(false);
  };

  /* =========================
     SIGNUP
  ========================= */

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    setMessage("");

    /* Check passwords */

    if (signupPassword !== signupConfirmPassword) {
      setMessage("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/auth/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: signupName,
            email: signupEmail,
            password: signupPassword,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(
          data.detail || "Registration failed"
        );

        setLoading(false);
        return;
      }

      /* Clear signup form */

      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setSignupConfirmPassword("");

      /* Go to login */

      setShowSignup(false);
      setShowLogin(true);

      setMessage(
        "Account created successfully. Please login."
      );

    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to server");
    }

    setLoading(false);
  };

  /* =========================
     LOGOUT
  ========================= */

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");

    setLoggedIn(false);
    setAthlete(null);

    setShowLogin(true);
    setShowSignup(false);

    setMessage("");

    window.history.replaceState(
      null,
      "",
      window.location.href
    );
  };

  /* =========================
     BIOMECHANICS ANALYSIS HANDLERS
  ========================= */

  const handleRunDemo = async (movement: string) => {
    setAnalysisLoading(true);
    setAnalysisError("");
    try {
      const athleteParam = athlete?.athlete_id ? `&athlete_id=${athlete.athlete_id}` : "";
      const res = await fetch(`http://127.0.0.1:8000/analysis/synthetic-demo?movement_type=${movement}${athleteParam}`, {
        method: "POST"
      });
      if (!res.ok) {
        throw new Error("Failed to process biomechanical assessment");
      }
      const data: VideoAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setCurrentFrameIndex(0);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to run analysis");
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

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
        body: formData
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Video analysis processing failed");
      }
      const data: VideoAnalysisResponse = await res.json();
      setAnalysisResult(data);
      setCurrentFrameIndex(0);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to upload and analyze video");
    } finally {
      setAnalysisLoading(false);
    }
  };

  /* =========================================================
     LANDING PAGE
  ========================================================= */

  if (!loggedIn && !showLogin && !showSignup) {
    return (
      <div className="login-page">

        <div className="login-wrapper">

          <div className="brand">
            <div className="brand-icon">
              SG
            </div>

            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>
          </div>

          <div className="login-card">

            <div className="top-line">
              <span className="online-label">
                AI POWERED
              </span>
            </div>

            <h1>
              SPORTS INJURY
              <br />
              RISK DETECTION
            </h1>

            <p className="login-description">
              AI-powered athlete movement
              analysis and injury risk detection.
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
              Don't have an account?{" "}
              <span>SIGN UP</span>
            </button>

          </div>

          <div className="login-footer">
            SPORTGUARD AI • SECURE ATHLETE MONITORING
          </div>

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

            <div className="brand-icon">
              SG
            </div>

            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>

          </div>

          <div className="login-card">

            <div className="top-line">
              <span className="online-label">
                CREATE ACCOUNT
              </span>
            </div>

            <h1>SIGN UP</h1>

            <p className="login-description">
              Create your SPORTGUARD AI athlete account.
            </p>

            <form onSubmit={handleSignup}>

              {/* NAME */}

              <div className="form-group">

                <label>NAME</label>

                <input
                  type="text"
                  value={signupName}
                  onChange={(e) =>
                    setSignupName(e.target.value)
                  }
                  placeholder="Enter your name"
                  required
                />

              </div>

              {/* EMAIL */}

              <div className="form-group">

                <label>EMAIL</label>

                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) =>
                    setSignupEmail(e.target.value)
                  }
                  placeholder="Enter your email"
                  required
                />

              </div>

              {/* PASSWORD */}

              <div className="form-group">

                <label>PASSWORD</label>

                <input
                  type="password"
                  value={signupPassword}
                  onChange={(e) =>
                    setSignupPassword(e.target.value)
                  }
                  placeholder="Create password"
                  required
                />

              </div>

              {/* CONFIRM PASSWORD */}

              <div className="form-group">

                <label>CONFIRM PASSWORD</label>

                <input
                  type="password"
                  value={signupConfirmPassword}
                  onChange={(e) =>
                    setSignupConfirmPassword(e.target.value)
                  }
                  placeholder="Confirm password"
                  required
                />

              </div>

              <button
                type="submit"
                className="login-button"
                disabled={loading}
              >
                {loading
                  ? "CREATING..."
                  : "CREATE ACCOUNT"}
              </button>

            </form>

            {message && (
              <div className="message">
                {message}
              </div>
            )}

            <button
              type="button"
              className="signup-link"
              onClick={() => {
                setShowSignup(false);
                setShowLogin(true);
                setMessage("");
              }}
            >
              Already have an account?{" "}
              <span>LOGIN</span>
            </button>

          </div>

          <div className="login-footer">
            SPORTGUARD AI • SECURE ATHLETE MONITORING
          </div>

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

            <div className="brand-icon">
              SG
            </div>

            <div>
              <h2>SPORTGUARD AI</h2>
              <span>ATHLETE SAFETY SYSTEM</span>
            </div>

          </div>

          <div className="login-card">

            <div className="top-line">
              <span className="online-label">
                SYSTEM ONLINE
              </span>
            </div>

            <h1>LOGIN</h1>

            <p className="login-description">
              Access your athlete safety dashboard.
            </p>

            <form onSubmit={handleLogin}>

              {/* EMAIL */}

              <div className="form-group">

                <label>EMAIL</label>

                <input
                  type="email"
                  value={email}
                  onChange={(e) =>
                    setEmail(e.target.value)
                  }
                  placeholder="Enter your email"
                  required
                />

              </div>

              {/* PASSWORD */}

              <div className="form-group">

                <label>PASSWORD</label>

                <input
                  type="password"
                  value={password}
                  onChange={(e) =>
                    setPassword(e.target.value)
                  }
                  placeholder="Enter your password"
                  required
                />

              </div>

              <button
                type="submit"
                className="login-button"
                disabled={loading}
              >
                {loading
                  ? "AUTHENTICATING..."
                  : "LOGIN"}
              </button>

            </form>

            {message && (
              <div className="message">
                {message}
              </div>
            )}

            <button
              type="button"
              className="signup-link"
              onClick={() => {
                setShowLogin(false);
                setShowSignup(true);
                setMessage("");
              }}
            >
              Don't have an account?{" "}
              <span>SIGN UP</span>
            </button>

          </div>

          <div className="login-footer">
            SPORTGUARD AI • SECURE ATHLETE MONITORING
          </div>

        </div>

      </div>
    );
  }

  /* =========================================================
     DASHBOARD
  ========================================================= */

  return (
    <div className="dashboard">

      {/* ================= NAVBAR ================= */}

      <nav className="navbar">

        <div className="brand">

          <div className="brand-icon">
            SG
          </div>

          <div>
            <h2>SPORTGUARD AI</h2>
            <span>ATHLETE SAFETY SYSTEM</span>
          </div>

        </div>

        <div className="navbar-right">

          <span className="online-label">
            ● SYSTEM ONLINE
          </span>

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            LOGOUT
          </button>

        </div>

      </nav>

      {/* ================= MAIN ================= */}

      <main className="dashboard-container">

        {/* HERO */}

        <section className="dashboard-hero">

          <div>

            <span className="online-label">
              AI MOVEMENT ANALYSIS
            </span>

            <h1>
              ATHLETE
              <br />
              SAFETY DASHBOARD
            </h1>

            <p>
              Monitor movement patterns,
              biomechanics and injury risk
              using AI-powered analysis.
            </p>

          </div>

          {/* AI VISUAL */}

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

        {/* ================= ATHLETE PROFILE ================= */}

        <section className="profile-card">

          <div className="section-title">
            ATHLETE PROFILE
          </div>

          {athlete ? (
            <div className="metrics">

              <div className="metric">
                <span>ATHLETE ID</span>
                <strong>
                  {athlete.athlete_id}
                </strong>
              </div>

              <div className="metric">
                <span>SPORT</span>
                <strong>
                  {athlete.sport_type}
                </strong>
              </div>

              <div className="metric">
                <span>POSITION</span>
                <strong>
                  {athlete.position}
                </strong>
              </div>

              <div className="metric">
                <span>AGE</span>
                <strong>
                  {athlete.age}
                </strong>
              </div>

              <div className="metric">
                <span>HEIGHT</span>
                <strong>
                  {athlete.height} cm
                </strong>
              </div>

              <div className="metric">
                <span>WEIGHT</span>
                <strong>
                  {athlete.weight} kg
                </strong>
              </div>

            </div>
          ) : (
            <p>
              Loading athlete information...
            </p>
          )}

        </section>

        {/* ================= TRAINING + INJURY ================= */}

        <div className="dashboard-grid">

          <section className="training-card">

            <div className="section-title">
              TRAINING LOAD
            </div>

            <div className="training-value">

              <strong>
                {athlete
                  ? athlete.training_load
                  : "--"}
              </strong>

              <span>
                CURRENT LOAD
              </span>

            </div>

            <div className="performance">

              <div>
                <span>STATUS</span>

                <strong>
                  {athlete &&
                  athlete.training_load > 80
                    ? "HIGH"
                    : "NORMAL"}
                </strong>
              </div>

              <div>
                <span>MONITORING</span>

                <strong>ACTIVE</strong>
              </div>

            </div>

          </section>

          <section className="injury-card">

            <div className="section-title">
              INJURY HISTORY
            </div>

            <p>
              {athlete
                ? athlete.injury_history
                : "Loading..."}
            </p>

          </section>

        </div>

        {/* ================= AI PANEL ================= */}

        {/* ================= MILESTONE 2: BIOMECHANICAL ANALYSIS STUDIO ================= */}

        <section className="biomechanics-section">
          <div className="biomechanics-header">
            <div>
              <span className="online-label">
                MILESTONE 2 • POSE ESTIMATION & KINEMATICS
              </span>
              <h2>BIOMECHANICAL MOVEMENT QUALITY STUDIO</h2>
              <p>
                Analyze joint kinematics, dynamic knee valgus, bilateral symmetry, and movement quality using 33 3D MediaPipe pose landmarks.
              </p>
            </div>

            {/* MOVEMENT SELECTOR */}
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

          {/* ACTION BUTTONS */}
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

          {analysisError && (
            <div className="message" style={{ marginBottom: "20px" }}>
              {analysisError}
            </div>
          )}

          {/* RESULTS DISPLAY */}
          {analysisResult && (
            <div>
              {/* QUALITY REPORT & SCORES */}
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
                  <div className="k-val">
                    {analysisResult.quality_report.metrics_summary.peak_valgus_overall}°
                  </div>
                  <div className="k-sub">
                    L: {analysisResult.quality_report.metrics_summary.peak_knee_valgus_left}° | R: {analysisResult.quality_report.metrics_summary.peak_knee_valgus_right}°
                  </div>
                </div>

                <div className="kinematic-tile">
                  <small>MAX KNEE FLEXION</small>
                  <div className="k-val">
                    {analysisResult.quality_report.metrics_summary.peak_flexion_overall}°
                  </div>
                  <div className="k-sub">
                    L: {analysisResult.quality_report.metrics_summary.peak_knee_flexion_left}° | R: {analysisResult.quality_report.metrics_summary.peak_knee_flexion_right}°
                  </div>
                </div>

                <div className="kinematic-tile">
                  <small>MEAN ASYMMETRY</small>
                  <div className="k-val">
                    {analysisResult.quality_report.metrics_summary.mean_asymmetry_index}%
                  </div>
                  <div className="k-sub">
                    {analysisResult.quality_report.metrics_summary.mean_asymmetry_index < 10
                      ? "Optimal Bilateral Balance (<10%)"
                      : "Elevated Asymmetry (>10%)"}
                  </div>
                </div>

                <div className="kinematic-tile">
                  <small>PEAK TRUNK LEAN</small>
                  <div className="k-val">
                    {analysisResult.quality_report.metrics_summary.peak_trunk_lean}°
                  </div>
                  <div className="k-sub">
                    Mean: {analysisResult.quality_report.metrics_summary.mean_trunk_lean}° deviation
                  </div>
                </div>
              </div>

              {/* ANOMALIES */}
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

      </main>

    </div>
  );
}

export default App;