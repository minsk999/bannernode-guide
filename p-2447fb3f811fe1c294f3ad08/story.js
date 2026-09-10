(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const timeDisplay=$('#manual-time');
  timeDisplay.innerHTML='<span class="time-reel" data-unit="minutes"></span><small>분</small><span class="time-reel" data-unit="seconds"></span><small>초</small>';
  let lastQuantity=1;
  const reducedQuantity=matchMedia('(prefers-reduced-motion: reduce)');
  function roll(slot,value,direction){
    const next=String(value).padStart(2,'0');
    if(slot.dataset.value===next)return;
    const old=slot.dataset.value;slot.dataset.value=next;
    // Keep the most visible glyph at its current pose if a fresh value arrives mid-roll.
    const previous=[...slot.children].sort((a,b)=>Number(getComputedStyle(b).opacity)-Number(getComputedStyle(a).opacity))[0];
    const pose=previous?{transform:getComputedStyle(previous).transform,opacity:getComputedStyle(previous).opacity,filter:getComputedStyle(previous).filter}:null;
    const oldText=previous?.textContent||old;
    slot.getAnimations({subtree:true}).forEach(a=>a.cancel());
    slot.replaceChildren();
    const incoming=document.createElement('span');incoming.textContent=next;slot.append(incoming);
    if(old===undefined||reducedQuantity.matches)return;
    const outgoing=document.createElement('span');outgoing.textContent=oldText;slot.append(outgoing);
    const options={duration:240,easing:'cubic-bezier(.3,0,.25,1)'};
    incoming.animate([{transform:`translateY(${direction*42}%)`,opacity:0,filter:'blur(1.4px)'},{transform:'translateY(0)',opacity:1,filter:'blur(0px)'}],options);
    outgoing.animate([pose||{transform:'translateY(0)',opacity:1,filter:'blur(0px)'},{transform:`translateY(${-direction*42}%)`,opacity:0,filter:'blur(1.4px)'}],options).onfinish=()=>outgoing.remove();
  }

  function quantity(n){
    const seconds=100*n,minutes=Math.floor(seconds/60),rest=seconds%60,direction=n>=lastQuantity?1:-1;
    roll(timeDisplay.querySelector('[data-unit="minutes"]'),minutes,direction);
    roll(timeDisplay.querySelector('[data-unit="seconds"]'),rest,direction);
    timeDisplay.setAttribute('aria-label',String(minutes).padStart(2,'0')+'분 '+String(rest).padStart(2,'0')+'초');
    lastQuantity=n;
    $('#manual-formula').textContent='1분 40초 × '+n+'개';$('#node-quantity').textContent=n+'개';
    $('#quantity-value').innerHTML=n+'<small>개</small>';
    $('#manual-count').textContent=n+'회';
    const progress=(n-1)/(Number($('#banner-quantity').max)-1);
    $('#banner-quantity').style.setProperty('--fill',progress*100+'%');
    $('.node-reason').style.setProperty('--quantity-progress',progress);
    const fanWidth=$('.job-fan').clientWidth,spread=Math.min(Math.max(0,fanWidth-185),(n-1)*18);
    document.querySelectorAll('.job-card').forEach((card,i)=>{
      card.classList.toggle('is-visible',i<n);
      card.setAttribute('aria-hidden',String(i>=n));
      const position=n>1?(Math.min(i,n-1)/(n-1)*2-1):0;
      card.style.setProperty('--fan-x',position*spread/2+'px');
      card.style.setProperty('--fan-y',position*position*12+'px');
      card.style.setProperty('--fan-angle',position*Math.min(14,(n-1)*1.4)+'deg');
      card.style.zIndex=String(i+1);
    });
    $('.batch-sheet.back-one').style.opacity=n>=2?'1':'0';
    $('.batch-sheet.back-two').style.opacity=n>=3?'1':'0';
  }
  $('#banner-quantity').addEventListener('input',e=>quantity(Number(e.target.value)));quantity(1);
  window.addEventListener('resize',()=>quantity(Number($('#banner-quantity').value)));
  const featureRows=[...document.querySelectorAll('.feature-row')];
  const setActive=(frame,on)=>{
    frame.dataset.featureActive=String(on);
    frame.contentWindow?.postMessage({type:'bn-feature-visibility',active:on},location.origin);
  };
  const reducedEntry=matchMedia('(prefers-reduced-motion: reduce)');
  const featureState=featureRows.map((row,i)=>{
    row.classList.add('feature-reveal');
    row.style.setProperty('--entry-x',i%2?'112px':'-112px');
    const frame=row.querySelector('iframe');frame.dataset.featureActive='false';
    return {row,card:row.querySelector('.feature-motion'),frame,shownAt:0,timer:0};
  });
  const archiveFrame=document.querySelector('.ar-demo iframe');
  if(archiveFrame){
    archiveFrame.dataset.featureActive='false';
    featureState.push({row:null,card:archiveFrame,frame:archiveFrame,shownAt:0,timer:0});
  }
  let featureRAF=0;
  function visibleRatio(el){
    const r=el.getBoundingClientRect(),header=document.querySelector('.bn-header');
    const nav=document.querySelector('.bn-reader:not(.is-ending)');
    const top=header?Math.max(0,header.getBoundingClientRect().bottom):0;
    const bottom=nav?Math.min(innerHeight,nav.getBoundingClientRect().top-12):innerHeight;
    return Math.max(0,Math.min(bottom,r.bottom)-Math.max(top,r.top))/Math.max(1,r.height);
  }
  function checkFeatures(){
    featureRAF=0;
    featureState.forEach(state=>{
      const ratio=visibleRatio(state.card),now=performance.now();
      state.frame.dataset.visibleRatio=ratio.toFixed(3);
      if(!state.shownAt&&(ratio>=.30||reducedEntry.matches)){
        state.row?.classList.add('feature-shown');state.shownAt=now;
      }
      if(document.hidden||ratio<=.03){
        clearTimeout(state.timer);state.timer=0;setActive(state.frame,false);return;
      }
      if(state.frame.dataset.featureActive==='true')return;
      // Begin during the arrival, once the prepared frame is already visible.
      // The first click then lands after the row has settled, without an empty pause.
      if(ratio<.35||!state.shownAt||state.frame.dataset.sceneReady!=='true'){clearTimeout(state.timer);state.timer=0;return;}
      const remaining=Math.max(0,(reducedEntry.matches?0:160)-(now-state.shownAt));
      if(remaining>0){
        if(!state.timer)state.timer=setTimeout(()=>{state.timer=0;scheduleFeatures();},remaining);
      }else setActive(state.frame,true);
    });
  }
  function scheduleFeatures(){if(!featureRAF)featureRAF=requestAnimationFrame(checkFeatures);}
  addEventListener('scroll',scheduleFeatures,{passive:true});
  addEventListener('resize',scheduleFeatures);
  document.addEventListener('visibilitychange',scheduleFeatures);
  reducedEntry.addEventListener('change',scheduleFeatures);
  const frameRatios=new Map();
  function fitSceneFrame(frame){
    const isFeature=frame.closest('.feature-row'),isArchive=frame.closest('.ar-demo');
    if(!isFeature&&!isArchive)return;
    const config=frameRatios.get(frame);
    const bar=config?.height||(frame.clientWidth<=760?112:68);
    frame.style.height=Math.ceil(frame.clientWidth*(config?.ratio||(isFeature ? .64 : 1120/1440))+bar)+'px';
  }
  addEventListener('message',e=>{
    if(e.origin!==location.origin||e.data?.type!=='bn-demo-layout')return;
    const frame=[...document.querySelectorAll('iframe[data-scene-src]')].find(f=>f.contentWindow===e.source);
    if(!frame||!Number.isFinite(e.data.height)||e.data.height<44||e.data.height>220)return;
    const ratio=frame.closest('.feature-row') ? .64 : 1120/1440;
    frameRatios.set(frame,{height:e.data.height,ratio});fitSceneFrame(frame);scheduleFeatures();
  });
  const frameSizer=new ResizeObserver(entries=>{
    entries.forEach(e=>{const frame=e.target.querySelector('iframe');if(frame)fitSceneFrame(frame);});
    scheduleFeatures();
  });
  document.querySelectorAll('.feature-motion,.ar-demo').forEach(el=>{frameSizer.observe(el);fitSceneFrame(el.querySelector('iframe'));});
  scheduleFeatures();
  // Only mount a complete scene document. An interrupted iframe response otherwise
  // leaves a permanently blank frame with no controls and no browser error message.
  const sceneLoader=new IntersectionObserver(entries=>entries.forEach(entry=>{
    if(!entry.isIntersecting)return;
    sceneLoader.unobserve(entry.target);loadScene(entry.target);
  }),{rootMargin:'800px 0px'});
  async function loadScene(frame){
    const box=frame.parentElement;
    frame.dataset.sceneReady='false';
    let note=box.querySelector('.scene-loading');
    if(!note){note=document.createElement('button');note.className='scene-loading';box.append(note);}
    note.disabled=true;note.textContent='시연 불러오는 중…';
    for(let attempt=0;attempt<3;attempt++){
      try{
        const response=await fetch(frame.dataset.sceneSrc,{cache:'no-store',signal:AbortSignal.timeout(15000)});
        if(!response.ok)throw Error('Scene response');
        const html=await response.text();
        if(!html.trimEnd().endsWith('</html>'))throw Error('Incomplete scene');
        await new Promise((resolve,reject)=>{
          const timeout=setTimeout(()=>reject(Error('Scene startup')),6000);
          frame.onload=()=>{
            if(frame.contentDocument?.documentElement.dataset.sceneReady==='true'){clearTimeout(timeout);resolve();}
          };
          frame.srcdoc=html;
        });
        await frame.contentDocument.fonts.ready;
        frame.dataset.sceneReady='true';box.classList.add('scene-ready');
        if(frame.dataset.featureActive!==undefined)setActive(frame,frame.dataset.featureActive==='true');
        scheduleFeatures();
        note.remove();return;
      }catch(error){if(attempt===2){note.disabled=false;note.textContent='시연 다시 불러오기 ↻';note.onclick=()=>loadScene(frame);}}
    }
  }
  document.querySelectorAll('iframe[data-scene-src]').forEach(frame=>sceneLoader.observe(frame));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const journey = $('.journey');
  const journeySticky = journey.querySelector('.journey-sticky');
  let scheduled = false;
  const clamp = x => Math.max(0, Math.min(1, x));
  const phase = (p, a, b) => { const t = clamp((p-a)/(b-a)); return t*t*(3-2*t); };
  function scrollScene() {
    scheduled = false;
    // Use the measured content height: short displays retain a complete static comparison.
    const animated = innerWidth > 760 && !reduced.matches && journeySticky.offsetHeight + 180 <= innerHeight;
    journey.dataset.animated = String(animated);
    const rect = journey.getBoundingClientRect();
    const travel = Math.max(1, journey.offsetHeight - journeySticky.offsetHeight);
    const p = animated ? clamp((86 - rect.top) / travel) : 1;
    const values = {
      'dim': animated ? phase(p,.14,.40) : 0,
      'bridge': phase(p,.24,.43), 'after': phase(p,.36,.51),
      'one': phase(p,.42,.60), 'two': phase(p,.49,.67), 'three': phase(p,.56,.74),
      'progress': p
    };
    for (const [key,value] of Object.entries(values)) journey.style.setProperty('--j-'+key,value.toFixed(4));
  }
  function scheduleJourney(){ if(!scheduled){scheduled=true;requestAnimationFrame(scrollScene);} }
  addEventListener('scroll', scheduleJourney, {passive:true});
  addEventListener('resize', scheduleJourney); reduced.addEventListener('change',scheduleJourney);
  new ResizeObserver(scheduleJourney).observe(journeySticky);
  document.fonts.ready.then(scheduleJourney);
  scrollScene();
  const frame = $('#workflow');
  function fitDemo(){
    if(innerWidth<=700){ const width=frame.parentElement.clientWidth; frame.style.width='850px'; frame.style.height='293px'; frame.style.transform=`scale(${width/850})`; frame.style.marginBottom=`${293*(width/850-1)}px`; }
    else { frame.style.cssText=''; }
  }
  addEventListener('resize',fitDemo); fitDemo();
  const heroBar=$('.app-caption');
  heroBar.classList.add('hero-demo-toolbar');
  const heroActions=document.createElement('div');heroActions.className='hero-demo-actions';
  const heroPause=$('#demo-toggle');heroActions.append(heroPause);
  const heroReplay=document.createElement('button');heroReplay.id='hero-replay';heroReplay.type='button';
  BNDemoControls.label(heroReplay,'처음부터','replay');heroActions.append(heroReplay);heroBar.append(heroActions);
  BNDemoControls.play(heroPause,true,false);
  frame.addEventListener('load',()=>{
    const doc=frame.contentDocument,stage=doc?.querySelector('.stage');if(!stage)return;
    const update=()=>BNDemoControls.play(heroPause,doc.documentElement.classList.contains('paused'),Number(stage.dataset.time)>0);
    heroPause.onclick=()=>{stage.click();update();};
    heroReplay.onclick=()=>{frame.contentWindow.__bnDemoRestart?.();update();};
    new MutationObserver(update).observe(doc.documentElement,{attributes:true,attributeFilter:['class']});update();
  });

})();

