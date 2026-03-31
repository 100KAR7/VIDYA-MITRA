import { useState, useEffect, createContext, useContext } from "react";
import "./styles.css";

// ─── API CONFIG ───────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000"; 
const API_BASE = "http://localhost:8000"; 

const api = {
  post: (path, body) =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  get: (path) =>
    fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    }).then((r) => r.json()),
};

// ─── CONTEXT ──────────────────────────────────────────────────────────────────
const AppContext = createContext(null);
const useApp = () => useContext(AppContext);

// ─── ICONS ────────────────────────────────────────────────────────────────────
const Icon = ({ name, size = 20 }) => {
  const icons = {
    home: "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10",
    book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
    zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    bar: "M18 20V10 M12 20V4 M6 20v-6",
    user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    map: "M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4z M8 2v16 M16 6v16",
    gamepad: "M6 11h4 M8 9v4 M15 12h.01 M18 10h.01 M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z",
    lightbulb: "M9 21h6 M12 3a6 6 0 0 1 6 6 6 6 0 0 1-3 5.197V17H9v-2.803A6 6 0 0 1 6 9a6 6 0 0 1 6-6z",
    logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4 M16 17l5-5-5-5 M21 12H9",
    check: "M20 6L9 17l-5-5",
    star: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
    target: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12z M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
    trophy: "M6 9H4.5a2.5 2.5 0 0 1 0-5H6 M18 9h1.5a2.5 2.5 0 0 0 0-5H18 M4 22h16 M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22 M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22 M18 2H6v7a6 6 0 0 0 12 0V2z",
    play: "M5 3l14 9-14 9V3z",
    bell: "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0",
    search: "M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0",
    menu: "M3 12h18 M3 6h18 M3 18h18",
    x: "M18 6L6 18 M6 6l12 12",
    arrow: "M5 12h14 M12 5l7 7-7 7",
    clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 6v6l4 2",
    flame: "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z",
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {(icons[name] || "").split(" M").map((d, i) => (
        <path key={i} d={i === 0 ? d : "M" + d} />
      ))}
    </svg>
  );
};

// ─── PROGRESS BAR ─────────────────────────────────────────────────────────────
const ProgressBar = ({ value, color = "var(--accent)" }) => (
  <div className="progress-track">
    <div className="progress-fill" style={{ width: `${Math.min(100, value)}%`, background: color }} />
  </div>
);

// ─── BADGE ────────────────────────────────────────────────────────────────────
const Badge = ({ label, type = "default" }) => (
  <span className={`badge badge-${type}`}>{label}</span>
);

// ─── CARD ─────────────────────────────────────────────────────────────────────
const Card = ({ children, className = "", onClick }) => (
  <div className={`card ${className}`} onClick={onClick} style={{ cursor: onClick ? "pointer" : undefined }}>
    {children}
  </div>
);

// ─── MODAL ────────────────────────────────────────────────────────────────────
const Modal = ({ open, onClose, title, children }) => {
  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose}><Icon name="x" /></button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AUTH PAGES
