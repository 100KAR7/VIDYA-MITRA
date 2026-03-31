const state = {
  sessionId: document.body.dataset.sessionId,
  authToken: null,
  currentUser: null,
  session: null,
  feedback: null,
  timerId: null,
  timerExpired: false,
  lessonSelections: {},
};

const playerStage = document.getElementById("player-stage");
const playerStatus = document.getElementById("player-status");

playerStage.addEventListener("click", handleStageAction);

boot();

async function boot() {
  loadAuth();
  if (!state.authToken) {
    renderSignedOut();
    return;
  }
  await refreshSession();
}

function loadAuth() {
  try {
    state.currentUser = JSON.parse(localStorage.getItem("vidya_mitra_user") || "null");
    state.authToken = localStorage.getItem("vidya_mitra_token");
  } catch {
    state.currentUser = null;
    state.authToken = null;
  }
}

async function refreshSession() {
  try {
    playerStatus.textContent = "Loading the live session...";
    state.session = await apiFetch(`/api/games/session/${state.sessionId}`);
    renderSession(state.session, state.feedback);
    playerStatus.textContent = state.session.phase === "completed"
      ? "Mission complete. Final test recorded."
      : "Mission ready.";
  } catch (error) {
    clearTimer();
    playerStatus.textContent = error.message;
    playerStage.innerHTML = `<div class="session-summary"><strong>Session unavailable</strong><p>${error.message}</p></div>`;
  }
}

async function handleStageAction(event) {
  const lessonButton = event.target.closest("[data-action='advance-lesson']");
  const answerButton = event.target.closest("[data-choice]");
  const mechanicButton = event.target.closest("[data-mechanic-choice]");

  if (!state.authToken) {
    renderSignedOut();
    return;
  }

  if (mechanicButton) {
    handleMechanicChoice(mechanicButton.dataset.mechanicChoice);
    return;
  }

  if (lessonButton) {
    await advanceLesson();
    return;
  }

  if (answerButton) {
    await submitAnswer(answerButton.dataset.choice);
  }
}

function handleMechanicChoice(choiceId) {
  const lesson = state.session?.lesson;
  if (!lesson) return;
  state.lessonSelections[lesson.id] = choiceId;
  const correct = choiceId === lesson.correct_option_id;
  state.feedback = correct ? lesson.success_message : lesson.retry_message;
  playerStatus.textContent = correct ? "Mechanic solved. Badge ready to bank." : "Close. Review the mechanic and choose again.";
  renderSession(state.session, state.feedback);
}

async function advanceLesson() {
  const lesson = state.session?.lesson;
  if (!lesson) return;

  const selectionId = state.lessonSelections[lesson.id] || null;
  if (!selectionId && !state.timerExpired) {
    playerStatus.textContent = "Pick a mechanic option first, or wait for the timer to finish.";
    return;
  }

  try {
    playerStatus.textContent = "Saving lesson progress...";
    const payload = await apiFetch(`/api/games/session/${state.sessionId}/learn`, {
      method: "POST",
      body: JSON.stringify({ selection_id: selectionId }),
    });
    state.session = payload;
    state.feedback = payload.badge_awarded
      ? `${payload.badge_awarded.label} earned. ${payload.transition_note || ""}`.trim()
      : payload.transition_note || null;
    renderSession(state.session, state.feedback);
    playerStatus.textContent = payload.transition_note || "Lesson complete.";
  } catch (error) {
    playerStatus.textContent = error.message;
  }
}

