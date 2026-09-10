(() => {
  const box=document.querySelector('.compare-experience');
  if(!box)return;
  const videos=['before','after'].map(k=>document.getElementById(k+'-video'));
  const slots=videos.map(v=>v.parentElement);
  const toggle=document.getElementById('compare-toggle'), replay=document.getElementById('compare-replay');
  const status=document.getElementById('compare-status');
  BNDemoControls.label(replay,'처음부터','replay');
  const reduced=matchMedia('(prefers-reduced-motion:reduce)'), mobile=matchMedia('(max-width:760px)');
  let loaded=false, wanted=false, everStarted=false, userPaused=false, autoBlocked=false, timer=0, generation=0, buffering=false;
  const ratios=new Map(slots.map(s=>[s,0]));
  const visible=()=>!document.hidden && (document.fullscreenElement || slots.every(s=>ratios.get(s)>=.62));
  const autoAllowed=()=>!reduced.matches&&!mobile.matches&&!navigator.connection?.saveData&&!autoBlocked&&!userPaused;
  const finished=()=>videos.every(v=>v.ended);
  function ui(text){
    status.textContent=text;
    BNDemoControls.play(toggle,!wanted,everStarted,true);
    box.dataset.playback=wanted?'playing':finished()?'ended':everStarted?'paused':'ready';
  }
  function load(){
    if(loaded)return;loaded=true;
    videos.forEach((v,i)=>{v.muted=true;v.defaultMuted=true;v.preload='auto';v.src=window.BN_MEDIA[i?'after':'before'];v.load();});
  }
  function stop(text, manual=false){
    clearTimeout(timer);timer=0;generation++;wanted=false;buffering=false;
    if(manual)userPaused=true;
    videos.forEach(v=>v.pause());ui(text);
  }
  function ready(v){
    if(v.readyState>=3||v.ended)return Promise.resolve();
    return new Promise((resolve,reject)=>{
      const done=e=>{clearTimeout(timeout);v.removeEventListener('canplay',done);v.removeEventListener('error',done);e?.type==='error'?reject(Error('media')):resolve();};
      const timeout=setTimeout(()=>{v.removeEventListener('canplay',done);v.removeEventListener('error',done);reject(Error('timeout'));},12000);
      v.addEventListener('canplay',done);v.addEventListener('error',done);
    });
  }
  async function play(manual=false, restart=false){
    clearTimeout(timer);timer=0;load();
    if(restart||finished()){wanted=false;videos.forEach(v=>{v.pause();v.currentTime=0;});box.querySelectorAll('[data-end]').forEach(e=>e.hidden=true);box.querySelectorAll('.compare-ready-frame').forEach(e=>e.hidden=false);}
    if(manual)userPaused=false;
    const id=++generation;
    ui('두 녹화본을 준비하고 있습니다.');
    try{
      await Promise.all(videos.map(ready));
      if(id!==generation||(!manual&&!visible()))return;
      wanted=true;buffering=false;
      const attempts=await Promise.allSettled(videos.filter(v=>!v.ended).map(v=>v.play()));
      if(id!==generation){if(!wanted)videos.forEach(v=>v.pause());return;}
      if(attempts.some(r=>r.status==='rejected'))throw Error('play');
      everStarted=true;if(finished()){wanted=false;ui('');}else ui('두 녹화본을 함께 보고 있습니다.');
    }catch{if(id===generation){autoBlocked=true;stop('함께 재생을 눌러 녹화본을 확인하세요.');}}
  }
  function schedule(){
    if(!visible()||!autoAllowed()||wanted||timer||finished())return;
    load();timer=setTimeout(()=>{timer=0;if(visible()&&autoAllowed())play(false);},everStarted?400:700);
  }
  const viewportObserver=new IntersectionObserver(entries=>{
    entries.forEach(e=>ratios.set(e.target,e.intersectionRatio));
    if(!visible()){clearTimeout(timer);timer=0;}
    if(wanted&&!document.fullscreenElement && (mobile.matches?slots.every(s=>ratios.get(s)<.2):slots.some(s=>ratios.get(s)<.2)))stop('화면을 벗어나 잠시 멈췄습니다.');
    else schedule();
  },{rootMargin:'-80px 0px -75px',threshold:[0,.2,.62,1]});
  slots.forEach(s=>viewportObserver.observe(s));
  const near=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){load();near.disconnect();}},{rootMargin:'350px'});near.observe(box);
  toggle.addEventListener('click',()=>wanted?stop('일시정지 · 준비되면 이어서 재생하세요.',true):play(true));
  replay.addEventListener('click',()=>play(true,true));
  videos.forEach((v,i)=>{
    v.addEventListener('playing',()=>{v.parentElement.querySelector('.compare-ready-frame').hidden=true;});
    v.addEventListener('ended',()=>{box.querySelector(`[data-end="${i?'after':'before'}"]`).hidden=false;if(finished()){wanted=false;ui('');}else ui(i===1?'배너노드 녹화본 완료 · 기존 방식은 계속 재생됩니다.':'기존 방식 녹화본 완료 · 배너노드는 계속 재생됩니다.');});
    v.addEventListener('pause',()=>{if(wanted&&v.paused&&!v.ended&&!buffering)stop('일시정지 · 준비되면 이어서 재생하세요.',true);});
    v.addEventListener('play',()=>{if(!wanted)play(true);});
    v.addEventListener('waiting',()=>{if(wanted){buffering=true;videos.forEach(other=>other.pause());ui('녹화본을 불러오는 중입니다.');}});
    v.addEventListener('canplay',()=>{if(buffering&&wanted&&videos.every(x=>x.readyState>=3||x.ended))play(false);});
    v.addEventListener('error',()=>{autoBlocked=true;stop('녹화본을 불러오지 못했습니다. 페이지를 새로고침해 주세요.');});
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop('탭을 벗어나 잠시 멈췄습니다.');else schedule();});
  reduced.addEventListener('change',()=>{if(reduced.matches)stop('함께 재생을 눌러 두 녹화본을 확인하세요.',true);});
  if(!autoAllowed())ui('Ready · 함께 재생을 눌러 두 녹화본을 확인하세요.');
})();

