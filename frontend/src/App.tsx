import { useState } from "react";
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

function App() {
  const [showLogin, setShowLogin] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [athlete, setAthlete] = useState<Athlete | null>(null);
  const [message, setMessage] = useState("");

  async function loadAthlete(token: string) {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/athletes/1",
        {
          headers: {
            Authorization: "Bearer " + token,
          },
        }
      );

      const data = await response.json();

      if (response.ok) {
        setAthlete(data);
      } else {
        setMessage(
          data.detail || "Could not load athlete profile."
        );
      }
    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to FastAPI backend.");
    }
  }

  async function login() {
    setMessage("");

    if (!email || !password) {
      setMessage("Please enter email and password.");
      return;
    }

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Login failed.");
        return;
      }

      localStorage.setItem(
        "access_token",
        data.access_token
      );

      localStorage.setItem("role", data.role);

      setLoggedIn(true);

      await loadAthlete(data.access_token);
    } catch (error) {
      console.error(error);
      setMessage("Cannot connect to FastAPI backend.");
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");

    setLoggedIn(false);
    setShowLogin(false);

    setAthlete(null);
    setEmail("");
    setPassword("");
    setMessage("");
  }

  /* =========================
     FIRST SCREEN
  ========================= */

  if (!loggedIn && !showLogin) {
    return (
      <div className="login-page">

        <div className="background-grid"></div>

        <div className="glow glow-red"></div>
        <div className="glow glow-red-two"></div>

        <div className="login-wrapper">

          <div className="brand">

            <div className="brand-icon">
              AI
            </div>

            <div>
              <h2>
                SPORTGUARD <span>AI</span>
              </h2>

              <p>
                SPORTS INJURY INTELLIGENCE
              </p>
            </div>

          </div>

          <div className="login-card">

            <div className="top-line"></div>

            <div className="online-label">
              <span className="pulse"></span>
              AI MONITORING PLATFORM
            </div>

            <h1>
              Welcome <span>Back.</span>
            </h1>

            <p className="login-description">
              Access your athlete performance
              and injury monitoring dashboard.
            </p>

            <button
              className="login-button"
              onClick={() => setShowLogin(true)}
            >
              <span>LOGIN</span>
              <b>→</b>
            </button>

            <div className="secure">
              SECURE JWT AUTHENTICATION
            </div>

            <div className="login-footer">
              SPORTGUARD AI • ATHLETE INTELLIGENCE
            </div>

          </div>

        </div>

      </div>
    );
  }

  /* =========================
     LOGIN FORM
  ========================= */

  if (!loggedIn) {
    return (
      <div className="login-page">

        <div className="background-grid"></div>

        <div className="glow glow-red"></div>
        <div className="glow glow-red-two"></div>

        <div className="login-wrapper">

          <div className="brand">

            <div className="brand-icon">
              AI
            </div>

            <div>
              <h2>
                SPORTGUARD <span>AI</span>
              </h2>

              <p>
                SPORTS INJURY INTELLIGENCE
              </p>
            </div>

          </div>

          <div className="login-card">

            <div className="top-line"></div>

            <div className="online-label">
              <span className="pulse"></span>
              SECURE LOGIN
            </div>

            <h1>
              Login <span>Now.</span>
            </h1>

            <p className="login-description">
              Enter your credentials to access
              the athlete monitoring platform.
            </p>

            <div className="form-group">

              <label>
                EMAIL ADDRESS
              </label>

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="Enter your email"
              />

            </div>

            <div className="form-group">

              <label>
                PASSWORD
              </label>

              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
              />

            </div>

            <button
              className="login-button"
              onClick={login}
            >
              <span>LOGIN</span>
              <b>→</b>
            </button>

            {message && (
              <div className="message">
                {message}
              </div>
            )}

            <div className="secure">
              SECURE JWT AUTHENTICATION
            </div>

            <button
              className="logout"
              onClick={() => {
                setShowLogin(false);
                setMessage("");
              }}
            >
              ← BACK
            </button>

          </div>

        </div>

      </div>
    );
  }

  /* =========================
     DASHBOARD
  ========================= */

  return (
    <div className="dashboard">

      <div className="dashboard-grid"></div>

      <nav className="navbar">

        <div className="small-brand">

          <div className="brand">

            <div className="brand-icon">
              AI
            </div>

            <div>
              <h2>
                SPORTGUARD <span>AI</span>
              </h2>

              <p>
                SPORTS INJURY INTELLIGENCE
              </p>
            </div>

          </div>

        </div>

        <div className="nav-right">

          <div className="system-online">
            <span className="pulse"></span>
            SYSTEM ONLINE
          </div>

          <button
            className="logout"
            onClick={logout}
          >
            LOGOUT
          </button>

        </div>

      </nav>

      <main className="dashboard-container">

        <div className="dashboard-hero">

          <div>
            <div className="label">
              ATHLETE PERFORMANCE CENTER
            </div>

            <h1>
              Welcome back<span>.</span>
            </h1>

            <p>
              AI-powered movement and injury-risk
              monitoring.
            </p>
          </div>

          <div className="live">
            <span></span>
            LIVE
          </div>

        </div>

        <div className="dashboard-grid-layout">

          {/* =====================
              MOVEMENT ANALYSIS
          ===================== */}

          <div className="movement-card">

            <div className="card-title">

              <span>
                MOVEMENT ANALYSIS
              </span>

              <b>
                LIVE
              </b>

            </div>

            <div className="movement-area">

              <div className="scan"></div>

              <div className="circle circle-1"></div>
              <div className="circle circle-2"></div>
              <div className="circle circle-3"></div>

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

              <div className="tracking">
                MOTION TRACKING ACTIVE
              </div>

            </div>

            <div className="movement-footer">

              <div>
                <small>POSE ESTIMATION</small>
                <strong>ACTIVE</strong>
              </div>

              <div>
                <small>KEYPOINTS</small>
                <strong>33</strong>
              </div>

              <div>
                <small>FRAME RATE</small>
                <strong>60 FPS</strong>
              </div>

            </div>

          </div>

          {/* =====================
              ATHLETE PROFILE
          ===================== */}

          <div className="profile-card">

            <div className="card-title">
              ATHLETE PROFILE
            </div>

            {athlete ? (
              <>
                <div className="label">
                  ATHLETE ID
                </div>

                <h2>
                  {athlete.athlete_id}
                </h2>

                <div className="tags">

                  <span>
                    {athlete.sport_type}
                  </span>

                  <span>
                    {athlete.position}
                  </span>

                </div>

                <div className="separator"></div>

                <div className="profile-numbers">

                  <div>
                    <strong>
                      {athlete.age}
                    </strong>

                    <small>
                      AGE
                    </small>
                  </div>

                  <div>
                    <strong>
                      {athlete.height}
                    </strong>

                    <small>
                      CM
                    </small>
                  </div>

                  <div>
                    <strong>
                      {athlete.weight}
                    </strong>

                    <small>
                      KG
                    </small>
                  </div>

                </div>

                <div className="verified">
                  ✓ PROFILE VERIFIED
                </div>
              </>
            ) : (
              <div className="profile-loading">
                Loading athlete profile...
              </div>
            )}

          </div>

          {/* =====================
              TRAINING LOAD
          ===================== */}

          <div className="training-card">

            <div className="card-title">
              TRAINING LOAD
            </div>

            {athlete ? (
              <>
                <div className="training-number">

                  <strong>
                    {athlete.training_load}
                  </strong>

                  <span>
                    %
                  </span>

                </div>

                <div className="load-bar">

                  <div
                    style={{
                      width:
                        `${athlete.training_load}%`,
                    }}
                  ></div>

                </div>

                <div className="load-labels">

                  <span>LOW</span>
                  <span>OPTIMAL</span>
                  <span>HIGH</span>

                </div>

                <div className="training-status">
                  CURRENT TRAINING LOAD
                </div>
              </>
            ) : (
              <div className="profile-loading">
                Loading...
              </div>
            )}

          </div>

          {/* =====================
              INJURY HISTORY
          ===================== */}

          <div className="injury-card">

            <div className="card-title">
              INJURY HISTORY
            </div>

            {athlete ? (
              <>
                <div className="injury-content">

                  <div className="warning-icon">
                    !
                  </div>

                  <div>

                    <h3>
                      {athlete.injury_history}
                    </h3>

                    <p>
                      Historical injury information
                      available for analysis.
                    </p>

                  </div>

                </div>

                <div className="injury-note">
                  Used as one factor in injury-risk
                  screening.
                </div>
              </>
            ) : (
              <div className="profile-loading">
                Loading...
              </div>
            )}

          </div>

        </div>

        {/* =====================
            PERFORMANCE
        ===================== */}

        <section className="performance">

          <div className="label">
            PERFORMANCE INTELLIGENCE
          </div>

          <div className="performance-heading">

            <div>

              <h2>
                Movement <span>Insights.</span>
              </h2>

              <p>
                Real-time athlete movement
                monitoring status.
              </p>

            </div>

            <div className="synced">
              ● DATA SYNCED
            </div>

          </div>

          <div className="metrics">

            <div className="metric">

              <span>◉</span>

              <div>
                <small>POSE TRACKING</small>
                <strong>ACTIVE</strong>
              </div>

            </div>

            <div className="metric">

              <span>⌁</span>

              <div>
                <small>MOVEMENT ANALYSIS</small>
                <strong>READY</strong>
              </div>

            </div>

            <div className="metric">

              <span>△</span>

              <div>
                <small>BIOMECHANICS</small>
                <strong>STANDBY</strong>
              </div>

            </div>

            <div className="metric">

              <span>◎</span>

              <div>
                <small>RISK ENGINE</small>
                <strong>READY</strong>
              </div>

            </div>

          </div>

        </section>

        {/* =====================
            AI MOVEMENT ENGINE
        ===================== */}

        <section className="ai-panel">

          <div className="ai-text">

            <div className="label">
              AI MOVEMENT ENGINE
            </div>

            <h2>
              Injury risk analysis
              <span>.</span>
            </h2>

            <p>
              The platform combines movement
              patterns, athlete history, training
              load and biomechanical indicators
              for injury-risk screening.
            </p>

            <div className="ai-tags">

              <span>
                POSE ESTIMATION
              </span>

              <span>
                BIOMECHANICS
              </span>

              <span>
                MOVEMENT INTELLIGENCE
              </span>

              <span>
                RISK ANALYSIS
              </span>

            </div>

          </div>

          <div className="ai-rings">

            <div></div>
            <div></div>
            <div></div>

          </div>

        </section>

        <div className="next">

          <small>
            NEXT MODULE
          </small>

          <strong>
            →
          </strong>

        </div>

      </main>

    </div>
  );
}

export default App;