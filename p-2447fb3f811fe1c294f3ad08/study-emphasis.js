(() => {
  const details = document.querySelector('.history-study');
  const summary = details?.querySelector('summary');
  const toggle = summary?.querySelector('.study-toggle');
  if (!toggle) return;
  const reduced = matchMedia('(prefers-reduced-motion:reduce)');
  let visible = false, shown = false, timer = 0, animation = null;
  function stop() {
    clearTimeout(timer); timer = 0;
    animation?.cancel(); animation = null;
  }
  function schedule() {
    stop();
    if (shown || !visible || details.open || document.hidden || reduced.matches) return;
    timer = setTimeout(() => {
      timer = 0; shown = true;
      const base = getComputedStyle(toggle).backgroundColor;
      const lime = getComputedStyle(toggle).color;
      animation = toggle.animate([
        {backgroundColor:base},
        {backgroundColor:`color-mix(in srgb, ${lime} 24%, transparent)`,offset:.42},
        {backgroundColor:`color-mix(in srgb, ${lime} 24%, transparent)`,offset:.62},
        {backgroundColor:base}
      ], {duration:950,easing:'cubic-bezier(.22,.68,0,1)'});
      animation.onfinish = () => { animation = null; };
    }, 800);
  }
  new IntersectionObserver(entries => {
    visible = entries[0].intersectionRatio >= .5; schedule();
  }, {threshold:[0,.5]}).observe(summary);
  const interacted = () => { shown = true; stop(); };
  summary.addEventListener('pointerenter',interacted);
  summary.addEventListener('focusin',interacted);
  details.addEventListener('toggle',interacted);
  document.addEventListener('visibilitychange',schedule);
  reduced.addEventListener('change',schedule);
})();
