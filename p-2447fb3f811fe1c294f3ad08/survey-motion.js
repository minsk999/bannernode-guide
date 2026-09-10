/* Standalone: load with defer or at the end of body, after survey-motion.css.
   QA: data-survey-motion="armed|running|done"; --survey-entry-delay.
   Actual accessible text and all inline percentage widths are never rewritten. */
(() => {
  'use strict';

  function init() {
    // An empty hook is uninitialized. Duplicate script loads cannot replay cards.
    const cards = [...document.querySelectorAll('.survey-distribution[data-survey-motion=""]')];
    if (!cards.length) return;

    const timers = new Map();
    let observer;
    let reduced;
    let desktop;

    function finish(card) {
      clearTimeout(timers.get(card));
      timers.delete(card);
      card.dataset.surveyMotion = 'done';
      card.style.removeProperty('--survey-entry-delay');
      observer?.unobserve(card);
    }

    function finishAll() {
      cards.forEach(finish);
      observer?.disconnect();
    }

    function enter(entries) {
      try {
        if (reduced.matches) return finishAll();
        const arriving = entries.filter(entry =>
          entry.isIntersecting && entry.intersectionRatio >= .52 &&
          entry.target.dataset.surveyMotion === 'armed'
        ).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top ||
          a.boundingClientRect.left - b.boundingClientRect.left);

        let rowTop = -Infinity;
        let rowIndex = 0;
        arriving.forEach(entry => {
          const card = entry.target;
          if (Math.abs(entry.boundingClientRect.top - rowTop) > 8) {
            rowTop = entry.boundingClientRect.top;
            rowIndex = 0;
          }
          const delay = 120 + (desktop.matches ? Math.min(rowIndex++, 2) * 90 : 0);
          card.style.setProperty('--survey-entry-delay', `${delay}ms`);
          card.dataset.surveyMotion = 'running';
          // Consume at entry, so scroll bounces cannot restart even mid-animation.
          observer.unobserve(card);
          timers.set(card, setTimeout(() => finish(card), 1200 + delay));
        });
      } catch (_) {
        finishAll();
      }
    }

    try {
      if (!('IntersectionObserver' in window) || !window.matchMedia) return finishAll();
      reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
      desktop = window.matchMedia('(min-width: 701px)');
      // Missing/late CSS must never make previously visible content disappear.
      if (reduced.matches || getComputedStyle(cards[0]).getPropertyValue('--survey-motion-ready').trim() !== '1') {
        return finishAll();
      }

      observer = new IntersectionObserver(enter, {
        threshold: [0, .52],
        rootMargin: '0px 0px -32px 0px'
      });

      // CSS honors the setting instantly; JS permanently consumes pending cards.
      const onReduction = event => { if (event.matches) finishAll(); };
      if (reduced.addEventListener) reduced.addEventListener('change', onReduction);
      else reduced.addListener(onReduction);
      window.addEventListener('pagehide', finishAll, { once: true });

      cards.forEach(card => {
        const rect = card.getBoundingClientRect();
        // Visible/previously passed cards stay final on deep links, restored scroll
        // and late loading. Only cards entirely below the viewport are prepared.
        if (rect.top < window.innerHeight || !rect.width || !rect.height) return finish(card);
        card.dataset.surveyMotion = 'armed';
        observer.observe(card);
      });
    } catch (_) {
      finishAll();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
