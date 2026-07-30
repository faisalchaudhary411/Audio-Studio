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
    if(durationEst) durationEst.textContent = `~${(words/2.5).toFixed(1)}s`;
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

document.addEventListener('DOMContentLoaded', () => {
  initWave();
  initStudio();
});
