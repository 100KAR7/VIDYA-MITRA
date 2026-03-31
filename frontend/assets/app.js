const state = {
  options: null,
  demos: [],
  history: [],
  latestResult: null,
  currentSession: null,
  currentUser: null,
  authToken: null,
};

const form = document.getElementById("student-form");
const subjectSelect = document.getElementById("subject");
const topicSelect = document.getElementById("topic");
const demoList = document.getElementById("demo-list");
const historyList = document.getElementById("history-list");
const gameLibrary = document.getElementById("game-library");
const gameSession = document.getElementById("game-session");
const statusMessage = document.getElementById("status-message");
const studentProgress = document.getElementById("student-progress");
const teacherDashboard = document.getElementById("teacher-dashboard");
const teacherDashboardCard = document.getElementById("teacher-dashboard-card");
const authStatus = document.getElementById("auth-status");

document.getElementById("login-btn").addEventListener("click", loginUser);
document.getElementById("predict-now").addEventListener("click", submitPrediction);
document.getElementById("load-demo").addEventListener("click", loadDemoStudents);
subjectSelect.addEventListener("change", syncTopics);
gameLibrary.addEventListener("click", launchGameFromCard);
gameSession.addEventListener("click", submitGameAnswer);

boot();

async function boot() {
  loadHistory();
  loadUser();
  await Promise.all([loadOptions(), loadDemoStudents()]);
  await refreshRoleViews();
}

async function loadOptions() {
  const payload = await apiFetch("/api/options");
  state.options = payload;
  fillSelect(document.getElementById("grade"), state.options.grades);
  fillSelect(subjectSelect, state.options.subjects);
  fillSelect(document.getElementById("learning_style"), state.options.learning_styles);
  fillSelect(document.getElementById("device_type"), state.options.device_types);
  syncTopics();
}

async function loadDemoStudents() {
  const payload = await apiFetch("/api/demo-students");
  state.demos = payload.students;
  renderDemos();
}

function renderDemos() {
  demoList.innerHTML = "";
  state.demos.forEach((student) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "demo-pill";
    button.textContent = `${student.name} · ${humanize(student.subject)}`;
    button.addEventListener("click", () => populateForm(student));
    demoList.appendChild(button);
  });
}

