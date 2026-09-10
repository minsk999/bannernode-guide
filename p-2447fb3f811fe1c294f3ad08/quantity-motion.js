(() => {
  'use strict';

  const range = document.querySelector('#banner-quantity');
  const button = document.querySelector('#quantity-auto');
  const container = document.querySelector('.node-reason');
  if (!range || !button || !container) return;

  const MIN = 1;
  const MAX = Number(range.max);
  const LEG = 8000;
  const HOLD = 800;
  const CYCLE = 2 * (LEG + HOLD);
  const GRACE = 4000;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const adjustmentKeys = new Set([
    'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
    'Home', 'End', 'PageUp', 'PageDown'
  ]);
  const pointers = new Set();
  const keys = new Set();
  let paused = reduced.matches;
  let intersecting = false;
  let keyboardFocus = false;
  let graceUntil = 0;
  let graceTimer = null;
  let frame = null;
  let previousTime = null;
  let phase = 0;

  function manuallyBlocked() {
    return pointers.size > 0 || keys.size > 0 || keyboardFocus || performance.now() < graceUntil;
  }

  function canRun() {
    return !paused && !manuallyBlocked() && intersecting && !document.hidden;
  }

  function updateButton() {
    // Offscreen/hidden suspension does not change the user's playback intent.
    BNDemoControls.play(button, paused || manuallyBlocked(), phase > 0);
    button.setAttribute('aria-label', '수량 자동 재생 · ' + button.dataset.controlLabel);
  }

  function stopFrame() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    previousTime = null;
  }

  function reconcile() {
    updateButton();
    if (!canRun()) stopFrame();
    else if (frame === null) frame = requestAnimationFrame(tick);
  }

  function syncPhase() {
    const value = Math.max(MIN, Math.min(MAX, Number(range.value)));
    const progress = Math.acos(1 - 2 * (value - MIN) / (MAX - MIN)) / Math.PI;
    const descending = phase >= LEG + HOLD && phase < 2 * LEG + HOLD;
    // Invert easeInOutSine so resuming never jumps back to an old value.
    if (value === MAX) phase = LEG;
    else if (value === MIN) phase = 2 * LEG + HOLD;
    else phase = descending ? LEG + HOLD + (1 - progress) * LEG : progress * LEG;
  }

  function tick(now) {
    frame = null;
    if (!canRun()) {
      previousTime = null;
      updateButton();
      return;
    }
    if (previousTime !== null) phase = (phase + Math.max(0, now - previousTime)) % CYCLE;
    previousTime = now;

    let progress;
    if (phase < LEG) progress = (1 - Math.cos(Math.PI * phase / LEG)) / 2;
    else if (phase < LEG + HOLD) progress = 1;
    else if (phase < 2 * LEG + HOLD) {
      progress = (1 + Math.cos(Math.PI * (phase - LEG - HOLD) / LEG)) / 2;
    } else progress = 0;

    const value = Math.round(MIN + (MAX - MIN) * progress);
    if (Number(range.value) !== value) {
      range.value = String(value);
      const event = new Event('input', { bubbles: true });
      event.quantityAuto = true;
      range.dispatchEvent(event);
    }
    // Input listeners may synchronously suspend playback.
    if (canRun() && frame === null) frame = requestAnimationFrame(tick);
  }

  function clearGrace() {
    if (graceTimer !== null) clearTimeout(graceTimer);
    graceTimer = null;
    graceUntil = 0;
  }

  function giveGrace() {
    clearGrace();
    graceUntil = performance.now() + GRACE;
    function finishGrace() {
      const remaining = graceUntil - performance.now();
      if (remaining > 0) {
        graceTimer = setTimeout(finishGrace, remaining);
        return;
      }
      graceTimer = null;
      reconcile();
    }
    graceTimer = setTimeout(finishGrace, GRACE);
    reconcile();
  }

  range.addEventListener('input', event => {
    if (event.quantityAuto === true) return;
    syncPhase();
    giveGrace();
  });

  range.addEventListener('pointerdown', event => {
    pointers.add(event.pointerId);
    keyboardFocus = false;
    clearGrace();
    reconcile();
  });

  function releasePointer(event) {
    if (!pointers.delete(event.pointerId)) return;
    syncPhase();
    giveGrace();
  }
  window.addEventListener('pointerup', releasePointer, true);
  window.addEventListener('pointercancel', releasePointer, true);
  range.addEventListener('lostpointercapture', releasePointer);

  range.addEventListener('keydown', event => {
    if (!adjustmentKeys.has(event.key)) return;
    keys.add(event.key);
    keyboardFocus = true;
    clearGrace();
    reconcile();
  });
  range.addEventListener('focus', () => {
    if (pointers.size > 0) return;
    keyboardFocus = true;
    reconcile();
  });
  window.addEventListener('keyup', event => {
    if (!keys.delete(event.key)) return;
    syncPhase();
    giveGrace();
  }, true);
  range.addEventListener('blur', () => {
    if (!keyboardFocus && keys.size === 0) return;
    keyboardFocus = false;
    keys.clear();
    giveGrace();
  });

  button.addEventListener('click', () => {
    if (paused || manuallyBlocked()) {
      paused = false;
      keyboardFocus = false;
      keys.clear();
      clearGrace();
    } else paused = true;
    reconcile();
  });

  function releaseInteractions() {
    // Releases can be lost when the tab/window is switched during a drag/key press.
    if (pointers.size === 0 && keys.size === 0) return;
    pointers.clear();
    keys.clear();
    giveGrace();
  }
  window.addEventListener('blur', releaseInteractions);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) releaseInteractions();
    reconcile();
  });
  reduced.addEventListener('change', () => {
    if (reduced.matches) paused = true;
    reconcile();
  });

  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.target === container) intersecting = entry.isIntersecting;
    }
    reconcile();
  }, { threshold: 0 });

  syncPhase();
  observer.observe(container);
  reconcile();
})();
