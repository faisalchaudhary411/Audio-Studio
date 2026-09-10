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

// ---- Optional permissions (non-blocking) ----
// Never trap the landing page. Never prompt during an active generation
// (mobile browsers can reload/navigate when the system permission dialog
// opens mid-request). Mic is still requested only inside the clone flow.
function initPermissionsSheet(){
  const sheet = document.getElementById('perm-sheet');
  if(sheet){
    sheet.hidden = true;
    sheet.setAttribute('hidden', '');
    sheet.style.display = 'none';
    sheet.classList.add('perm-sheet--closed');
    sheet.setAttribute('aria-hidden', 'true');
  }
  try { localStorage.setItem('voxcraft_perm_seen', '1'); } catch(e) {}

  const NOTIF_KEY = 'voxcraft_notif_asked';
  function softAskNotifications(){
    try {
      if(localStorage.getItem(NOTIF_KEY)) return;
      if(typeof Notification === 'undefined' || Notification.permission !== 'default') return;
      if(window.__voxGenerating) return; // never during generate
      const path = location.pathname || '';
      if(path === '/' || path === '') return;
      if(!path.startsWith('/studio') && !path.startsWith('/tools') && !path.startsWith('/voice')) return;
      // Don't stack over sticky generate bars on small screens
      if(window.matchMedia && window.matchMedia('(max-width:700px)').matches){
        // On mobile, only ask from Account or after explicit idle — skip auto.
        return;
      }
      localStorage.setItem(NOTIF_KEY, '1');
      const toast = document.createElement('div');
      toast.className = 'soft-perm-toast';
      toast.setAttribute('role', 'status');
      toast.innerHTML =
        '<span class="soft-perm-toast__text">Want occasional product updates?</span>' +
        '<button type="button" class="btn btn--brass btn--sm" data-soft-perm="yes">Enable</button>' +
        '<button type="button" class="btn btn--ghost btn--sm" data-soft-perm="no">Not now</button>';
      document.body.appendChild(toast);
      requestAnimationFrame(() => toast.classList.add('is-visible'));
      const dismiss = () => {
        toast.classList.remove('is-visible');
        setTimeout(() => { if(toast.parentNode) toast.remove(); }, 280);
      };
      toast.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-soft-perm]');
        if(!btn) return;
        if(btn.getAttribute('data-soft-perm') === 'yes'){
          // Defer so we are not mid-fetch when the OS dialog opens
          setTimeout(() => { try { Notification.requestPermission(); } catch(err) {} }, 400);
        }
        dismiss();
      });
      setTimeout(dismiss, 10000);
    } catch(e) {}
  }
  // Only after generate completed AND user is idle (8s), never on a timer alone.
  window.addEventListener('voxcraft:generated', () => {
    setTimeout(() => {
      if(!window.__voxGenerating) softAskNotifications();
    }, 8000);
  }, { once: true });
}

// Track in-flight generation so permission prompts never interrupt it.
window.__voxGenerating = false;
const _origSetBusy = typeof voxSetBusy === 'function' ? null : null;


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

// ---- Unified generate-button loading state (spinner + progress bar + status pulse) ----
// Every tool used to roll its own combination of these: some added the
// button spinner, some didn't; some had a progress bar, some didn't;
// almost none pulsed the status text. The HTML/CSS for all three pieces
// (.is-loading spinner, .gen-progress bar, .render-status pulse) already
// existed and was consistent — the JS files just weren't all using them.
// This is the one shared implementation; every tool script calls this
// instead of toggling classes by hand, so the animation can't drift
// between tools again.
function voxSetBusy(btn, on) {
  if (!btn) return;
  window.__voxGenerating = !!on;
  btn.disabled = !!on;
  btn.classList.toggle('is-loading', !!on);
  if (on) btn.classList.remove('is-success');
  const panel = btn.closest('.panel');
  if (panel) {
    panel.querySelectorAll('.render-status').forEach((s) => {
      s.classList.toggle('is-busy', !!on);
    });
  }
}

/** Brief success pulse on primary generate CTAs after a clean finish. */
function voxButtonSuccess(btn) {
  if (!btn) return;
  btn.classList.remove('is-loading');
  btn.classList.add('is-success');
  window.setTimeout(() => btn.classList.remove('is-success'), 650);
}

function voxShowProgress(bar, on) {
  if (!bar) return;
  bar.classList.toggle('is-active', !!on);
  bar.setAttribute('aria-hidden', on ? 'false' : 'true');
}



