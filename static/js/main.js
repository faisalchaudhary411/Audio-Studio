// ===== VoxCraft main.js =====

// ---- Hero waveform (JS-driven, looks like a live audio waveform) ----
// The old version relied purely on a CSS @keyframes loop. That loop gets
// killed outright by `prefers-reduced-motion: reduce`, which a lot of
// phones ship with turned on by default (battery savers, some Android
// skins) — so the bars just sat there static with zero fallback. This
// drives the bars from rAF instead: layered sine waves per bar (different
// speed + phase so bars don't move in lockstep) plus a little random
// jitter and occasional "transient" spikes, which reads much more like a
// real audio meter than a uniform pulse. It also pauses when the tab is
// hidden to avoid burning battery in the background.
function initWave(){
  const wave = document.querySelector('.wave');
  if(!wave) return;
  const container = wave.querySelector('.wave-container');
  const bars = container ? Array.from(container.querySelectorAll('.wave-bar')) : [];

  // Entrance animation for the whole waveform block.
  wave.style.opacity = '0';
  wave.style.transform = 'translateY(12px)';
  wave.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      wave.style.opacity = '1';
      wave.style.transform = 'translateY(0)';
    });
  });

  if(!bars.length) return;

  const reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Kill the CSS keyframe loop per-bar so our inline transform actually
  // takes effect (a running CSS animation otherwise wins over inline
  // styles for the same property).
  bars.forEach(bar => { bar.style.animation = 'none'; });

  // Per-bar randomized "voice", so the wave never looks like it's just
  // repeating the same loop.
  const bar_state = bars.map((bar, i) => ({
    bar,
    freq1: 0.6 + Math.random() * 0.9,
    freq2: 1.3 + Math.random() * 1.6,
    phase1: Math.random() * Math.PI * 2,
    phase2: Math.random() * Math.PI * 2,
    // spread base phase across the row so it reads left-to-right like a
    // traveling wave instead of every bar breathing in sync
    travel: i * 0.18,
    nextSpike: Math.random() * 3,
    spikeUntil: 0
  }));

  let playing = wave.classList.contains('is-playing');
  const mo = new MutationObserver(() => {
    playing = wave.classList.contains('is-playing');
  });
  mo.observe(wave, { attributes: true, attributeFilter: ['class'] });

  const amplitude = reduceMotion ? 0.08 : 0.5;   // how far bars swing
  const floor = reduceMotion ? 0.92 : 0.35;      // minimum scale
  const speedMul = () => (playing ? 2.4 : 1);

  let rafId = null;
  let running = true;
  let lastFrame = 0;
  const frameInterval = 1000 / 30; // cap at ~30fps, plenty smooth, easy on battery

  function tick(now){
    if(!running) return;
    rafId = requestAnimationFrame(tick);
    if(now - lastFrame < frameInterval) return;
    lastFrame = now;
    const t = now / 1000;

    bar_state.forEach(s => {
      const speed = speedMul();
      let v = Math.sin((t - s.travel) * s.freq1 * speed + s.phase1) * 0.6
            + Math.sin((t - s.travel) * s.freq2 * speed + s.phase2) * 0.4;
      v = (v + 1) / 2; // normalize 0..1

      // Occasional transient "hit" so it doesn't look perfectly periodic —
      // real audio has irregular peaks, not a clean sine wave.
      if(!reduceMotion){
        if(t > s.spikeUntil && t > s.nextSpike){
          s.spikeUntil = t + 0.12 + Math.random() * 0.1;
          s.nextSpike = t + 1.5 + Math.random() * 3;
          s.spikeBoost = 0.3 + Math.random() * 0.3;
        }
        if(t < s.spikeUntil){
          v = Math.min(1, v + (s.spikeBoost || 0));
        }
      }

      const scale = floor + v * amplitude;
      s.bar.style.transform = `scaleY(${scale.toFixed(3)})`;
    });
  }

  rafId = requestAnimationFrame(tick);

  document.addEventListener('visibilitychange', () => {
    if(document.hidden){
      running = false;
      if(rafId) cancelAnimationFrame(rafId);
    } else if(!running){
      running = true;
      lastFrame = 0;
      rafId = requestAnimationFrame(tick);
    }
  });
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
      }

      if(!audio){
        audio = new Audio(src);
        audio.addEventListener('ended', () => btn.classList.remove('is-playing'));
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
      audio.play().catch(() => {});
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