// Print buttons: open the browser's print window (which can also save as PDF)
document.querySelectorAll("[data-print]").forEach((button) => {
  button.onclick = () => window.print();
});
