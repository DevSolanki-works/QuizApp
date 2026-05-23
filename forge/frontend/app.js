/**
 * app.js — Forge Frontend: Core Application Controller
 *
 * Responsibilities:
 *  1. Screen navigation (show/hide screens)
 *  2. WebSocket lifecycle (connect, reconnect, handle messages)
 *  3. Global app state
 *  4. Dispatch incoming WS messages to the correct screen handler
 *
 * WHY no framework (React/Vue)?
 *  CapacitorJS wraps plain HTML/JS perfectly. No build step = simpler
 *  deployment, faster load on mobile, easier for a solo developer to debug.
 */

// ─── Config ───────────────────────────────────────────────
// Update BACKEND_URL before deploying. Use ws:// locally, wss:// on Cloud Run.
const CONFIG = {
  BACKEND_HTTP: "http://localhost:8000",
  BACKEND_WS:   "ws://localhost:8000",
  // After deployment, these become:
  // BACKEND_HTTP: "https://your-cloud-run-url.run.app",
  // BACKEND_WS:   "wss://your-cloud-run-url.run.app",
};

// ─── Global State ─────────────────────────────────────────
const State = {
  playerName: "",
  roomCode: "",
  isHost: false,
  ws: null,
  currentScreen: "home",
};

// ─── Screen Navigation ────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  const el = document.getElementById(`screen-${name}`);
  if (el) {
    el.classList.add("active");
    State.currentScreen = name;
  }
}

// ─── Toast Notifications ──────────────────────────────────
let toastTimer = null;
function showToast(message, type = "default", duration = 3000) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.className = "";
  }, duration);
}

// ─── WebSocket Manager ────────────────────────────────────
function connectWS(roomCode, playerName) {
  const url = `${CONFIG.BACKEND_WS}/ws/${roomCode}/${encodeURIComponent(playerName)}`;
  console.log(`[WS] Connecting to ${url}`);

  const ws = new WebSocket(url);
  State.ws = ws;

  ws.onopen = () => {
    console.log("[WS] Connected");
  };

  ws.onmessage = (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      console.error("[WS] Invalid JSON:", event.data);
      return;
    }
    console.log("[WS] Received:", msg.type, msg.data);
    handleServerMessage(msg);
  };

  ws.onclose = (event) => {
    console.log("[WS] Closed:", event.code, event.reason);
    State.ws = null;
    // Only show error if we didn't intentionally leave
    if (State.currentScreen !== "home" && State.currentScreen !== "results") {
      showToast("Connection lost. Returning to menu.", "error", 4000);
      setTimeout(() => App.goHome(), 2000);
    }
  };

  ws.onerror = (err) => {
    console.error("[WS] Error:", err);
    showToast("Connection error. Check your network.", "error");
  };
}

function sendWS(payload) {
  if (State.ws && State.ws.readyState === WebSocket.OPEN) {
    State.ws.send(JSON.stringify(payload));
  } else {
    console.warn("[WS] Tried to send but socket not open:", payload);
  }
}

function disconnectWS() {
  if (State.ws) {
    State.ws.close();
    State.ws = null;
  }
}

// ─── Message Dispatcher ───────────────────────────────────
// Routes incoming server messages to the right screen handler.
function handleServerMessage(msg) {
  switch (msg.type) {
    case "PLAYER_JOINED":
    case "PLAYER_LEFT":
      Lobby.onPlayerUpdate(msg.data);
      break;

    case "GAME_STARTING":
      Game.onGameStarting(msg.data);
      break;

    case "QUESTION":
      Game.onQuestion(msg.data);
      break;

    case "LEADERBOARD":
      Game.onLeaderboard(msg.data);
      break;

    case "GAME_OVER":
      Results.onGameOver(msg.data);
      break;

    case "ERROR":
      showToast(`ERROR: ${msg.data.message}`, "error", 5000);
      break;

    default:
      console.warn("[WS] Unknown message type:", msg.type);
  }
}

// ─── App Controller (called from HTML onclick) ────────────
const App = {

  async createRoom() {
    const name = document.getElementById("home-name").value.trim();
    if (!name) {
      showToast("Enter your callsign first.", "error");
      return;
    }

    try {
      const res = await fetch(`${CONFIG.BACKEND_HTTP}/rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ host_name: name }),
      });

      if (!res.ok) {
        const err = await res.json();
        showToast(err.detail || "Failed to create room.", "error");
        return;
      }

      const data = await res.json();
      State.playerName = name;
      State.roomCode   = data.room_code;
      State.isHost     = true;

      connectWS(State.roomCode, State.playerName);
      Lobby.setup(State.roomCode, State.isHost);
      showScreen("lobby");

    } catch (err) {
      console.error(err);
      showToast("Cannot reach server. Is the backend running?", "error");
    }
  },

  joinRoom() {
    const name = document.getElementById("home-name").value.trim();
    const code = document.getElementById("home-code").value.trim().toUpperCase();

    if (!name) { showToast("Enter your callsign first.", "error"); return; }
    if (code.length !== 4) { showToast("Room code must be 4 characters.", "error"); return; }

    State.playerName = name;
    State.roomCode   = code;
    State.isHost     = false;

    connectWS(State.roomCode, State.playerName);
    Lobby.setup(State.roomCode, State.isHost);
    showScreen("lobby");
  },

  startGame() {
    const topic = document.getElementById("lobby-topic").value.trim();
    if (!topic) { showToast("Enter a quiz topic.", "error"); return; }
    sendWS({ action: "start_game", topic });
  },

  leaveRoom() {
    disconnectWS();
    App.goHome();
  },

  goHome() {
    disconnectWS();
    State.playerName = "";
    State.roomCode   = "";
    State.isHost     = false;
    document.getElementById("home-name").value = "";
    document.getElementById("home-code").value = "";
    showScreen("home");
  },

  playAgain() {
    // Go back to lobby (same room, host can start a new topic)
    Lobby.setup(State.roomCode, State.isHost);
    showScreen("lobby");
  },
};

// Expose globals
window.App      = App;
window.State    = State;
window.sendWS   = sendWS;
window.showToast = showToast;
window.showScreen = showScreen;