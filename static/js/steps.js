// Task steps page: move through steps one at a time with Done, Back and I need a break

const steps = document.querySelectorAll(".step-text");
const backButton = document.getElementById("back");
const views = {
  steps: document.getElementById("steps-view"),
  break: document.getElementById("break-view"),
  finish: document.getElementById("finish-view"),
};
let current = 0;

// Show only the current step, and update the counter, progress bar and Back button
function showStep() {
  steps.forEach((step, i) => (step.hidden = i !== current));
  document.getElementById("step-count").textContent = `Step ${current + 1} of ${steps.length}`;
  document.getElementById("progress-fill").style.width = `${((current + 1) / steps.length) * 100}%`;
  backButton.disabled = current === 0;
}

// Show one panel (steps, break or finish), hide the others, and move focus to it
function showView(name) {
  for (const key in views) views[key].hidden = key !== name;
  views[name].focus();
}

// Done: go to the next step. After the last one, a routine sends its finish form (to mark the
// weekly goal); anything else shows the finish message.
document.getElementById("done").onclick = () => {
  const finishForm = document.getElementById("finish-form");
  if (current < steps.length - 1) {
    current++;
    showStep();
  } else if (finishForm) {
    finishForm.submit();
  } else {
    showView("finish");
  }
};

// Back: go to the previous step
backButton.onclick = () => {
  current--;
  showStep();
};

// I need a break: show the break panel; Back to my step returns to the same step
document.getElementById("break").onclick = () => showView("break");
document.getElementById("resume").onclick = () => showView("steps");

showStep();
