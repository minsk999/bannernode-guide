/* Builder must load demo-controls.js first. No sources are attached until nearby. */
(() => {
  function init() {
    const root = document.getElementById('study');
    const controls = window.BNDemoControls;
    if (!root || !controls || root.dataset.studyVideosReady) return;
    root.dataset.studyVideosReady = 'true';

    const details = root.closest('details');
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const visibleRatio = .65;
    let expanded = null, dialog = null, pageActive = true;
    const players = Array.from(root.querySelectorAll('[data-study-player]'), figure => ({
      figure, home: figure.parentElement, stage: figure.querySelector('.study-video-stage'),
      video: figure.querySelector('video'), toggle: figure.querySelector('[data-study-toggle]'),
      replay: figure.querySelector('[data-study-replay]'), expand: figure.querySelector('[data-study-expand]'),
      status: figure.querySelector('.study-video-status'), message: figure.querySelector('.study-video-message'),
      progress: figure.querySelector('.study-video-progress'),
      title: figure.closest('article').querySelector('.study-card-title > span').textContent,
      // User intent survives viewport, tab, details and dialog transitions.
      intent: 'auto', near: false, visible: false, loaded: false, started: false,
      pending: false, buffering: false, failed: false, blocked: false, restart: false, request: 0
    }));
    if (!players.length) return;

    const sectionOpen = () => !details || details.open;
    const available = state => pageActive && !document.hidden && sectionOpen() && (!expanded || expanded === state);
    const shouldPlay = state => available(state) && (expanded === state || state.visible) &&
      !state.failed && state.intent !== 'paused' &&
      (state.intent === 'play' || (!reduced.matches && !state.blocked));

    function render(state) {
      const running = !state.failed && (state.pending || !state.video.paused);
      controls.play(state.toggle, !running, state.started);
      let text, mode;
      if (state.failed) { mode = 'error'; text = '영상을 다시 불러와 주세요'; }
      else if (running && (state.pending || state.buffering)) { mode = 'loading'; text = '불러오는 중'; }
      else if (running) { mode = 'playing'; text = '반복 재생 중'; }
      else if (state.intent === 'paused') { mode = 'paused'; text = '일시정지'; }
      else if (reduced.matches || state.blocked) { mode = 'ready'; text = '눌러서 재생'; }
      else { mode = 'ready'; text = '화면에 보이면 재생'; }
      state.figure.dataset.playback = mode;
      state.status.textContent = '무음 · ' + text;
      state.message.hidden = !state.failed;
      if (state.failed) state.message.textContent = '영상을 불러오지 못했습니다. 재생을 눌러 다시 시도해 주세요.';
      const duration = state.video.duration || Number(state.figure.dataset.duration);
      const progress = Number.isFinite(duration) && duration > 0 ? state.video.currentTime / duration : 0;
      state.progress.style.setProperty('--study-progress', String(Math.min(1, Math.max(0, progress))));
    }

    function pause(state) {
      if (state.pending || !state.video.paused) {
        state.request++;
        state.pending = false;
        state.video.pause();
      }
      state.buffering = false;
    }

    function load(state, retry = false) {
      if (state.loaded && !retry) return;
      state.loaded = true;
      state.video.preload = 'metadata';
      state.video.src = state.video.dataset.src;
      state.video.load();
    }

    function failed(state) {
      state.failed = true;
      pause(state);
      render(state);
    }

    function sync(state) {
      if (available(state) && (state.near || expanded === state)) load(state);
      if (!shouldPlay(state)) {
        pause(state);
        render(state);
        return;
      }
      load(state);
      if (!state.video.paused || state.pending) { render(state); return; }
      state.video.preload = 'auto';
      state.video.muted = true;
      state.pending = true;
      const request = ++state.request;
      Promise.resolve(state.video.play()).then(() => {
        if (request !== state.request) {
          if (!shouldPlay(state)) pause(state);
          return;
        }
        state.pending = false;
        if (!shouldPlay(state)) pause(state);
        render(state);
      }).catch(error => {
        if (request !== state.request) return;
        state.pending = false;
        if (error.name === 'NotAllowedError') {
          state.blocked = true;
          state.intent = 'paused';
          pause(state);
          render(state);
        } else if (error.name !== 'AbortError') failed(state);
        else render(state);
      });
      render(state);
    }

    function syncAll() { players.forEach(sync); }

    // Refresh immediately after DOM moves/open changes; IO may still describe the old position.
    function measure() {
      players.forEach(state => {
        const rect = state.stage.getBoundingClientRect();
        const width = Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0));
        const height = Math.max(0, Math.min(rect.bottom, innerHeight - 75) - Math.max(rect.top, 80));
        state.visible = rect.width > 0 && rect.height > 0 && width * height / (rect.width * rect.height) >= visibleRatio;
        state.near = rect.width > 0 && rect.height > 0 && rect.bottom > -360 && rect.top < innerHeight + 360;
      });
    }

    function manualPlay(state, restart = false) {
      const retry = state.failed || Boolean(state.video.error);
      pause(state);
      state.intent = 'play';
      state.failed = false;
      state.blocked = false;
      state.restart = restart;
      load(state, retry);
      if (restart && state.video.readyState >= 1) {
        state.video.currentTime = 0;
        state.restart = false;
      }
      measure();
      sync(state);
    }

    function restoreDialog() {
      if (!expanded) return;
      const state = expanded;
      expanded = null;
      state.home.append(state.figure);
      state.home.style.removeProperty('min-height');
      document.documentElement.classList.remove('study-video-modal-open');
      measure();
      syncAll();
      const focusTarget = sectionOpen() ? state.expand : details.querySelector('summary');
      focusTarget?.focus({preventScroll: true});
    }

    function closeDialog() {
      if (dialog?.open) dialog.close();
      restoreDialog();
    }

    function openDialog(state) {
      if (expanded) closeDialog();
      if (!dialog) {
        dialog = document.createElement('dialog');
        dialog.className = 'study-video-dialog';
        dialog.id = 'study-video-dialog';
        dialog.setAttribute('aria-labelledby', 'study-video-dialog-title');
        dialog.innerHTML = '<div class="study-video-dialog-heading"><p class="study-video-dialog-title" id="study-video-dialog-title"></p><button class="study-video-close" type="button" aria-label="크게 보기 닫기" autofocus><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div><div class="study-video-dialog-slot"></div>';
        document.body.append(dialog);
        dialog.querySelector('.study-video-close').addEventListener('click', closeDialog);
        dialog.addEventListener('close', () => { if (!dialog.open) restoreDialog(); });
        dialog.addEventListener('cancel', event => { event.preventDefault(); closeDialog(); });
        let backdropDown = false;
        const outside = event => {
          const rect = dialog.getBoundingClientRect();
          return event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
        };
        dialog.addEventListener('pointerdown', event => { backdropDown = event.target === dialog && outside(event); });
        dialog.addEventListener('click', event => {
          if (backdropDown && event.target === dialog && outside(event)) closeDialog();
          backdropDown = false;
        });
      }
      state.home.style.minHeight = state.figure.getBoundingClientRect().height + 'px';
      expanded = state;
      dialog.querySelector('.study-video-dialog-title').textContent = state.title + ' · 실제 작업 화면';
      // Move the same player, preserving currentTime, decoded media and manual pause intent.
      dialog.querySelector('.study-video-dialog-slot').append(state.figure);
      document.documentElement.classList.add('study-video-modal-open');
      dialog.showModal();
      syncAll();
    }

    players.forEach(state => {
      state.video.muted = true;
      state.video.defaultMuted = true;
      controls.label(state.replay, '처음부터', 'replay');
      controls.label(state.expand, '크게 보기', 'expand');
      state.toggle.disabled = false;
      state.replay.disabled = false;
      state.expand.disabled = typeof HTMLDialogElement === 'undefined' || !HTMLDialogElement.prototype.showModal;
      state.expand.setAttribute('aria-controls', 'study-video-dialog');
      state.toggle.addEventListener('click', () => {
        if (state.pending || !state.video.paused) {
          state.intent = 'paused';
          pause(state);
          render(state);
        } else manualPlay(state);
      });
      state.replay.addEventListener('click', () => manualPlay(state, true));
      state.expand.addEventListener('click', () => openDialog(state));
      state.video.addEventListener('loadedmetadata', () => {
        if (state.restart) { state.video.currentTime = 0; state.restart = false; }
        render(state);
      });
      state.video.addEventListener('playing', () => {
        if (!shouldPlay(state)) { pause(state); render(state); return; }
        state.started = true;
        state.pending = false;
        state.buffering = false;
        state.figure.dataset.hasFrame = 'true';
        render(state);
      });
      state.video.addEventListener('waiting', () => { state.buffering = shouldPlay(state); render(state); });
      state.video.addEventListener('pause', () => render(state));
      state.video.addEventListener('timeupdate', () => render(state));
      state.video.addEventListener('error', () => failed(state));
      render(state);
    });

    if ('IntersectionObserver' in window) {
      const byStage = new Map(players.map(state => [state.stage, state]));
      const near = new IntersectionObserver(entries => {
        entries.forEach(entry => { const state = byStage.get(entry.target); state.near = entry.isIntersecting; sync(state); });
      }, {rootMargin: '360px 0px', threshold: 0});
      const visible = new IntersectionObserver(entries => {
        entries.forEach(entry => { const state = byStage.get(entry.target); state.visible = entry.intersectionRatio >= visibleRatio; sync(state); });
      }, {rootMargin: '-80px 0px -75px', threshold: [0, visibleRatio, 1]});
      players.forEach(state => { near.observe(state.stage); visible.observe(state.stage); });
    } else {
      let scheduled = false;
      addEventListener('scroll', () => {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => { scheduled = false; measure(); syncAll(); });
      }, {passive: true});
      measure();
      syncAll();
    }
    if (details) new MutationObserver(() => {
      if (!sectionOpen()) closeDialog();
      measure();
      syncAll();
    }).observe(details, {attributes: true, attributeFilter: ['open']});
    document.addEventListener('visibilitychange', () => { measure(); syncAll(); });
    reduced.addEventListener('change', syncAll);
    addEventListener('resize', () => { measure(); syncAll(); });
    addEventListener('pagehide', () => { pageActive = false; syncAll(); });
    addEventListener('pageshow', () => { pageActive = true; measure(); syncAll(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
