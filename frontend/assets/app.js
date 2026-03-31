const state = {
  options: null,
  demos: [],
};

const form = document.getElementById("student-form");
const subjectSelect = document.getElementById("subject");
const topicSelect = document.getElementById("topic");
const demoList = document.getElementById("demo-list");
const statusMessage = document.getElementById("status-message");

document.getElementById("predict-now").addEventListener("click", submitPrediction);
document.getElementById("load-demo").addEventListener("click", loadDemoStudents);
subjectSelect.addEventListener("change", syncTopics);

boot();

async function boot() {
  await Promise.all([loadOptions(), loadDemoStudents()]);
}

async function loadOptions() {
  const response = await fetch("/api/options");
  state.options = await response.json();

  fillSelect(document.getElementById("grade"), state.options.grades);
  fillSelect(subjectSelect, state.options.subjects);
  fillSelect(document.getElementById("learning_style"), state.options.learning_styles);
  fillSelect(document.getElementById("device_type"), state.options.device_types);
  syncTopics();
}

async function loadDemoStudents() {
  const response = await fetch("/api/demo-students");
  const payload = await response.json();
  state.demos = payload.students;
  renderDemos();
}

function renderDemos() {
  demoList.innerHTML = "";
  state.demos.forEach((student) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "demo-pill";
    button.textContent = `${student.name} · ${student.subject}`;
    button.addEventListener("click", () => populateForm(student));
    demoList.appendChild(button);
  });
}

function fillSelect(select, values) {
  select.innerHTML = values
    .map((value) => `<option value="${value}">${humanize(value)}</option>`)
    .join("");
}

function syncTopics() {
  if (!state.options) {
    return;
  }
  const subject = subjectSelect.value || state.options.subjects[0];
  const topics = state.options.topics_by_subject[subject] || [];
  const current = topicSelect.value;
  fillSelect(topicSelect, topics);
  if (topics.includes(current)) {
    topicSelect.value = current;
  }
}

function populateForm(student) {
  Object.entries(student).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (field) {
      field.value = value;
    }
  });
  syncTopics();
  form.elements.namedItem("topic").value = student.topic;
  statusMessage.textContent = `Loaded demo learner: ${student.name}.`;
}

async function submitPrediction() {
  const payload = Object.fromEntries(new FormData(form).entries());
  numericFields().forEach((field) => {
    payload[field] = Number(payload[field]);
  });

  statusMessage.textContent = "Generating adaptive recommendation...";

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Prediction failed");
    }
    paintResult(result);
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
}

function renderRules(rules) {
  const list = document.getElementById("content_rules");
  list.innerHTML = rules.map((rule) => `<li>${rule}</li>`).join("");
}

function text(id, value) {
  document.getElementById(id).textContent = value;
}

function humanize(value) {
  return String(value).replaceAll("_", " ");
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
