// ===== VoxCraft main.js =====

// ---- Hero waveform (oscilloscope-style animated bars) ----
function initWave(){
  const svg = document.querySelector('.wave');
  if(!svg) return;
  const barCount = 64;
  const w = 1000, h = 120;
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  const gap = 4;
  const barWidth = (w / barCount) - gap;
  const bars = [];

  for(let i=0;i<barCount;i++){
    const rect = document.createElementNS('http://www.w3.org/2000/svg','rect');
    rect.setAttribute('width', barWidth);
    rect.setAttribute('rx', 2);
    rect.setAttribute('x', i * (barWidth+gap));
    svg.appendChild(rect);
    bars.push(rect);
  }

  let t = 0;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function frame(){
    t += 0.045;
    bars.forEach((rect, i) => {
      const phase = i * 0.35;
      const amp = (Math.sin(t + phase) * 0.5 + 0.5) * 0.7
                + (Math.sin(t*2.3 + phase*1.7) * 0.5 + 0.5) * 0.3;
      const barH = 8 + amp * (h - 16);
      rect.setAttribute('height', barH.toFixed(1));
      rect.setAttribute('y', ((h - barH) / 2).toFixed(1));
    });
    if(!reduced) requestAnimationFrame(frame);
  }
  frame();
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