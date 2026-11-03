// Confetti for reaching the summit: about 80 small pieces in the theme's colours fall for 3 seconds.
// Skipped when the device asks for reduced motion (the soft glow and the message still show).
(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const style = getComputedStyle(document.body);
  const colours = ["--primary", "--secondary", "--celebrate", "--alert"].map((name) => style.getPropertyValue(name).trim());
  const canvas = document.createElement("canvas");
  canvas.className = "confetti";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  // Each piece starts above the screen with its own speed, sideways drift, size and colour
  const pieces = Array.from({ length: 80 }, () => ({
    x: Math.random() * canvas.width,
    y: -20 - Math.random() * canvas.height / 2,
    speed: 2 + Math.random() * 3,
    drift: Math.random() * 2 - 1,
    size: 6 + Math.random() * 6,
    colour: colours[Math.floor(Math.random() * colours.length)],
  }));

  // Move and draw every piece each frame, then remove the canvas after 3 seconds
  const start = performance.now();
  function frame(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach((p) => {
      p.y += p.speed;
      p.x += p.drift;
      ctx.fillStyle = p.colour;
      ctx.fillRect(p.x, p.y, p.size, p.size * 0.6);
    });
    if (now - start < 3000) requestAnimationFrame(frame);
    else canvas.remove();
  }
  requestAnimationFrame(frame);
})();
