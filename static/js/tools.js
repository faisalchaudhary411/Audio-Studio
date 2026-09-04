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
        <audio controls style="width:100%;" src="data:${mime};base64,${b64}"></audio>
        <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;" download="${filename}" href="data:${mime};base64,${b64}">Download</a>
      </div>
    `;
  }

  // Shared helpers matching studio.js generate-button behaviour
  function setLoading(btn, on) {
    if (!btn) return;
    btn.disabled = !!on;
    btn.classList.toggle('is-loading', !!on);
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
    vcEffect.addEventListener('change', () => {
      if (vcPitchControls) vcPitchControls.style.display = vcEffect.value === 'pitch_shift' ? '' : 'none';
      if (vcRobotControls) vcRobotControls.style.display = vcEffect.value === 'robot' ? '' : 'none';
      if (vcEchoControls) vcEchoControls.style.display = vcEffect.value === 'echo' ? '' : 'none';
    });
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
    const dw = document.getElementById('voicechange-drywet');
    form.append('dry_wet', dw ? dw.value : '1');
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

  // Soft-fail if ads helper is missing so tools still work on pages without ads.js
  if (!window.VoxCraftAds) {
    window.VoxCraftAds = { showInterstitial: function (cb) { if (typeof cb === 'function') cb(); } };
  }
})();
