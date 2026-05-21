/**
 * screens/lobby.js — Lobby screen logic
 * Handles player list updates and host controls visibility.
 */
const Lobby = {
  setup(roomCode, isHost) {
    document.getElementById("lobby-code").textContent = roomCode;
    document.getElementById("lobby-players").innerHTML = "";
    document.getElementById("lobby-host-controls").style.display = isHost ? "block" : "none";
    document.getElementById("lobby-guest-msg").style.display     = isHost ? "none"  : "block";
    document.getElementById("lobby-topic").value = "";
  },

  onPlayerUpdate(data) {
    const list = document.getElementById("lobby-players");
    list.innerHTML = "";
    (data.players || []).forEach(name => {
      const div = document.createElement("div");
      div.className = "player-item";
      const isHost = name === data.host;
      div.innerHTML = `
        <div class="player-dot"></div>
        <span style="flex:1;">${name}</span>
        ${isHost ? '<span style="font-size:10px;letter-spacing:2px;color:var(--neon-yellow);">HOST</span>' : ""}
      `;
      list.appendChild(div);
    });
  },
};
window.Lobby = Lobby;