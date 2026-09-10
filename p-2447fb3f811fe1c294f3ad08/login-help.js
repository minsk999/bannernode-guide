(() => {
  const password='aicompetition2026';
  document.querySelectorAll('[data-copy-password]').forEach(button=>{
    const group=button.closest('.ar-access')||button.closest('article');
    const output=group.querySelector('.password-copy-status');
    const label=group.querySelector('.ar-password-note .password-label-current')||button.querySelector('.password-label-current');
    const originalLabel=label.textContent;
    const icon=button.querySelector('svg'),originalIcon=icon.innerHTML,originalStroke=icon.getAttribute('stroke-width');
    let reset,attempt=0;
    function restoreIcon(){icon.innerHTML=originalIcon;icon.setAttribute('stroke-width',originalStroke);}
    function restore(){restoreIcon();label.textContent=originalLabel;}
    button.addEventListener('click',async()=>{
      const current=++attempt;
      clearTimeout(reset);
      try {
        await navigator.clipboard.writeText(password);
        if(current!==attempt)return;
        icon.innerHTML='<path d="m5 12 4 4L19 6"/>';
        icon.setAttribute('stroke-width','2');
        label.textContent=button.classList.contains('password-copy-icon')?'패스워드를 복사했습니다.':'복사 완료';
        output.textContent='';
        reset=setTimeout(restore,1600);
      } catch {
        if(current!==attempt)return;
        restore();
        output.textContent='자동 복사가 제한되어 있습니다. 직접 복사해 주세요: '+password;
      }
    });
  });
  const dialog=document.createElement('dialog');dialog.id='login-help';dialog.setAttribute('aria-labelledby','login-help-title');
  dialog.innerHTML='<div class="help-top"><button class="help-close" aria-label="입장 안내 닫기"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div><iframe title="패스워드 펼치기·입력·입장 시연"></iframe><div class="help-bottom"><h2 id="login-help-title">패스워드로 입장하기</h2><div class="help-password"><button id="help-secret" aria-label="패스워드 표시하고 복사">•••••••••••••••••</button><button id="help-copy" aria-label="패스워드 복사"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/></svg></button></div><p class="help-status" role="status"></p><button class="help-replay">입장 방법 다시 보기</button><a class="help-destination" target="_blank" rel="noopener"></a></div>';
  document.body.append(dialog);let opener=null,mode='app',copyTimer;
  const frame=dialog.querySelector('iframe'),status=dialog.querySelector('.help-status'),secret=dialog.querySelector('#help-secret');
  function replay(){frame.src='login-demo.html?mode='+mode+'&replay='+Date.now();}
  const copyButton=dialog.querySelector('#help-copy'),copyIcon=copyButton.innerHTML,destination=dialog.querySelector('.help-destination');
  function open(link){clearTimeout(copyTimer);copyButton.innerHTML=copyIcon;destination.href=link.href;destination.textContent=link.href.includes('github.com/')?(link.href.includes('Windows')?'Windows 다운로드':link.href.includes('arm64')?'macOS Apple 실리콘 다운로드':'macOS Intel CPU 다운로드'):'사용 설명서로 이동';opener=link;mode=link.href.includes('bannernode-guide/')&&!link.href.includes('github.com/')?'guide':'app';secret.textContent='•••••••••••••••••';status.textContent='패스워드를 눌러 복사한 뒤 로그인 화면에 붙여넣으세요.';replay();if(!dialog.open)dialog.showModal();}
  document.addEventListener('click',e=>{
    const a=e.target.closest('a[href]');if(!a||dialog.contains(a)||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
    const url=new URL(a.href),guide=url.hostname==='minsk999.github.io'&&/^\/bannernode-guide\/(?:index\.html)?$/.test(url.pathname),download=url.hostname==='github.com'&&/BannerNode-(Windows|macOS-[^/]+)\.zip$/.test(url.pathname);
    if(!guide&&!download)return;
    // Show instructions first; only the dialog destination follows the external link.
    e.preventDefault();open(a);
  });
  async function copy(){secret.textContent=password;try{await navigator.clipboard.writeText(password);clearTimeout(copyTimer);copyButton.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 4 4L19 6"/></svg>';copyTimer=setTimeout(()=>{copyButton.innerHTML=copyIcon;},1600);status.textContent='복사했습니다. 패스워드 입력란에 붙여넣으세요.';}catch{status.textContent='자동 복사가 제한됐습니다. 표시된 패스워드를 선택해 복사하세요.';}}
  secret.onclick=copy;dialog.querySelector('#help-copy').onclick=copy;dialog.querySelector('.help-replay').onclick=replay;
  dialog.querySelector('.help-close').onclick=()=>dialog.close();
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  dialog.addEventListener('close',()=>{clearTimeout(copyTimer);frame.src='about:blank';secret.textContent='•••••••••••••••••';opener?.focus();});
})();
