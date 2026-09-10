/* Outer demo controls. The recreated application UI remains independent. */
window.BNDemoControls = (() => {
  const paths = {
    play: '<path d="m7 5 11 7-11 7Z" fill="currentColor" stroke="none"/>',
    pause: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
    replay: '<path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/>',
    expand: '<path d="M8 5h11v11M19 5 5 19"/>'
  };
  const icon = kind => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[kind]}</svg>`;
  function label(button, text, kind) {
    if (!button || button.dataset.controlLabel === text) return;
    button.dataset.controlLabel = text;
    button.innerHTML = '<span class="demo-control-content">' + icon(kind) + '<span class="demo-control-label">' + text + '</span></span>';
    button.setAttribute('aria-label', text);
  }
  function play(button, paused, started = true, together = false) {
    label(button, together ? paused ? '함께 재생' : '함께 일시정지' : paused ? started ? '이어서 재생' : '재생' : '일시정지', paused ? 'play' : 'pause');
  }
  function mount(bar, ratio, file) {
    if (!bar) return;
    bar.classList.add('demo-toolbar');
    const actions = bar.lastElementChild;
    actions.classList.add('demo-actions');
    label(bar.querySelector('#replay'), '처음부터', 'replay');
    if (window.frameElement && file) {
      const expand = document.createElement('a');
      expand.href = file; expand.target = '_blank'; expand.rel = 'noopener';
      label(expand, '크게 보기', 'expand');
      actions.append(expand);
    }
    let previous = 0;
    const measure = () => {
      const height = Math.ceil(bar.getBoundingClientRect().height);
      if (height === previous) return;
      previous = height;
      document.documentElement.style.setProperty('--demo-controls-height', height + 'px');
      window.dispatchEvent(new Event('bn-controls-resize'));
      if (window.frameElement) parent.postMessage({type:'bn-demo-layout', height, ratio}, parent.location.origin);
    };
    new ResizeObserver(measure).observe(bar);
    measure();
  }
  return {icon, label, play, mount};
})();
