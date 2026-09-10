/* Native card geometry and motion values from ad.archive. No media/API requests. */
(() => {
  const scene=document.querySelector('#scene'),library=document.querySelector('.library');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const arrow=document.createElement('div');arrow.id='card-follow';arrow.setAttribute('aria-hidden','true');
  arrow.innerHTML='<svg viewBox="0 0 100 100" fill="currentColor"><path d="M58.5 20 L43 20 L67 44.5 L12 44.5 L12 55.5 L67 55.5 L43 80 L58.5 80 L88 50 Z"/></svg>';
  const dot=document.createElement('span');dot.id='card-dot';scene.append(arrow,dot);
  class Spring {
    constructor(x=0,k=300,c=30){this.x=x;this.v=0;this.t=x;this.k=k;this.c=c;}
    step(dt){const n=Math.max(1,Math.ceil(dt/.008)),h=dt/n;for(let i=0;i<n;i++){this.v+=(-this.k*(this.x-this.t)-this.c*this.v)*h;this.x+=this.v*h;}return this.x;}
    jump(x){this.x=this.t=x;this.v=0;}
    get moving(){return Math.abs(this.x-this.t)>.001||Math.abs(this.v)>.01;}
  }
  const states=new Map(),fx=new Spring(0,1600,50),fy=new Spring(0,1600,50),blend=new Spring(0,600,50);
  let automatic=null,manual=null,active=null,raf=0,last=0,initialized=false,instant=false;
  function rect(el){const r=el.getBoundingClientRect(),s=scene.getBoundingClientRect(),k=s.width/1440;return {x:(r.x-s.x)/k,y:(r.y-s.y)/k,w:r.width/k,h:r.height/k};}
  function size(){const grid=document.querySelector('#cards');grid.style.setProperty('--card-size',`${(grid.clientWidth-36)/4}px`);}
  new ResizeObserver(size).observe(library);size();
  function kick(){if(!raf)raf=requestAnimationFrame(frame);}
  function frame(now){
    raf=0;const dt=last?Math.min(.04,(now-last)/1000):1/60;last=now;
    const p=manual||automatic,visible=p&&!document.hidden&&document.querySelector('#player').hidden&&document.querySelector('#fpicker').hidden;
    const clip=rect(library);
    active=visible&&p.x>=clip.x&&p.x<=clip.x+clip.w&&p.y>=clip.y&&p.y<=clip.y+clip.h?[...library.querySelectorAll('.card')].find(c=>{const b=rect(c);return p.x>=b.x&&p.x<=b.x+b.w&&p.y>=b.y&&p.y<=b.y+b.h}):null;
    if(active&&!states.has(active))states.set(active,{rx:new Spring(),ry:new Spring(),z:new Spring(),b:new Spring(),rawX:0,rawY:0});
    let moving=false;
    for(const [card,st] of states){
      if(!card.isConnected){states.delete(card);continue;}
      const on=card===active,r=rect(card),pull=card.classList.contains('big')?.0125:.025;
      card.classList.toggle('card-hover',on);card.style.zIndex=on?'5':'';
      st.rx.t=on&&!reduced.matches?3*(.5-(p.y-r.y)/r.h):0;
      st.ry.t=on&&!reduced.matches?3*((p.x-r.x)/r.w-.5):0;
      st.z.t=on&&!reduced.matches?-10:0;st.b.t=on&&!reduced.matches?1:0;
      if(on){st.rawX=pull*(p.x-r.x-r.w/2);st.rawY=pull*(p.y-r.y-r.h/2);}
      for(const spring of [st.rx,st.ry,st.z,st.b]){if(instant||reduced.matches)spring.jump(spring.t);else spring.step(dt);moving ||=spring.moving;}
      const mx=st.rawX*Math.max(0,st.b.x),my=st.rawY*Math.max(0,st.b.x),box=card.querySelector('.tilt-box');
      box.style.transform=`perspective(500px) translate3d(${mx}px,${my}px,${st.z.x}px) rotateX(${st.rx.x}deg) rotateY(${st.ry.x}deg)`;
      card.querySelector('.card-overlay').style.transform=`translate(${mx*.5}px,${my*.5}px)`;
      if(!on&&![st.rx,st.ry,st.z,st.b].some(s=>s.moving)){box.style.transform='';card.querySelector('.card-overlay').style.transform='';states.delete(card);}
    }
    scene.classList.toggle('card-pointing',!!active);scene.classList.toggle('real-card-pointer',!!manual&&!!active);
    arrow.classList.toggle('on',!!active);dot.classList.toggle('on',!!active);
    if(active){
      const b=rect(active),cx=b.x+b.w/2,cy=b.y+b.h/2;
      if(!initialized){fx.jump(p.x);fy.jump(p.y);initialized=true;}
      fx.t=p.x;fy.t=p.y;blend.t=.4;
      if(instant||reduced.matches){fx.jump(p.x);fy.jump(p.y);blend.jump(.4);}else{fx.step(dt);fy.step(dt);blend.step(dt);}
      arrow.style.transform=`translate(${fx.x+(cx-fx.x)*blend.x-40}px,${fy.x+(cy-fy.x)*blend.x-40}px)`;
      dot.style.transform=`translate(${p.x+(cx-p.x)*.1-5}px,${p.y+(cy-p.y)*.1-5}px)`;
      moving ||=fx.moving||fy.moving||blend.moving;
    }else{initialized=false;blend.jump(0);}
    instant=false;
    if(moving)kick();else last=0;
  }
  library.addEventListener('pointermove',e=>{
    if(e.pointerType==='touch')return;const s=scene.getBoundingClientRect(),k=s.width/1440;
    manual={x:(e.clientX-s.x)/k,y:(e.clientY-s.y)/k};kick();
  });
  library.addEventListener('pointerleave',()=>{manual=null;kick();});
  library.addEventListener('scroll',kick,{passive:true});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)manual=null;kick();});
  window.ARCHIVE_CARDS={size,update(p,still=false){automatic=p;instant=still;kick();}};
})();
