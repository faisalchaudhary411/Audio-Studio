// ===== VoxCraft main.js =====

// ---- Hero waveform (organic idle motion + audio-reactive preview) ----
function initWave(){
  const wrap=document.querySelector('.hero-wave'), svg=document.querySelector('.wave');
  if(!wrap||!svg)return;
  const barsLayer=svg.querySelector('.wave-bars'), coreLayer=svg.querySelector('.wave-core');
  const NS='http://www.w3.org/2000/svg',count=72,W=1000,H=140,center=70,gap=6,barW=(W-gap*(count-1))/count;
  const bars=[],cores=[];
  for(let i=0;i<count;i++){
    const x=i*(barW+gap);
    for(const [layer,list,cls] of [[barsLayer,bars,'wave-bar'],[coreLayer,cores,'wave-core-bar']]){
      const r=document.createElementNS(NS,'rect');r.setAttribute('class',cls);r.setAttribute('x',x.toFixed(2));r.setAttribute('width',barW.toFixed(2));r.setAttribute('rx',Math.min(barW/2,2.5));layer.appendChild(r);list.push(r);}
  }
  const envelope=x=>{const peaks=[[.08,.38,.07],[.17,.78,.065],[.27,.48,.07],[.37,.95,.075],[.49,.55,.065],[.59,.88,.07],[.70,.48,.06],[.79,.78,.07],[.91,.52,.075]];let v=.08;for(const [p,a,w] of peaks)v+=a*Math.exp(-((x-p)/w)**2);return Math.min(1,v);};
  let analyser=null,data=null;
  window.__voxWave={
    setAudio(audio){try{const C=window.AudioContext||window.webkitAudioContext;if(!C)throw 0;const ctx=window.__voxAudioContext||(window.__voxAudioContext=new C());if(!audio.__voxAnalyser){const src=ctx.createMediaElementSource(audio);analyser=ctx.createAnalyser();analyser.fftSize=128;analyser.smoothingTimeConstant=.8;data=new Uint8Array(analyser.frequencyBinCount);src.connect(analyser);analyser.connect(ctx.destination);audio.__voxAnalyser=analyser;}else{analyser=audio.__voxAnalyser;data=new Uint8Array(analyser.frequencyBinCount);}if(ctx.state==='suspended')ctx.resume();}catch(e){}wrap.classList.add('is-playing');},
    stop(){wrap.classList.remove('is-playing');}
  };
  function frame(now){
    const t=now*.001;if(analyser&&data)analyser.getByteFrequencyData(data);
    for(let i=0;i<count;i++){const x=i/(count-1),env=envelope(x),a=.5+.5*Math.sin(t*2.2+i*.42),b=.5+.5*Math.sin(t*.91-i*.18),c=.5+.5*Math.sin(t*3.7+i*.73);let audio=0;if(data)audio=data[Math.min(data.length-1,Math.floor(x*data.length))]/255;const amp=Math.max(.06,env*(.48+.28*a+.16*b+.08*c+audio*.95));const h=8+amp*112;bars[i].setAttribute('y',(center-h/2).toFixed(1));bars[i].setAttribute('height',h.toFixed(1));const ch=Math.max(4,h*.22);cores[i].setAttribute('y',(center-ch/2).toFixed(1));cores[i].setAttribute('height',ch.toFixed(1));}
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// ---- Studio: voice picker + character counter + mock generate ----
function initStudio(){
  const textarea = document.querySelector('.script-input');
  const charCount = document.querySelector('[data-char-count]');
  const durationEst = document.querySelector('[data-duration-est]');
  const voicePicks = document.querySelectorAll('.voice-pick');
  const generateBtn = document.querySelector('[data-generate]');
  const status = document.querySelector('[data-render-status]');
  if(!textarea || !generateBtn) return;

  let selectedVoice = voicePicks.length ? voicePicks[0].dataset.voiceId : null;

  voicePicks.forEach(pick => {
    pick.addEventListener('click', () => {
      voicePicks.forEach(p => p.classList.remove('is-active'));
      pick.classList.add('is-active');
      selectedVoice = pick.dataset.voiceId;
    });
  });

  function updateMeta(){
    const len = textarea.value.length;
    const words = textarea.value.trim().split(/\s+/).filter(Boolean).length;
    if(charCount) charCount.textContent = `${len} chars`;
    if(durationEst) durationEst.textContent = `\~${(words/2.5).toFixed(1)}s`;
  }
  textarea.addEventListener('input', updateMeta);
  updateMeta();

  generateBtn.addEventListener('click', async () => {
    if(!textarea.value.trim()){
      status.textContent = 'Write something first.';
      return;
    }
    generateBtn.disabled = true;
    status.textContent = 'Rendering…';
    try{
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ text: textarea.value, voice_id: selectedVoice })
      });
      const data = await res.json();
      if(!res.ok){
        status.textContent = data.error || 'Something went wrong.';
      } else {
        status.textContent = `Done — est. ${data.duration_sec}s of audio.`;
      }
    } catch(e){
      status.textContent = 'Network error — check your connection.';
    } finally {
      generateBtn.disabled = false;
    }
  });
}

// ---- Mobile nav hamburger ----
function initNavToggle(){
  const btn = document.getElementById('nav-hamburger');
  const links = document.getElementById('nav-links');
  if(!btn || !links) return;
  btn.addEventListener('click', () => {
    const open = links.classList.toggle('is-open');
    btn.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      links.classList.remove('is-open');
      btn.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
    });
  });
}

