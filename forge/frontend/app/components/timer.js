/**
 * components/timer.js — Reusable countdown timer utility
 * Used by game.js internally; exposed globally for potential reuse.
 */
const Timer = {
  create(durationSeconds, onTick, onDone) {
    let remaining = durationSeconds;
    const id = setInterval(() => {
      remaining -= 0.1;
      onTick(Math.max(0, remaining), durationSeconds);
      if (remaining <= 0) {
        clearInterval(id);
        onDone();
      }
    }, 100);
    return id; // caller stores this to cancel if needed
  },
  cancel(id) {
    if (id) clearInterval(id);
  },
};
window.Timer = Timer;