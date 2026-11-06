// Theme cards (sign up step 2 and Settings): picking a card previews that theme on the whole page
// at once, the same way base.html applies it (data-theme on <body>). Only Next or Save keeps it.
const savedTheme = document.body.dataset.theme;
const themeInputs = document.querySelectorAll(".theme-option input[name='theme']");

// Show one theme on the page (with a short fade) and select its card
function previewTheme(name) {
  document.body.classList.add("theme-fade");
  document.body.dataset.theme = name;
  themeInputs.forEach((input) => (input.checked = input.value === name));
}

themeInputs.forEach((input) => {
  input.addEventListener("change", () => previewTheme(input.value));
  // Enter on a card picks it (instead of sending the form), like a click
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      previewTheme(input.value);
    }
  });
});

// Coming back with the browser's Back button (or a refresh that kept the old choice) shows the saved theme
window.addEventListener("pageshow", () => themeInputs.length && previewTheme(savedTheme));

// Celebrations in Settings: if the device asks for less motion and the person has not chosen a
// setting yet, show Calm as picked (confetti never moves on such a device anyway)
const celebrationsForm = document.getElementById("celebrations-form");
if (celebrationsForm && celebrationsForm.dataset.chosen === "no" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  celebrationsForm.querySelector("input[value='calm']").checked = true;
  const note = document.getElementById("confetti-note");
  if (note) note.textContent = "Your device asks for less motion, so Pair uses Calm. You can change this at any time.";
}

// Print buttons: open the browser's print window (which can also save as PDF)
document.querySelectorAll("[data-print]").forEach((button) => {
  button.onclick = () => window.print();
});

// Disable Check In's Save button after its first submit to prevent accidental double taps.
const singleSubmitForms = document.querySelectorAll("form[data-disable-repeat]");
singleSubmitForms.forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitted === "yes") {
      event.preventDefault();
      return;
    }
    form.dataset.submitted = "yes";
    form.querySelectorAll("button[type='submit']").forEach((button) => {
      button.disabled = true;
      button.textContent = "Saving…";
    });
  });
});

// Read the current activity instruction using the browser's built-in speech voice.
const readAloudButton = document.querySelector("[data-read-aloud]");
if (readAloudButton) {
  readAloudButton.addEventListener("click", () => {
    if (!("speechSynthesis" in window)) {
      document.getElementById("read-aloud-status").textContent =
        "Read Aloud is not available in this browser.";
      return;
    }
    window.speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(
      document.getElementById("activity-instruction").textContent
    );
    speech.rate = Number(document.body.dataset.speechRate) || 1;
    window.speechSynthesis.speak(speech);
  });
}

// Update optional activity timers without changing or completing the activity.
document.querySelectorAll("[data-countdown]").forEach((timer) => {
  let remaining = Number(timer.dataset.countdown) || 0;
  let previous = Date.now();
  const value = timer.querySelector("span");
  const interval = window.setInterval(() => {
    const now = Date.now();
    remaining = Math.max(0, remaining - Math.floor((now - previous) / 1000));
    previous = now;
    value.textContent = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`;
    if (remaining === 0) window.clearInterval(interval);
  }, 1000);
});
