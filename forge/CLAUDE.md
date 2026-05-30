# CLAUDE.md — Forge: AI Trivia Showdown
> Paste this file at the start of every new conversation so Claude has full context.
> Claude updates this file after every major milestone and provides the new version.

---

## 🧠 Who I Am
You are an expert full-stack web developer and game designer. You build high-quality, high-performance web applications and games. You are currently working on **Forge**, a real-time AI-powered trivia game.

## 🛠 Tech Stack
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+).
- **Backend**: Python 3.11+, FastAPI, WebSockets (`websockets` library).
- **AI**: Google Gemini Pro (via API).
- **Architecture**: Single Page Application (SPA) with custom router, real-time WebSocket state sync.

## 🎮 Core Game Mechanics
- **Lobby**: Host creates room, shared room code, real-time player list.
- **Modes**:
  - **Classic**: Solo or group, host picks one topic, everyone plays individually.
  - **Team Battle**: Players join Team A or Team B. Both teams suggest a topic; the randomizer picks one. Scores are aggregated by team.
- **Game Flow**: Question reveal -> Timer countdown -> All answer -> Speed-based scoring -> Leaderboard update -> Next question.
- **Scoring**: Base 500-1000 pts (speed) + Streak Multipliers (up to 3x).

---

## 🚀 Recent Feature Updates (Milestone 21-22)

### 1. Room Locking System
- **Mandatory Finalization**: The Host must now click **"LOCK ROOM"** before the **Team Mode** toggle becomes available.
- **Join Prevention**: Once locked, no new players can enter the room, ensuring a stable player list for team configuration.
- **Toggleable**: The host can unlock the room at any time. Unlocking while in Team Mode automatically reverts the room to **Classic Mode** for safety.

### 2. Team Host System
- **Team Leadership**: The first person to join **Team A** becomes the **Host of Team A**. Same for **Team B**.
- **Topic Restrictions**: Only the Team Host can write or edit the topic suggestion for their team. Other members see a waiting message.
- **Main Host Enjection**: The Room Creator (Main Host) is now required to join a team before the Team Mode game can be started.

### 3. Team Swapping
- **Flexibility**: Regular players (non-Team Hosts) can now use the **"SWAP TEAM"** button to switch sides if they joined the wrong team by mistake.
- **Stability**: Team Hosts cannot swap teams; they must remain to lead their team's topic selection.

### 4. Input Stability (The "Typing Fix")
- **Focus Preservation**: The lobby UI now preserves input focus and cursor position during real-time re-renders.
- **Debounced Updates**: Team names and topics are updated via WebSockets with a 400ms debounce to prevent network congestion and UI stutter.

---

## 📋 Technical Guidelines
- **Real-time Sync**: Use `PLAYER_JOINED` broadcasts to sync all lobby state (Mode, Teams, Locking).
- **Frontend State**: Initialize `lobby.html` state from global `State` to ensure instant UI sync for late-joiners.
- **Clean Transitions**: Always ensure `_applyModeUI()` is called when mode or lock status changes.
- **Security**: Prevent non-hosts from sending privileged actions (`lock_room`, `set_lobby_mode`).

## ✅ Compliance Checklist
- [x] Room Locking for Team Mode stability.
- [x] Team Host role for topic selection.
- [x] Team Swapping for regular players.
- [x] Input focus preservation & debouncing.
- [x] Late-join synchronization logic.
- [x] Privacy/Policy links and mobile responsive UI.
