// ===== VoxCraft main.js =====

// ---- Hero waveform (organic VoxCraft voice signal) ----
function initWave(){
  const svg = document.querySelector('.wave');
  if(!svg) return;

  const NS = 'http://www.w3.org/2000/svg';
  const W = 1000, H = 124, CY = H / 2;
  const count = 58;
  const step = W / count;
  const barW = Math.max(7, step * 0.42);
  const bars = [];

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.innerHTML = `
    <defs>
      <linearGradient id="voxWaveGradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#f3b33f"/>
        <stop offset="46%" stop-color="#e9a93d"/>
        <stop offset="72%" stop-color="#62b9ad"/>
        <stop offset="100%" stop-color="#48aaa3"/>
      </linearGradient>
      <filter id="voxWaveBlur" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="5"/>
      </filter>
    </defs>
    <path class="wave-track" d="M0 ${CY} H${W}"/>
    <path class="wave-glow" d="M0 ${CY} H${W}"/>
    <g class="wave-bars"></g>
    <rect class="wave-sweep" x="0" y="${CY-42}" width="3" height="84" rx="1.5"/>
  `;

  const group = svg.querySelector('.wave-bars');
  const sweep = svg.querySelector('.wave-sweep');

  // A handcrafted envelope: quiet edges, four natural speech clusters,
  // and a small breathing valley in the middle.
  const envelope = Array.from({length:count}, (_, i) => {
    const x = i / (count - 1);
    const peaks = [
      [0.12, .92, .075],
      [0.31, .70, .085],
      [0.53, .84, .095],
      [0.73, .62, .085],
      [0.89, .90, .075]
    ];
    let v = .13;
    for(const [p,a,s] of peaks) v += a * Math.exp(-Math.pow((x-p)/s,2));
    return Math.min(1, v);
  });

  for(let i=0;i<count;i++){
    const rect = document.createElementNS(NS,'rect');
    rect.classList.add('wave-bar');
    rect.setAttribute('x', (i*step + (step-barW)/2).toFixed(2));
    rect.setAttribute('width', barW.toFixed(2));
    rect.setAttribute('rx', (barW/2).toFixed(2));
    rect.setAttribute('y', CY);
    rect.setAttribute('height', 4);
    group.appendChild(rect);
    bars.push(rect);
  }

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let t = 0;
  let playing = false;
  let raf = 0;
  let visible = true;

  function draw(){
    t += playing ? .055 : .032;
    bars.forEach((bar,i)=>{
      const x = i/(count-1);
      const speech = .5 + .5*Math.sin(t*1.8 + i*.48);
      const texture = .5 + .5*Math.sin(t*3.7 - i*.93 + Math.sin(t*.7)*.5);
      const travelling = .5 + .5*Math.sin(t*.72 - i*.18);
      const energy = playing ? (0.82 + .18*speech) : (0.88 + .12*speech);
      const h = 4 + envelope[i] * (H*.83) * (.55 + .28*speech + .12*texture) * energy * (.88 + .12*travelling);
      const y = CY - h/2;
      bar.setAttribute('y', y.toFixed(2));
      bar.setAttribute('height', h.toFixed(2));
      bar.style.opacity = (0.62 + envelope[i]*.34).toFixed(2);
    });

    const sweepX = ((t*92) % (W+160)) - 80;
    sweep.setAttribute('x', sweepX.toFixed(1));
    sweep.style.opacity = playing ? '.72' : '.18';

    if(!reduced && visible) raf = requestAnimationFrame(draw);
  }

  const io = 'IntersectionObserver' in window ? new IntersectionObserver(entries=>{
    visible = entries[0].isIntersecting;
    if(visible && !reduced && !raf) raf=requestAnimationFrame(draw);
    if(!visible && raf){ cancelAnimationFrame(raf); raf=0; }
  }, {threshold:.05}) : null;
  if(io) io.observe(svg);

  svg._setPlaying = value => {
    playing = !!value;
    svg.classList.toggle('is-playing', playing);
  };
  draw();

  window.addEventListener('beforeunload', ()=>{ if(raf) cancelAnimationFrame(raf); }, {once:true});
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

      const wave = document.querySelector('.wave');
      if(currentAudio && currentBtn === btn && !currentAudio.paused){
        currentAudio.pause();
        btn.classList.remove('is-playing');
        if(wave && wave._setPlaying) wave._setPlaying(false);
        return;
      }
      if(currentAudio && currentBtn !== btn){
        currentAudio.pause();
        currentBtn.classList.remove('is-playing');
        if(wave && wave._setPlaying) wave._setPlaying(false);
      }

      if(!audio){
        audio = new Audio(src);
        audio.addEventListener('ended', () => {
          btn.classList.remove('is-playing');
          if(wave && wave._setPlaying) wave._setPlaying(false);
        });
        audio.addEventListener('error', () => {
          btn.disabled = true;
          btn.title = 'Preview coming soon';
          btn.style.opacity = '0.35';
          btn.style.cursor = 'not-allowed';
          if(wave && wave._setPlaying) wave._setPlaying(false);
        });
      }
      currentAudio = audio;
      currentBtn = btn;
      audio.currentTime = 0;
      audio.play().catch(() => {});
      btn.classList.add('is-playing');
      if(wave && wave._setPlaying) wave._setPlaying(true);
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