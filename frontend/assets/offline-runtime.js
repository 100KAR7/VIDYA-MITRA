(function (global) {
  const DB_NAME = "vidya-mitra-offline";
  const DB_VERSION = 1;
  const STORE_NAMES = {
    OFFLINE_PACK: "offlinePack",
    ACTIVE_SESSION: "activeSession",
    MASTERY_LEDGER: "masteryLedger",
    COMPLETED_PREDICTIONS: "completedPredictions",
    COMPLETED_GAME_SUMMARIES: "completedGameSummaries",
    SYNC_QUEUE: "syncQueue",
  };

  let dbPromise = null;

  function openDatabase() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!global.indexedDB) {
        reject(new Error("IndexedDB is not available in this browser."));
        return;
      }
      const request = global.indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        Object.values(STORE_NAMES).forEach((storeName) => {
          if (!db.objectStoreNames.contains(storeName)) {
            if (storeName === STORE_NAMES.SYNC_QUEUE) {
              db.createObjectStore(storeName, { keyPath: "event_id" });
            } else if (storeName === STORE_NAMES.OFFLINE_PACK) {
              db.createObjectStore(storeName, { keyPath: "pack_id" });
            } else if (storeName === STORE_NAMES.ACTIVE_SESSION) {
              db.createObjectStore(storeName, { keyPath: "session_id" });
            } else if (storeName === STORE_NAMES.MASTERY_LEDGER) {
              db.createObjectStore(storeName, { keyPath: "student_id" });
            } else {
              db.createObjectStore(storeName, { autoIncrement: true });
            }
          }
        });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Unable to open offline database."));
    });
    return dbPromise;
  }

  function withStore(storeName, mode, operation) {
    return openDatabase().then((db) => new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);
      const result = operation(store);
      transaction.oncomplete = () => resolve(result);
      transaction.onerror = () => reject(transaction.error || new Error("Store transaction failed."));
      transaction.onabort = () => reject(transaction.error || new Error("Store transaction aborted."));
    }));
  }

  async function saveOfflinePack(pack) {
    if (!pack) return null;
    return withStore(STORE_NAMES.OFFLINE_PACK, "readwrite", (store) => {
      store.put(pack);
      return pack;
    });
  }

  async function loadOfflinePack() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.OFFLINE_PACK, "readonly");
      const store = transaction.objectStore(STORE_NAMES.OFFLINE_PACK);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result[0] || null);
      request.onerror = () => reject(request.error || new Error("Unable to load offline pack."));
    });
  }

  async function saveActiveSession(session) {
    if (!session) return null;
    return withStore(STORE_NAMES.ACTIVE_SESSION, "readwrite", (store) => {
      store.put(session);
      return session;
    });
  }

  async function loadActiveSession(sessionId) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.ACTIVE_SESSION, "readonly");
      const store = transaction.objectStore(STORE_NAMES.ACTIVE_SESSION);
      const request = store.get(sessionId);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error("Unable to load active session."));
    });
  }

  async function loadAnyActiveSession() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.ACTIVE_SESSION, "readonly");
      const store = transaction.objectStore(STORE_NAMES.ACTIVE_SESSION);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result[0] || null);
      request.onerror = () => reject(request.error || new Error("Unable to load active sessions."));
    });
  }

  async function deleteActiveSession(sessionId) {
    if (!sessionId) return null;
    return withStore(STORE_NAMES.ACTIVE_SESSION, "readwrite", (store) => {
      store.delete(sessionId);
      return true;
    });
  }

  async function saveMasteryLedger(studentId, ledger) {
    if (!studentId) return null;
    return withStore(STORE_NAMES.MASTERY_LEDGER, "readwrite", (store) => {
      store.put({ student_id: studentId, ...ledger });
      return ledger;
    });
  }

  async function loadMasteryLedger(studentId) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.MASTERY_LEDGER, "readonly");
      const store = transaction.objectStore(STORE_NAMES.MASTERY_LEDGER);
      const request = studentId ? store.get(studentId) : store.getAll();
      request.onsuccess = () => {
        const result = request.result;
        if (result && result.student_id) {
          const { student_id, ...ledger } = result;
          resolve(ledger);
          return;
        }
        resolve(result || { topics: {} });
      };
      request.onerror = () => reject(request.error || new Error("Unable to load mastery ledger."));
    });
  }

  async function appendCompletedPrediction(entry) {
    return withStore(STORE_NAMES.COMPLETED_PREDICTIONS, "readwrite", (store) => {
      store.put({ ...entry, recorded_at: new Date().toISOString() });
      return true;
    });
  }

  async function appendCompletedGameSummary(entry) {
    return withStore(STORE_NAMES.COMPLETED_GAME_SUMMARIES, "readwrite", (store) => {
      store.put({ ...entry, recorded_at: new Date().toISOString() });
      return true;
    });
  }

  async function getCompletedPredictions() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.COMPLETED_PREDICTIONS, "readonly");
      const store = transaction.objectStore(STORE_NAMES.COMPLETED_PREDICTIONS);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error || new Error("Unable to read completed predictions."));
    });
  }

  async function getCompletedGameSummaries() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.COMPLETED_GAME_SUMMARIES, "readonly");
      const store = transaction.objectStore(STORE_NAMES.COMPLETED_GAME_SUMMARIES);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error || new Error("Unable to read completed game summaries."));
    });
  }

  async function addSyncQueueEvent(event) {
    if (!event || !event.event_id) return false;
    const existing = await getSyncQueueEvents();
    if (existing.some((item) => item.event_id === event.event_id)) return false;
    return withStore(STORE_NAMES.SYNC_QUEUE, "readwrite", (store) => {
      store.put(event);
      return true;
    });
  }

  async function getSyncQueueEvents() {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAMES.SYNC_QUEUE, "readonly");
      const store = transaction.objectStore(STORE_NAMES.SYNC_QUEUE);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error || new Error("Unable to read sync queue."));
    });
  }

  async function clearSyncQueue(events) {
    if (!events?.length) return true;
    return withStore(STORE_NAMES.SYNC_QUEUE, "readwrite", (store) => {
      events.forEach((event) => store.delete(event.event_id));
      return true;
    });
  }

  function normalizeKey(value) {
    return String(value || "general_knowledge").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  }

  function humanize(value) {
    return String(value || "").replaceAll("_", " ");
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function buildOfflineRecommendation(studentProfile, pack, masteryLedger, recentOutcomes, revisionHistory) {
    const topic = studentProfile?.topic || studentProfile?.subject || "general_knowledge";
    const topicKey = normalizeKey(topic);
    const masteryEntry = masteryLedger?.topics?.[topicKey] || masteryLedger?.topics?.[topic] || {};
    const masteryPercent = Number(masteryEntry.average_score_percent || 50);
    const attempts = Number(masteryEntry.attempts || studentProfile?.num_attempts || 1);
    const accuracy = Number(studentProfile?.accuracy_percentage || 70);
    const streak = Number(studentProfile?.learning_streak_days || 0);
    const recentLowScore = (recentOutcomes || []).some((entry) => Number(entry?.score || 0) < 60);
    const needsRevision = masteryPercent < 70 || attempts >= 3 || recentLowScore || (revisionHistory || []).length >= 1;
    const reviewed = masteryPercent < 55 ? "high" : masteryPercent < 70 ? "medium" : "low";
    const successProbability = clamp(0.35 + (accuracy / 100) * 0.35 + (masteryPercent / 100) * 0.2 + (streak / 90) * 0.1, 0.1, 0.95);
    const successProbabilityLabel = successProbability >= 0.78 ? "high" : successProbability >= 0.55 ? "medium" : "low";
    const recommendedDifficulty = accuracy >= 78 || masteryPercent >= 80 ? "medium" : masteryPercent < 55 || attempts >= 3 ? "easy" : "hard";
    const recommendedGame = buildGameLibrary(studentProfile, pack, topic)[0] || {
      game_name: "Offline Quest",
      game_variant_id: "offline-quest",
      game_type: "adaptive",
      theme: "exploration",
      interaction_style: "tap",
      game_mode: "guided",
      learning_objective: "Practice the next concept with a local mission.",
      adaptation_reason: "Offline rule engine selected the safest local mission.",
      progression_arc: "steady",
      session_length: "10 min",
      reward_loop: "badge loop",
      learning_target: topic,
      slot: 1,
      status: "offline-ready",
      launch_label: "Launch Offline Mission",
      content_rules: ["Review the concept before the final test.", "Keep pacing calm and steady."],
    };
    return {
      next_recommended_topic: topic,
      recommended_difficulty: recommendedDifficulty,
      success_probability: successProbability,
      success_probability_label: successProbabilityLabel,
      needs_revision: needsRevision,
      revision_urgency: reviewed,
      adaptive_action: needsRevision
        ? `Revisit ${humanize(topic)} with a lighter warm-up and a guided review loop.`
        : `Advance ${humanize(topic)} with a new challenge and an adaptive mission.`,
      recommended_game: recommendedGame,
      game_library: buildGameLibrary(studentProfile, pack, topic),
    };
  }

  function buildGameLibrary(studentProfile, pack, topic) {
    const gamePools = (pack?.game_templates?.game_pools || []).map((game, index) => ({
      ...game,
      game_name: game.game_name || `Offline ${humanize(topic)} Mission`,
      game_variant_id: game.game_variant_id || `${normalizeKey(topic)}-${index + 1}`,
      game_type: game.game_type || "adaptive",
      theme: game.theme || (pack?.game_templates?.themes_by_subject?.[studentProfile?.subject] || "exploration"),
      interaction_style: game.interaction_style || "tap",
      game_mode: game.game_mode || "guided",
      learning_objective: game.learning_objective || `Practice ${humanize(topic)} with local support.`,
      adaptation_reason: game.adaptation_reason || "Chosen by the local rules engine for offline use.",
      progression_arc: game.progression_arc || "steady",
      session_length: game.session_length || "10 min",
      reward_loop: game.reward_loop || "badge loop",
      learning_target: topic,
      slot: index + 1,
      status: "offline-ready",
      launch_label: index === 0 ? "Launch Offline Mission" : "Launch Local Variant",
      content_rules: game.content_rules || [
        "Start with a short warm-up.",
        "Practice the core concept before the final test.",
      ],
    }));
    return gamePools.length ? gamePools.slice(0, 3) : [
      {
        game_name: "Offline Quest",
        game_variant_id: "offline-quest",
        game_type: "adaptive",
        theme: "exploration",
        interaction_style: "tap",
        game_mode: "guided",
        learning_objective: `Practice ${humanize(topic)} with local support.`,
        adaptation_reason: "Fallback game for offline use.",
        progression_arc: "steady",
        session_length: "10 min",
        reward_loop: "badge loop",
        learning_target: topic,
        slot: 1,
        status: "offline-ready",
        launch_label: "Launch Offline Mission",
        content_rules: ["Start with a short warm-up.", "Practice the core concept before the final test."],
      },
    ];
  }

  function buildLocalSession({ studentProfile, prediction, game }) {
    const sessionId = `${studentProfile?.student_id || "student"}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const targetTopic = prediction?.next_recommended_topic || studentProfile?.topic || "general_knowledge";
    const lessonCards = [1, 2, 3].map((index) => ({
      id: `lesson-${index}`,
      title: `${humanize(targetTopic)} mission ${index}`,
      subtitle: `Warm-up ${index} for ${humanize(targetTopic)}.`,
      coach_line: `Stay guided and build confidence through step ${index}.`,
      focus_points: ["Review the idea", "Try the supported move", "Bank the learning badge"],
      example: `Example for ${humanize(targetTopic)}.`,
      action_label: index < 3 ? "Bank Badge And Continue" : "Unlock Final Test",
      scene_title: `Scene ${index}`,
      scene_tokens: ["Focus", "Practice", "Reward"],
      mechanic_type: index === 1 ? "choice_path" : index === 2 ? "pattern_stack" : "signal_scan",
      mechanic_prompt: `Choose the move that best supports ${humanize(targetTopic)}.`,
      mechanic_options: [
        { id: `${index}-a`, label: "Try the scaffolded choice", description: "Use the guided support path." },
        { id: `${index}-b`, label: "Try the challenge choice", description: "Take the harder route." },
      ],
      correct_option_id: `${index}-a`,
      success_message: "That route keeps the learning arc steady.",
      retry_message: "Try the guided support path to keep building confidence.",
      reward_badge: {
        id: `badge-${index}`,
        label: `Badge ${index}`,
        description: `A local badge for ${humanize(targetTopic)}.`,
      },
      timer_seconds: 45 + index * 5,
    }));
    const questions = [1, 2, 3, 4].map((index) => ({
      id: `question-${index}`,
      prompt: `Which answer best fits ${humanize(targetTopic)}?`,
      arena_title: `Final arena ${index}`,
      choices: [
        { id: `choice-${index}-a`, label: "Option A" },
        { id: `choice-${index}-b`, label: "Option B" },
      ],
      correct_choice_id: `choice-${index}-a`,
      explanation: `The guided answer is Option A for ${humanize(targetTopic)}.`,
      timer_seconds: 25,
    }));
    const badgeTrack = lessonCards.map((lesson) => ({
      id: lesson.reward_badge.id,
      label: lesson.reward_badge.label,
      description: lesson.reward_badge.description,
    }));
    return {
      session_id: sessionId,
      phase: "learn",
      lesson: lessonCards[0],
      lesson_cards: lessonCards,
      lesson_index: 0,
      lesson_history: [],
      earned_badges: [],
      question: null,
      summary: null,
      questions,
      current_index: 0,
      student_profile: studentProfile,
      prediction,
      game: {
        ...game,
        badge_track: badgeTrack,
        scene_pack: {
          world_name: game?.game_name || "Offline mission",
          mentor_title: "Guide",
          palette: studentProfile?.subject || "default",
        },
      },
      learner: {
        name: studentProfile?.name || studentProfile?.student_id || "Learner",
        grade: studentProfile?.grade || "Grade_7",
      },
      progress: {
        lessons_completed: 0,
        total_lessons: lessonCards.length,
        current_lesson: 1,
        total_rounds: questions.length,
        current_round: 0,
        max_score: questions.length * 10,
        score: 0,
      },
      play_url: `/games/${sessionId}`,
      completed: false,
      result_recorded: false,
    };
  }

  function advanceLocalSession(session, selectionId) {
    if (!session) return null;
    if (session.phase === "learn") {
      const lesson = session.lesson_cards[session.lesson_index];
      const correct = Boolean(selectionId && selectionId === lesson.correct_option_id);
      const badgeAwarded = correct ? { ...lesson.reward_badge, status: "earned" } : null;
      if (badgeAwarded) {
        session.earned_badges.push(badgeAwarded);
      }
      session.lesson_history.push({ lesson_id: lesson.id, correct, badge_id: badgeAwarded?.id || null });
      session.lesson_index += 1;
      if (session.lesson_index >= session.lesson_cards.length) {
        session.phase = "assessment";
        session.question = session.questions[0];
        session.lesson = null;
      } else {
        session.lesson = session.lesson_cards[session.lesson_index];
      }
      session.progress.lessons_completed = Math.min(session.lesson_history.length, session.lesson_cards.length);
      session.progress.current_lesson = session.phase === "learn" ? session.lesson_index + 1 : session.lesson_cards.length;
      return {
        phase: session.phase,
        lesson: session.lesson,
        question: session.question,
        summary: session.summary,
        earned_badges: session.earned_badges,
        progress: session.progress,
        badge_awarded: badgeAwarded,
        transition_note: session.phase === "assessment"
          ? "Lesson path complete. The final test is ready."
          : "Lesson complete. The next mechanic is ready.",
      };
    }
    return {
      phase: session.phase,
      lesson: session.lesson,
      question: session.question,
      summary: session.summary,
      earned_badges: session.earned_badges,
      progress: session.progress,
      badge_awarded: null,
      transition_note: "The mission is already in the assessment phase.",
    };
  }

  function submitLocalAnswer(session, choiceId) {
    if (!session || session.phase !== "assessment") {
      return { session, completed: false, correct: false, explanation: "Assessment not active." };
    }
    const question = session.question;
    const correct = Boolean(question && choiceId && choiceId === question.correct_choice_id);
    const points = correct ? 10 : 0;
    session.progress.score += points;
    session.progress.current_round += 1;
    const completed = session.progress.current_round >= session.progress.total_rounds;
    if (completed) {
      session.phase = "completed";
      session.summary = {
        game_name: session.game?.game_name || "Offline mission",
        completion_note: "Offline mission completed. The local progress summary is ready to sync.",
        score: session.progress.score,
        max_score: session.progress.max_score,
        score_percent: Math.round((session.progress.score / session.progress.max_score) * 100),
        stars: session.progress.score >= 30 ? 3 : 2,
        target_topic: session.prediction?.next_recommended_topic || session.student_profile?.topic || "general_knowledge",
        lessons_completed: session.progress.lessons_completed,
        total_lessons: session.progress.total_lessons,
        badges_earned: session.earned_badges,
        recommended_next_action: "Reconnect to sync this offline session and refresh the learner profile.",
      };
      session.question = null;
      session.lesson = null;
    } else {
      session.question = session.questions[session.progress.current_round];
    }
    return {
      session,
      completed,
      correct,
      explanation: correct ? "Correct. The next challenge is ready." : "Not quite. Review the concept and try again.",
      summary: session.summary,
      progress: session.progress,
    };
  }

  function ensureDeviceId() {
    const existing = global.localStorage?.getItem("vidya_mitra_device_id");
    if (existing) return existing;
    const next = `device-${Math.random().toString(36).slice(2, 10)}`;
    global.localStorage?.setItem("vidya_mitra_device_id", next);
    return next;
  }

  global.OfflineRuntime = {
    STORE_NAMES,
    ensureDeviceId,
    openDatabase,
    saveOfflinePack,
    loadOfflinePack,
    saveActiveSession,
    loadActiveSession,
    loadAnyActiveSession,
    deleteActiveSession,
    saveMasteryLedger,
    loadMasteryLedger,
    appendCompletedPrediction,
    appendCompletedGameSummary,
    getCompletedPredictions,
    getCompletedGameSummaries,
    addSyncQueueEvent,
    getSyncQueueEvents,
    clearSyncQueue,
    buildOfflineRecommendation,
    buildLocalSession,
    advanceLocalSession,
    submitLocalAnswer,
    humanize,
  };
})(window);
