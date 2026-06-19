/**
 * components/leaderboard.js — Live score bar during the game
 * Shows compact score chips at the top of the game screen.
 */
const Leaderboard = {
  updateBar(scores, myName) {
    const bar = document.getElementById("game-scores-bar");
    bar.innerHTML = "";

    const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a);
    sorted.forEach(([name, score]) => {
      const chip = document.createElement("div");
      chip.className = "score-chip";
      const isMe = name === myName;
      if (isMe) chip.style.borderColor = "var(--neon-cyan)";
      chip.textContent = `${name}: ${score}`;
      bar.appendChild(chip);
    });
  },
};
window.Leaderboard = Leaderboard;