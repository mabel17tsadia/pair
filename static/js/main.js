// Print buttons: open the browser's print window (which can also save as PDF)
document.querySelectorAll("[data-print]").forEach((button) => {
  button.onclick = () => window.print();
});

// Copy buttons: copy the text box named in data-copy, then say "Copied"
document.querySelectorAll("[data-copy]").forEach((button) => {
  button.onclick = () => {
    const text = document.getElementById(button.dataset.copy).value;
    navigator.clipboard.writeText(text)
      .then(() => (button.textContent = "Copied"))
      .catch(() => (button.textContent = "Select the text to copy it"));
  };
});
