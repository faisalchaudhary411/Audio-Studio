// ===== VoxCraft — Tools hub (shared with /tools/<slug> pages) =====
(function () {
  // ---- Tab switching (hub only; individual tool pages have one panel) ----
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
      Object.entries(panels).forEach(([k, el]) => {
        if (el) el.style.display = k === key ? '' : 'none';
      });
      tabs.forEach(t => {
        t.className = t.dataset.toolTab === key ? 'btn btn--sm btn--brass is-active' : 'btn btn--sm btn--ghost';
      });
    });
  });

  // BUG FIX: browsers don't recognize "audio/m4a" as a MIME type — the
  // actual container is MP4, so the correct MIME type is audio/mp4.
  const AUDIO_MIME = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    ogg: 'audio/ogg',
    m4a: 'audio/mp4',
    flac: 'audio/flac',
  };
  function mimeFor(fmt) {
    return AUDIO_MIME[fmt] || 'audio/mpeg';
  }

  function audioPlayerHtml(b64, filename, mime) {
    mime = mime || 'audio/mpeg';
    return `
      <div class="result-panel">
        <audio controls src="data:${mime};base64,${b64}"></audio>
        <div class="result-panel__actions">
          <a class="btn btn--brass btn--sm" download="${filename}" href="data:${mime};base64,${b64}">Download</a>
          <button type="button" class="btn btn--ghost btn--sm" onclick="this.closest('.result-panel').querySelector('audio').play()">Play again</button>
        </div>
        <div class="result-panel__next">
          <span class="result-panel__next-label">Next step</span>
          <div class="result-panel__next-links">
            <a class="btn btn--ghost btn--sm" href="/tools/trim-cut-audio">Trim</a>
            <a class="btn btn--ghost btn--sm" href="/tools/remove-background-noise">Denoise</a>
            <a class="btn btn--ghost btn--sm" href="/tools/normalize-audio-volume">Normalize</a>
            <a class="btn btn--ghost btn--sm" href="/tools/merge-audio-files">Merge</a>
            <a class="btn btn--ghost btn--sm" href="/tools/convert-audio-format">Convert</a>
          </div>
        </div>
      </div>
    `;
  }

  // Upgrade plain file inputs into drop zones (empty-state UX)
  function enhanceFileInputs() {
    document.querySelectorAll('input.file-input[type="file"]').forEach((input) => {
      if (input.dataset.dropEnhanced === '1') return;
      if (input.closest('.dropzone')) return;
      // Skip hidden multi inputs used by merge-add pattern
      if (input.style.display === 'none' || input.getAttribute('style') && input.getAttribute('style').includes('display:none')) return;
      input.dataset.dropEnhanced = '1';
      const zone = document.createElement('div');
      zone.className = 'dropzone';
      const title = document.createElement('div');
      title.className = 'dropzone__title';
      title.textContent = 'Drop a file here';
      const hint = document.createElement('div');
      hint.className = 'dropzone__hint';
      hint.textContent = input.multiple
        ? 'or tap to choose files · up to 10MB each'
        : 'or tap to choose · usually under 10MB';
      const name = document.createElement('div');
      name.className = 'dropzone__name';
      input.parentNode.insertBefore(zone, input);
      zone.appendChild(title);
      zone.appendChild(hint);
      zone.appendChild(input);
      zone.appendChild(name);
      const updateName = () => {
        const files = input.files;
        if (!files || !files.length) { name.textContent = ''; return; }
        if (files.length === 1) name.textContent = files[0].name;
        else name.textContent = files.length + ' files selected';
      };
      input.addEventListener('change', updateName);
      zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('is-drag'); });
      zone.addEventListener('dragleave', () => zone.classList.remove('is-drag'));
      zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('is-drag');
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
          try {
            input.files = e.dataTransfer.files;
          } catch (err) {
            // some browsers block setting files; fall through to click
          }
          input.dispatchEvent(new Event('change', { bubbles: true }));
          updateName();
        }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceFileInputs);
  } else {
    enhanceFileInputs();
  }

  // Shared helpers matching studio.js generate-button behaviour
  function setLoading(btn, on) {
    if (!btn) return;
    btn.disabled = !!on;
    btn.classList.toggle('is-loading', !!on);
    // Pair status text with pulse when present
    const panel = btn.closest('.panel');
    if (panel) {
      panel.querySelectorAll('.render-status').forEach((s) => {
        s.classList.toggle('is-busy', !!on);
      });
    }
  }

  function ensureProgress(afterEl) {
    if (!afterEl) return null;
    let bar = afterEl.parentElement && afterEl.parentElement.querySelector('.gen-progress');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'gen-progress';
      bar.innerHTML = '<div class="gen-progress__bar"></div>';
      // Prefer placing after the render-bar when present
      const renderBar = afterEl.closest('.panel') && afterEl.closest('.panel').querySelector('.render-bar');
      if (renderBar && renderBar.parentNode) {
        renderBar.parentNode.insertBefore(bar, renderBar.nextSibling);
      } else if (afterEl.parentNode) {
        afterEl.parentNode.insertBefore(bar, afterEl.nextSibling);
      }
    }
    return bar;
  }

  function showProgress(bar, on) {
    if (!bar) return;
    bar.classList.toggle('is-active', !!on);
  }

  function friendlyError(data, fallback) {
    if (data && typeof data.error === 'string' && data.error.trim()) {
      return data.error.trim();
    }
    return fallback || 'Something went wrong. Please try again.';
  }

  function bindFileLabel(input) {
    if (!input || input.dataset.labelBound) return;
    input.dataset.labelBound = '1';
    const update = () => {
      const file = input.files && input.files[0];
      if (file) {
        const mb = (file.size / (1024 * 1024)).toFixed(2);
        input.setAttribute('data-file-label', `${file.name} · ${mb} MB`);
        input.classList.add('has-file');
      } else {
        input.removeAttribute('data-file-label');
        input.classList.remove('has-file');
      }
    };
    input.addEventListener('change', update);
    update();
  }

  // Wire every visible file input for nicer "file chosen" feedback
  document.querySelectorAll('input.file-input[type="file"]').forEach(bindFileLabel);

  // ---- Transcribe ----
  const transcribeBtn = document.getElementById('transcribe-btn');
  const transcribeStatus = document.querySelector('[data-transcribe-status]');
  const transcribeResult = document.getElementById('transcribe-result');
  const transcribeProgress = ensureProgress(transcribeResult);
  if (transcribeBtn) {
    transcribeBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runTranscribe);
    });
  }
  async function runTranscribe() {
    const fileInput = document.getElementById('transcribe-file');
    const file = fileInput && fileInput.files[0];
    if (!file) {
      if (transcribeStatus) transcribeStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(transcribeBtn, true);
    showProgress(transcribeProgress, true);
    if (transcribeStatus) transcribeStatus.textContent = 'Transcribing… this may take a moment for longer files.';
    if (transcribeResult) transcribeResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('lang_code', document.getElementById('transcribe-lang').value);
    try {
      const res = await fetch('/api/tools/transcribe', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (transcribeStatus) transcribeStatus.textContent = friendlyError(data, 'Transcription failed.');
        return;
      }
      if (transcribeStatus) transcribeStatus.textContent = `Done (${data.method || 'ok'})`;
      if (transcribeResult) {
        const meta = data.word_count ? ` · ${data.word_count} words` : '';
        transcribeResult.innerHTML = `
          <p style="font-size:0.8rem;color:var(--text-dim);margin-bottom:6px;">${data.method || ''}${meta}</p>
          <textarea class="script-input" style="min-height:140px;" readonly>${data.text || ''}</textarea>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
            <a class="btn btn--ghost btn--sm" download="transcription.txt"
               href="data:text/plain;charset=utf-8,${encodeURIComponent(data.text || '')}">Download TXT</a>
            ${data.srt ? `<a class="btn btn--ghost btn--sm" download="captions.srt"
               href="data:text/plain;charset=utf-8,${encodeURIComponent(data.srt)}">Download SRT</a>` : ''}
          </div>
        `;
      }
    } catch (e) {
      if (transcribeStatus) transcribeStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(transcribeBtn, false);
      showProgress(transcribeProgress, false);
    }
  }

  // ---- Convert ----
  const convertQuality = document.getElementById('convert-quality');
  const convertBtn = document.getElementById('convert-btn');
  const convertStatus = document.querySelector('[data-convert-status]');
  const convertResult = document.getElementById('convert-result');
  const convertProgress = ensureProgress(convertResult);
  if (convertQuality) {
    const label = document.getElementById('convert-quality-label');
    if (label) label.textContent = convertQuality.value;
    convertQuality.addEventListener('input', () => {
      if (label) label.textContent = convertQuality.value;
    });
  }
  if (convertBtn) {
    convertBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runConvert);
    });
  }
  async function runConvert() {
    const file = document.getElementById('convert-file').files[0];
    if (!file) {
      if (convertStatus) convertStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(convertBtn, true);
    showProgress(convertProgress, true);
    if (convertStatus) convertStatus.textContent = 'Converting…';
    if (convertResult) convertResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('output_format', document.getElementById('convert-format').value);
    form.append('quality', convertQuality ? convertQuality.value : '192');
    const presetEl = document.getElementById('convert-preset');
    if (presetEl && presetEl.value) form.append('preset', presetEl.value);
    try {
      const res = await fetch('/api/tools/convert', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (convertStatus) convertStatus.textContent = friendlyError(data, 'Conversion failed.');
        return;
      }
      if (convertStatus) convertStatus.textContent = `Converted to ${(data.format || '').toUpperCase()}`;
      if (convertResult) convertResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      if (convertStatus) convertStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(convertBtn, false);
      showProgress(convertProgress, false);
    }
  }

  // ---- Merge ----
  const mergeGap = document.getElementById('merge-gap');
  const mergeAddBtn = document.getElementById('merge-add-btn');
  const mergeFilesInput = document.getElementById('merge-files');
  const mergeFileList = document.getElementById('merge-file-list');
  const mergeBtn = document.getElementById('merge-btn');
  const mergeStatus = document.querySelector('[data-merge-status]');
  const mergeResult = document.getElementById('merge-result');
  const mergeProgress = ensureProgress(mergeResult);
  let mergeSelectedFiles = [];

  function renderMergeList() {
    if (!mergeFileList) return;
    if (!mergeSelectedFiles.length) {
      mergeFileList.innerHTML = '<p style="color:var(--text-dim);font-size:0.82rem;">No files added yet.</p>';
      return;
    }
    mergeFileList.innerHTML = mergeSelectedFiles
      .map((f, i) => {
        const mb = (f.size / (1024 * 1024)).toFixed(2);
        return `
        <div class="file-chip">
          <span class="file-chip__name">${i + 1}. ${f.name} <span class="file-chip__meta">${mb} MB</span></span>
          <button type="button" data-remove-idx="${i}" class="btn btn--ghost btn--sm" style="padding:4px 10px;">Remove</button>
        </div>`;
      })
      .join('');
    mergeFileList.querySelectorAll('[data-remove-idx]').forEach(btn => {
      btn.addEventListener('click', () => {
        mergeSelectedFiles.splice(parseInt(btn.dataset.removeIdx, 10), 1);
        renderMergeList();
      });
    });
  }

  if (mergeGap) {
    const gapLabel = document.getElementById('merge-gap-label');
    if (gapLabel) gapLabel.textContent = mergeGap.value;
    mergeGap.addEventListener('input', () => {
      if (gapLabel) gapLabel.textContent = mergeGap.value;
    });
  }
  const mergeCrossfade = document.getElementById('merge-crossfade');
  if (mergeCrossfade) {
    const cfLabel = document.getElementById('merge-crossfade-label');
    if (cfLabel) cfLabel.textContent = mergeCrossfade.value;
    mergeCrossfade.addEventListener('input', () => {
      if (cfLabel) cfLabel.textContent = mergeCrossfade.value;
    });
  }
  if (mergeFileList) renderMergeList();
  if (mergeAddBtn && mergeFilesInput) {
    mergeAddBtn.addEventListener('click', () => mergeFilesInput.click());
  }
  if (mergeFilesInput) {
    mergeFilesInput.addEventListener('change', () => {
      for (const f of mergeFilesInput.files) mergeSelectedFiles.push(f);
      mergeFilesInput.value = '';
      renderMergeList();
    });
  }
  if (mergeBtn) {
    mergeBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runMerge);
    });
  }
  async function runMerge() {
    if (mergeSelectedFiles.length < 2) {
      if (mergeStatus) mergeStatus.textContent = 'Add at least 2 files first.';
      return;
    }
    setLoading(mergeBtn, true);
    showProgress(mergeProgress, true);
    if (mergeStatus) mergeStatus.textContent = `Merging ${mergeSelectedFiles.length} files…`;
    if (mergeResult) mergeResult.innerHTML = '';
    const form = new FormData();
    for (const f of mergeSelectedFiles) form.append('files', f);
    form.append('gap_ms', mergeGap ? mergeGap.value : '500');
    const cf = document.getElementById('merge-crossfade');
    form.append('crossfade_ms', cf && cf.value !== '' ? cf.value : '0');
    form.append('output_format', document.getElementById('merge-format').value);
    try {
      const res = await fetch('/api/tools/merge', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (mergeStatus) mergeStatus.textContent = friendlyError(data, 'Merge failed.');
        return;
      }
      if (mergeStatus) mergeStatus.textContent = `Merged ${mergeSelectedFiles.length} files`;
      if (mergeResult) mergeResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      if (mergeStatus) mergeStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(mergeBtn, false);
      showProgress(mergeProgress, false);
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
  const cutterProgress = ensureProgress(cutterResult);
  let cutterMode = 'trim';
  let cutterDurationSec = 0;

  if (cutterModeBtns.length) {
    cutterModeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        cutterMode = btn.dataset.cutterMode;
        cutterModeBtns.forEach(b => {
          b.className =
            b.dataset.cutterMode === cutterMode ? 'btn btn--sm btn--brass is-active' : 'btn btn--sm btn--ghost';
        });
        if (trimControls) trimControls.style.display = cutterMode === 'trim' ? '' : 'none';
        if (splitControls) splitControls.style.display = cutterMode === 'split' ? '' : 'none';
      });
    });
  }

  if (cutterFile) {
    cutterFile.addEventListener('change', async () => {
      const file = cutterFile.files[0];
      if (!file) return;
      if (cutterDuration) cutterDuration.textContent = 'Reading duration…';
      const form = new FormData();
      form.append('file', file);
      try {
        const res = await fetch('/api/tools/cutter/duration', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (cutterDuration) cutterDuration.textContent = friendlyError(data, 'Could not read file.');
          return;
        }
        cutterDurationSec = data.duration_sec;
        if (cutterDuration) cutterDuration.textContent = `Duration: ${cutterDurationSec.toFixed(1)}s`;
        const endEl = document.getElementById('cutter-end');
        const splitEl = document.getElementById('cutter-split') || document.getElementById('cutter-split-at');
        if (endEl) endEl.value = cutterDurationSec.toFixed(1);
        if (splitEl) splitEl.value = (cutterDurationSec / 2).toFixed(1);
      } catch (e) {
        if (cutterDuration) cutterDuration.textContent = 'Network error.';
      }
    });
  }

  if (cutterBtn) {
    cutterBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runCutter);
    });
  }
  async function runCutter() {
    const file = cutterFile && cutterFile.files[0];
    if (!file) {
      if (cutterStatus) cutterStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(cutterBtn, true);
    showProgress(cutterProgress, true);
    if (cutterResult) cutterResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    try {
      if (cutterMode === 'auto') {
        if (cutterStatus) cutterStatus.textContent = 'Auto-trimming silence…';
        const res = await fetch('/api/tools/cutter/auto-trim', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (cutterStatus) cutterStatus.textContent = friendlyError(data, 'Auto-trim failed.');
          return;
        }
        if (cutterStatus) cutterStatus.textContent = 'Silence trimmed';
        if (cutterResult) cutterResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } else if (cutterMode === 'trim') {
        if (cutterStatus) cutterStatus.textContent = 'Trimming…';
        form.append('start_sec', document.getElementById('cutter-start').value);
        form.append('end_sec', document.getElementById('cutter-end').value);
        const res = await fetch('/api/tools/cutter/trim', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (cutterStatus) cutterStatus.textContent = friendlyError(data, 'Trim failed.');
          return;
        }
        if (cutterStatus) cutterStatus.textContent = 'Trimmed';
        if (cutterResult) cutterResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } else {
        if (cutterStatus) cutterStatus.textContent = 'Splitting…';
        const splitEl = document.getElementById('cutter-split') || document.getElementById('cutter-split-at');
        form.append('split_sec', splitEl ? splitEl.value : '0');
        const res = await fetch('/api/tools/cutter/split', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (cutterStatus) cutterStatus.textContent = friendlyError(data, 'Split failed.');
          return;
        }
        if (cutterStatus) cutterStatus.textContent = 'Split complete';
        if (cutterResult) {
          cutterResult.innerHTML = `
            <p style="font-family:var(--mono);font-size:0.8rem;color:var(--text-dim);">Part 1</p>
            ${audioPlayerHtml(data.part1_b64, data.filename_base + '-1.mp3')}
            <p style="font-family:var(--mono);font-size:0.8rem;color:var(--text-dim);margin-top:10px;">Part 2</p>
            ${audioPlayerHtml(data.part2_b64, data.filename_base + '-2.mp3')}
          `;
        }
      }
    } catch (e) {
      if (cutterStatus) cutterStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(cutterBtn, false);
      showProgress(cutterProgress, false);
    }
  }

  // ---- Denoise ----
  const denoiseStrength = document.getElementById('denoise-strength');
  const denoiseStrengthLabel = document.getElementById('denoise-strength-label');
  function denoiseLabel(v) {
    const n = parseFloat(v);
    if (n <= 0.4) return 'Light';
    if (n <= 0.65) return 'Medium';
    return 'Strong';
  }
  if (denoiseStrength && denoiseStrengthLabel) {
    denoiseStrengthLabel.textContent = denoiseLabel(denoiseStrength.value);
    denoiseStrength.addEventListener('input', () => {
      denoiseStrengthLabel.textContent = denoiseLabel(denoiseStrength.value);
    });
  }
  document.querySelectorAll('[data-denoise-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (!denoiseStrength) return;
      denoiseStrength.value = btn.dataset.denoisePreset;
      if (denoiseStrengthLabel) denoiseStrengthLabel.textContent = denoiseLabel(denoiseStrength.value);
    });
  });
  // Voice dry/wet label
  const vcDryWet = document.getElementById('voicechange-drywet');
  const vcDryWetLabel = document.getElementById('voicechange-drywet-label');
  if (vcDryWet && vcDryWetLabel) {
    vcDryWet.addEventListener('input', () => {
      vcDryWetLabel.textContent = Math.round(parseFloat(vcDryWet.value) * 100) + '%';
    });
  }
  const denoiseBtn = document.getElementById('denoise-btn');
  const denoiseStatus = document.querySelector('[data-denoise-status]');
  const denoiseResult = document.getElementById('denoise-result');
  const denoiseProgress = ensureProgress(denoiseResult);
  if (denoiseBtn) {
    denoiseBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runDenoise);
    });
  }
  async function runDenoise() {
    const file = document.getElementById('denoise-file').files[0];
    if (!file) {
      if (denoiseStatus) denoiseStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(denoiseBtn, true);
    showProgress(denoiseProgress, true);
    if (denoiseStatus) denoiseStatus.textContent = 'Removing noise…';
    if (denoiseResult) denoiseResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('strength', denoiseStrength ? denoiseStrength.value : '0.5');
    const st = document.getElementById('denoise-stationary');
    form.append('stationary', st && st.checked ? '1' : '0');
    try {
      const res = await fetch('/api/tools/denoise', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (denoiseStatus) denoiseStatus.textContent = friendlyError(data, 'Denoise failed.');
        return;
      }
      if (denoiseStatus) denoiseStatus.textContent = 'Noise removed';
      if (denoiseResult) denoiseResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
    } catch (e) {
      if (denoiseStatus) denoiseStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(denoiseBtn, false);
      showProgress(denoiseProgress, false);
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
  const vcProgress = ensureProgress(vcResult);

  if (vcEffect) {
    const vcDryWetWrap = document.getElementById('voicechange-drywet-wrap');
    function syncVcControls() {
      const v = vcEffect.value;
      if (vcPitchControls) vcPitchControls.style.display = v === 'pitch_shift' ? '' : 'none';
      if (vcRobotControls) vcRobotControls.style.display = v === 'robot' ? '' : 'none';
      if (vcEchoControls) vcEchoControls.style.display = v === 'echo' ? '' : 'none';
      // Presets are always full effect — hide mix slider to avoid confusion
      const isPreset = ['slight_deeper','anon','chipmunk','deep_voice'].indexOf(v) >= 0;
      if (vcDryWetWrap) vcDryWetWrap.style.display = isPreset ? 'none' : '';
    }
    vcEffect.addEventListener('change', syncVcControls);
    syncVcControls();
    if (vcSemitones && vcSemitonesLabel) {
      vcSemitones.addEventListener('input', () => {
        vcSemitonesLabel.textContent = vcSemitones.value;
      });
    }
    if (vcIntensity && vcIntensityLabel) {
      vcIntensity.addEventListener('input', () => {
        vcIntensityLabel.textContent = vcIntensity.value;
      });
    }
    if (vcDelay && vcDelayLabel) {
      vcDelay.addEventListener('input', () => {
        vcDelayLabel.textContent = vcDelay.value;
      });
    }
    if (vcDecay && vcDecayLabel) {
      vcDecay.addEventListener('input', () => {
        vcDecayLabel.textContent = vcDecay.value;
      });
    }
    if (vcBtn) {
      vcBtn.addEventListener('click', () => {
        window.VoxCraftAds.showInterstitial(runVoiceChange);
      });
    }
  }

  async function runVoiceChange() {
    const fileEl = document.getElementById('voicechange-file');
    const file = fileEl && fileEl.files[0];
    if (!file) {
      if (vcStatus) vcStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(vcBtn, true);
    showProgress(vcProgress, true);
    if (vcStatus) vcStatus.textContent = 'Applying effect…';
    if (vcResult) vcResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('effect', vcEffect.value);
    const effectVal = vcEffect ? vcEffect.value : 'pitch_shift';
    const isPreset = ['slight_deeper','anon','chipmunk','deep_voice'].indexOf(effectVal) >= 0;
    const dw = document.getElementById('voicechange-drywet');
    form.append('dry_wet', isPreset ? '1' : (dw ? dw.value : '1'));
    if (vcEffect.value === 'pitch_shift' && vcSemitones) form.append('semitones', vcSemitones.value);
    if (vcEffect.value === 'robot' && vcIntensity) form.append('intensity', vcIntensity.value);
    if (vcEffect.value === 'echo') {
      if (vcDelay) form.append('delay_ms', vcDelay.value);
      if (vcDecay) form.append('decay', vcDecay.value);
    }
    try {
      const res = await fetch('/api/tools/voicechange', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (vcStatus) vcStatus.textContent = friendlyError(data, 'Effect failed.');
        return;
      }
      if (vcStatus) vcStatus.textContent = 'Effect applied';
      if (vcResult) vcResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
    } catch (e) {
      if (vcStatus) vcStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(vcBtn, false);
      showProgress(vcProgress, false);
    }
  }


  // ---- Video Extract ----
  const vxFile = document.getElementById('videoxtract-file');
  const vxQuality = document.getElementById('videoxtract-quality');
  const vxQualityLabel = document.getElementById('videoxtract-quality-label');
  const vxBtn = document.getElementById('videoxtract-btn');
  const vxStatus = document.querySelector('[data-videoxtract-status]');
  const vxResult = document.getElementById('videoxtract-result');
  const vxProgress = ensureProgress(vxResult);

  if (vxQuality && vxQualityLabel) {
    vxQuality.addEventListener('input', () => {
      vxQualityLabel.textContent = vxQuality.value;
    });
  }
  if (vxBtn) {
    vxBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runVideoExtract);
    });
  }

  async function runVideoExtract() {
    const file = vxFile && vxFile.files[0];
    if (!file) {
      if (vxStatus) vxStatus.textContent = 'Choose a video file first.';
      return;
    }
    // Client-side size guard matching server (50MB)
    if (file.size > 50 * 1024 * 1024) {
      if (vxStatus) vxStatus.textContent = 'File is over 50MB. Please use a smaller video.';
      return;
    }
    setLoading(vxBtn, true);
    showProgress(vxProgress, true);
    if (vxStatus) vxStatus.textContent = 'Extracting audio (this can take a moment for larger files)…';
    if (vxResult) vxResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('output_format', document.getElementById('videoxtract-format').value);
    form.append('quality', vxQuality ? vxQuality.value : '192');
    const vxs = document.getElementById('videoxtract-start');
    const vxe = document.getElementById('videoxtract-end');
    if (vxs && vxs.value !== '') form.append('start_sec', vxs.value);
    if (vxe && vxe.value !== '') form.append('end_sec', vxe.value);
    try {
      const res = await fetch('/api/tools/videoxtract', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (vxStatus) vxStatus.textContent = friendlyError(data, 'Extraction failed.');
        return;
      }
      if (vxStatus) vxStatus.textContent = `Extracted · ${data.size_kb} KB`;
      if (vxResult) vxResult.innerHTML = audioPlayerHtml(data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      if (vxStatus) vxStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      setLoading(vxBtn, false);
      showProgress(vxProgress, false);
    }
  }


  // ---- Normalize ----
  (function () {
    const btn = document.getElementById('normalize-btn');
    if (!btn) return;
    const status = document.querySelector('[data-normalize-status]');
    const result = document.getElementById('normalize-result');
    const progress = ensureProgress(result);
    const target = document.getElementById('normalize-target');
    const targetLabel = document.getElementById('normalize-target-label');
    if (target && targetLabel) {
      target.addEventListener('input', () => { targetLabel.textContent = target.value; });
    }
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('normalize-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Normalizing…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('target_dbfs', target ? target.value : '-3');
      form.append('output_format', (document.getElementById('normalize-format') || {}).value || 'mp3');
      try {
        const res = await fetch('/api/tools/normalize', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Normalize failed.'); return; }
        if (status) status.textContent = `Done · ${data.size_kb || ''} KB`;
        if (result) result.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  })();

  // ---- Volume ----
  (function () {
    const btn = document.getElementById('volume-btn');
    if (!btn) return;
    const status = document.querySelector('[data-volume-status]');
    const result = document.getElementById('volume-result');
    const progress = ensureProgress(result);
    const gain = document.getElementById('volume-gain');
    const gainLabel = document.getElementById('volume-gain-label');
    if (gain && gainLabel) gain.addEventListener('input', () => { gainLabel.textContent = gain.value; });
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('volume-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Adjusting volume…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('gain_db', gain ? gain.value : '0');
      form.append('output_format', (document.getElementById('volume-format') || {}).value || 'mp3');
      try {
        const res = await fetch('/api/tools/volume', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Volume adjust failed.'); return; }
        if (status) status.textContent = `Done · ${data.size_kb || ''} KB`;
        if (result) result.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  })();

  // ---- Speed ----
  (function () {
    const btn = document.getElementById('speed-btn');
    if (!btn) return;
    const status = document.querySelector('[data-speed-status]');
    const result = document.getElementById('speed-result');
    const progress = ensureProgress(result);
    const rate = document.getElementById('speed-rate');
    const rateLabel = document.getElementById('speed-rate-label');
    function syncRate() {
      if (rate && rateLabel) rateLabel.textContent = parseFloat(rate.value).toFixed(2);
    }
    if (rate) rate.addEventListener('input', syncRate);
    document.querySelectorAll('[data-speed-preset]').forEach((b) => {
      b.addEventListener('click', () => {
        if (!rate) return;
        rate.value = b.getAttribute('data-speed-preset');
        syncRate();
      });
    });
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('speed-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Changing speed…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('speed', rate ? rate.value : '1');
      form.append('output_format', (document.getElementById('speed-format') || {}).value || 'mp3');
      const pp = document.getElementById('speed-preserve-pitch');
      form.append('preserve_pitch', pp && pp.checked ? '1' : '0');
      try {
        const res = await fetch('/api/tools/speed', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Speed change failed.'); return; }
        if (status) status.textContent = `Done · ${data.size_kb || ''} KB`;
        if (result) result.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  })();

  // ---- Fade ----
  (function () {
    const btn = document.getElementById('fade-btn');
    if (!btn) return;
    const status = document.querySelector('[data-fade-status]');
    const result = document.getElementById('fade-result');
    const progress = ensureProgress(result);
    const fin = document.getElementById('fade-in');
    const fout = document.getElementById('fade-out');
    const finL = document.getElementById('fade-in-label');
    const foutL = document.getElementById('fade-out-label');
    if (fin && finL) fin.addEventListener('input', () => { finL.textContent = fin.value; });
    if (fout && foutL) fout.addEventListener('input', () => { foutL.textContent = fout.value; });
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('fade-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Applying fades…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('fade_in_ms', fin ? fin.value : '0');
      form.append('fade_out_ms', fout ? fout.value : '0');
      form.append('output_format', (document.getElementById('fade-format') || {}).value || 'mp3');
      try {
        const res = await fetch('/api/tools/fade', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Fade failed.'); return; }
        if (status) status.textContent = `Done · ${data.size_kb || ''} KB`;
        if (result) result.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  })();

  // ---- Split by silence ----
  (function () {
    const btn = document.getElementById('split-btn');
    if (!btn) return;
    const status = document.querySelector('[data-split-status]');
    const result = document.getElementById('split-result');
    const progress = ensureProgress(result);
    const sil = document.getElementById('split-silence');
    const thr = document.getElementById('split-thresh');
    const silL = document.getElementById('split-silence-label');
    const thrL = document.getElementById('split-thresh-label');
    if (sil && silL) sil.addEventListener('input', () => { silL.textContent = sil.value; });
    if (thr && thrL) thr.addEventListener('input', () => { thrL.textContent = thr.value; });
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('split-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Splitting on silence…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('min_silence_ms', sil ? sil.value : '500');
      form.append('silence_thresh_db', thr ? thr.value : '-40');
      form.append('output_format', (document.getElementById('split-format') || {}).value || 'mp3');
      try {
        const res = await fetch('/api/tools/split-silence', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Split failed.'); return; }
        const clips = data.clips || [];
        if (status) status.textContent = `${clips.length} clip${clips.length === 1 ? '' : 's'} ready`;
        if (result) {
          const zipBtn = data.zip_b64
            ? `<a class="btn btn--brass btn--sm" style="margin-bottom:12px;display:inline-flex;"
                 download="${data.zip_filename || 'voxcraft-split.zip'}"
                 href="data:application/zip;base64,${data.zip_b64}">Download all as ZIP</a>`
            : '';
          result.innerHTML = zipBtn + clips.map((c) => `
            <div class="batch-clip" style="margin-bottom:12px;">
              <div class="batch-clip__idx">Part ${c.idx} · ${c.duration_sec}s · ${c.size_kb} KB</div>
              <audio controls src="data:audio/mpeg;base64,${c.audio_b64}"></audio>
              <a class="btn btn--ghost btn--sm" style="margin-top:6px;display:inline-flex;"
                 download="${c.filename}" href="data:audio/mpeg;base64,${c.audio_b64}">Download</a>
            </div>
          `).join('');
        }
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  })();


  function wireSimpleTool(opts) {
    const btn = document.getElementById(opts.btnId);
    if (!btn) return;
    const status = document.querySelector(opts.statusSel);
    const result = document.getElementById(opts.resultId);
    const progress = ensureProgress(result);
    if (opts.onInit) opts.onInit();
    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const fileEl = document.getElementById(opts.fileId);
      const file = fileEl && fileEl.files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = opts.busyText || 'Working…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      if (opts.append) opts.append(form);
      try {
        const res = await fetch(opts.url, { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Failed.'); return; }
        if (status) status.textContent = `Done · ${data.size_kb || ''} KB`;
        if (result) result.innerHTML = audioPlayerHtml(data.audio_b64, data.filename);
      } catch (e) {
        if (status) status.textContent = 'Network error.';
      } finally { setLoading(btn, false); showProgress(progress, false); }
    }));
  }

  wireSimpleTool({
    btnId: 'reverse-btn', fileId: 'reverse-file', statusSel: '[data-reverse-status]',
    resultId: 'reverse-result', url: '/api/tools/reverse', busyText: 'Reversing…',
    append: (f) => f.append('output_format', (document.getElementById('reverse-format') || {}).value || 'mp3'),
  });
  wireSimpleTool({
    btnId: 'mono-btn', fileId: 'mono-file', statusSel: '[data-mono-status]',
    resultId: 'mono-result', url: '/api/tools/mono', busyText: 'Converting to mono…',
    append: (f) => f.append('output_format', (document.getElementById('mono-format') || {}).value || 'mp3'),
  });
  wireSimpleTool({
    btnId: 'loop-btn', fileId: 'loop-file', statusSel: '[data-loop-status]',
    resultId: 'loop-result', url: '/api/tools/loop', busyText: 'Looping…',
    onInit: () => {
      const c = document.getElementById('loop-count');
      const l = document.getElementById('loop-count-label');
      if (c && l) c.addEventListener('input', () => { l.textContent = c.value; });
    },
    append: (f) => {
      f.append('loops', (document.getElementById('loop-count') || {}).value || '2');
      f.append('output_format', (document.getElementById('loop-format') || {}).value || 'mp3');
    },
  });
  wireSimpleTool({
    btnId: 'eq-btn', fileId: 'eq-file', statusSel: '[data-eq-status]',
    resultId: 'eq-result', url: '/api/tools/eq', busyText: 'Applying EQ…',
    onInit: () => {
      const b = document.getElementById('eq-bass');
      const t = document.getElementById('eq-treble');
      const bl = document.getElementById('eq-bass-label');
      const tl = document.getElementById('eq-treble-label');
      if (b && bl) b.addEventListener('input', () => { bl.textContent = b.value; });
      if (t && tl) t.addEventListener('input', () => { tl.textContent = t.value; });
    },
    append: (f) => {
      f.append('bass_db', (document.getElementById('eq-bass') || {}).value || '0');
      f.append('treble_db', (document.getElementById('eq-treble') || {}).value || '0');
      f.append('output_format', (document.getElementById('eq-format') || {}).value || 'mp3');
    },
  });

  // Soft-fail if ads helper is missing so tools still work on pages without ads.js
  if (!window.VoxCraftAds) {
    window.VoxCraftAds = { showInterstitial: function (cb) { if (typeof cb === 'function') cb(); } };
  }
})();
