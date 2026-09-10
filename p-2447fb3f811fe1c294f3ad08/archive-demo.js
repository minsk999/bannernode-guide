/* Portable, deterministic recreation. All media are local; no NAS API or share
   endpoint is called. The timeline controls the illustrated interface only. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const scene = $('#scene'), viewport = $('.viewport'), video = $('#previewVideo');
  const timeline = window.ARCHIVE_TIMELINE, data = window.ARCHIVE_DATA;
  const selectedCard = data.ai.find(card => card.image === 'media/archive-68156a2ba279b83d.jpg');
  const eventTime = Object.fromEntries(timeline.events.map(e => [e.action, e.at]));
  const params = new URLSearchParams(location.search);
  const staticTime = params.has('at') ? Math.max(0, Math.min(timeline.duration, Number(params.get('at')) || 0)) : null;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let time = staticTime ?? 0, paused = staticTime !== null || reduced.matches;
  let inView = false, ready = false, lastFrame = 0, frameId = 0, scale = 1;
  let currentKey = '', cardMode = '', sortMode = '', measuring = false, cursorPoints = [];
  const categories = [
    ['전체',12241], ['커머스',1570], ['뷰티',6667], ['패션',386], ['엔터',286],
    ['공익/교육',1449], ['식음료/리빙',1101], ['여행/레저',379], ['금융/서비스',328], ['비딩',75]
  ];
  const workTypes = [['전체',0],['모션영상',12],['모션배너',286],['배너결합',35],['편집',85],['AI활용영상',27],['AI활용배너',21],['사이즈베리',39],['용량베리',6]];
  const advertisers = [
    {name:'네플스',period:'25.03–26.09',count:888,end:2609,id:'adv-neples'},
    {name:'더한섬닷컴',period:'25.01–26.09',count:228,end:2609},
    {name:'한섬EQL',period:'25.02–26.07',count:120,end:2607},
    {name:'현대면세점',period:'25.01–26.01',count:48,end:2601},
    {name:'SIV',period:'25.01–26.01',count:283,end:2601},
    {name:'쿠팡애즈',period:'25.08',count:1,end:2508},
    {name:'SK스토아',period:'25.01',count:2,end:2501}
  ];
  const escape = text => String(text).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  $('#catPills').innerHTML = categories.map(([label,count],i) => `<button class="pill${i === 0 ? ' on' : ''}" id="${i === 1 ? 'commerce' : `category-${i}`}" data-category="${i}">${label}<b>${count}</b></button>`).join('');
  $('#typePills').innerHTML = workTypes.map(([label,count],i) => `<button class="pill${i === 0 ? ' on' : ''}" id="${i === 5 ? 'type-ai' : `type-${i}`}" data-type="${i}">${label}${count ? `<b>${count}</b>` : ''}</button>`).join('');
  const rows = advertisers.map((adv,i) => {
    const el = document.createElement('button');
    el.id = adv.id || `adv-${i}`; el.className = 'adv-row';
    el.innerHTML = `<span class="adv-name">${adv.name}</span><span class="adv-period">${adv.period}</span><span class="adv-count">${adv.count}</span>`;
    adv.el = el; return adv;
  });
  $('#shareDlgSub').textContent = `“${selectedCard.title}” — 로그인 없이 비밀번호로 열람.`;
  $('#shareResultLink').value = 'https://adarchive.example/s/neples-demo';
  $('#shareResultPw').value = '1111';
  // Keep the recreation inert; only its pause/replay controls accept input.
  scene.setAttribute('aria-hidden', 'true');
  scene.addEventListener('click', e => e.preventDefault());
  scene.addEventListener('contextmenu', e => e.preventDefault());

  function show(selector, on) {
    const el = $(selector), changed = el.hidden === on;
    el.hidden = !on;
    if (changed && on && ready && !measuring && !paused && !reduced.matches) {
      if(selector==='#radial') {
        el.querySelectorAll('.radial-item').forEach(item=>item.animate([
          {opacity:0,transform:'translate(0,0) scale(.3)'},
          {opacity:1,transform:getComputedStyle(item).transform}
        ],{duration:450,easing:'cubic-bezier(.34,1.3,.64,1)'}));
      } else {
        const target=el.querySelector('.appdlg-panel,.player-panel')||el;
        const picker=selector==='#fpicker'||selector==='#shareMenu';
        target.animate([{opacity:0,transform:picker?'translateY(8px) scale(.96)':'translateY(8px) scale(.98)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:picker?350:280,easing:picker?'cubic-bezier(.34,1.3,.64,1)':'cubic-bezier(.22,1,.36,1)'});
      }
    }
  }
  function sortAdvertisers(mode) {
    if (mode === sortMode) return;
    // Native renderAdvRows replaces row order immediately.
    const ordered = [...rows];
    if (mode === 'name') ordered.sort((a,b) => a.name.localeCompare(b.name,'ko'));
    if (mode === 'period') ordered.sort((a,b) => b.end-a.end);
    if (mode === 'count') ordered.sort((a,b) => b.count-a.count);
    ordered.forEach(a => $('#advertisers').append(a.el));
    sortMode = mode;
    ['name','period','count'].forEach(key => {
      $(`#sort-${key}`).classList.toggle('on', key === mode);
      $(`#sort-${key} span`).textContent = key === mode ? (key === 'name' ? '↑' : '↓') : '';
    });
  }
  function fillCards(mode) {
    if (mode === cardMode) return;
    cardMode = mode; $('#cards').dataset.count=data[mode].length;
    $('#cards').innerHTML = data[mode].map((card,i) => `<article class="card${i%3===0 ? ' big' : ''}" id="${card.image === selectedCard.image ? 'card-selected' : `card-${i}`}"><div class="tilt-box"><img class="card-poster" src="${card.image}" alt="" decoding="async"><div class="card-overlay"><span class="ov-top"><strong class="ov-title">${escape(card.title)}</strong>${card.versions>1 ? `<span class="ov-ver">${card.versions} ver</span>` : ''}</span><span class="ov-client"><span class="ov-campaign">${escape(card.campaign)}</span><small>${card.duration}</small></span></div></div></article>`).join('');
  }
  function stateAt(t) {
    const reset = t >= eventTime.reset;
    const has = action => !reset && t >= eventTime[action];
    return {
      neples:has('select-neples'), types:has('open-types'), ai:has('select-ai'),
      picker:has('open-advertisers') && !has('select-neples'),
      sort:has('sort-count') ? 'count' : has('sort-period') ? 'period' : has('sort-name') ? 'name' : 'period',
      player:has('open-player'), radial:has('open-radial') && !has('open-share-menu'),
      hover:has('hover-share') ? 'share' : has('hover-copy') ? 'copy' : has('hover-save') ? 'save' : '',
      shareMenu:has('open-share-menu') && !has('open-share-dialog'),
      dialog:has('open-share-dialog') && !has('result'), result:has('result'),
      password:[1,2,3,4].filter(i=>has(`password-${i}`)).length,
      download:has('permission-download'), week:has('expiry-week'), creating:has('create-link') && !has('result')
    };
  }
  function drawState(t) {
    const state = stateAt(t), key = JSON.stringify(state);
    if (key === currentKey) return;
    currentKey = key;
    const pillSizes=new Map($$('#catPills .pill,#typeToggle').map(el=>[el,el.offsetWidth]));
    fillCards(state.ai ? 'ai' : 'initial');
    sortAdvertisers(state.sort);
    categories.forEach(([label,count],i) => {
      const el = $(`[data-category="${i}"]`);
      el.classList.toggle('on', state.neples ? i === 1 : i === 0);
      el.querySelector('b').textContent = state.neples ? (i <= 1 ? (state.ai ? 27 : 888) : 0) : count;
    });
    $('#libraryTitle').innerHTML = `네플스 <small>(${state.ai ? 27 : 888})</small>`;
    $('#libraryCount').textContent = state.neples ? `${state.ai ? 27 : 888} films — 1 advertiser` : '1570 films — 7 advertisers';
    ['#activeChips','#typePills'].forEach((selector,i)=>{
      const el=$(selector);el.hidden=false;el.classList.toggle('open',i?state.types:state.neples);
    });
    show('#fpicker',state.picker);
    $('#typeToggle').classList.toggle('on',state.ai);
    $('#typeToggle').classList.toggle('open',state.types);
    $('#typeToggle').setAttribute('aria-expanded',String(state.types));
    $('#typeToggleLabel').textContent = state.ai ? '작업 성격: AI활용영상' : '작업 성격';
    $$('[data-type]').forEach(el=>el.classList.toggle('on',Number(el.dataset.type)===(state.ai?5:0)));
    if(ready&&!measuring&&!paused&&!reduced.matches) pillSizes.forEach((w0,el)=>{
      const w1=el.offsetWidth;
      if(Math.abs(w1-w0)>1) el.animate([{width:w0+'px'},{width:w1+'px'}],{duration:400,easing:'cubic-bezier(.22,1,.36,1)'});
    });
    if (state.player) layoutOverlays();
    show('#player',state.player); show('#radial',state.radial); show('#shareMenu',state.shareMenu);
    show('#shareDlg',state.dialog); show('#shareResult',state.result);
    document.body.classList.toggle('player-open',state.player);
    document.body.classList.toggle('sharing',state.dialog || state.result);

    $('#shareDlgPw').value = '1'.repeat(state.password);
    $('#shareDlgPw').classList.toggle('focus',state.password > 0);
    $$('#shareDlgPerm button').forEach(el => {
      const on = el.dataset.v === (state.download ? 'download' : 'play');
      el.classList.toggle('on',on); el.setAttribute('aria-checked',String(on));
    });
    $$('#shareDlgExp button').forEach(el => {
      const on = el.dataset.v === (state.week ? '7' : '30');
      el.classList.toggle('on',on); el.setAttribute('aria-checked',String(on));
    });
    $('#shareDlgOk').textContent = state.creating ? '만드는 중…' : '링크 만들기';
    $('#shareDlgOk').disabled = state.creating;
    $$('#scene button, #scene input').forEach(el => el.tabIndex = -1);
    if (state.player) layoutOverlays();
    if (!measuring) syncVideo();
  }
  function box(el) {
    const b = el.getBoundingClientRect(), s = scene.getBoundingClientRect();
    return {x:(b.left-s.left)/scale,y:(b.top-s.top)/scale,width:b.width/scale,height:b.height/scale};
  }
  function playerAnchor() {
    const b = box($('#playerStage'));
    // Open the radial at the same point the cursor approaches inside the video.
    return {x:b.x+135,y:b.y+b.height*.67};
  }
  function layoutOverlays() {
    const origin = playerAnchor(), radius = 126;
    $('#radial').style.left = `${origin.x}px`; $('#radial').style.top = `${origin.y}px`;
    $$('.radial-item').forEach((el,i)=>{
      const angle = (-120+i*30)*Math.PI/180;
      el.style.setProperty('--tx',`${Math.cos(angle)*radius}px`);
      el.style.setProperty('--ty',`${Math.sin(angle)*radius}px`);
      el.style.setProperty('--lx',`${Math.cos(angle)*38}px`);
      el.style.setProperty('--ly',`${Math.sin(angle)*38}px`);
    });
    $('#shareMenu').style.left = `${origin.x+18}px`;
    $('#shareMenu').style.top = `${origin.y-118}px`;
  }
  function measureTarget(cue) {
    const el = $(cue.target);
    if (!el) throw new Error(`Missing archive timeline target: ${cue.target}`);
    const hidden = [];
    for (let node = el; node && node !== scene; node = node.parentElement) {
      if (node.hidden) { hidden.push(node); node.hidden = false; }
    }
    if (cue.target.startsWith('#radial-') || cue.target.startsWith('#share-')) layoutOverlays();
    const b = box(el);
    const p = cue.target === '#playerStage' ? playerAnchor() : {x:b.x+b.width/2,y:b.y+b.height/2};
    hidden.forEach(node => node.hidden = true);
    return {...cue,x:p.x+(cue.dx||0),y:p.y+(cue.dy||0)};
  }
  function measureRoute() {
    measuring = true; scene.classList.add('measuring');
    const remembered = new Map();
    cursorPoints = timeline.cursor.map(cue => {
      drawState(cue.at);
      scrollLibrary(cue.at);
      const el = $(cue.target), concealed = el.closest('[hidden]');
      // Keep the last visible click location during the following UI change.
      const p = concealed && remembered.has(cue.target) ? {...cue,...remembered.get(cue.target)} : measureTarget(cue);
      if (!concealed) remembered.set(cue.target,{x:p.x,y:p.y});
      return p;
    });
    currentKey=''; drawState(time); scrollLibrary(time); scene.getBoundingClientRect(); scene.classList.remove('measuring'); measuring=false;
  }
  function scrollLibrary(t) {
    const library=$('.library'),card=$('#card-selected');
    window.ARCHIVE_CARDS.size();
    if(t<5.9||t>=eventTime.reset){library.scrollTop=0;return;}
    const b=box(card),r=box(library);
    const destination=library.scrollTop+b.y-r.y-(r.height-b.height)/2;
    const progress=Math.max(0,Math.min(1,(t-5.9)/.55));
    library.scrollTop=destination*progress*progress*(3-2*progress);
  }
  const cursorArt = {
    pointer:'<path d="M3 2v22l5.6-5.9 4.2 8 4.1-2.1-4.2-8 8-.5Z" fill="white" stroke="#151515" stroke-width="1.2" stroke-linejoin="round"/>',
    hand:'<path d="M8 14V4a2 2 0 0 1 4 0v7.5c.4-1.3 3.5-1.2 3.7.4 1.2-1.1 3.6-.3 3.6 1.3 1.7-.6 3.1.6 3 2.5l-.4 5.2c-.3 4-3 5.8-6.3 5.8h-2.2c-2.8 0-4.5-1-6-3.2L3.4 17a2.1 2.1 0 0 1 3.2-2.7L8 16Z" fill="white" stroke="#151515" stroke-width="1.15" stroke-linejoin="round"/>',
    text:'<path d="M7 3h10M12 3v22M7 25h10" fill="none" stroke="white" stroke-width="4"/><path d="M7 3h10M12 3v22M7 25h10" fill="none" stroke="#111" stroke-width="1.7"/>',
    'right-click':'<rect x="4" y="2" width="16" height="24" rx="8" fill="white" stroke="#151515" stroke-width="1.2"/><path d="M12 2v10h8V10a8 8 0 0 0-8-8Z" fill="#111"/><path d="M4 12h16M12 2v10" stroke="#151515" stroke-width="1.2"/>'
  };
  const smooth = v => v*v*(3-2*v);
  function cursorAt(t) {
    let i = cursorPoints.findLastIndex(cue => cue.at <= t);
    i = Math.max(0,i);
    const a=cursorPoints[i], b=cursorPoints[Math.min(i+1,cursorPoints.length-1)];
    const fraction=b.at === a.at ? 0 : smooth(Math.min(1,Math.max(0,(t-a.at)/(b.at-a.at))));
    return {x:a.x+(b.x-a.x)*fraction,y:a.y+(b.y-a.y)*fraction,kind:fraction>.75?b.kind:a.kind,target:fraction>.8?b.target:a.target};
  }
  const clickActions = new Set(['open-advertisers','sort-name','sort-period','sort-count','select-neples','open-types','select-ai','open-player','open-radial','open-share-menu','open-share-dialog','permission-download','expiry-week','create-link','reset']);
  function draw(t) {
    drawState(t);
    scrollLibrary(t);
    const p=cursorAt(t), el=$('#cursor');
    window.ARCHIVE_CARDS.update(p,staticTime!==null&&paused);
    const kind = p.kind || 'pointer';
    if (el.dataset.kind !== kind) {el.innerHTML=cursorArt[kind]||cursorArt.pointer;el.dataset.kind=kind;}
    const hotspot=kind==='hand'?{x:11,y:4}:kind==='text'?{x:14,y:16}:kind==='right-click'?{x:14,y:16}:{x:3.5,y:2.3};
    el.style.transform=`translate(${p.x-hotspot.x}px,${p.y-hotspot.y}px)`;
    $$('.radial-item').forEach(node=>{
      const b=box(node);node.classList.toggle('is-hover',!$('#radial').hidden&&p.x>=b.x&&p.x<=b.x+b.width&&p.y>=b.y&&p.y<=b.y+b.height);
    });
    $$('#scene .is-hover:not(.radial-item)').forEach(node=>node.classList.remove('is-hover'));
    if (!$('#player').hidden && !p.target.startsWith('#radial-')) { /* Player masks library hover. */ }
    else if(!p.target.startsWith('#radial-')&&!p.target.startsWith('#card-')) $(p.target)?.classList.add('is-hover');
    const recent=timeline.events.findLast(e=>clickActions.has(e.action)&&e.at<=t&&t-e.at<.36);
    const ring=$('#click-ring');
    if (recent && !reduced.matches) {
      const q=cursorAt(recent.at), k=(t-recent.at)/.36;
      ring.style.transform=`translate(${q.x-16}px,${q.y-16}px) scale(${.5+k*.8})`;
      ring.style.opacity=String((1-k)*.55);
    } else ring.style.opacity='0';
    $('#caption').textContent=timeline.captions.findLast(c=>c.at<=t)?.text||'';
    $('#meter').style.width=`${Math.min(100,t/timeline.duration*100)}%`;
    document.body.dataset.time=t.toFixed(3);
    document.body.dataset.step=timeline.events.findLast(e=>e.at<=t)?.action||'ready';
  }
  function syncVideo() {
    if (!ready || measuring) return;
    const canPlay=!paused&&inView&&!document.hidden&&!$('#player').hidden;
    if (canPlay && video.paused) video.play().catch(()=>{});
    if (!canPlay && !video.paused) video.pause();
    if ($('#player').hidden && video.currentTime) video.currentTime=0;
  }
  function size() {
    scale=Math.min(viewport.clientWidth/1440,viewport.clientHeight/1120);
    scene.style.transform=`scale(${scale})`;
    scene.style.left=`${(viewport.clientWidth-1440*scale)/2}px`;
    scene.style.top=`${(viewport.clientHeight-1120*scale)/2}px`;
    if (ready) {measureRoute();draw(time);}
  }
  function tick(now) {
    frameId=0;
    if (!ready||paused||!inView||document.hidden) {lastFrame=0;return;}
    if (lastFrame) time=(time+Math.min((now-lastFrame)/1000,.12))%timeline.duration;
    lastFrame=now;draw(time);frameId=requestAnimationFrame(tick);
  }
  function run() {lastFrame=0;controls();syncVideo();if(ready&&!paused&&inView&&!document.hidden&&!frameId) frameId=requestAnimationFrame(tick);}
  function controls() {BNDemoControls.play($('#pause'),paused||!inView,time>0);document.body.dataset.userPaused=String(paused);}
  $('#pause').addEventListener('click',()=>{paused=inView?!paused:false;if(!inView)inView=true;controls();run();});
  $('#replay').addEventListener('click',()=>{time=0;paused=false;controls();draw(time);run();});
  document.addEventListener('visibilitychange',run);
  BNDemoControls.mount($('.demo-controls'),1120/1440,'archive-demo.html');
  window.addEventListener('bn-controls-resize',size);
  window.addEventListener('resize',size);
  if(!window.frameElement?.closest('.ar-demo'))new IntersectionObserver(entries=>{inView=entries.some(e=>e.isIntersecting&&e.intersectionRatio>=.15);run();},{threshold:.15}).observe(viewport);
  else inView=window.frameElement.dataset.featureActive==='true';
  window.addEventListener('message',e=>{if(e.source===parent&&e.origin===parent.location.origin&&e.data?.type==='bn-feature-visibility'){inView=!!e.data.active;run();}});
  reduced.addEventListener('change',e=>{if(e.matches){paused=true;controls();run();}});
  // The font-dependent layout and all cursor endpoints settle before first paint.
  scene.style.visibility='hidden';
  size(); drawState(time); controls();
  document.documentElement.dataset.sceneReady='true';
  Promise.all([document.fonts.ready,...data.ai.map(card=>new Promise(resolve=>{const img=new Image();img.onload=img.onerror=resolve;img.src=card.image;}))]).then(()=>{
    size();measureRoute();draw(time);scene.style.visibility='visible';ready=true;
    document.body.dataset.ready='true';
    if (staticTime!==null && staticTime>=eventTime['open-player'] && staticTime<eventTime.reset) {
      const seek=()=>{video.currentTime=(staticTime-eventTime['open-player'])%(video.duration||13);};
      video.readyState>=1?seek():video.addEventListener('loadedmetadata',seek,{once:true});
    }
    run();
  });
})();