// ---- UTF-8 text downloads (Android/Windows need BOM or Blob) ----
// data:text/plain;charset=utf-8,... is often saved without encoding metadata
// on mobile, so Urdu/Hindi opens as mojibake. Blob + UTF-8 BOM fixes that.
function voxDownloadUtf8Text(filename, text, mime) {
  mime = mime || 'text/plain';
  const body = (text == null) ? '' : String(text);
  // UTF-8 BOM so Notepad / Android "Open as text" detect Unicode
  const bom = '\uFEFF';
  const blob = new Blob([bom + body], { type: mime + ';charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'download.txt';
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function voxBindUtf8DownloadButtons(root) {
  const scope = root || document;
  scope.querySelectorAll('[data-utf8-download]').forEach((btn) => {
    if (btn.dataset.utf8Bound === '1') return;
    btn.dataset.utf8Bound = '1';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const name = btn.getAttribute('data-filename') || 'download.txt';
      const mime = btn.getAttribute('data-mime') || 'text/plain';
      let text = btn.getAttribute('data-text');
      if (text == null || text === '') {
        const src = btn.getAttribute('data-text-from');
        if (src) {
          const el = document.querySelector(src);
          text = el ? (el.value != null ? el.value : el.textContent) : '';
        }
      }
      // Prefer text stored on the button via property (avoids HTML-attr length limits)
      if (btn._voxText != null) text = btn._voxText;
      voxDownloadUtf8Text(name, text || '', mime);
    });
  });
}

// ---- Cross-tool audio handoff ----
// sessionStorage is capped ~5MB and clone/music WAV base64 often exceeds it,
// so saves failed silently and "Send to …" arrived empty. We store the
// payload in IndexedDB (much larger) and only keep a tiny pointer in
// sessionStorage so destination pages know a transfer is waiting.
const VOX_TRANSFER_KEY = 'voxcraft_transfer_v1';
const VOX_TRANSFER_DB = 'voxcraft_transfer_db';
const VOX_TRANSFER_STORE = 'transfers';
const VOX_NEXT_TOOLS = [
  { slug: 'trim-cut-audio', label: 'Trim' },
  { slug: 'remove-background-noise', label: 'Denoise' },
  { slug: 'normalize-audio-volume', label: 'Normalize' },
  { slug: 'merge-audio-files', label: 'Merge' },
  { slug: 'convert-audio-format', label: 'Convert' },
  { slug: 'change-audio-speed', label: 'Speed' },
  { slug: 'fade-audio', label: 'Fade' },
];

function voxOpenTransferDB() {
  return new Promise((resolve, reject) => {
    try {
      const req = indexedDB.open(VOX_TRANSFER_DB, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(VOX_TRANSFER_STORE)) {
          db.createObjectStore(VOX_TRANSFER_STORE);
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('idb open failed'));
    } catch (e) {
      reject(e);
    }
  });
}

async function voxIdbPut(record) {
  const db = await voxOpenTransferDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(VOX_TRANSFER_STORE, 'readwrite');
    tx.objectStore(VOX_TRANSFER_STORE).put(record, 'current');
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error || new Error('idb put failed'));
  });
}

async function voxIdbGet() {
  const db = await voxOpenTransferDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(VOX_TRANSFER_STORE, 'readonly');
    const req = tx.objectStore(VOX_TRANSFER_STORE).get('current');
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error || new Error('idb get failed'));
  });
}

