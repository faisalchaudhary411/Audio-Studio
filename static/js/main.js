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
    freq1: 1.8 + Math.random() * 1.4,
    freq2: 3.2 + Math.random() * 2.4,
    phase1: Math.random() * Math.PI * 2,
    phase2: Math.random() * Math.PI * 2,
    // spread base phase across the row so it reads left-to-right like a
    // traveling wave instead of every bar breathing in sync
    travel: i * 0.08,
    nextSpike: Math.random() * 3,
    spikeUntil: 0
  }));

  let playing = wave.classList.contains('is-playing');
  const mo = new MutationObserver(() => {
    playing = wave.classList.contains('is-playing');
  });
  mo.observe(wave, { attributes: true, attributeFilter: ['class'] });

  const amplitude = reduceMotion ? 0.08 : 0.55;   // how far bars swing
  const floor = reduceMotion ? 0.92 : 0.3;      // minimum scale
  const speedMul = () => (playing ? 1.4 : 1);   // small extra boost if .is-playing is ever toggled

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

// ---- Custom select (replaces native open-dropdown UI on .studio-select) ----
// See the .custom-select CSS block for why this exists: a native <select>'s
// closed state can be themed, but the open list is OS-rendered (Android's
// full-screen picker, etc.) and CSS can't touch it at all. This wraps every
// .studio-select found on the page in a small in-page panel instead. The
// original <select> stays in the DOM as the real data model — its value and
// change events work completely unchanged, so no other script needs to
// know this happened.
function enhanceSelect(select) {
  if (!select || select.dataset.customSelectEnhanced) return;
  select.dataset.customSelectEnhanced = '1';

  const wrap = document.createElement('div');
  wrap.className = 'custom-select';
  select.parentNode.insertBefore(wrap, select);
  wrap.appendChild(select);
  select.classList.add('custom-select__native');
  select.setAttribute('tabindex', '-1');
  select.setAttribute('aria-hidden', 'true');

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'custom-select__trigger studio-select';
  trigger.setAttribute('aria-haspopup', 'listbox');
  trigger.setAttribute('aria-expanded', 'false');
  trigger.innerHTML = '<span class="custom-select__label"></span>' +
    '<svg class="custom-select__chevron" viewBox="0 0 12 8" fill="none"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  wrap.appendChild(trigger);
  const label = trigger.querySelector('.custom-select__label');

  const panel = document.createElement('div');
  panel.className = 'custom-select__panel';
  panel.setAttribute('role', 'listbox');
  wrap.appendChild(panel);

  function syncTrigger() {
    const opt = select.options[select.selectedIndex];
    label.textContent = opt ? opt.textContent : (select.getAttribute('aria-label') || 'Select…');
    trigger.disabled = !!select.disabled;
  }

  function buildOptionRow(opt) {
    const row = document.createElement('div');
    row.className = 'custom-select__option' + (opt.selected ? ' is-selected' : '');
    row.setAttribute('role', 'option');
    row.dataset.value = opt.value;
    const dot = document.createElement('span');
    dot.className = 'custom-select__dot';
    const text = document.createElement('span');
    text.textContent = opt.textContent;
    row.appendChild(dot);
    row.appendChild(text);
    row.addEventListener('click', () => {
      if (select.value !== opt.value) {
        select.value = opt.value;
        select.dispatchEvent(new Event('change', { bubbles: true }));
      }
      syncTrigger();
      closePanel();
    });
    return row;
  }

  function buildPanel() {
    panel.innerHTML = '';
    Array.from(select.children).forEach((child) => {
      if (child.tagName === 'OPTGROUP') {
        const groupLabel = document.createElement('div');
        groupLabel.className = 'custom-select__group-label';
        groupLabel.textContent = child.label;
        panel.appendChild(groupLabel);
        Array.from(child.children).forEach((opt) => panel.appendChild(buildOptionRow(opt)));
      } else if (child.tagName === 'OPTION') {
        panel.appendChild(buildOptionRow(child));
      }
    });
  }

  function onDocClick(e) {
    if (!wrap.contains(e.target)) closePanel();
  }
  function onKeydown(e) {
    if (e.key === 'Escape') { closePanel(); trigger.focus(); }
  }

  function openPanel() {
    if (select.disabled) return;
    buildPanel();
    panel.classList.add('is-open');
    trigger.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onKeydown);
  }
  function closePanel() {
    panel.classList.remove('is-open');
    trigger.classList.remove('is-open');
    trigger.setAttribute('aria-expanded', 'false');
    document.removeEventListener('click', onDocClick, true);
    document.removeEventListener('keydown', onKeydown);
  }

  trigger.addEventListener('click', () => {
    if (panel.classList.contains('is-open')) closePanel(); else openPanel();
  });

  // Keeps the trigger's label correct whenever anything else changes the
  // select programmatically — studio.js populating voices after a fetch,
  // clone_music.js rebuilding options on refreshSavedVoices(), setting
  // .value directly, etc. — none of that code needs to know this wrapper
  // exists.
  select.addEventListener('change', syncTrigger);
  new MutationObserver(syncTrigger).observe(select, { childList: true, subtree: true, attributes: true });

  syncTrigger();
}

function enhanceAllSelects() {
  document.querySelectorAll('.studio-select').forEach((el) => {
    // Native <select> only — skip if somehow already a non-select node,
    // and never touch anything under /admin (admin keeps native selects).
    if (el.tagName === 'SELECT') enhanceSelect(el);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // Admin pages don't currently use .studio-select at all, but this guard
  // keeps it that way explicitly — user-facing redesign only, per request.
  if (!location.pathname.startsWith('/admin')) enhanceAllSelects();
  initWave();
  initStudio();
  initNavToggle();
  initNavMore();
  initVoicePreviews();
  initStickyCta();
  initBillingToggle();
  initPermissionsSheet();
});