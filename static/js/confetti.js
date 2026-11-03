// Confetti in the theme's colours. Two sizes, set on the script tag with data-size:
// "full" (the summit) = 80 pieces falling from above for 3 seconds,
// "small" (a new flag) = 30 pieces already on screen for about 1 second.
// Silent (no sound). Skipped when the device asks for reduced motion, so Big then works like Calm
// (the soft glow and the message still show).
(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const small = document.currentScript.dataset.size === "small";
  const style = getComputedStyle(document.body);
  const colours = ["--primary", "--secondary", "--celebrate", "--alert"].map((name) => style.getPropertyValue(name).trim());
  const canvas = document.createElement("canvas");
  canvas.className = "confetti";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  // Each piece gets its own start (above the screen, or on it for a small burst), speed, drift, size and colour
  const pieces = Array.from({ length: small ? 30 : 80 }, () => ({
    x: Math.random() * canvas.width,
    y: small ? Math.random() * canvas.height * 0.4 : -20 - Math.random() * canvas.height / 2,
    speed: (small ? 4 : 2) + Math.random() * 3,
    drift: Math.random() * 2 - 1,
    size: 6 + Math.random() * 6,
    colour: colours[Math.floor(Math.random() * colours.length)],
  }));

  // Move and draw every piece each frame, then remove the canvas (after 1 or 3 seconds)
  const start = performance.now();
  function frame(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach((p) => {
      p.y += p.speed;
      p.x += p.drift;
      ctx.fillStyle = p.colour;
      ctx.fillRect(p.x, p.y, p.size, p.size * 0.6);
    });
    if (now - start < (small ? 1000 : 3000)) requestAnimationFrame(frame);
    else canvas.remove();
  }
  requestAnimationFrame(frame);
})();
