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

  const TRANSFER_KEY = 'voxcraft_transfer_v1';
  const NEXT_TOOLS = [
    { slug: 'trim-cut-audio', label: 'Trim' },
    { slug: 'remove-background-noise', label: 'Denoise' },
    { slug: 'normalize-audio-volume', label: 'Normalize' },
    { slug: 'merge-audio-files', label: 'Merge' },
    { slug: 'convert-audio-format', label: 'Convert' },
    { slug: 'change-audio-speed', label: 'Speed' },
    { slug: 'fade-audio', label: 'Fade' },
  ];

  function saveTransfer(b64, filename, mime) {
    if (typeof voxSaveTransfer === 'function') {
      voxSaveTransfer(b64, filename, mime || 'audio/mpeg');
      return;
    }
    try {
      sessionStorage.setItem(TRANSFER_KEY, JSON.stringify({
        b64: b64,
        filename: filename || 'audio.mp3',
        mime: mime || 'audio/mpeg',
        ts: Date.now(),
      }));
    } catch (e) {
      // quota exceeded — ignore
    }
  }

  function loadTransfer() {
    try {
      const raw = sessionStorage.getItem(TRANSFER_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      // Expire after 30 minutes
      if (!data || !data.b64 || (Date.now() - (data.ts || 0)) > 30 * 60 * 1000) {
        sessionStorage.removeItem(TRANSFER_KEY);
        return null;
      }
      return data;
    } catch (e) {
      return null;
    }
  }

  function clearTransfer() {
    try { sessionStorage.removeItem(TRANSFER_KEY); } catch (e) {}
  }

  function fileFromTransfer(data) {
    const bin = atob(data.b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    return new File([arr], data.filename || 'audio.mp3', { type: data.mime || 'audio/mpeg' });
  }

  function applyTransferToInput(input, data) {
    if (!input || !data) return false;
    try {
      const file = fileFromTransfer(data);
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    } catch (e) {
      return false;
    }
  }

  function audioPlayerHtml(b64, filename, mime) {
    mime = mime || 'audio/mpeg';
    // Prefer sitewide helper from main.js (quota-safe + same panel markup)
    if (typeof voxAudioPlayerHtml === 'function') {
      return voxAudioPlayerHtml(b64, filename, mime);
    }
    saveTransfer(b64, filename, mime);
    const links = NEXT_TOOLS.map((t) =>
      `<a class="btn btn--ghost btn--sm" data-send-tool="${t.slug}" href="/tools/${t.slug}">${t.label}</a>`
    ).join('');
    return `
      <div class="result-panel" data-vox-b64-pending="1">
        <audio controls data-vox-audio-src></audio>
        <div class="result-panel__actions">
          <button type="button" class="btn btn--brass btn--sm" data-vox-download disabled>Preparing download…</button>
          <button type="button" class="btn btn--ghost btn--sm" onclick="this.closest('.result-panel').querySelector('audio').play()">Play again</button>
        </div>
        <div class="result-panel__next">
          <span class="result-panel__next-label">Send to another tool</span>
          <div class="result-panel__next-links">${links}</div>
        </div>
      </div>
    `;
  }

  /** Insert player HTML and hydrate blob URL via background worker. */
  function setAudioResult(el, b64, filename, mime) {
    if (!el) return;
    mime = mime || 'audio/mpeg';
    el.innerHTML = audioPlayerHtml(b64, filename, mime);
    if (typeof voxHydrateAudioResult === 'function') {
      voxHydrateAudioResult(el, b64, filename, mime);
    }
  }

  // When landing on a tool with a saved transfer, offer to load it
  function offerIncomingTransfer() {
    // Prefer the shared implementation from main.js (IndexedDB + auto-apply)
    if (typeof voxOfferIncomingTransfer === 'function') {
      Promise.resolve(voxOfferIncomingTransfer({ autoApply: true })).catch(() => {});
      return;
    }
    const data = loadTransfer();
    if (!data) return;
    const input = document.querySelector('input.file-input[type="file"]:not([style*="display:none"])');
    if (!input) return;
    const panel = input.closest('.panel') || document.body;
    if (panel.querySelector('[data-transfer-banner]')) return;
    const ban = document.createElement('div');
    ban.setAttribute('data-transfer-banner', '1');
    ban.style.cssText = 'margin-bottom:12px;padding:10px 12px;border-radius:10px;border:1px solid rgba(79,166,156,0.35);background:rgba(79,166,156,0.08);font-size:0.85rem;color:var(--text-mid);display:flex;flex-wrap:wrap;gap:8px;align-items:center;';
    ban.innerHTML = `<span>Audio from previous tool ready: <strong style="color:var(--text-hi)">${(data.filename || 'file').replace(/[<>]/g,'')}</strong></span>`;
    const useBtn = document.createElement('button');
    useBtn.type = 'button';
    useBtn.className = 'btn btn--brass btn--sm';
    useBtn.textContent = 'Use this file';
    useBtn.addEventListener('click', () => {
      if (applyTransferToInput(input, data)) {
        ban.innerHTML = '<span style="color:var(--jade-hi)">File loaded — adjust settings and run the tool.</span>';
      } else {
        ban.innerHTML = '<span style="color:var(--brass-hi)">Could not load automatically — please choose the file again.</span>';
      }
    });
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'btn btn--ghost btn--sm';
    dismiss.textContent = 'Dismiss';
    dismiss.addEventListener('click', () => { clearTransfer(); ban.remove(); });
    ban.appendChild(useBtn);
    ban.appendChild(dismiss);
    panel.insertBefore(ban, panel.firstChild);
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-send-tool]');
    if (!a) return;
    // transfer already saved by audioPlayerHtml; navigation proceeds
  });


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
        ? 'or tap to choose files · 15MB max each'
        : 'or tap to choose · 15MB max';
      const name = document.createElement('div');
      name.className = 'dropzone__name';
      input.parentNode.insertBefore(zone, input);
      zone.appendChild(title);
      zone.appendChild(hint);
      zone.appendChild(input);
      zone.appendChild(name);
      const formatSize = (bytes) => {
        if (!bytes && bytes !== 0) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      };
      const updateName = () => {
        const files = input.files;
        if (!files || !files.length) { name.textContent = ''; return; }
        if (files.length === 1) {
          name.textContent = files[0].name + ' · ' + formatSize(files[0].size);
        } else {
          let total = 0;
          for (let i = 0; i < files.length; i++) total += files[i].size || 0;
          name.textContent = files.length + ' files · ' + formatSize(total);
        }
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
  // BUG FIX: offerIncomingTransfer() was defined above but never actually
  // called anywhere in this file (or any template) — so a file saved via
  // saveTransfer()/audioPlayerHtml() on one tool's result panel was written
  // to sessionStorage correctly, but the destination tool page never read
  // it back. Every "Send to another tool" link across the whole site was a
  // dead handoff: it navigated to the next tool but never offered the file.
  function initPage() {
    enhanceFileInputs();
    // After dropzones exist, load any staged audio from clone/music/studio
    offerIncomingTransfer();
    // Second pass: IDB is async; catch late readiness
    setTimeout(offerIncomingTransfer, 200);
    setTimeout(offerIncomingTransfer, 600);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPage);
  } else {
    initPage();
  }

  // Shared helpers matching studio.js generate-button behaviour — both
  // now delegate to the sitewide voxSetBusy/voxShowProgress in main.js,
  // which is loaded before this file on every page.
  function setLoading(btn, on) {
    voxSetBusy(btn, on);
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
    voxShowProgress(bar, on);
  }

  function friendlyError(data, fallback) {
    const msg = (data && (data.error || data.message)) || fallback || 'Something went wrong.';
    if (/limit|quota|daily|monthly/i.test(msg)) {
      return msg + ' — See Pricing for higher limits.';
    }
    if (/network|fetch|failed to fetch/i.test(msg)) {
      return 'Network error — check your connection and try again.';
    }
    if (/too large|file size|10mb|15mb|50mb/i.test(msg)) {
      return msg + ' Try a shorter clip or compress first.';
    }
    if (/no file|choose a file|upload/i.test(msg)) {
      return 'Choose an audio file first.';
    }
    return msg;
  }

  /** Consistent empty / error panels for tool result areas. */
  function toolEmptyHtml(title, body) {
    return `<div class="tool-empty"><strong>${title || 'Nothing here yet'}</strong>${body || 'Upload a file and run the tool to see results.'}</div>`;
  }
  function toolErrorHtml(msg) {
    const safe = String(msg || 'Something went wrong.').replace(/[<>&]/g, (ch) => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[ch]));
    const upgrade = /limit|quota|pricing/i.test(safe)
      ? ` <a href="/pricing">See plans</a>`
      : '';
    return `<div class="tool-error" role="alert"><strong>Couldn’t finish</strong>${safe}${upgrade}</div>`;
  }
  function setToolError(resultEl, statusEl, data, fallback) {
    const msg = friendlyError(data, fallback);
    if (statusEl) statusEl.textContent = msg;
    if (resultEl) resultEl.innerHTML = toolErrorHtml(msg);
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
        setToolError(transcribeResult, transcribeStatus, data, 'Transcription failed.');
        return;
      }
      const wordBit = data.word_count ? `${data.word_count} words` : '';
      const durBit = data.duration_sec ? ` · ${Number(data.duration_sec).toFixed(0)}s` : '';
      const partialBit = data.partial ? ' · may be partial' : '';
      if (transcribeStatus) {
        transcribeStatus.textContent = wordBit
          ? `Done · ${wordBit}${durBit}${partialBit}`
          : `Done${partialBit}`;
      }
      if (transcribeResult) {
        // Build DOM nodes so Urdu/Hindi is never HTML-escaped wrong and downloads
        // use a real UTF-8 Blob (data: URIs often save without charset on Android).
        transcribeResult.innerHTML = '';
        const metaP = document.createElement('p');
        metaP.style.cssText = 'font-size:0.8rem;color:var(--text-dim);margin-bottom:6px;';
        metaP.textContent = wordBit
          ? `${wordBit}${durBit}${partialBit}`
          : (partialBit ? 'Transcript may be partial' : '');
        const ta = document.createElement('textarea');
        ta.className = 'script-input';
        ta.style.minHeight = '140px';
        ta.readOnly = true;
        ta.dir = 'auto'; // RTL for Urdu/Arabic, LTR for English
        ta.value = data.text || '';
        const actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;';
        const txtBtn = document.createElement('button');
        txtBtn.type = 'button';
        txtBtn.className = 'btn btn--ghost btn--sm';
        txtBtn.textContent = 'Download TXT';
        txtBtn.addEventListener('click', () => {
          if (typeof voxDownloadUtf8Text === 'function') {
            voxDownloadUtf8Text('transcription.txt', data.text || '', 'text/plain');
          } else {
            // Fallback: BOM + base64 data URI
            const bom = '﻿' + (data.text || '');
            const b64 = btoa(unescape(encodeURIComponent(bom)));
            const a = document.createElement('a');
            a.href = 'data:text/plain;charset=utf-8;base64,' + b64;
            a.download = 'transcription.txt';
            a.click();
          }
        });
        actions.appendChild(txtBtn);
        if (data.srt) {
          const srtBtn = document.createElement('button');
          srtBtn.type = 'button';
          srtBtn.className = 'btn btn--ghost btn--sm';
          srtBtn.textContent = 'Download SRT';
          srtBtn.addEventListener('click', () => {
            if (typeof voxDownloadUtf8Text === 'function') {
              voxDownloadUtf8Text('captions.srt', data.srt, 'application/x-subrip');
            } else {
              const bom = '﻿' + data.srt;
              const b64 = btoa(unescape(encodeURIComponent(bom)));
              const a = document.createElement('a');
              a.href = 'data:application/x-subrip;charset=utf-8;base64,' + b64;
              a.download = 'captions.srt';
              a.click();
            }
          });
          actions.appendChild(srtBtn);
        }
        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'btn btn--ghost btn--sm';
        copyBtn.textContent = 'Copy text';
        copyBtn.addEventListener('click', async () => {
          try {
            await navigator.clipboard.writeText(data.text || '');
            copyBtn.textContent = 'Copied';
            setTimeout(() => { copyBtn.textContent = 'Copy text'; }, 1500);
          } catch (e) {
            ta.select();
            document.execCommand('copy');
          }
        });
        actions.appendChild(copyBtn);
        transcribeResult.appendChild(metaP);
        transcribeResult.appendChild(ta);
        transcribeResult.appendChild(actions);
      }
    } catch (e) {
      setToolError(transcribeResult, transcribeStatus, null, 'Network error — check your connection and try again.');
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
        setToolError(convertResult, convertStatus, data, 'Conversion failed.');
        return;
      }
      if (convertStatus) convertStatus.textContent = `Converted to ${(data.format || '').toUpperCase()}`;
      if (convertResult) setAudioResult(convertResult, data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      setToolError(convertResult, convertStatus, null, 'Network error — check your connection and try again.');
    } finally {
      setLoading(convertBtn, false);
      showProgress(convertProgress, false);
    }
  }

  // ---- Compress ----
  const compressBtn = document.getElementById('compress-btn');
  const compressStatus = document.querySelector('[data-compress-status]');
  const compressResult = document.getElementById('compress-result');
  const compressProgress = ensureProgress(compressResult);
  if (compressBtn) {
    compressBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runCompress);
    });
  }
  async function runCompress() {
    const file = document.getElementById('compress-file').files[0];
    if (!file) {
      if (compressStatus) compressStatus.textContent = 'Choose a file first.';
      return;
    }
    setLoading(compressBtn, true);
    showProgress(compressProgress, true);
    if (compressStatus) compressStatus.textContent = 'Compressing…';
    if (compressResult) compressResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('level', document.getElementById('compress-level').value);
    try {
      const res = await fetch('/api/tools/compress', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setToolError(compressResult, compressStatus, data, 'Compression failed.');
        return;
      }
      const savedMsg = (typeof data.saved_pct === 'number')
        ? `${data.original_size_mb}MB → ${data.output_size_mb}MB (${data.saved_pct}% smaller)`
        : 'Compressed';
      if (compressStatus) compressStatus.textContent = savedMsg;
      if (compressResult) setAudioResult(compressResult, data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      setToolError(compressResult, compressStatus, null, 'Network error — check your connection and try again.');
    } finally {
      setLoading(compressBtn, false);
      showProgress(compressProgress, false);
    }
  }

  // ---- Decompress ----
  const decompressBtn = document.getElementById('decompress-btn');
  const decompressStatus = document.querySelector('[data-decompress-status]');
  const decompressResult = document.getElementById('decompress-result');
  const decompressProgress = ensureProgress(decompressResult);
  if (decompressBtn) {
    decompressBtn.addEventListener('click', () => {
      window.VoxCraftAds.showInterstitial(runDecompress);
    });
  }
  async function runDecompress() {
    const file = document.getElementById('decompress-file').files[0];
    if (!file) {
      if (decompressStatus) decompressStatus.textContent = 'Choose a file first.';
      return;
    }
    const presetEl = document.getElementById('decompress-preset');
    const preset = presetEl ? (presetEl.value || 'voice') : 'voice';
    setLoading(decompressBtn, true);
    showProgress(decompressProgress, true);
    if (decompressStatus) decompressStatus.textContent = 'Decompressing…';
    if (decompressResult) decompressResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('preset', preset);
    try {
      const res = await fetch('/api/tools/decompress', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setToolError(decompressResult, decompressStatus, data, 'Decompression failed.');
        return;
      }
      const ch = data.channels === 1 ? 'mono' : (data.channels === 2 ? 'stereo' : '');
      const rate = data.sample_rate ? `${Math.round(data.sample_rate / 1000 * 10) / 10}kHz` : '';
      const detail = [ch, rate].filter(Boolean).join(' ');
      if (decompressStatus) {
        decompressStatus.textContent = detail
          ? `${data.original_size_mb}MB → ${data.output_size_mb}MB WAV (${detail})`
          : `${data.original_size_mb}MB → ${data.output_size_mb}MB (WAV)`;
      }
      if (decompressResult) setAudioResult(decompressResult, data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      setToolError(decompressResult, decompressStatus, null, 'Network error — check your connection and try again.');
    } finally {
      setLoading(decompressBtn, false);
      showProgress(decompressProgress, false);
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
        setToolError(mergeResult, mergeStatus, data, 'Merge failed.');
        return;
      }
      if (mergeStatus) mergeStatus.textContent = `Merged ${mergeSelectedFiles.length} files`;
      if (mergeResult) setAudioResult(mergeResult, data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      setToolError(mergeResult, mergeStatus, null, 'Network error — check your connection and try again.');
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
          setToolError(cutterResult, cutterStatus, data, 'Auto-trim failed.');
          return;
        }
        if (cutterStatus) cutterStatus.textContent = 'Silence trimmed';
        if (cutterResult) setAudioResult(cutterResult, data.audio_b64, data.filename);
      } else if (cutterMode === 'trim') {
        if (cutterStatus) cutterStatus.textContent = 'Trimming…';
        form.append('start_sec', document.getElementById('cutter-start').value);
        form.append('end_sec', document.getElementById('cutter-end').value);
        const res = await fetch('/api/tools/cutter/trim', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setToolError(cutterResult, cutterStatus, data, 'Trim failed.');
          return;
        }
        if (cutterStatus) cutterStatus.textContent = 'Trimmed';
        if (cutterResult) setAudioResult(cutterResult, data.audio_b64, data.filename);
      } else {
        if (cutterStatus) cutterStatus.textContent = 'Splitting…';
        const splitEl = document.getElementById('cutter-split') || document.getElementById('cutter-split-at');
        form.append('split_sec', splitEl ? splitEl.value : '0');
        const res = await fetch('/api/tools/cutter/split', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setToolError(cutterResult, cutterStatus, data, 'Split failed.');
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
      setToolError(cutterResult, cutterStatus, null, 'Network error — check your connection and try again.');
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

  // Standard / Studio (AI) engine toggle
  const denoiseEngineStandardBtn = document.getElementById('denoise-engine-standard');
  const denoiseEngineStudioBtn = document.getElementById('denoise-engine-studio');
  const denoiseStandardControls = document.getElementById('denoise-standard-controls');
  const denoiseStudioNote = document.getElementById('denoise-studio-note');
  let denoiseEngine = 'standard';
  function setDenoiseEngine(next) {
    if (next === 'studio' && denoiseEngineStudioBtn && denoiseEngineStudioBtn.disabled) return; // Pro-gated
    denoiseEngine = next;
    const isStandard = denoiseEngine === 'standard';
    if (denoiseEngineStandardBtn) {
      denoiseEngineStandardBtn.dataset.active = isStandard ? 'true' : 'false';
      denoiseEngineStandardBtn.classList.toggle('btn--brass', isStandard);
    }
    if (denoiseEngineStudioBtn) {
      denoiseEngineStudioBtn.dataset.active = isStandard ? 'false' : 'true';
      denoiseEngineStudioBtn.classList.toggle('btn--brass', !isStandard);
    }
    if (denoiseStandardControls) denoiseStandardControls.style.display = isStandard ? '' : 'none';
    if (denoiseStudioNote) denoiseStudioNote.style.display = isStandard ? 'none' : '';
  }
  if (denoiseEngineStandardBtn) denoiseEngineStandardBtn.addEventListener('click', () => setDenoiseEngine('standard'));
  if (denoiseEngineStudioBtn) denoiseEngineStudioBtn.addEventListener('click', () => setDenoiseEngine('studio'));

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
    if (denoiseStatus) denoiseStatus.textContent = denoiseEngine === 'studio' ? 'Running AI enhancement…' : 'Removing noise…';
    if (denoiseResult) denoiseResult.innerHTML = '';
    const form = new FormData();
    form.append('file', file);
    form.append('engine', denoiseEngine);
    form.append('strength', denoiseStrength ? denoiseStrength.value : '0.5');
    const st = document.getElementById('denoise-stationary');
    form.append('stationary', st && st.checked ? '1' : '0');
    const ps = document.getElementById('denoise-preserve-stereo');
    form.append('preserve_stereo', ps && ps.checked ? '1' : '0');
    try {
      const res = await fetch('/api/tools/denoise', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setToolError(denoiseResult, denoiseStatus, data, 'Denoise failed.');
        return;
      }
      if (denoiseStatus) denoiseStatus.textContent = data.engine === 'studio' ? 'Enhanced (Studio AI)' : 'Noise removed';
      if (denoiseResult) setAudioResult(denoiseResult, data.audio_b64, data.filename);
    } catch (e) {
      setToolError(denoiseResult, denoiseStatus, null, 'Network error — check your connection and try again.');
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
        setToolError(vcResult, vcStatus, data, 'Effect failed.');
        return;
      }
      if (vcStatus) vcStatus.textContent = 'Effect applied';
      if (vcResult) setAudioResult(vcResult, data.audio_b64, data.filename);
    } catch (e) {
      setToolError(vcResult, vcStatus, null, 'Network error — check your connection and try again.');
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
        setToolError(vxResult, vxStatus, data, 'Extraction failed.');
        return;
      }
      if (vxStatus) vxStatus.textContent = `Extracted · ${data.size_kb} KB`;
      if (vxResult) setAudioResult(vxResult, data.audio_b64, data.filename, mimeFor(data.format));
    } catch (e) {
      setToolError(vxResult, vxStatus, null, 'Network error — check your connection and try again.');
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

    // Peak / LUFS mode toggle
    const peakModeBtn = document.getElementById('normalize-mode-peak');
    const lufsModeBtn = document.getElementById('normalize-mode-lufs');
    const peakControls = document.getElementById('normalize-peak-controls');
    const lufsControls = document.getElementById('normalize-lufs-controls');
    let mode = 'peak';
    function setMode(next) {
      mode = next;
      const isPeak = mode === 'peak';
      if (peakModeBtn) peakModeBtn.dataset.active = isPeak ? 'true' : 'false';
      if (lufsModeBtn) lufsModeBtn.dataset.active = isPeak ? 'false' : 'true';
      if (peakModeBtn) peakModeBtn.classList.toggle('btn--brass', isPeak);
      if (lufsModeBtn) lufsModeBtn.classList.toggle('btn--brass', !isPeak);
      if (peakControls) peakControls.style.display = isPeak ? '' : 'none';
      if (lufsControls) lufsControls.style.display = isPeak ? 'none' : '';
    }
    if (peakModeBtn) peakModeBtn.addEventListener('click', () => setMode('peak'));
    if (lufsModeBtn) lufsModeBtn.addEventListener('click', () => setMode('lufs'));

    // LUFS preset dropdown (Streaming / Podcast / Broadcast / Custom)
    const lufsPreset = document.getElementById('normalize-lufs-preset');
    const lufsCustomRow = document.getElementById('normalize-lufs-custom-row');
    const lufsCustom = document.getElementById('normalize-lufs-custom');
    const lufsCustomLabel = document.getElementById('normalize-lufs-custom-label');
    if (lufsPreset) {
      lufsPreset.addEventListener('change', () => {
        const isCustom = lufsPreset.value === 'custom';
        if (lufsCustomRow) lufsCustomRow.style.display = isCustom ? '' : 'none';
      });
    }
    if (lufsCustom && lufsCustomLabel) {
      lufsCustom.addEventListener('input', () => { lufsCustomLabel.textContent = lufsCustom.value; });
    }
    function currentTargetLufs() {
      if (!lufsPreset) return -16;
      if (lufsPreset.value === 'custom') return lufsCustom ? lufsCustom.value : -16;
      return lufsPreset.value;
    }

    btn.addEventListener('click', () => window.VoxCraftAds.showInterstitial(async () => {
      const file = document.getElementById('normalize-file').files[0];
      if (!file) { if (status) status.textContent = 'Choose a file first.'; return; }
      setLoading(btn, true); showProgress(progress, true);
      if (status) status.textContent = 'Normalizing…';
      if (result) result.innerHTML = '';
      const form = new FormData();
      form.append('file', file);
      form.append('mode', mode);
      form.append('target_dbfs', target ? target.value : '-3');
      form.append('target_lufs', currentTargetLufs());
      form.append('output_format', (document.getElementById('normalize-format') || {}).value || 'mp3');
      try {
        const res = await fetch('/api/tools/normalize', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (status) status.textContent = friendlyError(data, 'Normalize failed.'); return; }
        let statusText = `Done · ${data.size_kb || ''} KB`;
        if (data.mode === 'lufs' && data.target_lufs != null) {
          const before = data.before_lufs != null ? `${data.before_lufs} LUFS → ` : '';
          statusText = `Done · ${before}${data.target_lufs} LUFS · ${data.size_kb || ''} KB`;
        }
        if (status) status.textContent = statusText;
        if (result) setAudioResult(result, data.audio_b64, data.filename);
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
        if (result) setAudioResult(result, data.audio_b64, data.filename);
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
        if (result) setAudioResult(result, data.audio_b64, data.filename);
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
        if (result) setAudioResult(result, data.audio_b64, data.filename);
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
          result.innerHTML = `
            <div data-split-extra style="margin-bottom:12px;"></div>
            ${clips.map((c, i) => `
              <div class="batch-clip" style="margin-bottom:12px;" data-split-clip="${i}">
                <div class="batch-clip__idx">Part ${c.idx} · ${c.duration_sec}s · ${c.size_kb} KB</div>
                <audio controls data-vox-audio-src preload="metadata"></audio>
                <button type="button" class="btn btn--ghost btn--sm" style="margin-top:6px;display:inline-flex;"
                   data-vox-download disabled>Preparing…</button>
              </div>
            `).join('')}`;
          (async function () {
            const toUrl = typeof voxB64ToObjectURL === 'function'
              ? voxB64ToObjectURL
              : async (b64, mime) => {
                  const bin = atob(b64.replace(/^data:[^;]+;base64,/, ''));
                  const bytes = new Uint8Array(bin.length);
                  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                  return URL.createObjectURL(new Blob([bytes], { type: mime }));
                };
            if (data.zip_b64) {
              try {
                const url = await toUrl(data.zip_b64, 'application/zip');
                const wrap = result.querySelector('[data-split-extra]');
                if (wrap) {
                  const btn = document.createElement('button');
                  btn.type = 'button';
                  btn.className = 'btn btn--brass btn--sm';
                  btn.style.cssText = 'margin-bottom:12px;display:inline-flex;';
                  btn.textContent = 'Download all as ZIP';
                  btn.onclick = () => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = data.zip_filename || 'voxcraft-split.zip';
                    a.click();
                  };
                  wrap.appendChild(btn);
                }
              } catch (e) {}
            }
            for (let i = 0; i < clips.length; i++) {
              const c = clips[i];
              const el = result.querySelector(`[data-split-clip="${i}"]`);
              if (!el || !c.audio_b64) continue;
              try {
                const url = await toUrl(c.audio_b64, 'audio/mpeg');
                const audio = el.querySelector('audio');
                const btn = el.querySelector('[data-vox-download]');
                if (audio) audio.src = url;
                if (btn) {
                  btn.disabled = false;
                  btn.textContent = 'Download';
                  btn.onclick = () => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = c.filename || ('part-' + c.idx + '.mp3');
                    a.click();
                  };
                }
              } catch (e) {}
            }
          })();
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
        if (result) setAudioResult(result, data.audio_b64, data.filename);
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

  // ---- Video audio redub (Pro) ----
  (function initRedub() {
    const fileInput = document.getElementById('redub-file');
    const btn = document.getElementById('redub-btn');
    const status = document.querySelector('[data-redub-status]');
    const result = document.getElementById('redub-result');
    const progress = document.getElementById('redub-progress');
    const sourceLang = document.getElementById('redub-source-lang');
    const targetLang = document.getElementById('redub-target-lang');
    const voiceSelect = document.getElementById('redub-voice');
    const voiceSelectB = document.getElementById('redub-voice-b');
    const speed = document.getElementById('redub-speed');
    const speedLabel = document.getElementById('redub-speed-label');
    if (!btn || !fileInput) return;

    const VOICES = window.VOXCRAFT_VOICES || {};

    function populateVoices() {
      if (!targetLang) return;
      const lang = targetLang.value;
      const voices = VOICES[lang] || {};
      if (voiceSelect) {
        voiceSelect.innerHTML = '';
        Object.entries(voices).forEach(([name, id]) => {
          const opt = document.createElement('option');
          opt.value = id;
          opt.textContent = name;
          voiceSelect.appendChild(opt);
        });
      }
      if (voiceSelectB) {
        const prev = voiceSelectB.value;
        voiceSelectB.innerHTML = '';
        const none = document.createElement('option');
        none.value = '';
        none.textContent = 'Same as primary';
        voiceSelectB.appendChild(none);
        Object.entries(voices).forEach(([name, id]) => {
          const opt = document.createElement('option');
          opt.value = id;
          opt.textContent = name;
          voiceSelectB.appendChild(opt);
        });
        if (prev && Array.from(voiceSelectB.options).some(o => o.value === prev)) {
          voiceSelectB.value = prev;
        }
      }
    }
    if (targetLang) {
      targetLang.addEventListener('change', populateVoices);
      populateVoices();
    }
    if (speed && speedLabel) {
      speed.addEventListener('input', () => { speedLabel.textContent = speed.value + '%'; });
    }

    const nameEl = document.querySelector('[data-redub-filename]');
    fileInput.addEventListener('change', () => {
      const f = fileInput.files && fileInput.files[0];
      if (nameEl) {
        if (f) {
          const mb = (f.size / (1024 * 1024)).toFixed(1);
          nameEl.textContent = f.name + ' · ' + mb + ' MB';
        } else {
          nameEl.textContent = '';
        }
      }
    });

    function setBusy(on) {
      btn.disabled = !!on;
      if (typeof voxSetBusy === 'function') voxSetBusy(btn, on);
      else btn.classList.toggle('is-loading', !!on);
      if (progress) {
        progress.classList.toggle('is-active', !!on);
        progress.setAttribute('aria-hidden', on ? 'false' : 'true');
      }
    }

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    btn.addEventListener('click', async () => {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        if (status) status.textContent = 'Choose a video file first.';
        return;
      }
      if (!voiceSelect || !voiceSelect.value) {
        if (status) status.textContent = 'Pick a target voice.';
        return;
      }

      setBusy(true);
      if (result) result.innerHTML = '';
      const asrChoice = (document.getElementById('redub-asr-engine') || {}).value || 'auto';
      const slowHint = (asrChoice === 'whisper' || asrChoice === 'auto')
        ? 'Whisper GPU may take 30–90s on first run…'
        : 'this can take a minute.';
      if (status) status.textContent = 'Extracting · transcribing · translating · re-voicing… ' + slowHint;

      const form = new FormData();
      form.append('file', file);
      form.append('source_lang', sourceLang ? sourceLang.value : 'auto');
      form.append('target_lang', targetLang ? targetLang.value : 'US English');
      form.append('voice_id', voiceSelect.value);
      if (voiceSelectB && voiceSelectB.value) {
        form.append('voice_id_b', voiceSelectB.value);
      }
      const asrEl = document.getElementById('redub-asr-engine');
      form.append('asr_engine', asrEl ? asrEl.value : 'auto');
      form.append('speed_pct', speed ? speed.value : '100');
      const matchEl = document.getElementById('redub-match-length');
      form.append('match_length', matchEl && matchEl.checked ? '1' : '0');

      try {
        const res = await fetch('/api/tools/redub', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const msg = data.error || 'Redub failed.';
          if (status) status.textContent = msg;
          if (result && data.upgrade_url) {
            result.innerHTML = '<div class="limit-toast">' + msg +
              ' <a href="' + data.upgrade_url + '" style="color:var(--brass-hi);margin-left:6px;">See plans →</a></div>';
          }
          return;
        }

        if (status) {
          let msg = data.skipped_translation
            ? ('Done · same language, voice replaced · ' + (data.size_kb || '') + ' KB')
            : ('Done · ' + (data.char_count || 0) + ' chars · ' + (data.size_kb || '') + ' KB');
          if (data.timed_segments) msg += ' · ' + data.timed_segments + ' timed segments';
          else if (data.length_matched) msg += ' · length matched';
          status.textContent = msg;
          status.classList.add('studio-status-ready');
        }
        if (typeof voxButtonSuccess === 'function') voxButtonSuccess(btn);

        const videoName = data.filename || 'VoxCraft-Redub.mp4';
        const audioName = data.audio_filename || 'VoxCraft-Redub-Audio.mp3';
        const notes = [data.translation_note, data.voice_note, data.length_note].filter(Boolean);
        const notesHtml = notes.map(function (n) {
          return '<div class="limit-toast" style="margin-bottom:10px;">⚠ ' + escapeHtml(n) + '</div>';
        }).join('');
        if (result) {
          result.innerHTML =
            '<div class="result-panel">' +
              '<div class="result-panel__label">Dubbed video</div>' +
              notesHtml +
              '<div class="redub-video-wrap">' +
                '<video class="redub-video-player" data-redub-video-el controls playsinline preload="metadata"></video>' +
                '<div class="redub-video-wrap__placeholder" data-redub-video-placeholder>Preparing preview…</div>' +
              '</div>' +
              '<p style="color:var(--text-mid);font-size:0.85rem;margin:0 0 10px;">' +
                (data.skipped_translation ? 'Translation skipped (same language). ' : '') +
                (data.length_matched ? 'Audio stretched to match original length. ' : '') +
                'New voice: <strong style="color:var(--text-hi);">' + (data.target_lang || '') + '</strong>' +
                ' · ' + (data.char_count || 0) + ' characters billed to your TTS quota' +
              '</p>' +
              '<div class="result-panel__actions" style="display:flex;flex-wrap:wrap;gap:8px;">' +
                '<button type="button" class="btn btn--brass btn--sm" data-redub-dl-video disabled>Preparing video…</button>' +
                '<button type="button" class="btn btn--ghost btn--sm" data-redub-dl-audio disabled>Preparing audio…</button>' +
              '</div>' +
              '<details style="margin-top:12px;">' +
                '<summary style="cursor:pointer;color:var(--text-mid);font-size:0.85rem;">Show transcript &amp; translation</summary>' +
                '<div style="margin-top:8px;display:grid;gap:10px;">' +
                  '<div><div style="font-family:var(--mono);font-size:0.72rem;color:var(--brass);margin-bottom:4px;">ORIGINAL</div>' +
                  '<pre style="white-space:pre-wrap;font-size:0.85rem;color:var(--text-mid);background:var(--ink);padding:10px;border-radius:8px;margin:0;max-height:160px;overflow:auto;">' +
                  escapeHtml(data.transcript || '') + '</pre></div>' +
                  '<div><div style="font-family:var(--mono);font-size:0.72rem;color:var(--brass);margin-bottom:4px;">TRANSLATED / RE-VOICED</div>' +
                  '<pre style="white-space:pre-wrap;font-size:0.85rem;color:var(--text-mid);background:var(--ink);padding:10px;border-radius:8px;margin:0;max-height:160px;overflow:auto;">' +
                  escapeHtml(data.translated || '') + '</pre></div>' +
                '</div>' +
              '</details>' +
            '</div>';

          // Prefer download URLs (no multi-MB base64 in the JSON response)
          const videoUrl = data.download_video_url || null;
          const audioUrl = data.download_audio_url || null;
          try {
            if (videoUrl) {
              const vid = result.querySelector('[data-redub-video-el]');
              const placeholder = result.querySelector('[data-redub-video-placeholder]');
              if (vid) {
                vid.src = videoUrl;
                vid.classList.add('is-ready');
              }
              if (placeholder) placeholder.remove();
              const b = result.querySelector('[data-redub-dl-video]');
              if (b) {
                b.disabled = false;
                b.textContent = 'Download dubbed MP4';
                b.onclick = function () {
                  const a = document.createElement('a');
                  a.href = videoUrl;
                  a.download = videoName;
                  a.rel = 'noopener';
                  a.click();
                };
              }
            }
            if (audioUrl) {
              const b = result.querySelector('[data-redub-dl-audio]');
              if (b) {
                b.disabled = false;
                b.textContent = 'Download audio only';
                b.onclick = function () {
                  const a = document.createElement('a');
                  a.href = audioUrl;
                  a.download = audioName;
                  a.rel = 'noopener';
                  a.click();
                };
              }
            }
            if (!videoUrl && !audioUrl) {
              const placeholder = result.querySelector('[data-redub-video-placeholder]');
              if (placeholder) placeholder.textContent = 'Download links unavailable — please try again.';
            }
          } catch (e) {
            console.warn('[voxcraft] redub download hydrate failed', e);
            if (status) status.textContent = 'Ready — use the download buttons below.';
            const placeholder = result.querySelector('[data-redub-video-placeholder]');
            if (placeholder) placeholder.textContent = 'Preview unavailable — use the download button below.';
          }
        }
      } catch (e) {
        if (status) status.textContent = 'Network error — check your connection and try again.';
      } finally {
        setBusy(false);
      }
    });
  })();
})();