// ---- Voice preview play/pause ----
function initVoicePreviews(){
  const buttons = document.querySelectorAll('.voice-card__play[data-audio]');
  if(!buttons.length) return;
  let currentAudio = null;
  let currentBtn = null;

  buttons.forEach(btn => {
    const src = btn.getAttribute('data-audio');
    let audio = null;

    btn.addEventListener('click', () => {
      if(btn.disabled) return;

      if(currentAudio && currentBtn === btn && !currentAudio.paused){
        currentAudio.pause();
        btn.classList.remove('is-playing');
        return;
      }
      if(currentAudio && currentBtn !== btn){
        currentAudio.pause();
        currentBtn.classList.remove('is-playing');
        window.__voxWave?.stop();
      }

      if(!audio){
        audio = new Audio(src);
        audio.addEventListener('ended', () => { btn.classList.remove('is-playing'); window.__voxWave?.stop(); });
        audio.addEventListener('error', () => {
          btn.disabled = true;
          btn.title = 'Preview coming soon';
          btn.style.opacity = '0.35';
          btn.style.cursor = 'not-allowed';
        });
      }
      currentAudio = audio;
      currentBtn = btn;
      audio.currentTime = 0;
      audio.play().then(() => { window.__voxWave?.setAudio(audio); }).catch(() => {});
      btn.classList.add('is-playing');
    });
  });
}

// ---- "More" dropdown in desktop nav ----
function initNavMore(){
  const wrap = document.getElementById('nav-more');
  const btn = document.getElementById('nav-more-btn');
  if(!wrap || !btn) return;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = wrap.classList.toggle('is-open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('click', () => {
    wrap.classList.remove('is-open');
    btn.setAttribute('aria-expanded', 'false');
  });
  wrap.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      wrap.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
    });
  });
}

// ---- Sticky mobile CTA after scrolling past hero ----
function initStickyCta(){
  const bar = document.getElementById('sticky-cta');
  if(!bar) return;
  if(!document.querySelector('.hero')) return;
  bar.hidden = false;
  const onScroll = () => {
    const show = window.scrollY > 420;
    bar.classList.toggle('is-visible', show);
    document.body.classList.toggle('has-sticky-cta', show);
  };
  window.addEventListener('scroll', onScroll, {passive: true});
  onScroll();
}

// ---- Pricing monthly / annual display toggle ----
function initBillingToggle(){
  const monthBtn = document.getElementById('bill-month');
  const yearBtn = document.getElementById('bill-year');
  if(!monthBtn || !yearBtn) return;

  // Rewrites each plan card's CTA link to carry the selected billing
  // period through to /upgrade (e.g. ?plan=pro&billing=annual), so
  // toggling this control actually changes what the customer checks
  // out for — previously it only changed the displayed price text and
  // the button still always linked to the monthly checkout regardless.
  function setLinkBilling(url, billing){
    try{
      const u = new URL(url, window.location.origin);
      u.searchParams.set('billing', billing);
      return u.pathname + u.search;
    }catch(e){ return url; }
  }

  const setAnnual = (on) => {
    document.body.classList.toggle('is-annual', on);
    monthBtn.classList.toggle('is-active', !on);
    yearBtn.classList.toggle('is-active', on);
    document.querySelectorAll('.plan__pkr-annual').forEach(el => {
      el.style.display = on ? 'block' : 'none';
    });
    document.querySelectorAll('.plan__pkr-month').forEach(el => {
      el.style.display = on ? 'none' : 'block';
    });
    document.querySelectorAll('.plan[data-plan] > a.btn[href]').forEach(link => {
      link.href = setLinkBilling(link.getAttribute('href'), on ? 'annual' : 'monthly');
    });
  };
  monthBtn.addEventListener('click', () => setAnnual(false));
  yearBtn.addEventListener('click', () => setAnnual(true));
}

// ---- First-visit optional permissions sheet ----
// Must NEVER trap the page: hide via hidden + display + class, always.
function initPermissionsSheet(){
  const sheet = document.getElementById('perm-sheet');
  if(!sheet) return;
  const KEY = 'voxcraft_perm_seen';

  function forceClose(){
    try { localStorage.setItem(KEY, '1'); } catch(e) {}
    sheet.hidden = true;
    sheet.setAttribute('hidden', '');
    sheet.style.display = 'none';
    sheet.classList.add('perm-sheet--closed');
    sheet.setAttribute('aria-hidden', 'true');
  }

  try {
    if(localStorage.getItem(KEY)){
      forceClose();
      return;
    }
  } catch(e) {
    forceClose();
    return;
  }

  sheet.hidden = false;
  sheet.style.display = '';
  sheet.classList.remove('perm-sheet--closed');

  const close = (allowNotif) => {
    forceClose();
    if(allowNotif && typeof Notification !== 'undefined' && Notification.permission === 'default'){
      setTimeout(() => {
        try { Notification.requestPermission(); } catch(e) {}
      }, 150);
    }
  };

  const allow = document.getElementById('perm-allow');
  const decline = document.getElementById('perm-decline');
  if(allow) allow.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); close(true); });
  if(decline) decline.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); close(false); });
  sheet.addEventListener('click', (e) => {
    if(e.target === sheet) close(false);
  });
  document.addEventListener('keydown', function onEsc(e){
    if(e.key === 'Escape' && !sheet.hidden){
      close(false);
      document.removeEventListener('keydown', onEsc);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initWave();
  initStudio();
  initNavToggle();
  initNavMore();
  initVoicePreviews();
  initStickyCta();
  initBillingToggle();
  initPermissionsSheet();
});