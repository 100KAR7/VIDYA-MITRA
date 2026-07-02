import { useEffect, useState } from "react";
import "./styles.css";

const pillars = [
  {
    title: "Adaptive API",
    description: "Flask endpoints handle auth, predictions, progress tracking, and game session state.",
  },
  {
    title: "Game Center",
    description: "Learners move from recommendation to live mission flow with lesson mechanics and assessment rounds.",
  },
  {
    title: "ML Runtime",
    description: "Saved models and encoders power next-topic, difficulty, revision, and success predictions.",
  },
  {
    title: "Teacher View",
    description: "Persistent learner progress and classroom analytics are available through the same platform store.",
  },
];

const runbook = [
  "Run `python -m pip install -r requirements.txt`.",
  "Start the main platform with `python app.py`.",
  "Open `http://127.0.0.1:5000` for the full learner dashboard.",
  "Use this Vite preview only as a lightweight developer overview.",
];

export default function App() {
  const [health, setHealth] = useState({
    status: "checking",
    detail: "Trying to reach the Flask API through the local Vite proxy.",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadHealth() {
      try {
        const response = await fetch("/api/health");
        if (!response.ok) {
          throw new Error(`API responded with ${response.status}`);
        }
        const payload = await response.json();
        if (cancelled) return;
        setHealth({
          status: "online",
          detail: `${payload.app} ${payload.version} is ready with ${payload.active_game_sessions} live sessions.`,
        });
      } catch (error) {
        if (cancelled) return;
        setHealth({
          status: "offline",
          detail: "Backend not detected yet. Start `python app.py` to enable the full platform flow.",
        });
      }
    }

    loadHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Vidya Mitra Developer Preview</h1>
          <p className="subtitle">
            The canonical product UI is the Flask-served dashboard in `frontend/`.
            This React app is a lightweight repo overview and health check.
          </p>
        </div>
        <a className="btn-primary" href="http://127.0.0.1:5000">
          Open Full Platform
        </a>
      </div>

      <div className="stats-grid">
        <div className="card stat-card">
          <div>
            <p className="stat-value">{health.status.toUpperCase()}</p>
            <p className="stat-label">API Status</p>
          </div>
        </div>
        <div className="card stat-card">
          <div>
            <p className="stat-value">Flask</p>
            <p className="stat-label">Primary runtime</p>
          </div>
        </div>
        <div className="card stat-card">
          <div>
            <p className="stat-value">4</p>
            <p className="stat-label">Core prediction targets</p>
          </div>
        </div>
        <div className="card stat-card">
          <div>
            <p className="stat-value">Live</p>
            <p className="stat-label">Game session engine</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>VIDYA-MITRA</h1>
        <button onClick={handleLogout}>Logout</button>
      </header>
      <main className="app-main">
        <h2>Welcome, {user?.name}!</h2>
        <p>Gamified learning platform for personalized education</p>
      </main>
    </div>
  )
}

      <div className="dashboard-grid">
        <div className="card wide">
          <div className="card-header">
            <h3>Platform Health</h3>
          </div>
          <p className="subtitle">{health.detail}</p>
        </div>

        {pillars.map((pillar) => (
          <div key={pillar.title} className="card">
            <div className="card-header">
              <h3>{pillar.title}</h3>
            </div>
            <p className="subtitle">{pillar.description}</p>
          </div>
        ))}

        <div className="card wide">
          <div className="card-header">
            <h3>4-Step Run Pattern</h3>
          </div>
          <div className="topic-list">
            {runbook.map((step) => (
              <div key={step} className="topic-row">
                <div className="topic-info">
                  <strong>{step}</strong>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