async function voxIdbClear() {
  try {
    const db = await voxOpenTransferDB();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(VOX_TRANSFER_STORE, 'readwrite');
      tx.objectStore(VOX_TRANSFER_STORE).delete('current');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (e) {}
}

// Last in-flight save so "Send to …" can await it before navigating
let _voxTransferSavePromise = null;

/** Save generated audio for cross-tool handoff. Returns true on success. */
function voxSaveTransfer(b64, filename, mime) {
  if (!b64) return false;
  const record = {
    b64: b64,
    filename: filename || 'audio.wav',
    mime: mime || 'audio/wav',
    ts: Date.now(),
  };
  // Pointer in sessionStorage (tiny) so other tabs/pages know to look in IDB
  try {
    sessionStorage.setItem(VOX_TRANSFER_KEY, JSON.stringify({
      has: true,
      filename: record.filename,
      mime: record.mime,
      ts: record.ts,
      bytes: Math.floor((b64.length * 3) / 4),
    }));
  } catch (e) {
    // even pointer failed — still try IDB
  }
  // Tiny files: also keep full payload in sessionStorage as sync fallback
  try {
    const full = JSON.stringify(record);
    if (full.length < 2 * 1024 * 1024) {
      sessionStorage.setItem(VOX_TRANSFER_KEY, full);
    }
  } catch (e) {}
  // Always write IndexedDB (handles large clone/music WAVs)
  _voxTransferSavePromise = voxIdbPut(record).catch((err) => {
    console.warn('[voxcraft] transfer IDB save failed', err);
    return false;
  });
  return true;
}

function voxWaitForTransferSave() {
  return _voxTransferSavePromise || Promise.resolve(true);
}

async function voxLoadTransferAsync() {
  // Prefer IndexedDB (handles large clone/music WAVs)
  try {
    const fromIdb = await voxIdbGet();
    if (fromIdb && fromIdb.b64 && (Date.now() - (fromIdb.ts || 0)) <= 30 * 60 * 1000) {
      return fromIdb;
    }
  } catch (e) {}
  // Fallback: full record still in sessionStorage (small files)
  try {
    const raw = sessionStorage.getItem(VOX_TRANSFER_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !data.b64 || (Date.now() - (data.ts || 0)) > 30 * 60 * 1000) {
      sessionStorage.removeItem(VOX_TRANSFER_KEY);
      return null;
    }
    return data;
  } catch (e) {
    return null;
  }
}

function voxLoadTransfer() {
  // Sync path for legacy callers — only works if full payload is in sessionStorage
  try {
    const raw = sessionStorage.getItem(VOX_TRANSFER_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !data.b64 || (Date.now() - (data.ts || 0)) > 30 * 60 * 1000) return null;
    return data;
  } catch (e) {
    return null;
  }
}

function voxClearTransfer() {
  try { sessionStorage.removeItem(VOX_TRANSFER_KEY); } catch (e) {}
  voxIdbClear();
}

function voxFileFromTransfer(data) {
  const bin = atob(data.b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new File([arr], data.filename || 'audio.wav', { type: data.mime || 'audio/wav' });
}

function voxApplyTransferToInput(input, data) {
  if (!input || !data || !data.b64) return false;
  try {
    const file = voxFileFromTransfer(data);
    const dt = new DataTransfer();
    // Merge tool: keep any already-selected files and append
    if (input.multiple && input.files && input.files.length) {
      Array.from(input.files).forEach((f) => dt.items.add(f));
    }
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
    // Update dropzone filename label if present
    const zone = input.closest('.dropzone');
    if (zone) {
      const nameEl = zone.querySelector('.dropzone__name');
      if (nameEl) {
        nameEl.textContent = input.files.length > 1
          ? (input.files.length + ' files selected')
          : (file.name || 'audio.wav');
      }
    }
    return true;
  } catch (e) {
    console.warn('[voxcraft] apply transfer failed', e);
    return false;
  }
}

/** Shared result panel HTML used by clone, music, studio, and tools. */
function voxAudioPlayerHtml(b64, filename, mime) {
  mime = mime || 'audio/wav';
  filename = filename || 'audio.wav';
  const ok = voxSaveTransfer(b64, filename, mime);
  const links = VOX_NEXT_TOOLS.map((t) =>
    `<a class="btn btn--ghost btn--sm" data-send-tool="${t.slug}" href="/tools/${t.slug}">${t.label}</a>`
  ).join('');
  const handoffNote = ok
    ? ''
    : `<p style="margin:8px 0 0;font-size:0.78rem;color:var(--brass-hi);">Could not stage this file for other tools (storage full). Download it, then upload on the next tool.</p>`;
  const safeName = String(filename).replace(/[<>&"']/g, '');
  const src = `data:${mime};base64,${b64}`;
  return `
    <div class="result-panel">
      <div class="result-panel__label">Your audio</div>
      <div class="vox-player" data-vox-player>
        <audio preload="metadata" src="${src}"></audio>
        <div class="vox-player__row">
          <button type="button" class="vox-player__play" data-vp-play aria-label="Play">
            <svg class="vox-player__icon vox-player__icon--play" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>
            <svg class="vox-player__icon vox-player__icon--pause" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>
          </button>
          <div class="vox-player__timeline">
            <input type="range" class="vox-player__seek" data-vp-seek min="0" max="1000" value="0" step="1" aria-label="Seek">
            <div class="vox-player__times"><span data-vp-cur>0:00</span><span data-vp-dur>0:00</span></div>
          </div>
        </div>
        <div class="vox-player__meta"><strong>${safeName}</strong><span data-vp-state>Ready</span></div>
      </div>
      <div class="result-panel__actions">
        <a class="btn btn--brass btn--sm" download="${filename}" href="${src}">Download</a>
        <button type="button" class="btn btn--ghost btn--sm" data-vp-replay>Play again</button>
      </div>
      <div class="result-panel__next">
        <span class="result-panel__next-label">Send to another tool</span>
        <div class="result-panel__next-links">${links}</div>
        ${handoffNote}
      </div>
    </div>
  `;
}

function voxFormatTime(sec) {
  if (!isFinite(sec) || sec < 0) return '0:00';
  const s = Math.floor(sec % 60);
  const m = Math.floor(sec / 60);
  return m + ':' + String(s).padStart(2, '0');
}

/** Wire custom players inside a root (or document). Safe to call repeatedly. */
function voxBindPlayers(root) {
  const scope = root || document;
  scope.querySelectorAll('[data-vox-player]').forEach((wrap) => {
    if (wrap.dataset.bound === '1') return;
    wrap.dataset.bound = '1';
    const audio = wrap.querySelector('audio');
    const playBtn = wrap.querySelector('[data-vp-play]');
    const seek = wrap.querySelector('[data-vp-seek]');
    const cur = wrap.querySelector('[data-vp-cur]');
    const dur = wrap.querySelector('[data-vp-dur]');
    const state = wrap.querySelector('[data-vp-state]');
    const panel = wrap.closest('.result-panel');
    const replay = panel && panel.querySelector('[data-vp-replay]');
    if (!audio || !playBtn || !seek) return;

    const setPlaying = (on) => {
      playBtn.classList.toggle('is-playing', !!on);
      playBtn.setAttribute('aria-label', on ? 'Pause' : 'Play');
      if (state) state.textContent = on ? 'Playing' : 'Ready';
    };

    playBtn.addEventListener('click', () => {
      if (audio.paused) {
        document.querySelectorAll('[data-vox-player] audio').forEach((a) => {
          if (a !== audio) { try { a.pause(); } catch (e) {} }
        });
        audio.play().catch(() => {});
      } else {
        audio.pause();
      }
    });
    if (replay) {
      replay.addEventListener('click', () => {
        audio.currentTime = 0;
        audio.play().catch(() => {});
      });
    }
    audio.addEventListener('play', () => setPlaying(true));
    audio.addEventListener('pause', () => setPlaying(false));
    audio.addEventListener('ended', () => {
      setPlaying(false);
      seek.value = '0';
      if (cur) cur.textContent = '0:00';
    });
    audio.addEventListener('loadedmetadata', () => {
      if (dur) dur.textContent = voxFormatTime(audio.duration);
    });
    audio.addEventListener('timeupdate', () => {
      if (!audio.duration) return;
      if (!seek.dataset.dragging) {
        seek.value = String(Math.round((audio.currentTime / audio.duration) * 1000));
      }
      if (cur) cur.textContent = voxFormatTime(audio.currentTime);
    });
    seek.addEventListener('pointerdown', () => { seek.dataset.dragging = '1'; });
    seek.addEventListener('pointerup', () => {
      delete seek.dataset.dragging;
      if (audio.duration) audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
    });
    seek.addEventListener('input', () => {
      if (!audio.duration) return;
      const t = (Number(seek.value) / 1000) * audio.duration;
      if (cur) cur.textContent = voxFormatTime(t);
    });
    seek.addEventListener('change', () => {
      if (audio.duration) audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
    });
  });
}

// Auto-bind players when result HTML is injected
const _vpObserver = new MutationObserver((muts) => {
  for (const m of muts) {
    if (m.addedNodes && m.addedNodes.length) {
      voxBindPlayers(document);
      break;
    }
  }
});
try {
  _vpObserver.observe(document.documentElement, { childList: true, subtree: true });
} catch (e) {}


function voxFindTransferInput() {
  const inputs = Array.from(document.querySelectorAll('input.file-input[type="file"], input[type="file"].file-input, input[type="file"]'));
  // Prefer a primary visible/dropzone input; allow opacity:0 dropzone overlays
  const ranked = inputs.filter((el) => {
    const style = (el.getAttribute('style') || '');
    // Skip deliberately hidden multi-add helpers only when NOT the sole input
    if (style.includes('display:none') || style.includes('display: none')) {
      // keep if it's the merge multi input (only file input on that page)
      return inputs.length === 1 || el.multiple;
    }
    return true;
  });
  // Prefer single-file non-hidden, then any
  return (
    ranked.find((el) => !el.multiple && el.closest('.dropzone')) ||
    ranked.find((el) => !el.multiple) ||
    ranked.find((el) => el.multiple) ||
    ranked[0] ||
    null
  );
}

async function voxOfferIncomingTransfer(opts) {
  opts = opts || {};
  const autoApply = opts.autoApply !== false; // default: load file automatically
  const data = await voxLoadTransferAsync();
  if (!data || !data.b64) return false;
  const input = voxFindTransferInput();
  if (!input) return false;
  const panel = input.closest('.panel') || input.closest('.dropzone')?.parentElement || document.body;
  if (panel.querySelector('[data-transfer-banner]')) return true;

  let applied = false;
  if (autoApply) {
    applied = voxApplyTransferToInput(input, data);
  }

  const ban = document.createElement('div');
  ban.setAttribute('data-transfer-banner', '1');
  ban.style.cssText = 'margin-bottom:12px;padding:10px 12px;border-radius:10px;border:1px solid rgba(79,166,156,0.35);background:rgba(79,166,156,0.08);font-size:0.85rem;color:var(--text-mid);display:flex;flex-wrap:wrap;gap:8px;align-items:center;';
  const safeName = String(data.filename || 'file').replace(/[<>&"']/g, '');

  if (applied) {
    ban.innerHTML = `<span style="color:var(--jade-hi)">Loaded <strong style="color:var(--text-hi)">${safeName}</strong> from previous tool — adjust settings and run.</span>`;
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'btn btn--ghost btn--sm';
    dismiss.textContent = 'Dismiss';
    dismiss.addEventListener('click', () => { voxClearTransfer(); ban.remove(); });
    ban.appendChild(dismiss);
  } else {
    ban.innerHTML = `<span>Audio from previous tool ready: <strong style="color:var(--text-hi)">${safeName}</strong></span>`;
    const useBtn = document.createElement('button');
    useBtn.type = 'button';
    useBtn.className = 'btn btn--brass btn--sm';
    useBtn.textContent = 'Use this file';
    useBtn.addEventListener('click', () => {
      if (voxApplyTransferToInput(input, data)) {
        ban.innerHTML = '<span style="color:var(--jade-hi)">File loaded — adjust settings and run the tool.</span>';
      } else {
        ban.innerHTML = '<span style="color:var(--brass-hi)">Could not load automatically — please choose the file again.</span>';
      }
    });
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'btn btn--ghost btn--sm';
    dismiss.textContent = 'Dismiss';
    dismiss.addEventListener('click', () => { voxClearTransfer(); ban.remove(); });
    ban.appendChild(useBtn);
    ban.appendChild(dismiss);
  }

  // Place banner above the dropzone or at top of panel
  const drop = input.closest('.dropzone');
  if (drop && drop.parentNode) {
    drop.parentNode.insertBefore(ban, drop);
  } else {
    panel.insertBefore(ban, panel.firstChild);
  }
  return true;
}

// Ensure "Send to …" waits for IndexedDB write before navigating
document.addEventListener('click', (e) => {
  const a = e.target.closest && e.target.closest('a[data-send-tool]');
  if (!a) return;
  if (a.hasAttribute('data-send-navigating')) return;
  const href = a.getAttribute('href');
  if (!href) return;
  e.preventDefault();
  a.setAttribute('data-send-navigating', '1');
  const go = () => { window.location.href = href; };
  if (typeof voxWaitForTransferSave === 'function') {
    voxWaitForTransferSave().then(go).catch(go);
  } else {
    go();
  }
});


// ---- Subtle section reveal on scroll (landing polish) ----
function initRevealOnScroll(){
  const nodes = document.querySelectorAll('.reveal-on-scroll');
  if(!nodes.length) return;
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    nodes.forEach((n) => n.classList.add('is-inview'));
    return;
  }
  if(!('IntersectionObserver' in window)){
    nodes.forEach((n) => n.classList.add('is-inview'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if(en.isIntersecting){
        en.target.classList.add('is-inview');
        io.unobserve(en.target);
      }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  nodes.forEach((n) => io.observe(n));
}


function initStudioCoach(){
  const el = document.getElementById('studio-coach');
  if(!el) return;
  const KEY = 'voxcraft_studio_coach_v1';
  try {
    if(localStorage.getItem(KEY)) return;
  } catch(e) { return; }
  el.hidden = false;
  const dismiss = () => {
    el.hidden = true;
    try { localStorage.setItem(KEY, '1'); } catch(e) {}
  };
  const btn = document.getElementById('studio-coach-dismiss');
  if(btn) btn.addEventListener('click', dismiss);
  // Also dismiss after first successful generate
  window.addEventListener('voxcraft:generated', dismiss, { once: true });
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
  initRevealOnScroll();
  initStudioCoach();
  voxBindPlayers(document);
  try {
    // Run after a tick so tools.js can wrap inputs in dropzones first
    setTimeout(() => { voxOfferIncomingTransfer({ autoApply: true }); }, 0);
    setTimeout(() => { voxOfferIncomingTransfer({ autoApply: true }); }, 300);
  } catch (e) {}
});