function fillSelect(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${humanize(value)}</option>`).join("");
}

function syncTopics() {
  if (!state.options) return;
  const subject = subjectSelect.value || state.options.subjects[0];
  const topics = state.options.topics_by_subject[subject] || [];
  const current = topicSelect.value;
  fillSelect(topicSelect, topics);
  if (topics.includes(current)) topicSelect.value = current;
}

function populateForm(student) {
  Object.entries(student).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (field) field.value = value;
  });
  syncTopics();
  form.elements.namedItem("topic").value = student.topic;
  statusMessage.textContent = `Loaded demo learner: ${student.name}.`;
}

async function submitPrediction() {
  if (!ensureSignedIn()) return;

  const payload = formPayload();
  statusMessage.textContent = "Generating adaptive recommendation...";
  try {
    const result = await apiFetch("/api/predict", {
      method: "POST",
      body: JSON.stringify({ student_profile: payload }),
    });
    state.latestResult = result;
    paintResult(result);
    pushHistory(payload, result);
    await refreshStudentProgress(payload.student_id);
    await refreshTeacherDashboard();
    statusMessage.textContent = "Recommendation ready.";
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

function paintResult(result) {
  const game = result.recommended_game;
  text("next_topic", humanize(result.next_recommended_topic));
  text("difficulty", result.recommended_difficulty.toUpperCase());
  text("success_label", `${humanize(result.success_probability_label)} · ${Math.round(result.success_probability * 100)}%`);
  text("needs_revision", result.needs_revision ? `YES · ${result.revision_urgency}` : "NO");
  text("adaptive_action", result.adaptive_action);
  text("game_name", game.game_name);
  text("game_meta", `${game.game_variant_id} · ${humanize(game.game_mode)} · ${humanize(game.game_type)}`);
  text("game_type", humanize(game.game_type));
  text("game_theme", humanize(game.theme));
  text("game_style", humanize(game.interaction_style));
  text("game_mode", humanize(game.game_mode));
  text("learning_objective", game.learning_objective);
  text("adaptation_reason", game.adaptation_reason);
  text("hero-topic", humanize(result.next_recommended_topic));
  text("hero-difficulty", result.recommended_difficulty.toUpperCase());
  text("hero-game", game.game_name);
  renderRules(game.content_rules);
  renderGameLibrary(result.game_library || []);
  resetSessionPanel();
}

function renderRules(rules) {
  document.getElementById("content_rules").innerHTML = rules.map((rule) => `<li>${rule}</li>`).join("");
}

function renderGameLibrary(games) {
  if (!games.length) {
    gameLibrary.innerHTML = `
      <article class="game-card empty-card">
        <strong>Game cards will appear here</strong>
        <p>Generate a recommendation to unlock the game shelf.</p>
      </article>
    `;
    return;
  }

  gameLibrary.innerHTML = games.map((game) => `
    <article class="game-card">
      <div class="game-card-head">
        <strong>${game.game_name}</strong>
        <span class="game-badge">${game.status}</span>
      </div>
      <p>${humanize(game.learning_target)} · ${humanize(game.game_type)} · ${humanize(game.interaction_style)}</p>
      <div class="game-meta-grid">
        <div><span>Arc</span><strong>${game.progression_arc}</strong></div>
        <div><span>Session</span><strong>${game.session_length}</strong></div>
        <div><span>Rewards</span><strong>${game.reward_loop}</strong></div>
        <div><span>Variant</span><strong>${game.game_variant_id}</strong></div>
      </div>
      <button class="game-launch" type="button" data-slot="${game.slot}">${game.launch_label}</button>
    </article>
  `).join("");
}

async function launchGameFromCard(event) {
  if (!ensureSignedIn()) return;

  const button = event.target.closest("button[data-slot]");
  if (!button || !state.latestResult) return;

  const selectedGame = (state.latestResult.game_library || []).find((game) => String(game.slot) === button.dataset.slot);
  if (!selectedGame) return;

  statusMessage.textContent = `Launching ${selectedGame.game_name}...`;
  try {
    const result = await apiFetch("/api/games/launch", {
      method: "POST",
      body: JSON.stringify({
        student_profile: formPayload(),
        prediction: state.latestResult,
        game: selectedGame,
      }),
    });
    state.currentSession = result;
    renderSession(result, null);
    statusMessage.textContent = `${selectedGame.game_name} launched.`;
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

async function submitGameAnswer(event) {
  if (!ensureSignedIn()) return;

  const button = event.target.closest("button[data-choice]");
  if (!button || !state.currentSession) return;

  try {
    const result = await apiFetch("/api/games/answer", {
      method: "POST",
      body: JSON.stringify({ session_id: state.currentSession.session_id, choice_id: button.dataset.choice }),
    });

    state.currentSession = {
      ...state.currentSession,
      question: result.question,
      progress: result.progress,
      summary: result.summary,
      completed: result.completed,
    };
    renderSession(state.currentSession, result);
    if (result.completed) {
      await refreshStudentProgress(formPayload().student_id);
      await refreshTeacherDashboard();
    }
    statusMessage.textContent = result.completed ? "Game session completed." : `Round ${result.progress.current_round} ready.`;
  } catch (error) {
    statusMessage.textContent = error.message;
  }
}

function renderSession(session, feedback) {
  if (session.summary) {
    gameSession.innerHTML = `
      <div class="session-summary">
        <strong>${session.summary.game_name} complete</strong>
        <p>${session.summary.completion_note}</p>
        <div class="summary-score">
          <span>${session.summary.score}/${session.summary.max_score} points</span>
          <span>${session.summary.score_percent}% accuracy</span>
          <span>${session.summary.stars} star rating</span>
        </div>
        <p>Target topic: ${humanize(session.summary.target_topic)}</p>
        <p>${session.summary.recommended_next_action}</p>
      </div>
    `;
    return;
  }

  const question = session.question;
  const feedbackBlock = feedback
    ? `<div class="answer-feedback">${feedback.correct ? "Correct." : "Not quite."} ${feedback.explanation}</div>`
    : "";

  gameSession.innerHTML = `
    <div class="session-panel">
      <div class="session-top">
        <div>
          <strong>${session.game.game_name}</strong>
          <p>${humanize(session.game.learning_target)} · ${humanize(session.game.game_mode)}</p>
        </div>
        <div class="progress-pill">Round ${session.progress.current_round}/${session.progress.total_rounds} · ${session.progress.score}/${session.progress.max_score} pts</div>
      </div>
      ${feedbackBlock}
      <div class="question-card">
        <h3>${question.prompt}</h3>
        <div class="choice-grid">
          ${question.choices.map((choice) => `<button type="button" class="choice-button" data-choice="${choice.id}">${choice.label}</button>`).join("")}
        </div>
      </div>
    </div>
  `;
}

function resetSessionPanel() {
  state.currentSession = null;
  gameSession.innerHTML = "Launch a game card to start a live learning session.";
}

function formPayload() {
  const payload = Object.fromEntries(new FormData(form).entries());
  numericFields().forEach((field) => {
    payload[field] = Number(payload[field]);
  });
  return payload;
}

function pushHistory(payload, result) {
  const entry = {
    at: new Date().toLocaleString(),
    learner: `${payload.student_id} · ${humanize(payload.subject)} · ${humanize(payload.topic)}`,
    outcome: `${humanize(result.next_recommended_topic)} · ${result.recommended_difficulty.toUpperCase()}`,
    game: result.recommended_game.game_name,
  };
  state.history = [entry, ...state.history].slice(0, 6);
  localStorage.setItem("vidya_mitra_history", JSON.stringify(state.history));
  renderHistory();
}

function loadHistory() {
  try {
    state.history = JSON.parse(localStorage.getItem("vidya_mitra_history") || "[]");
  } catch {
    state.history = [];
  }
  renderHistory();
}

function renderHistory() {
  if (!state.history.length) {
    historyList.innerHTML = '<p class="history-empty">No runs yet. Generate a recommendation to begin.</p>';
    return;
  }
  historyList.innerHTML = state.history.map((item) => `
    <article class="history-item">
      <strong>${item.learner}</strong>
      <p>${item.outcome}</p>
      <p>${item.game}</p>
      <p>${item.at}</p>
    </article>
  `).join("");
}

async function loginUser() {
  const role = document.getElementById("user-role").value;
  const userId = document.getElementById("user-id").value.trim();
  const displayName = document.getElementById("display-name").value.trim();
  if (!userId || !displayName) {
    authStatus.textContent = "User ID and display name are required.";
    return;
  }

  try {
    const payload = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ role, user_id: userId, display_name: displayName }),
    });
    state.currentUser = payload.user;
    state.authToken = payload.access_token;
    localStorage.setItem("vidya_mitra_user", JSON.stringify(payload.user));
    localStorage.setItem("vidya_mitra_token", payload.access_token);
    applyUserToForm();
    syncUserDisplay();
    await refreshRoleViews();
  } catch (error) {
    authStatus.textContent = error.message || "Login failed.";
  }
}

function loadUser() {
  try {
    state.currentUser = JSON.parse(localStorage.getItem("vidya_mitra_user") || "null");
    state.authToken = localStorage.getItem("vidya_mitra_token");
  } catch {
    state.currentUser = null;
    state.authToken = null;
  }
  syncUserDisplay();
  applyUserToForm();
}

function applyUserToForm() {
  if (!state.currentUser) return;
  document.getElementById("user-role").value = state.currentUser.role;
  document.getElementById("user-id").value = state.currentUser.user_id;
  document.getElementById("display-name").value = state.currentUser.display_name;
  if (state.currentUser.role === "student") {
    form.elements.namedItem("student_id").value = state.currentUser.user_id;
  }
}

function syncUserDisplay() {
  if (!state.currentUser || !state.authToken) {
    authStatus.textContent = "Sign in to generate recommendations, track progress, and launch games.";
    teacherDashboardCard.classList.add("hidden");
    return;
  }
  authStatus.textContent = `${state.currentUser.display_name} signed in as ${state.currentUser.role}.`;
  teacherDashboardCard.classList.toggle("hidden", !["teacher", "admin"].includes(state.currentUser.role));
}

async function refreshRoleViews() {
  const studentId = form.elements.namedItem("student_id").value;
  if (!state.authToken) {
    studentProgress.textContent = "Sign in to view learner progress.";
    teacherDashboard.innerHTML = "Teacher dashboard will appear after teacher login.";
    return;
  }
  await refreshStudentProgress(studentId);
  await refreshTeacherDashboard();
}

async function refreshStudentProgress(studentId) {
  if (!state.authToken) {
    studentProgress.textContent = "Sign in to view learner progress.";
    return;
  }
  if (!studentId) {
    studentProgress.textContent = "Progress will appear here after login or prediction.";
    return;
  }
  try {
    const progress = await apiFetch(`/api/progress/${studentId}`);
    renderStudentProgress(progress);
  } catch (error) {
    studentProgress.textContent = error.message;
  }
}

function renderStudentProgress(progress) {
  const latest = progress.latest_prediction
    ? `${humanize(progress.latest_prediction.next_recommended_topic)} · ${progress.latest_prediction.recommended_difficulty.toUpperCase()}`
    : "No predictions yet";
  const recentGames = progress.recent_games.length
    ? progress.recent_games.map((item) => `<li>${item.game_name} · ${item.summary.score_percent}%</li>`).join("")
    : "<li>No completed game sessions yet.</li>";
  studentProgress.innerHTML = `
    <strong>${progress.student_id}</strong>
    <p>Predictions: ${progress.total_predictions} · Sessions: ${progress.total_sessions} · Avg score: ${progress.average_score_percent}%</p>
    <p>Latest learning path: ${latest}</p>
    <ul>${recentGames}</ul>
  `;
}

async function refreshTeacherDashboard() {
  if (!state.currentUser || !["teacher", "admin"].includes(state.currentUser.role) || !state.authToken) {
    teacherDashboard.innerHTML = "Teacher dashboard will appear after teacher login.";
    return;
  }
  try {
    const dashboard = await apiFetch("/api/dashboard/teacher");
    const activity = dashboard.recent_activity.length
      ? dashboard.recent_activity.map((item) => `
          <article class="activity-item">
            <strong>${item.student_id} · ${item.game_name}</strong>
            <p>${item.summary.score_percent}% · ${humanize(item.summary.target_topic)}</p>
            <p>${item.timestamp}</p>
          </article>
        `).join("")
      : "<p>No classroom activity yet.</p>";

    teacherDashboard.innerHTML = `
      <div class="teacher-metrics">
        <article class="teacher-metric"><span>Learners</span><strong>${dashboard.total_learners}</strong></article>
        <article class="teacher-metric"><span>Predictions</span><strong>${dashboard.total_predictions}</strong></article>
        <article class="teacher-metric"><span>Sessions</span><strong>${dashboard.total_game_sessions}</strong></article>
        <article class="teacher-metric"><span>Avg Score</span><strong>${dashboard.average_score_percent}%</strong></article>
        <article class="teacher-metric"><span>Revision Alerts</span><strong>${dashboard.revision_alerts}</strong></article>
      </div>
      <div class="activity-list">${activity}</div>
    `;
  } catch (error) {
    teacherDashboard.innerHTML = error.message;
  }
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (state.authToken) {
    headers.set("Authorization", `Bearer ${state.authToken}`);
  }

  const response = await fetch(url, { ...options, headers });
  const isJson = (response.headers.get("content-type") || "").includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthState();
    }
    throw new Error(payload?.error || `Request failed with status ${response.status}.`);
  }
  return payload;
}

function ensureSignedIn() {
  if (state.authToken && state.currentUser) {
    return true;
  }
  statusMessage.textContent = "Sign in first to use recommendations and games.";
  return false;
}

function clearAuthState() {
  state.currentUser = null;
  state.authToken = null;
  localStorage.removeItem("vidya_mitra_user");
  localStorage.removeItem("vidya_mitra_token");
  syncUserDisplay();
}

function text(id, value) {
  document.getElementById(id).textContent = value;
}

function humanize(value) {
  return String(value || "").replaceAll("_", " ");
}

function numericFields() {
  return [
    "past_quiz_score_avg",
    "accuracy_percentage",
    "avg_response_time_sec",
    "num_attempts",
    "learning_streak_days",
    "engagement_score",
    "hints_used",
    "video_watch_pct",
    "time_on_task_min",
    "session_count_week",
  ];
}
