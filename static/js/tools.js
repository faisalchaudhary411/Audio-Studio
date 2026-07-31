// ===== VoxCraft — Tools hub (Transcribe / Convert / Merge / Cutter) =====
(function () {
  // ---- Tab switching ----
  const tabs = document.querySelectorAll('[data-tool-tab]');
  const panels = {
    transcribe: document.getElementById('panel-transcribe'),
    convert: document.getElementById('panel-convert'),
    merge: document.getElementById('panel-merge'),
    cutter: document.getElementById('panel-cutter'),
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
})();
