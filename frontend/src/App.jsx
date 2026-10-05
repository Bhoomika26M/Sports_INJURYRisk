import "./App.css"

function App() {
  return (
    <div className="app">

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">S</div>
          <div>
            <h2>SportSafe</h2>
            <span>Injury Intelligence</span>
          </div>
        </div>

        <nav>
          <a className="active">Dashboard</a>
          <a>Athletes</a>
          <a>Movement Analysis</a>
          <a>Risk Assessment</a>
          <a>Reports</a>
        </nav>

        <div className="sidebar-bottom">
          <div className="user-mini">
            <div className="avatar">A</div>
            <div>
              <strong>Coach</strong>
              <span>Administrator</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="main">

        <header className="topbar">
          <div>
            <p className="eyebrow">SPORTS PERFORMANCE</p>
            <h1>Good morning 👋</h1>
            <p className="subtitle">
              Monitor athlete movement and identify potential injury risks.
            </p>
          </div>

          <div className="top-actions">
            <button className="notification">🔔</button>
            <div className="profile-avatar">A</div>
          </div>
        </header>

        {/* Stats */}
        <section className="stats">

          <div className="stat-card">
            <div className="stat-icon blue">👥</div>
            <div>
              <span>Total Athletes</span>
              <h2>24</h2>
              <small>↑ 8% this month</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon purple">🎥</div>
            <div>
              <span>Videos Analysed</span>
              <h2>86</h2>
              <small>↑ 12% this month</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon orange">⚠</div>
            <div>
              <span>At Risk</span>
              <h2>5</h2>
              <small className="warning">Needs attention</small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon green">✓</div>
            <div>
              <span>Low Risk</span>
              <h2>19</h2>
              <small>79% of athletes</small>
            </div>
          </div>

        </section>

        {/* Main grid */}
        <section className="content-grid">

          {/* Athletes */}
          <div className="panel athletes-panel">

            <div className="panel-header">
              <div>
                <h2>Athlete Profiles</h2>
                <p>Recently monitored athletes</p>
              </div>

              <button className="primary-btn">
                + Add Athlete
              </button>
            </div>

            <div className="athlete-list">

              <div className="athlete-row">
                <div className="athlete-info">
                  <div className="athlete-avatar">JD</div>
                  <div>
                    <strong>John Davis</strong>
                    <span>Football • 22 yrs</span>
                  </div>
                </div>

                <span className="risk low">Low Risk</span>
              </div>

              <div className="athlete-row">
                <div className="athlete-info">
                  <div className="athlete-avatar purple-bg">AS</div>
                  <div>
                    <strong>Alex Smith</strong>
                    <span>Basketball • 21 yrs</span>
                  </div>
                </div>

                <span className="risk medium">Moderate</span>
              </div>

              <div className="athlete-row">
                <div className="athlete-info">
                  <div className="athlete-avatar orange-bg">RK</div>
                  <div>
                    <strong>Rahul Kumar</strong>
                    <span>Football • 23 yrs</span>
                  </div>
                </div>

                <span className="risk high">High Risk</span>
              </div>

            </div>

            <button className="view-all">
              View all athletes →
            </button>

          </div>

          {/* Quick analysis */}
          <div className="panel analysis-panel">

            <div className="panel-header">
              <div>
                <h2>Movement Analysis</h2>
                <p>Start a new assessment</p>
              </div>
            </div>

            <div className="upload-box">
              <div className="upload-icon">↑</div>
              <h3>Upload movement video</h3>
              <p>
                Analyze athlete movement using<br />
                AI-powered pose estimation.
              </p>

              <button className="upload-btn">
                Choose Video
              </button>

              <small>MP4, MOV • Max 500 MB</small>
            </div>

          </div>

        </section>

        {/* Bottom section */}
        <section className="bottom-grid">

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Risk Overview</h2>
                <p>Current athlete risk distribution</p>
              </div>
            </div>

            <div className="risk-chart">
              <div className="chart-number">24</div>
              <div className="chart-label">Athletes monitored</div>

              <div className="progress">
                <div className="progress-low"></div>
                <div className="progress-medium"></div>
                <div className="progress-high"></div>
              </div>

              <div className="legend">
                <span><i className="dot low-dot"></i> Low 19</span>
                <span><i className="dot medium-dot"></i> Moderate 3</span>
                <span><i className="dot high-dot"></i> High 2</span>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Recent Activity</h2>
                <p>Latest system updates</p>
              </div>
            </div>

            <div className="activity">
              <div className="activity-icon">✓</div>
              <div>
                <strong>Movement analysis completed</strong>
                <span>John Davis • 15 minutes ago</span>
              </div>
            </div>

            <div className="activity">
              <div className="activity-icon orange">!</div>
              <div>
                <strong>High risk detected</strong>
                <span>Rahul Kumar • 1 hour ago</span>
              </div>
            </div>

          </div>

        </section>

      </main>
    </div>
  )
}

export default App