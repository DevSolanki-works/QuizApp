/**
 * screens/home.js — Home screen helpers
 *
 * Most home screen logic lives in App.createRoom() / App.joinRoom() in app.js.
 * This file handles UX polish: Enter key support, input formatting, etc.
 */

(function () {
  // Allow pressing Enter on the room code input to trigger join
  document.addEventListener("DOMContentLoaded", () => {
    const codeInput = document.getElementById("home-code");
    const nameInput = document.getElementById("home-name");

    // Auto-uppercase the room code as user types
    codeInput.addEventListener("input", () => {
      const pos = codeInput.selectionStart;
      codeInput.value = codeInput.value.toUpperCase();
      codeInput.setSelectionRange(pos, pos);
    });

    // Enter on code input → join room
    codeInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") App.joinRoom();
    });

    // Enter on name input → focus code input (if filled) or create room
    nameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (codeInput.value.trim().length === 4) {
          App.joinRoom();
        } else {
          App.createRoom();
        }
      }
    });
  });
})();