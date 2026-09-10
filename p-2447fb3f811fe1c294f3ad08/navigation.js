(() => {
  'use strict';
  function mount() {
    if (document.body.classList.contains('bn-navigation-ready')) return;
    const old = document.querySelector('body > header');
    const brand = old?.querySelector('.brand');
    if (!old || !brand) return;
    const svg = (paths, fill = 'none') => `<svg viewBox="0 0 24 24" fill="${fill}" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;
    const book = svg('<path d="M12 5v15M12 5C8 2 4 3 2 4v15c4-2 7-1 10 1 3-2 6-3 10-1V4c-2-1-6-2-10 1Z"/>');
    const windows = svg('<path stroke="none" d="M3 5.3l7.7-1.1v7.3H3zM12.2 4l8.8-1.3v8.8h-8.8zM3 13h7.7v7.3L3 19.2zM12.2 13H21v8.8L12.2 20.5z"/>', 'currentColor');
    const apple = svg('<path stroke="none" d="M16.7 12.7c0-2 1.6-3 1.7-3.1-1-1.5-2.6-1.7-3.2-1.7-1.4-.2-2.7.8-3.4.8-.7 0-1.8-.8-3-.8-1.6 0-3.1 1-3.9 2.4-1.7 2.9-.4 7.3 1.2 9.7.8 1.1 1.7 2.3 2.9 2.2 1.1 0 1.6-.7 3-.7 1.5 0 1.9.7 3.1.7 1.3 0 2.1-1.1 2.9-2.2.9-1.3 1.3-2.5 1.3-2.6-.1 0-2.6-1-2.6-3.7ZM14.4 6.4c.6-.8 1.1-1.9 1-3-.9 0-2.1.6-2.8 1.4-.6.7-1.2 1.8-1 2.9 1 .1 2.1-.5 2.8-1.3Z"/>', 'currentColor');
    const external = svg('<path d="M8 5h11v11M19 5 5 19"/>');
    // Verified against ../../guide/index.html: #dlWin and its BASE constant.
    const download = 'https://github.com/minsk999/bannernode-guide/releases/latest/download/BannerNode-Windows.zip';
    // Exact MAC_TAG / MAC_BASE / filenames from ../../guide/index.html.
    const macBase = 'https://github.com/minsk999/bannernode-guide/releases/download/v1.0.200/';
    const header = document.createElement('header');
    header.className = 'bn-header';
    const inner = document.createElement('div');
    inner.className = 'bn-header-inner';
    brand.setAttribute('aria-label', 'BannerNode · 페이지 처음으로');
    inner.append(brand); // Move the original brand, including its exact SVG.
    const actions = document.createElement('div');
    actions.className = 'bn-header-actions';
    actions.innerHTML = `<a class="bn-action bn-guide" href="https://minsk999.github.io/bannernode-guide/" target="_blank" rel="noopener" aria-label="사용 가이드 (새 탭)">${book}<span>사용 가이드</span></a><a class="bn-action bn-download" href="${download}" aria-label="Windows용 BannerNode 다운로드 (ZIP)">${windows}<span>Windows<span class="bn-download-word"> 다운로드</span></span></a><div class="bn-mac-slot"><div class="bn-mac"><button class="bn-action bn-mac-toggle" type="button" aria-expanded="false" aria-controls="bn-mac-options" aria-label="macOS 다운로드 옵션 열기">${apple}<span>macOS<span class="bn-download-word"> 다운로드</span></span></button><div class="bn-mac-options" id="bn-mac-options" inert aria-hidden="true"><a href="${macBase}BannerNode-macOS-arm64.zip" aria-label="Apple 실리콘용 BannerNode 다운로드 (ZIP)">Apple 실리콘</a><a href="${macBase}BannerNode-macOS-x86_64.zip" aria-label="Intel Mac용 BannerNode 다운로드 (ZIP)">Intel CPU</a></div></div></div>`;
    inner.append(actions);
    header.append(inner);
    old.replaceWith(header);
    const mac = actions.querySelector('.bn-mac');
    const macToggle = mac.querySelector('button');
    const macOptions = mac.querySelector('.bn-mac-options');
    function setMacOpen(open, restoreFocus = false) {
      mac.classList.toggle('is-open', open);
      macToggle.setAttribute('aria-expanded', String(open));
      macToggle.setAttribute('aria-label', `macOS 다운로드 옵션 ${open ? '닫기' : '열기'}`);
      macOptions.inert = !open;
      macOptions.setAttribute('aria-hidden', String(!open));
      if (restoreFocus) macToggle.focus();
    }
    macToggle.addEventListener('click', () => setMacOpen(!mac.classList.contains('is-open')));
    mac.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); setMacOpen(false, true); }
      // Both directions enter the choices; the compact panel reveals inward to the left.
      if (['ArrowLeft', 'ArrowRight', 'ArrowDown'].includes(event.key) && event.target === macToggle) {
        event.preventDefault(); setMacOpen(true); macOptions.querySelector('a').focus();
      }
    });
    document.addEventListener('pointerdown', event => { if (!mac.contains(event.target)) setMacOpen(false); });
    mac.addEventListener('focusout', event => { if (!mac.contains(event.relatedTarget)) setMacOpen(false); });

    const chapters = [
      ['why', '시작 배경'], ['history', '개발 과정'], ['compare', '작업 시간의 변화'], ['survey', '사용자 설문'],
      ['features', '주요 기능'], ['archive', '애드아카이브'], ['try-it', '직접 써보기']
    ];
    const nav = document.createElement('nav');
    nav.className = 'bn-reader';
    nav.setAttribute('aria-label', '본문 목차');
    nav.innerHTML = `<span class="bn-reader-label" aria-hidden="true">둘러보기</span><div class="bn-reader-track">${chapters.map(([id, label], i) => `<a class="bn-chapter" href="#${id}"><span class="bn-chapter-number" aria-hidden="true">${String(i + 1).padStart(2, '0')}</span><span>${label}</span></a>`).join('')}</div>`;
    document.body.append(nav);
    document.body.classList.add('bn-navigation-ready');
    const links = [...nav.querySelectorAll('a')];
    const track = nav.querySelector('.bn-reader-track');
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0, active = '', targets = [];
    function refreshTargets() {
      targets = chapters.map(([id]) => document.getElementById(id));
      links.forEach((link, i) => {
        if (targets[i]) { link.removeAttribute('aria-disabled'); link.removeAttribute('tabindex'); }
        else { link.setAttribute('aria-disabled', 'true'); link.tabIndex = -1; }
      });
      schedule();
    }
    function update() {
      frame = 0;
      const edge = Math.max(header.getBoundingClientRect().bottom + 32, innerHeight * .3);
      let current = '';
      targets.forEach((el, i) => {
        if (el && el.getClientRects().length && el.getBoundingClientRect().top <= edge) current = chapters[i][0];
      });
      const ending=document.querySelector('.outro');
      const atEnding=!!ending && ending.getBoundingClientRect().top<innerHeight*.68;
      nav.classList.toggle('is-ending',atEnding);nav.inert=atEnding;
      nav.setAttribute('aria-hidden',String(atEnding));
      if(atEnding)current='';
      if (current === active) return;
      active = current;
      links.forEach((link, i) => {
        const on = chapters[i][0] === current;
        if (on) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
        // Reveal the current chapter horizontally; never scroll the document or steal focus.
        if (on && !nav.contains(document.activeElement)) {
          track.scrollTo({left: link.offsetLeft - (track.clientWidth - link.offsetWidth) / 2, behavior: 'auto'});
        }
      });
    }
    function schedule() { if (!frame) frame = requestAnimationFrame(update); }
    nav.addEventListener('click', event => {
      const link = event.target.closest('a');
      if (!link) return;
      if (link.getAttribute('aria-disabled') === 'true') { event.preventDefault(); return; }
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
      const target = document.getElementById(link.hash.slice(1));
      if (!target) return;
      event.preventDefault();
      if (!target.hasAttribute('tabindex')) {
        target.tabIndex = -1;
        target.addEventListener('blur', () => target.removeAttribute('tabindex'), {once: true});
      }
      target.focus({preventScroll: true});
      target.scrollIntoView({behavior: reduced.matches ? 'auto' : 'smooth', block: 'start'});
      if (location.hash !== link.hash) history.pushState(null, '', link.hash);
      schedule();
    });
    nav.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      const enabled = links.filter(link => link.getAttribute('aria-disabled') !== 'true');
      const index = enabled.indexOf(document.activeElement);
      if (index < 0) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? enabled.length - 1 :
        (index + (event.key === 'ArrowRight' ? 1 : -1) + enabled.length) % enabled.length;
      enabled[next].focus({preventScroll: true});
      track.scrollTo({left: enabled[next].offsetLeft - (track.clientWidth - enabled[next].offsetWidth) / 2, behavior: 'auto'});
    });
    // Replace only the decorative text arrow; links, accessible names and targets survive.
    document.querySelectorAll('main .motion-expand, main a.primary').forEach(link => {
      if (link.children.length || !link.textContent.includes('↗')) return;
      const label = document.createElement('span');
      label.textContent = link.textContent.replace(/\s*↗\s*$/, '');
      link.replaceChildren(label);
      link.insertAdjacentHTML('beforeend', external);
    });
    addEventListener('scroll', schedule, {passive: true});
    addEventListener('resize', schedule);
    addEventListener('hashchange', schedule);
    addEventListener('popstate', schedule);
    if ('ResizeObserver' in window) new ResizeObserver(schedule).observe(document.querySelector('main') || document.body);
    // Parent may add the remaining section IDs after this script mounts.
    new MutationObserver(refreshTargets).observe(document.querySelector('main') || document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['id']});
    refreshTargets();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once: true});
  else mount();
})();