async function submitAnswer(choiceId) {
  try {
    playerStatus.textContent = "Checking the answer...";
    const payload = await apiFetch(`/api/games/session/${state.sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ choice_id: choiceId }),
    });
    state.session = payload.session;
    state.feedback = payload.completed
      ? payload.summary.completion_note
      : `${payload.correct ? "Correct." : "Not quite."} ${payload.explanation}`;
    renderSession(state.session, state.feedback);
    playerStatus.textContent = payload.completed ? "Final test complete." : "Next test question ready.";
  } catch (error) {
    playerStatus.textContent = error.message;
  }
}

function renderSession(session, feedback) {
  applyPalette(session.game?.scene_pack?.palette);
  text("player-title", session.game.game_name);
  text("player-subtitle", session.game.narrative_hook || `${humanize(session.game.learning_target)} mission ready.`);
  text("phase-chip", phaseLabel(session.phase));
  text("phase-label", phaseLabel(session.phase));
  text("lesson-progress", `${session.progress.lessons_completed} / ${session.progress.total_lessons}`);
  text("test-progress", `${session.progress.current_round} / ${session.progress.total_rounds}`);
  text("score-progress", `${session.progress.score} / ${session.progress.max_score}`);
  text("sidebar-learner", session.learner.name);
  text("sidebar-grade", humanize(session.learner.grade));
  text("sidebar-topic", humanize(session.game.learning_target || session.summary?.target_topic || ""));
  text("sidebar-variant", session.game.game_variant_id);
  text("stage-heading", stageHeading(session.phase));

  document.getElementById("mission-details").innerHTML = `
    <strong>${session.game.scene_pack?.world_name || session.game.game_name}</strong>
    <p>${session.game.scene_pack?.mentor_title || "Guide"} · ${humanize(session.game.game_mode)} mode · ${humanize(session.game.game_type)}</p>
    <p>${session.game.learning_objective || "Learning objective locked to the model outcome."}</p>
    <p>${session.game.difficulty_meter || ""}</p>
    <p>Mechanics: ${(session.game.mechanic_lineup || []).map(humanize).join(" · ")}</p>
    <p>Final arena: ${session.game.boss_stage || "Final test gate"}</p>
  `;

  renderBadgeTrack(session.game.badge_track || [], session.earned_badges || []);

  if (session.phase === "learn" && session.lesson) {
    startStageTimer(session.lesson.timer_seconds, "lesson");
    renderLesson(session.lesson, feedback);
    return;
  }

  if (session.phase === "assessment" && session.question) {
    startStageTimer(session.question.timer_seconds, "assessment");
    renderQuestion(session.question, feedback, session.progress);
    return;
  }

  clearTimer();
  text("timer-progress", "--");
  renderSummary(session.summary);
}

function renderLesson(lesson, feedback) {
  const selectedId = state.lessonSelections[lesson.id];
  const feedbackBlock = feedback ? `<div class="answer-feedback">${feedback}</div>` : "";
  const mechanicPanel = renderMechanicPanel(lesson, selectedId);
  playerStage.innerHTML = `
    <div class="player-card">
      ${feedbackBlock}
      <div class="lesson-banner scene-banner">
        <span class="lesson-tag">Learning Mission</span>
        <h3>${lesson.title}</h3>
        <p>${lesson.subtitle}</p>
      </div>
      <div class="scene-strip">
        <strong>${lesson.scene_title}</strong>
        <div class="scene-tokens">
          ${lesson.scene_tokens.map((token) => `<span class="scene-token">${token}</span>`).join("")}
        </div>
      </div>
      <div class="lesson-coach">${lesson.coach_line}</div>
      <ul class="lesson-points">
        ${lesson.focus_points.map((point) => `<li>${point}</li>`).join("")}
      </ul>
      ${mechanicPanel}
      <div class="lesson-example">
        <strong>Mission context</strong>
        <p>${lesson.example}</p>
      </div>
      <div class="lesson-footer">
        <div class="badge-preview">
          <span class="badge-chip badge-chip-preview">${lesson.reward_badge.label}</span>
          <p>${lesson.reward_badge.description}</p>
        </div>
        <button type="button" class="button button-primary player-action" data-action="advance-lesson">${lesson.action_label}</button>
      </div>
    </div>
  `;
}

function renderMechanicPanel(lesson, selectedId) {
  const header = mechanicHeader(lesson.mechanic_type);
  return `
    <div class="mechanic-panel mechanic-${lesson.mechanic_type}">
      <div class="mechanic-head">
        <span class="lesson-tag">${header}</span>
        <p>${lesson.mechanic_prompt}</p>
      </div>
      <div class="mechanic-options">
        ${lesson.mechanic_options.map((option) => `
          <button
            type="button"
            class="mechanic-option ${selectedId === option.id ? "selected" : ""}"
            data-mechanic-choice="${option.id}"
          >
            <strong>${option.label}</strong>
            <span>${option.description}</span>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function renderQuestion(question, feedback, progress) {
  const feedbackBlock = feedback ? `<div class="answer-feedback">${feedback}</div>` : "";
  playerStage.innerHTML = `
    <div class="player-card">
      ${feedbackBlock}
      <div class="lesson-banner test-banner">
        <span class="lesson-tag">${question.arena_title}</span>
        <h3>${question.prompt}</h3>
        <p>Question ${progress.current_round} of ${progress.total_rounds}</p>
      </div>
      <div class="choice-grid">
        ${question.choices.map((choice) => `<button type="button" class="choice-button" data-choice="${choice.id}">${choice.label}</button>`).join("")}
      </div>
    </div>
  `;
}

function renderSummary(summary) {
  playerStage.innerHTML = `
    <div class="session-summary player-card">
      <strong>${summary.game_name} complete</strong>
      <p>${summary.completion_note}</p>
      <div class="summary-score">
        <span>${summary.score}/${summary.max_score} points</span>
        <span>${summary.score_percent}% accuracy</span>
        <span>${summary.stars} star rating</span>
      </div>
      <p>Lessons completed: ${summary.lessons_completed}/${summary.total_lessons}</p>
      <p>${summary.test_title}</p>
      <div class="badge-track summary-badges">
        ${(summary.badges_earned || []).map((badge) => `<span class="badge-chip ${badge.status === "mastered" ? "badge-chip-mastered" : "badge-chip-earned"}">${badge.label}</span>`).join("")}
      </div>
      <p>Next action: ${summary.recommended_next_action}</p>
      <div class="hero-actions">
        <a href="/" class="button button-primary">Return To Dashboard</a>
      </div>
    </div>
  `;
}

function renderBadgeTrack(badgeTrack, earnedBadges) {
  const earnedMap = new Map(earnedBadges.map((badge) => [badge.id, badge]));
  const badgeTrackNode = document.getElementById("badge-track");
  badgeTrackNode.innerHTML = badgeTrack.map((badge) => {
    const earned = earnedMap.get(badge.id);
    const badgeClass = !earned
      ? "badge-chip-locked"
      : earned.status === "mastered"
        ? "badge-chip-mastered"
        : "badge-chip-earned";
    return `
      <article class="badge-card">
        <span class="badge-chip ${badgeClass}">${badge.label}</span>
        <p>${badge.description}</p>
      </article>
    `;
  }).join("");
}

function renderSignedOut() {
  clearTimer();
  text("player-title", "Sign in required");
  text("player-subtitle", "This game session needs the same signed-in learner or teacher account.");
  playerStatus.textContent = "Please sign in on the main dashboard first, then open the game again.";
  playerStage.innerHTML = `
    <div class="session-summary player-card">
      <strong>Session locked</strong>
      <p>Go back to the main dashboard, sign in, generate a recommendation, and relaunch the game.</p>
      <div class="hero-actions">
        <a href="/" class="button button-primary">Go To Dashboard</a>
      </div>
    </div>
  `;
}

function startStageTimer(seconds, phase) {
  clearTimer();
  state.timerExpired = false;
  let remaining = Number(seconds || 0);
  text("timer-progress", formatSeconds(remaining));
  if (!remaining) return;

  state.timerId = window.setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearTimer();
      state.timerExpired = true;
      text("timer-progress", "00:00");
      playerStatus.textContent = phase === "assessment"
        ? "Timer ended. Submit your best answer now."
        : "Timer ended. You can bank the lesson badge when ready.";
      return;
    }
    text("timer-progress", formatSeconds(remaining));
  }, 1000);
}

function clearTimer() {
  if (state.timerId) {
    window.clearInterval(state.timerId);
    state.timerId = null;
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
      state.authToken = null;
      state.currentUser = null;
      localStorage.removeItem("vidya_mitra_token");
      localStorage.removeItem("vidya_mitra_user");
    }
    throw new Error(payload?.error || `Request failed with status ${response.status}.`);
  }
  return payload;
}

function stageHeading(phase) {
  if (phase === "learn") return "Learning mission";
  if (phase === "assessment") return "Final test";
  return "Mission summary";
}

function phaseLabel(phase) {
  if (phase === "learn") return "Learn";
  if (phase === "assessment") return "Test";
  return "Complete";
}

function mechanicHeader(type) {
  return {
    choice_path: "Route Pick",
    pattern_stack: "Pattern Stack",
    signal_scan: "Signal Scan",
    build_combo: "Build Combo",
  }[type] || humanize(type);
}

function applyPalette(palette) {
  document.body.dataset.palette = palette || "default";
}

function formatSeconds(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function text(id, value) {
  document.getElementById(id).textContent = value;
}

function humanize(value) {
  return String(value || "").replaceAll("_", " ");
}
