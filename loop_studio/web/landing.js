'use strict';
const hero = document.getElementById('hero-ascii');
const lab = document.getElementById('lab-ascii');
const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
const state = {heroPaused: motionPreference.matches, labPaused: motionPreference.matches, heroTime: 0, labTime: 0, shape: 'orbit'};
const chars = ' .,:;+=*#%@';
// Project a rotating ribbon into a character grid with a depth buffer.
function art(cols, rows, time, kind) {
  const pixels = new Float32Array(cols * rows);
  const depth = new Float32Array(cols * rows).fill(-Infinity);
  const angle = time * .44, ca = Math.cos(angle), sa = Math.sin(angle);
  if (kind === 'wave') {
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
      const u = (x / cols - .5) * 7, v = (y / rows - .5) * 3;
      for (let n = 0; n < 3; n++) {
        const wave = Math.sin(u * 1.6 + time + n * .7) * .4 + (n - 1) * .3;
        pixels[y * cols + x] += Math.exp(-Math.pow((v - wave) * 13, 2)) * (.5 + .35 * Math.cos(u * 3 - time + n));
      }
    }
  } else {
    for (let a = 0; a < Math.PI * 2; a += .018) for (let b = -.25; b <= .25; b += .025) {
      const twist = kind === 'ribbon' ? a * 1.5 + time * .45 : a * .5;
      const radius = 1 + b * Math.cos(twist);
      const x = radius * Math.cos(a), y = radius * Math.sin(a), z = b * Math.sin(twist);
      const xx = x * ca + z * sa, zz = -x * sa + z * ca;
      const tilt = .55 + Math.sin(time * .35) * .35;
      const yy = y * Math.cos(tilt) - zz * Math.sin(tilt), d = y * Math.sin(tilt) + zz * Math.cos(tilt);
      const perspective = 2.9 / (3.5 - d);
      const px = Math.round(cols / 2 + xx * perspective * cols * .34);
      const py = Math.round(rows / 2 + yy * perspective * rows * .38);
      const index = py * cols + px;
      if (px >= 0 && px < cols && py >= 0 && py < rows && d > depth[index]) {
        depth[index] = d;
        pixels[index] = .28 + .65 * (d + 1.4) / 2.8 + .12 * Math.sin(a * 9 - time * 2);
      }
    }
  }
  return Array.from({length: rows}, (_, y) => Array.from({length: cols}, (_, x) => chars[Math.min(chars.length - 1, Math.max(0, Math.floor(pixels[y * cols + x] * (chars.length - 1))))]).join('')).join('\n');
}
function drawHero() { hero.textContent = art(120, 38, state.heroTime, 'ribbon'); }
function drawLab() { lab.textContent = art(Number(document.getElementById('density').value), 38, state.labTime, state.shape); }
function labels() {
  const heroButton = document.getElementById('pause-hero'), labButton = document.getElementById('pause-art');
  heroButton.textContent = state.heroPaused ? 'Play artwork ↗' : 'Pause artwork Ⅱ';
  labButton.textContent = state.labPaused ? 'Resume motion' : 'Pause motion';
  heroButton.setAttribute('aria-pressed', String(state.heroPaused));
  labButton.setAttribute('aria-pressed', String(state.labPaused));
  document.querySelector('.hero').classList.toggle('motion-paused', state.heroPaused);
  document.querySelector('.hero').classList.toggle('motion-enabled', !state.heroPaused);
}
document.getElementById('pause-hero').onclick = () => { state.heroPaused = !state.heroPaused; labels(); };
document.getElementById('pause-art').onclick = () => { state.labPaused = !state.labPaused; labels(); };
motionPreference.addEventListener('change', event => { state.heroPaused = state.labPaused = event.matches; labels(); });
document.querySelectorAll('[data-shape]').forEach(button => {
  button.setAttribute('aria-pressed', String(button.dataset.shape === state.shape));
  button.onclick = () => {
    state.shape = button.dataset.shape;
    document.querySelectorAll('[data-shape]').forEach(other => {
      other.classList.toggle('active', other === button);
      other.setAttribute('aria-pressed', String(other === button));
    });
    drawLab();
  };
});
document.getElementById('density').oninput = drawLab;
document.getElementById('download-ascii').onclick = () => {
  const url = URL.createObjectURL(new Blob([lab.textContent], {type: 'text/plain'}));
  const link = document.createElement('a'); link.href = url; link.download = 'loop-ascii-frame.txt'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
let lastFrame = 0;
function animate(now) {
  if (now - lastFrame >= 1000 / 24) {
    const delta = Math.min((now - lastFrame) / 1000, .1); lastFrame = now;
    if (!document.hidden) {
      if (!state.heroPaused) { state.heroTime += delta; drawHero(); }
      if (!state.labPaused) { state.labTime += delta * Number(document.getElementById('speed').value) / 100; drawLab(); }
    }
  }
  requestAnimationFrame(animate);
}
labels(); drawHero(); drawLab(); requestAnimationFrame(animate);
