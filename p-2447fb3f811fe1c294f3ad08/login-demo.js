(() => {
  const q=s=>document.querySelector(s),password='aicompetition2026';
  const guide=new URLSearchParams(location.search).get('mode')==='guide';
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  let time=0,last=0;
  const cursor=q('#demo-cursor');
  function point(el){const r=el.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}
  function draw(t){
    const open=t>=1.15;q('.card').classList.toggle('jg-open',open&&!guide);q('#jr').classList.toggle('on',open);
    q('#jc').value=t<2.1?'':password;
    q('#jc').classList.toggle('demo-focus',t>=1.8&&t<2.85);q('#jb').classList.toggle('demo-press',t>=2.85&&t<3.07);
    q('#mw').classList.toggle('on',guide?t>=2.85:open);q('#m').textContent=t>=3.45?'입장 완료':t>=2.85?'확인 중…':guide||!open?'':'공유받은 패스워드를 입력하세요.';
    const a=point(q('#jt')),b=point(q('#jc')),c=point(q('#jb'));
    const route=[[0,a[0]+90,a[1]+45],[.85,...a],[1.4,...a],[1.8,...b],[2.35,...b],[2.8,...c],[5.3,...c]];
    let p=route.at(-1).slice(1);for(let i=1;i<route.length;i++)if(t<route[i][0]){let k=Math.max(0,(t-route[i-1][0])/(route[i][0]-route[i-1][0]));k=1-Math.pow(1-k,3);p=route[i-1].slice(1).map((v,j)=>v+(route[i][j+1]-v)*k);break;}
    cursor.style.left=p[0]-7+'px';cursor.style.top=p[1]-3+'px';cursor.style.opacity=reduced?0:1;
    cursor.innerHTML=t>=1.7&&t<2.4?'<path d="M8 3h8M12 3v18M8 21h8" fill="none" stroke="white" stroke-width="2"/>':'<path d="M9 12V4a1.5 1.5 0 0 1 3 0v6l5 1c1 .3 2 1 2 3v3c0 3-2 5-5 5h-2c-2 0-3-1-4-2l-4-5c-1-2 1-3 2-2l3 2z" fill="white" stroke="#080a0e" stroke-width="1.2"/>';
    document.body.dataset.time=t.toFixed(2);
  }
  function tick(ts){if(!document.hidden){time+=last?Math.min((ts-last)/1000,.08):0;draw(time%5.3);}last=ts;requestAnimationFrame(tick);}
  // This is a scripted demonstration: do not send credentials or start OAuth.
  document.querySelectorAll('button,a,input').forEach(el=>el.tabIndex=-1);
  document.body.style.pointerEvents='none';
  // Font swaps change the card and button sizes. Prepare the actual first frame
  // while hidden, then reveal it and start the clock after layout has settled.
  async function start(){
    draw(reduced?4:0);
    await document.fonts.ready;
    await new Promise(requestAnimationFrame);
    draw(reduced?4:0);
    document.body.dataset.ready='true';
    if(!reduced)requestAnimationFrame(tick);
  }
  start();
})();