// ═══════════════════════════════════════════════════════════════════════════════
function AuthPage({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({ email: "", password: "", name: "", class: "", board: "", rollNo: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
    
      onLogin({ id: 1, email: form.email, name: "Student" }); // mock
      onLogin({ id: 1, email: form.email, name: "Student" }); 
    } catch {
      setError("Invalid credentials");
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      
      onLogin({ id: 1, email: form.email, name: form.name }); // mock
      onLogin({ id: 1, email: form.email, name: form.name }); 
    } catch {
      setError("Registration failed");
    }
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-art">
        <div className="auth-art-inner">
          <div className="auth-logo">
            <Icon name="zap" size={32} />
            <span>LearnPath</span>
          </div>
          <h1>Your learning<br />journey starts<br /><em>here.</em></h1>
          <p>Personalised paths, gamified practice, and real-time performance insights.</p>
          <div className="auth-stats">
            {[["10k+", "Students"], ["500+", "Modules"], ["98%", "Pass rate"]].map(([n, l]) => (
              <div key={l} className="auth-stat"><strong>{n}</strong><span>{l}</span></div>
            ))}
          </div>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-tabs">
          <button className={tab === "login" ? "active" : ""} onClick={() => setTab("login")}>Sign In</button>
          <button className={tab === "register" ? "active" : ""} onClick={() => setTab("register")}>Register</button>
        </div>

        {tab === "login" ? (
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Welcome back</h2>
            <label>Email<input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} required placeholder="you@example.com" /></label>
            <label>Password<input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required placeholder="••••••••" /></label>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Signing in…" : "Sign In"}</button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="auth-form">
            <h2>Create account</h2>
            <label>Full Name<input type="text" value={form.name} onChange={(e) => set("name", e.target.value)} required placeholder="Your name" /></label>
            <label>Email<input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} required placeholder="you@example.com" /></label>
            <label>Password<input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required placeholder="••••••••" /></label>
            <div className="form-row">
              <label>Class<input type="text" value={form.class} onChange={(e) => set("class", e.target.value)} placeholder="e.g. 10" /></label>
              <label>Board<input type="text" value={form.board} onChange={(e) => set("board", e.target.value)} placeholder="e.g. CBSE" /></label>
            </div>
            <label>Roll No.<input type="text" value={form.rollNo} onChange={(e) => set("rollNo", e.target.value)} placeholder="Optional" /></label>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Creating…" : "Create Account"}</button>
          </form>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════════════════════════
const NAV = [
  { id: "dashboard", icon: "home", label: "Dashboard" },
  { id: "topics", icon: "book", label: "Topics" },
  { id: "learning-path", icon: "map", label: "Learning Path" },
  { id: "modules", icon: "play", label: "Modules" },
  { id: "quiz", icon: "zap", label: "Quiz" },
  { id: "games", icon: "gamepad", label: "Games" },
  { id: "performance", icon: "bar", label: "Performance" },
  { id: "suggestions", icon: "lightbulb", label: "Suggestions" },
  { id: "profile", icon: "user", label: "Profile" },
];

function Sidebar({ page, setPage, user, onLogout, mobileOpen, setMobileOpen }) {
  return (
    <>
      {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="sidebar-logo">
          <Icon name="zap" size={24} />
          <span>LearnPath</span>
        </div>
        <nav>
          {NAV.map((n) => (
            <button key={n.id} className={`nav-item ${page === n.id ? "active" : ""}`}
              onClick={() => { setPage(n.id); setMobileOpen(false); }}>
              <Icon name={n.icon} size={18} />
              <span>{n.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="avatar">{user?.name?.[0]?.toUpperCase() || "U"}</div>
            <div>
              <p className="sidebar-name">{user?.name || "Student"}</p>
              <p className="sidebar-email">{user?.email}</p>
            </div>
          </div>
          <button className="icon-btn logout-btn" onClick={onLogout} title="Logout"><Icon name="logout" size={18} /></button>
        </div>
      </aside>
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function Dashboard() {
  const { user, setPage } = useApp();

  const stats = [
    { label: "Topics Enrolled", value: 8, icon: "book", color: "#6366f1" },
    { label: "Modules Done", value: 23, icon: "check", color: "#10b981" },
    { label: "Quiz Score", value: "87%", icon: "zap", color: "#f59e0b" },
    { label: "Game Level", value: 5, icon: "trophy", color: "#ec4899" },
  ];

  const recentTopics = [
    { name: "Algebra", progress: 72, subtopics: 6 },
    { name: "Photosynthesis", progress: 45, subtopics: 4 },
    { name: "World War II", progress: 90, subtopics: 8 },
    { name: "Python Basics", progress: 30, subtopics: 5 },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Good morning, {user?.name?.split(" ")[0] || "Student"} 👋</h1>
          <p className="subtitle">You have 3 modules pending today</p>
        </div>
        <button className="btn-primary" onClick={() => setPage("topics")}><Icon name="arrow" size={16} /> Continue Learning</button>
      </div>

      <div className="stats-grid">
        {stats.map((s) => (
          <Card key={s.label} className="stat-card">
            <div className="stat-icon" style={{ background: s.color + "20", color: s.color }}>
              <Icon name={s.icon} size={22} />
            </div>
            <div>
              <p className="stat-value">{s.value}</p>
              <p className="stat-label">{s.label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="dashboard-grid">
        <Card className="wide">
          <div className="card-header"><h3>Recent Topics</h3><button className="link-btn" onClick={() => setPage("topics")}>View all →</button></div>
          <div className="topic-list">
            {recentTopics.map((t) => (
              <div key={t.name} className="topic-row">
                <div className="topic-info">
                  <strong>{t.name}</strong>
                  <span>{t.subtopics} subtopics</span>
                </div>
                <div className="topic-progress">
                  <ProgressBar value={t.progress} />
                  <span>{t.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="card-header"><h3>Today's Streak</h3></div>
          <div className="streak-display">
            <Icon name="flame" size={48} />
            <span className="streak-num">7</span>
            <p>days in a row!</p>
          </div>
          <div className="week-dots">
            {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
              <div key={i} className={`week-dot ${i < 5 ? "done" : ""}`}><span>{d}</span></div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="card-header"><h3>Quick Actions</h3></div>
          <div className="quick-actions">
            {[
              { label: "Take a Quiz", icon: "zap", page: "quiz", color: "#6366f1" },
              { label: "Play Game", icon: "gamepad", page: "games", color: "#10b981" },
              { label: "View Analysis", icon: "bar", page: "performance", color: "#f59e0b" },
              { label: "Get Suggestions", icon: "lightbulb", page: "suggestions", color: "#ec4899" },
            ].map((a) => (
              <button key={a.label} className="quick-action-btn" style={{ "--qa-color": a.color }} onClick={() => setPage(a.page)}>
                <Icon name={a.icon} size={20} />
                {a.label}
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TOPICS PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function TopicsPage() {
  const [topics, setTopics] = useState([
    { id: 1, name: "Algebra", description: "Equations, polynomials, and algebraic structures", subtopics: ["Linear Equations", "Quadratics", "Polynomials", "Inequalities", "Functions", "Matrices"] },
    { id: 2, name: "Photosynthesis", description: "How plants convert sunlight into energy", subtopics: ["Light Reactions", "Calvin Cycle", "Chlorophyll", "Gas Exchange"] },
    { id: 3, name: "World War II", description: "Major events, causes, and consequences of WWII", subtopics: ["Causes", "Major Battles", "Allied Powers", "Axis Powers", "Holocaust", "End of War", "Aftermath", "Legacy"] },
    { id: 4, name: "Python Basics", description: "Introduction to programming with Python", subtopics: ["Variables", "Loops", "Functions", "OOP", "Libraries"] },
    { id: 5, name: "Organic Chemistry", description: "Carbon compounds and their reactions", subtopics: ["Hydrocarbons", "Functional Groups", "Reactions", "Polymers"] },
    { id: 6, name: "Trigonometry", description: "Study of triangles and periodic functions", subtopics: ["Sin/Cos/Tan", "Identities", "Graphs", "Applications"] },
  ]);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");

  const filtered = topics.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Topics</h1>
          <p className="subtitle">Explore all available subjects</p>
        </div>
        <div className="search-bar">
          <Icon name="search" size={16} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search topics…" />
        </div>
      </div>

      <div className="topics-grid">
        {filtered.map((t, i) => (
          <Card key={t.id} className="topic-card" onClick={() => setSelected(t)}>
            <div className="topic-card-icon" style={{ background: `hsl(${i * 60}, 80%, 90%)`, color: `hsl(${i * 60}, 60%, 40%)` }}>
              {t.name[0]}
            </div>
            <h3>{t.name}</h3>
            <p>{t.description}</p>
            <div className="topic-card-footer">
              <Badge label={`${t.subtopics.length} subtopics`} type="info" />
              <button className="link-btn">Explore →</button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.name}>
        <p className="modal-desc">{selected?.description}</p>
        <h4>Subtopics</h4>
        <div className="subtopic-list">
          {selected?.subtopics.map((s, i) => (
            <div key={s} className="subtopic-item">
              <span className="subtopic-num">{i + 1}</span>
              <span>{s}</span>
              <Icon name="arrow" size={14} />
            </div>
          ))}
        </div>
        <button className="btn-primary" style={{ width: "100%", marginTop: 16 }}>Start Learning</button>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEARNING PATH PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function LearningPathPage() {
  const paths = [
    { id: 1, topic: "Algebra", topicId: 1, progress: 72, status: "in-progress" },
    { id: 2, topic: "Python Basics", topicId: 4, progress: 30, status: "in-progress" },
    { id: 3, topic: "Photosynthesis", topicId: 2, progress: 100, status: "completed" },
    { id: 4, topic: "Trigonometry", topicId: 6, progress: 0, status: "not-started" },
  ];

  const steps = [
    { label: "Introduction", done: true },
    { label: "Core Concepts", done: true },
    { label: "Practice Problems", done: true },
    { label: "Quiz", done: false },
    { label: "Advanced Topics", done: false },
    { label: "Final Assessment", done: false },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Learning Path</h1><p className="subtitle">Track your journey through each topic</p></div>
      </div>

      <div className="lp-grid">
        <div>
          <h3 className="section-title">Enrolled Topics</h3>
          <div className="lp-list">
            {paths.map((p) => (
              <Card key={p.id} className={`lp-card ${p.status}`}>
                <div className="lp-card-header">
                  <div>
                    <strong>{p.topic}</strong>
                    <Badge label={p.status.replace("-", " ")} type={p.status === "completed" ? "success" : p.status === "in-progress" ? "warning" : "default"} />
                  </div>
                  <span className="lp-pct">{p.progress}%</span>
                </div>
                <ProgressBar value={p.progress} color={p.status === "completed" ? "#10b981" : p.status === "in-progress" ? "#6366f1" : "#94a3b8"} />
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h3 className="section-title">Algebra — Milestones</h3>
          <div className="milestones">
            {steps.map((s, i) => (
              <div key={s.label} className={`milestone ${s.done ? "done" : ""}`}>
                <div className="milestone-dot">
                  {s.done ? <Icon name="check" size={14} /> : <span>{i + 1}</span>}
                </div>
                <div className="milestone-line" />
                <div className="milestone-label">
                  <strong>{s.label}</strong>
                  {s.done && <span className="done-tag">Completed</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MODULES PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function ModulesPage() {
  const [selected, setSelected] = useState(null);
  const modules = [
    { id: 1, title: "Introduction to Algebra", notes: "Algebra is the branch of mathematics dealing with symbols and the rules for manipulating those symbols. In elementary algebra, those symbols represent quantities without fixed values, known as variables. This module covers the basics of algebraic thinking.", video: "https://www.youtube.com/embed/dQw4w9WgXcQ", difficulty: "Easy" },
    { id: 2, title: "Linear Equations", notes: "A linear equation is an equation that can be written in the form ax + b = c. Learn how to solve for unknowns using inverse operations and properties of equality.", video: "", difficulty: "Medium" },
    { id: 3, title: "Quadratic Equations", notes: "Quadratic equations are polynomial equations of the second degree. Learn the quadratic formula, factoring, and completing the square.", video: "", difficulty: "Hard" },
    { id: 4, title: "Cell Biology Basics", notes: "Cells are the basic unit of life. This module explores prokaryotic and eukaryotic cells, their organelles, and how they function.", video: "", difficulty: "Easy" },
    { id: 5, title: "Photosynthesis Deep Dive", notes: "Explore the light-dependent and light-independent reactions of photosynthesis. Understand how chlorophyll absorbs light and how ATP is produced.", video: "", difficulty: "Medium" },
  ];

  const diffColor = { Easy: "#10b981", Medium: "#f59e0b", Hard: "#ef4444" };

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Modules</h1><p className="subtitle">Study notes and video lessons</p></div>
      </div>
      <div className="modules-grid">
        {modules.map((m) => (
          <Card key={m.id} className="module-card" onClick={() => setSelected(m)}>
            <div className="module-thumb" style={{ background: `linear-gradient(135deg, hsl(${m.id * 55}, 70%, 85%), hsl(${m.id * 55 + 40}, 70%, 75%))` }}>
              <Icon name={m.video ? "play" : "book"} size={32} />
            </div>
            <div className="module-info">
              <h3>{m.title}</h3>
              <p>{m.notes.slice(0, 80)}…</p>
              <div className="module-meta">
                <Badge label={m.difficulty} type={m.difficulty === "Easy" ? "success" : m.difficulty === "Medium" ? "warning" : "error"} />
                {m.video && <Badge label="Has Video" type="info" />}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.title}>
        <div className="module-modal">
          <Badge label={selected?.difficulty} type="info" />
          {selected?.video && (
            <div className="video-wrap">
              <iframe src={selected.video} title="video" allowFullScreen />
            </div>
          )}
          <h4>Study Notes</h4>
          <p className="module-notes">{selected?.notes}</p>
          <div className="module-actions">
            <button className="btn-primary">Take Quiz on This</button>
            <button className="btn-outline">Mark as Done</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// QUIZ PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function QuizPage() {
  const questions = [
    { id: 1, question: "What is the value of x in: 2x + 4 = 10?", options: ["2", "3", "4", "5"], answer: 1, difficulty: "Easy" },
    { id: 2, question: "Which organelle is known as the 'powerhouse of the cell'?", options: ["Nucleus", "Ribosome", "Mitochondria", "Golgi body"], answer: 2, difficulty: "Easy" },
    { id: 3, question: "What is the discriminant of x² - 5x + 6 = 0?", options: ["1", "4", "25", "-24"], answer: 0, difficulty: "Hard" },
    { id: 4, question: "During which process do plants produce glucose?", options: ["Respiration", "Transpiration", "Photosynthesis", "Osmosis"], answer: 2, difficulty: "Medium" },
  ];

  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [done, setDone] = useState(false);

  const q = questions[current];
  const score = answers.filter((a, i) => a === questions[i].answer).length;

  const handleSelect = (i) => { if (selected === null) setSelected(i); };
  const handleNext = () => {
    setAnswers([...answers, selected]);
    if (current + 1 < questions.length) { setCurrent(current + 1); setSelected(null); }
    else setDone(true);
  };

  if (done) {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div className="page">
        <div className="quiz-result">
          <div className="result-circle" style={{ "--pct": pct }}>
            <span>{pct}%</span>
          </div>
          <h2>Quiz Complete!</h2>
          <p>You scored {score} out of {questions.length}</p>
          <div className="result-breakdown">
            {questions.map((q, i) => (
              <div key={i} className={`result-item ${answers[i] === q.answer ? "correct" : "wrong"}`}>
                <Icon name={answers[i] === q.answer ? "check" : "x"} size={16} />
                <span>{q.question.slice(0, 50)}…</span>
              </div>
            ))}
          </div>
          <button className="btn-primary" onClick={() => { setCurrent(0); setSelected(null); setAnswers([]); setDone(false); }}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Quiz</h1><p className="subtitle">Question {current + 1} of {questions.length}</p></div>
        <Badge label={q.difficulty} type={q.difficulty === "Easy" ? "success" : q.difficulty === "Medium" ? "warning" : "error"} />
      </div>

      <div className="quiz-wrap">
        <div className="quiz-progress">
          {questions.map((_, i) => (
            <div key={i} className={`quiz-dot ${i < current ? "done" : i === current ? "active" : ""}`} />
          ))}
        </div>

        <Card className="quiz-card">
          <p className="quiz-module">Module: Algebra</p>
          <h2 className="quiz-question">{q.question}</h2>
          <div className="quiz-options">
            {q.options.map((o, i) => (
              <button key={i}
                className={`quiz-option ${selected === i ? (i === q.answer ? "correct" : "wrong") : selected !== null && i === q.answer ? "reveal" : ""}`}
                onClick={() => handleSelect(i)}>
                <span className="option-letter">{String.fromCharCode(65 + i)}</span>
                {o}
              </button>
            ))}
          </div>
          <button className="btn-primary" disabled={selected === null} onClick={handleNext}>
            {current + 1 < questions.length ? "Next Question" : "See Results"}
          </button>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// GAMES PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function GamesPage() {
  const sessions = [
    { id: 1, score: 450, levels: "Level 3", date: "Mar 22" },
    { id: 2, score: 720, levels: "Level 5", date: "Mar 20" },
    { id: 3, score: 310, levels: "Level 2", date: "Mar 18" },
  ];

  const leaderboard = [
    { name: "Priya S.", score: 1840, level: "Level 8" },
    { name: "Arjun K.", score: 1620, level: "Level 7" },
    { name: "You", score: 1480, level: "Level 5", isYou: true },
    { name: "Sneha R.", score: 1390, level: "Level 6" },
    { name: "Dev M.", score: 980, level: "Level 4" },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Game Sessions</h1><p className="subtitle">Practice through play</p></div>
        <button className="btn-primary"><Icon name="play" size={16} /> New Game</button>
      </div>

      <div className="games-grid">
        <Card className="wide">
          <div className="card-header"><h3>Your Sessions</h3></div>
          <table className="data-table">
            <thead><tr><th>#</th><th>Level</th><th>Score</th><th>Date</th><th></th></tr></thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>{s.id}</td>
                  <td><Badge label={s.levels} type="info" /></td>
                  <td><strong>{s.score}</strong></td>
                  <td>{s.date}</td>
                  <td><button className="link-btn">Replay</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <div className="card-header"><h3>Leaderboard</h3><Icon name="trophy" size={18} /></div>
          <div className="leaderboard">
            {leaderboard.map((p, i) => (
              <div key={p.name} className={`lb-row ${p.isYou ? "you" : ""}`}>
                <span className={`lb-rank rank-${i + 1}`}>{i + 1}</span>
                <div className="lb-info">
                  <strong>{p.name}</strong>
                  <span>{p.level}</span>
                </div>
                <span className="lb-score">{p.score}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="card-header"><h3>Achievements</h3></div>
          <div className="achievements">
            {[
              { icon: "star", label: "First Quiz", unlocked: true },
              { icon: "flame", label: "7-Day Streak", unlocked: true },
              { icon: "trophy", label: "Top 3 Score", unlocked: false },
              { icon: "zap", label: "Speed Learner", unlocked: false },
              { icon: "target", label: "Perfect Score", unlocked: false },
              { icon: "clock", label: "Night Owl", unlocked: true },
            ].map((a) => (
              <div key={a.label} className={`achievement ${a.unlocked ? "unlocked" : ""}`}>
                <Icon name={a.icon} size={24} />
                <span>{a.label}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PERFORMANCE PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function PerformancePage() {
  const data = {
    accuracy: 87.4,
    strongTopics: ["Algebra", "World War II", "Python Basics"],
    weakTopics: ["Organic Chemistry", "Trigonometry"],
    recentScores: [65, 78, 82, 74, 90, 88, 87],
    days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  };

  const max = Math.max(...data.recentScores);

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Performance Analysis</h1><p className="subtitle">Your learning insights this week</p></div>
      </div>

      <div className="perf-grid">
        <Card className="accuracy-card">
          <h3>Overall Accuracy</h3>
          <div className="accuracy-ring">
            <svg viewBox="0 0 120 120" width="120" height="120">
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="10" />
              <circle cx="60" cy="60" r="50" fill="none" stroke="#6366f1" strokeWidth="10"
                strokeDasharray={`${2 * Math.PI * 50 * data.accuracy / 100} ${2 * Math.PI * 50}`}
                strokeLinecap="round" transform="rotate(-90 60 60)" />
            </svg>
            <div className="accuracy-label">
              <strong>{data.accuracy}%</strong>
              <span>Accuracy</span>
            </div>
          </div>
        </Card>

        <Card>
          <h3>Weekly Score Trend</h3>
          <div className="bar-chart">
            {data.recentScores.map((s, i) => (
              <div key={i} className="bar-col">
                <div className="bar-val">{s}</div>
                <div className="bar" style={{ height: `${(s / max) * 100}%` }} />
                <div className="bar-label">{data.days[i]}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="card-header"><h3>Strong Topics</h3><span className="chip success">🟢 Keep it up!</span></div>
          <div className="topic-pills">
            {data.strongTopics.map((t) => (
              <div key={t} className="topic-pill strong"><Icon name="check" size={14} />{t}</div>
            ))}
          </div>
          <div className="card-header" style={{ marginTop: 20 }}><h3>Weak Topics</h3><span className="chip error">🔴 Needs work</span></div>
          <div className="topic-pills">
            {data.weakTopics.map((t) => (
              <div key={t} className="topic-pill weak"><Icon name="target" size={14} />{t}</div>
            ))}
          </div>
        </Card>

        <Card className="wide">
          <h3>Topic-wise Accuracy</h3>
          <div className="topic-accuracy-list">
            {[
              { name: "Algebra", pct: 92 },
              { name: "Python Basics", pct: 88 },
              { name: "World War II", pct: 85 },
              { name: "Photosynthesis", pct: 74 },
              { name: "Trigonometry", pct: 58 },
              { name: "Organic Chemistry", pct: 45 },
            ].map((t) => (
              <div key={t.name} className="topic-accuracy-row">
                <span>{t.name}</span>
                <ProgressBar value={t.pct} color={t.pct > 75 ? "#10b981" : t.pct > 60 ? "#f59e0b" : "#ef4444"} />
                <span className="pct-label">{t.pct}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUGGESTIONS PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function SuggestionsPage() {
  const suggestions = [
    { id: 1, suggestedTopics: "Trigonometry", improvementArea: "Practice more identities and unit circle problems. Focus on sin/cos/tan values.", priority: "High" },
    { id: 2, suggestedTopics: "Organic Chemistry", improvementArea: "Review functional groups and basic reaction mechanisms like addition and substitution.", priority: "High" },
    { id: 3, suggestedTopics: "Photosynthesis", improvementArea: "Revisit the Calvin Cycle steps to solidify your understanding.", priority: "Medium" },
    { id: 4, suggestedTopics: "World War II Aftermath", improvementArea: "Explore post-war treaties and the formation of the UN for a complete picture.", priority: "Low" },
  ];

  const priorityColor = { High: "#ef4444", Medium: "#f59e0b", Low: "#10b981" };

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Suggestions</h1><p className="subtitle">Personalized recommendations based on your performance</p></div>
      </div>

      <div className="suggestions-list">
        {suggestions.map((s) => (
          <Card key={s.id} className="suggestion-card">
            <div className="suggestion-left" style={{ borderLeftColor: priorityColor[s.priority] }}>
              <div className="suggestion-header">
                <Icon name="lightbulb" size={20} />
                <h3>{s.suggestedTopics}</h3>
                <Badge label={s.priority + " Priority"} type={s.priority === "High" ? "error" : s.priority === "Medium" ? "warning" : "success"} />
              </div>
              <p>{s.improvementArea}</p>
              <div className="suggestion-actions">
                <button className="btn-primary">Start Studying</button>
                <button className="btn-outline">Remind Me Later</button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROFILE PAGE
// ═══════════════════════════════════════════════════════════════════════════════
function ProfilePage() {
  const { user } = useApp();
  const [editing, setEditing] = useState(false);
  const [profile, setProfile] = useState({ name: user?.name || "Student", class: "10", board: "CBSE", rollNo: "22-001" });
  const set = (k, v) => setProfile((p) => ({ ...p, [k]: v }));

  const handleSave = async () => {
    // await api.post("/profile/update", profile);
    setEditing(false);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div><h1>Profile</h1><p className="subtitle">Your account information</p></div>
      </div>

      <div className="profile-grid">
        <Card className="profile-hero">
          <div className="profile-avatar">{profile.name[0]?.toUpperCase()}</div>
          <h2>{profile.name}</h2>
          <p>{user?.email}</p>
          <div className="profile-badges">
            <Badge label="Class 10" type="info" />
            <Badge label="CBSE" type="info" />
          </div>
        </Card>

        <Card>
          <div className="card-header">
            <h3>Personal Details</h3>
            <button className="btn-outline small" onClick={() => setEditing(!editing)}>
              {editing ? "Cancel" : "Edit"}
            </button>
          </div>
          <div className="profile-form">
            <label>Full Name
              <input value={profile.name} onChange={(e) => set("name", e.target.value)} disabled={!editing} />
            </label>
            <label>Email
              <input value={user?.email || ""} disabled />
            </label>
            <div className="form-row">
              <label>Class
                <input value={profile.class} onChange={(e) => set("class", e.target.value)} disabled={!editing} />
              </label>
              <label>Board
                <input value={profile.board} onChange={(e) => set("board", e.target.value)} disabled={!editing} />
              </label>
            </div>
            <label>Roll No.
              <input value={profile.rollNo} onChange={(e) => set("rollNo", e.target.value)} disabled={!editing} />
            </label>
            {editing && <button className="btn-primary" onClick={handleSave}>Save Changes</button>}
          </div>
        </Card>

        <Card>
          <h3>Account Stats</h3>
          <div className="account-stats">
            {[
              { label: "Member Since", value: "Jan 2025" },
              { label: "Topics Enrolled", value: "8" },
              { label: "Total Quiz Attempts", value: "34" },
              { label: "Best Game Score", value: "720" },
            ].map((s) => (
              <div key={s.label} className="account-stat">
                <span>{s.label}</span>
                <strong>{s.value}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// APP ROOT
// ═══════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);

  const onLogout = () => { setUser(null); localStorage.removeItem("token"); };

  if (!user) return <AuthPage onLogin={setUser} />;

  const pages = {
    dashboard: <Dashboard />,
    topics: <TopicsPage />,
    "learning-path": <LearningPathPage />,
    modules: <ModulesPage />,
    quiz: <QuizPage />,
    games: <GamesPage />,
    performance: <PerformancePage />,
    suggestions: <SuggestionsPage />,
    profile: <ProfilePage />,
  };

  return (
    <AppContext.Provider value={{ user, setPage }}>
      <div className="app">
        <Sidebar page={page} setPage={setPage} user={user} onLogout={onLogout} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
        <main className="main">
          <div className="mobile-header">
            <button className="icon-btn" onClick={() => setMobileOpen(true)}><Icon name="menu" /></button>
            <span className="mobile-title">LearnPath</span>
            <div className="avatar small">{user?.name?.[0]?.toUpperCase()}</div>
          </div>
          {pages[page] || <Dashboard />}
        </main>
      </div>
    </AppContext.Provider>
  );
}
