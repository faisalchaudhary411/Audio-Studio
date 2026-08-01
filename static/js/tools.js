// ===== VoxCraft — Tools hub (Transcribe / Convert / Merge / Cutter) =====
(function () {
  // ---- Tab switching ----
  const tabs = document.querySelectorAll('[data-tool-tab]');
  const panels = {
    transcribe: document.getElementById('panel-transcribe'),
    convert: document.getElementById('panel-convert'),
    merge: document.getElementById('panel-merge'),
    cutter: document.getElementById('panel-cutter'),
    denoise: document.getElementById('panel-denoise'),
    voicechange: document.getElementById('panel-voicechange'),
    videoxtract: document.getElementById('panel-videoxtract'),
    music: document.getElementById('panel-music'),
  };
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const key = tab.dataset.toolTab;
      Object.entries(panels).forEach(([k, el]) => { el.style.display = k === key ? '' : 'none'; });
      tabs.forEach(t => t.className = t.dataset.toolTab === key ? 'btn btn--sm btn--brass' : 'btn btn--sm btn--ghost');
    });
  });

  function audioPlayerHtml(b64, filename, mime = 'audio/mpeg') {
    return `
      <audio controls style="width:100%;" src="data:${mime};base64,${b64}"></audio>
      <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;" download="${filename}" href="data:${mime};base64,${b64}">Download</a>
    `;
  }

  // ---- Transcribe ----
  const transcribeBtn = document.getElementById('transcribe-btn');
  const transcribeStatus = document.querySelector('[data-transcribe-status]');
  const transcribeResult = document.getElementById('transcribe-result');
  transcribeBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runTranscribe); });
  async function runTranscribe() {
    const file = document.getElementById('transcribe-file').files[0];
    if (!file) { transcribeStatus.textContent = 'Choose a file first.'; return; }
    transcribeBtn.disabled = true;
    transcribeStatus.textContent = 'Transcribing… this may take a moment for longer files.';
    transcribeResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('lang_code', document.getElementById('transcribe-lang').value);
    try {
      const res = await fetch('/api/tools/transcribe', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { transcribeStatus.textContent = data.error || 'Failed.'; return; }
      transcribeStatus.textContent = `Done (${data.method})`;
      transcribeResult.innerHTML = `
        <textarea class="script-input" style="min-height:140px;" readonly>${data.text}</textarea>
        <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
           download="transcription.txt" href="data:text/plain;charset=utf-8,${encodeURIComponent(data.text)}">Download TXT</a>
      `;
    } catch (e) {
      transcribeStatus.textContent = 'Network error.';
    } finally {
      transcribeBtn.disabled = false;
    }
  }

  // ---- Convert ----
  const convertQuality = document.getElementById('convert-quality');
  document.getElementById('convert-quality-label').textContent = convertQuality.value;
  convertQuality.addEventListener('input', () => {
    document.getElementById('convert-quality-label').textContent = convertQuality.value;
  });
  const convertBtn = document.getElementById('convert-btn');
  const convertStatus = document.querySelector('[data-convert-status]');
  const convertResult = document.getElementById('convert-result');
  convertBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runConvert); });
  async function runConvert() {
    const file = document.getElementById('convert-file').files[0];
    if (!file) { convertStatus.textContent = 'Choose a file first.'; return; }
    convertBtn.disabled = true;
    convertStatus.textContent = 'Converting…';
    convertResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('output_format', document.getElementById('convert-format').value);
    form.append('quality', convertQuality.value);
    try {
      const res = await fetch('/api/tools/convert', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { convertStatus.textContent = data.error || 'Failed.'; return; }
      convertStatus.textContent = `Converted to ${data.format.toUpperCase()}`;
      convertResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, `audio/${data.format}`);
    } catch (e) {
      convertStatus.textContent = 'Network error.';
    } finally {
      convertBtn.disabled = false;
    }
  }

  // ---- Merge ----
  const mergeGap = document.getElementById('merge-gap');
  document.getElementById('merge-gap-label').textContent = mergeGap.value;
  mergeGap.addEventListener('input', () => {
    document.getElementById('merge-gap-label').textContent = mergeGap.value;
  });
  const mergeBtn = document.getElementById('merge-btn');
  const mergeStatus = document.querySelector('[data-merge-status]');
  const mergeResult = document.getElementById('merge-result');
  mergeBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runMerge); });
  async function runMerge() {
    const files = document.getElementById('merge-files').files;
    if (files.length < 2) { mergeStatus.textContent = 'Choose at least 2 files.'; return; }
    mergeBtn.disabled = true;
    mergeStatus.textContent = `Merging ${files.length} files…`;
    mergeResult.innerHTML = '';
    const form = new FormData();
    for (const f of files) form.append('files', f);
    form.append('gap_ms', mergeGap.value);
    form.append('output_format', document.getElementById('merge-format').value);
    try {
      const res = await fetch('/api/tools/merge', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { mergeStatus.textContent = data.error || 'Failed.'; return; }
      mergeStatus.textContent = `Merged ${files.length} files`;
      mergeResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, `audio/${data.format}`);
    } catch (e) {
      mergeStatus.textContent = 'Network error.';
    } finally {
      mergeBtn.disabled = false;
    }
  }

  // ---- Cutter ----
  const cutterFile = document.getElementById('cutter-file');
  const cutterDuration = document.getElementById('cutter-duration');
  const cutterModeBtns = document.querySelectorAll('[data-cutter-mode]');
  const trimControls = document.getElementById('cutter-trim-controls');
  const splitControls = document.getElementById('cutter-split-controls');
  const cutterBtn = document.getElementById('cutter-btn');
  const cutterStatus = document.querySelector('[data-cutter-status]');
  const cutterResult = document.getElementById('cutter-result');
  let cutterMode = 'trim';
  let cutterDurationSec = 0;

  cutterModeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      cutterMode = btn.dataset.cutterMode;
      cutterModeBtns.forEach(b => b.className = b.dataset.cutterMode === cutterMode ? 'btn btn--sm btn--brass' : 'btn btn--sm btn--ghost');
      trimControls.style.display = cutterMode === 'trim' ? '' : 'none';
      splitControls.style.display = cutterMode === 'split' ? '' : 'none';
    });
  });

  cutterFile.addEventListener('change', async () => {
    const file = cutterFile.files[0];
    if (!file) return;
    cutterDuration.textContent = 'Reading duration…';
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/tools/cutter/duration', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { cutterDuration.textContent = data.error || 'Could not read file.'; return; }
      cutterDurationSec = data.duration_sec;
      cutterDuration.textContent = `Duration: ${cutterDurationSec.toFixed(1)}s`;
      document.getElementById('cutter-end').value = cutterDurationSec.toFixed(1);
      document.getElementById('cutter-split-at').value = (cutterDurationSec / 2).toFixed(1);
    } catch (e) {
      cutterDuration.textContent = 'Network error.';
    }
  });

  cutterBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runCutter); });
  async function runCutter() {
    const file = cutterFile.files[0];
    if (!file) { cutterStatus.textContent = 'Choose a file first.'; return; }
    cutterBtn.disabled = true;
    cutterResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    try {
      if (cutterMode === 'trim') {
        cutterStatus.textContent = 'Trimming…';
        form.append('start_sec', document.getElementById('cutter-start').value);
        form.append('end_sec', document.getElementById('cutter-end').value);
        const res = await fetch('/api/tools/cutter/trim', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) { cutterStatus.textContent = data.error || 'Failed.'; return; }
        cutterStatus.textContent = 'Trimmed';
        cutterResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } else {
        cutterStatus.textContent = 'Splitting…';
        form.append('split_sec', document.getElementById('cutter-split-at').value);
        const res = await fetch('/api/tools/cutter/split', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) { cutterStatus.textContent = data.error || 'Failed.'; return; }
        cutterStatus.textContent = 'Split complete';
        cutterResult.innerHTML = `
          <p style="font-family:var(--mono);font-size:0.8rem;color:var(--text-dim);">Part 1</p>
          ${audioPlayerHtml(data.part1_b64, data.filename_base + '-1.mp3')}
          <p style="font-family:var(--mono);font-size:0.8rem;color:var(--text-dim);margin-top:10px;">Part 2</p>
          ${audioPlayerHtml(data.part2_b64, data.filename_base + '-2.mp3')}
        `;
      }
    } catch (e) {
      cutterStatus.textContent = 'Network error.';
    } finally {
      cutterBtn.disabled = false;
    }
  }

  // ---- Denoise ----
  const denoiseStrength = document.getElementById('denoise-strength');
  const denoiseStrengthLabel = document.getElementById('denoise-strength-label');
  if (denoiseStrength) {
    denoiseStrength.addEventListener('input', () => {
      denoiseStrengthLabel.textContent = denoiseStrength.value;
    });
  }
  const denoiseBtn = document.getElementById('denoise-btn');
  const denoiseStatus = document.querySelector('[data-denoise-status]');
  const denoiseResult = document.getElementById('denoise-result');
  if (denoiseBtn) {
    denoiseBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runDenoise); });
  }
  async function runDenoise() {
    const file = document.getElementById('denoise-file').files[0];
    if (!file) { denoiseStatus.textContent = 'Choose a file first.'; return; }
    denoiseBtn.disabled = true;
    denoiseStatus.textContent = 'Removing noise…';
    denoiseResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('strength', denoiseStrength.value);
    try {
      const res = await fetch('/api/tools/denoise', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { denoiseStatus.textContent = data.error || 'Failed.'; return; }
      denoiseStatus.textContent = 'Noise removed';
      denoiseResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
    } catch (e) {
      denoiseStatus.textContent = 'Network error.';
    } finally {
      denoiseBtn.disabled = false;
    }
  }

  // ---- Voice Changer ----
  const vcEffect = document.getElementById('voicechange-effect');
  const vcPitchControls = document.getElementById('voicechange-pitch-controls');
  const vcRobotControls = document.getElementById('voicechange-robot-controls');
  const vcEchoControls = document.getElementById('voicechange-echo-controls');
  const vcSemitones = document.getElementById('voicechange-semitones');
  const vcSemitonesLabel = document.getElementById('voicechange-semitones-label');
  const vcIntensity = document.getElementById('voicechange-intensity');
  const vcIntensityLabel = document.getElementById('voicechange-intensity-label');
  const vcDelay = document.getElementById('voicechange-delay');
  const vcDelayLabel = document.getElementById('voicechange-delay-label');
  const vcDecay = document.getElementById('voicechange-decay');
  const vcDecayLabel = document.getElementById('voicechange-decay-label');
  const vcBtn = document.getElementById('voicechange-btn');
  const vcStatus = document.querySelector('[data-voicechange-status]');
  const vcResult = document.getElementById('voicechange-result');

  if (vcEffect) {
    vcEffect.addEventListener('change', () => {
      vcPitchControls.style.display = vcEffect.value === 'pitch_shift' ? '' : 'none';
      vcRobotControls.style.display = vcEffect.value === 'robot' ? '' : 'none';
      vcEchoControls.style.display = vcEffect.value === 'echo' ? '' : 'none';
    });
    vcSemitones.addEventListener('input', () => { vcSemitonesLabel.textContent = vcSemitones.value; });
    vcIntensity.addEventListener('input', () => { vcIntensityLabel.textContent = vcIntensity.value; });
    vcDelay.addEventListener('input', () => { vcDelayLabel.textContent = vcDelay.value; });
    vcDecay.addEventListener('input', () => { vcDecayLabel.textContent = vcDecay.value; });
    vcBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runVoiceChange); });
  }

  async function runVoiceChange() {
    const file = document.getElementById('voicechange-file').files[0];
    if (!file) { vcStatus.textContent = 'Choose a file first.'; return; }
    vcBtn.disabled = true;
    vcStatus.textContent = 'Applying effect…';
    vcResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('effect', vcEffect.value);
    if (vcEffect.value === 'pitch_shift') form.append('semitones', vcSemitones.value);
    if (vcEffect.value === 'robot') form.append('intensity', vcIntensity.value);
    if (vcEffect.value === 'echo') { form.append('delay_ms', vcDelay.value); form.append('decay', vcDecay.value); }
    try {
      const res = await fetch('/api/tools/voicechange', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { vcStatus.textContent = data.error || 'Failed.'; return; }
      vcStatus.textContent = 'Effect applied';
      vcResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
    } catch (e) {
      vcStatus.textContent = 'Network error.';
    } finally {
      vcBtn.disabled = false;
    }
  }

  // ---- Video Extract ----
  const vxFile = document.getElementById('videoxtract-file');
  const vxQuality = document.getElementById('videoxtract-quality');
  const vxQualityLabel = document.getElementById('videoxtract-quality-label');
  const vxBtn = document.getElementById('videoxtract-btn');
  const vxStatus = document.querySelector('[data-videoxtract-status]');
  const vxResult = document.getElementById('videoxtract-result');

  if (vxQuality) {
    vxQuality.addEventListener('input', () => { vxQualityLabel.textContent = vxQuality.value; });
    vxBtn.addEventListener('click', () => { window.VoxCraftAds.showInterstitial(runVideoExtract); });
  }

  async function runVideoExtract() {
    const file = vxFile.files[0];
    if (!file) { vxStatus.textContent = 'Choose a video file first.'; return; }
    vxBtn.disabled = true;
    vxStatus.textContent = 'Extracting audio (this can take a moment for larger files)…';
    vxResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('output_format', document.getElementById('videoxtract-format').value);
    form.append('quality', vxQuality.value);
    try {
      const res = await fetch('/api/tools/videoxtract', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) { vxStatus.textContent = data.error || 'Failed.'; return; }
      vxStatus.textContent = `Extracted · ${data.size_kb} KB`;
      vxResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, `audio/${data.format}`);
    } catch (e) {
      vxStatus.textContent = 'Network error.';
    } finally {
      vxBtn.disabled = false;
    }
  }
})();
