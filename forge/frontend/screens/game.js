/**
 * screens/game.js — Active game screen logic
 *
 * Handles:
 *  - Displaying incoming QUESTION messages
 *  - Running the countdown timer
 *  - Sending player's answer via WebSocket
 *  - Showing correct/incorrect reveal after LEADERBOARD message
 */
const Game = {
  _timer: null,           // setInterval reference
  _timeLeft: 15,          // seconds remaining
  _selectedChoice: null,  // index player tapped
  _timeStarted: null,     // Date.ms when question was shown

  onGameStarting(data) {
    document.getElementById("loading-topic").textContent =
      `TOPIC: ${data.topic.toUpperCase()}`;
    showScreen("loading");
  },

  onQuestion(data) {
    // Clear any previous timer
    Game._stopTimer();
    Game._selectedChoice = null;
    Game._timeStarted = Date.now();

    // Update question counter
    document.getElementById("game-q-counter").textContent =
      `Q ${data.index + 1}/${data.total}`;

    // Set question text
    document.getElementById("game-question").textContent = data.text;

    // Render answer buttons
    const optContainer = document.getElementById("game-options");
    optContainer.innerHTML = "";
    const labels = ["A", "B", "C", "D"];
    data.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.className = "answer-btn";
      btn.id = `opt-${i}`;
      btn.innerHTML = `<span style="color:var(--neon-cyan);margin-right:10px;">${labels[i]}.</span>${opt}`;
      btn.onclick = () => Game._onAnswer(i, data.time_limit_ms);
      optContainer.appendChild(btn);
    });

    // Show game screen and start timer
    showScreen("game");
    Game._startTimer(data.time_limit_ms / 1000);
  },

  onLeaderboard(data) {
    // Stop timer first
    Game._stopTimer();

    // Reveal correct/incorrect on buttons
    const labels = ["A", "B", "C", "D"];
    const optContainer = document.getElementById("game-options");
    const btns = optContainer.querySelectorAll(".answer-btn");

    btns.forEach((btn, i) => {
      btn.disabled = true;
      if (i === data.correct_index) {
        btn.classList.add("correct");
      } else if (i === Game._selectedChoice && i !== data.correct_index) {
        btn.classList.add("incorrect");
      }
    });

    // Update score bar with new scores
    Leaderboard.updateBar(data.scores, State.playerName);

    // The server will send the next QUESTION after 3 seconds — we just wait.
  },

  _onAnswer(choiceIndex, timeLimitMs) {
    if (Game._selectedChoice !== null) return; // Already answered
    Game._selectedChoice = choiceIndex;

    const elapsed = Date.now() - Game._timeStarted;

    // Visual feedback — mark button as selected immediately
    document.querySelectorAll(".answer-btn").forEach(b => b.disabled = true);
    document.getElementById(`opt-${choiceIndex}`).classList.add("selected");

    // Send to server
    sendWS({
      action: "answer",
      choice: choiceIndex,
      time_ms: Math.min(elapsed, timeLimitMs),
    });
  },

  _startTimer(seconds) {
    let remaining = seconds;
    const bar = document.getElementById("game-timer-bar");
    const num = document.getElementById("game-timer-num");

    const tick = () => {
      remaining -= 0.1;
      const pct = Math.max(0, (remaining / seconds) * 100);
      bar.style.width = `${pct}%`;

      // Color shift: green → cyan → red as time runs out
      if (pct > 50)      bar.style.background = "var(--neon-green)";
      else if (pct > 25) bar.style.background = "var(--neon-cyan)";
      else               bar.style.background = "var(--neon-red)";

      num.textContent = `${Math.ceil(remaining)}s`;

      if (remaining <= 0) {
        Game._stopTimer();
        // Auto-submit if player hasn't answered (sends invalid but server handles it)
        if (Game._selectedChoice === null) {
          Game._selectedChoice = -1; // Sentinel: timed out
          document.querySelectorAll(".answer-btn").forEach(b => b.disabled = true);
          showToast("Time's up!", "error", 1500);
          sendWS({ action: "answer", choice: -1, time_ms: seconds * 1000 });
        }
      }
    };

    Game._timer = setInterval(tick, 100); // 100ms for smooth bar animation
  },

  _stopTimer() {
    if (Game._timer) {
      clearInterval(Game._timer);
      Game._timer = null;
    }
  },
};
window.Game = Game;