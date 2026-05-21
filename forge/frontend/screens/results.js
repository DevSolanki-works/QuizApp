/**
 * screens/results.js — Final results screen
 */
const Results = {
  onGameOver(data) {
    const list = document.getElementById("results-list");
    list.innerHTML = "";

    // Sort players by score descending
    const sorted = Object.entries(data.final_scores)
      .sort(([, a], [, b]) => b - a);

    const medals = ["🥇", "🥈", "🥉"];
    const rankClasses = ["rank-1", "rank-2", "rank-3"];

    sorted.forEach(([name, score], i) => {
      const isMe = name === State.playerName;
      const row = document.createElement("div");
      row.className = `lb-row ${rankClasses[i] || ""}`;
      row.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="font-size:22px;width:28px;">${medals[i] || `${i+1}.`}</span>
          <span style="font-size:14px;${isMe ? "color:var(--neon-cyan);" : ""}">${name}${isMe ? " ◀" : ""}</span>
        </div>
        <span class="score-chip">${score.toLocaleString()} pts</span>
      `;
      list.appendChild(row);
    });

    showScreen("results");
  },
};
window.Results = Results;