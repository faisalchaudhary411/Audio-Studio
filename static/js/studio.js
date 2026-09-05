// ===== VoxCraft Studio JS =====
(function () {
  const VOICES = window.VOXCRAFT_VOICES || {};
  const langSelect = document.getElementById('language-select');
  const voiceSelect = document.getElementById('voice-select');
  const speedSlider = document.getElementById('speed-slider');
  const speedLabel = document.getElementById('speed-label');

  function populateVoices() {
    const lang = langSelect.value;
    const voices = VOICES[lang] || {};
    voiceSelect.innerHTML = '';
    Object.entries(voices).forEach(([name, id]) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = name;
      voiceSelect.appendChild(opt);
    });
  }
  langSelect.addEventListener('change', () => {
    populateVoices();
    try { localStorage.setItem('vox_lang', langSelect.value); } catch (e) {}
  });
  // Restore last language + voice
  try {
    const savedLang = localStorage.getItem('vox_lang');
    if (savedLang && VOICES[savedLang]) langSelect.value = savedLang;
  } catch (e) {}
  populateVoices();
  try {
    const savedVoice = localStorage.getItem('vox_voice');
    if (savedVoice) {
      for (const opt of voiceSelect.options) {
        if (opt.value === savedVoice) { voiceSelect.value = savedVoice; break; }
      }
    }
  } catch (e) {}
  voiceSelect.addEventListener('change', () => {
    try { localStorage.setItem('vox_voice', voiceSelect.value); } catch (e) {}
  });

  speedSlider.addEventListener('input', () => {
    speedLabel.textContent = speedSlider.value + '%';
  });

  // ---- Tabs ----
  const tabButtons = {
    single: document.getElementById('tab-single-btn'),
    batch: document.getElementById('tab-batch-btn'),
  };
  const tabPanels = {
    single: document.getElementById('tab-single'),
    batch: document.getElementById('tab-batch'),
  };
  function showTab(name) {
    Object.keys(tabPanels).forEach((key) => {
      if (!tabPanels[key] || !tabButtons[key]) return;
      const active = key === name;
      tabPanels[key].style.display = active ? '' : 'none';
      const btn = tabButtons[key];
      if (btn.classList.contains('mode-tab')) {
        btn.classList.toggle('is-active', active);
      } else {
        btn.className = active ? 'btn btn--sm btn--brass is-active' : 'btn btn--sm';
      }
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }
  Object.keys(tabButtons).forEach((key) => {
    if (tabButtons[key]) tabButtons[key].addEventListener('click', () => showTab(key));
  });

  // Deep-link support: /studio#clone or /studio#music opens that tab
  // directly instead of always landing on Single. Added so homepage promo
  // links (and the pricing page) can send people straight into the tab
  // they clicked on, instead of dropping them on Single and making them
  // hunt for the right button.
  const initialTab = (window.location.hash || '').replace('#', '');
  if (initialTab === 'clone') {
    window.location.replace('/voice-cloning');
  } else if (initialTab === 'music') {
    window.location.replace('/tools/ai-music-generator');
  } else if (initialTab && tabPanels[initialTab]) {
    showTab(initialTab);
  }

  // ---- SSML toggle ----
  const ssmlToggle = document.getElementById('ssml-toggle');
  const ssmlCheatsheet = document.getElementById('ssml-cheatsheet');
  if (ssmlToggle) ssmlToggle.addEventListener('change', () => {
    if (ssmlCheatsheet) ssmlCheatsheet.style.display = ssmlToggle.checked ? 'block' : 'none';
  });
  document.querySelectorAll('[data-ssml-insert]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tag = btn.getAttribute('data-ssml-insert') || '';
      const ta = document.getElementById('single-text');
      if (!ta) return;
      const start = ta.selectionStart || 0;
      const end = ta.selectionEnd || 0;
      const before = ta.value.slice(0, start);
      const selected = ta.value.slice(start, end);
      const after = ta.value.slice(end);
      // If tag is pair like [strong][/strong], put selection inside
      const m = tag.match(/^(\[[^\]]+\])(\[\/[^\]]+\])$/);
      let insert = tag;
      let cursor = start + tag.length;
      if (m) {
        insert = m[1] + (selected || '…') + m[2];
        cursor = start + m[1].length + (selected || '…').length;
      }
      ta.value = before + insert + after;
      ta.focus();
      ta.setSelectionRange(cursor, cursor);
      ta.dispatchEvent(new Event('input'));
    });
  });
  // Section label — only tags the download filename, never inserted into script
  let activeSection = 'none';
  function setSection(name) {
    activeSection = name || 'none';
    document.querySelectorAll('[data-section]').forEach((btn) => {
      const on = btn.getAttribute('data-section') === activeSection;
      btn.className = on ? 'btn btn--sm btn--brass is-active' : 'btn btn--ghost btn--sm';
    });
    const lab = document.getElementById('section-active-label');
    if (lab) lab.textContent = activeSection === 'none' ? 'Full script' : activeSection + ' (filename only)';
  }
  document.querySelectorAll('[data-section]').forEach((btn) => {
    btn.addEventListener('click', () => setSection(btn.getAttribute('data-section')));
  });
  setSection('none');

  // Local pronunciation dictionary (this browser only)
  function loadPron() {
    try { return JSON.parse(localStorage.getItem('vox_pron') || '[]'); } catch (e) { return []; }
  }
  function savePron(items) {
    localStorage.setItem('vox_pron', JSON.stringify(items.slice(0, 40)));
  }
  function renderPron() {
    const list = document.getElementById('pron-list');
    if (!list) return;
    const items = loadPron();
    if (!items.length) { list.innerHTML = '<span style="color:var(--text-dim)">No custom pronunciations yet.</span>'; return; }
    list.innerHTML = items.map((it, i) =>
      `<div style="display:flex;justify-content:space-between;gap:8px;margin:4px 0;">
        <span><strong>${it.find}</strong> → ${it.say}</span>
        <button type="button" class="btn btn--ghost btn--sm" data-pron-del="${i}">Remove</button>
      </div>`
    ).join('');
    list.querySelectorAll('[data-pron-del]').forEach((b) => {
      b.addEventListener('click', () => {
        const items = loadPron();
        items.splice(parseInt(b.getAttribute('data-pron-del'), 10), 1);
        savePron(items);
        renderPron();
      });
    });
  }
  const pronAdd = document.getElementById('pron-add-btn');
  if (pronAdd) {
    pronAdd.addEventListener('click', () => {
      const f = (document.getElementById('pron-find') || {}).value || '';
      const s = (document.getElementById('pron-say') || {}).value || '';
      if (!f.trim() || !s.trim()) return;
      const items = loadPron();
      items.unshift({ find: f.trim(), say: s.trim() });
      savePron(items);
      document.getElementById('pron-find').value = '';
      document.getElementById('pron-say').value = '';
      renderPron();
    });
  }
  renderPron();

  function applyLocalPron(text) {
    let t = text;
    loadPron().forEach((it) => {
      if (!it.find) return;
      try {
        const escaped = it.find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re = new RegExp('\\b' + escaped + '\\b', 'gi');
        t = t.replace(re, it.say);
      } catch (e) {}
    });
    return t;
  }

  // ---- Preview ----
  const previewBtn = document.getElementById('preview-btn');
  const previewPlayer = document.getElementById('preview-player');
  const previewStatus = document.querySelector('[data-preview-status]');
  async function runPreview(customText) {
    previewBtn.disabled = true;
    const psBtn = document.getElementById('preview-script-btn');
    if (psBtn) psBtn.disabled = true;
    previewStatus.textContent = 'Loading preview…';
    try {
      const body = {
        language: langSelect.value,
        voice_id: voiceSelect.value,
        speed_pct: parseInt(speedSlider.value, 10),
      };
      if (customText) body.text = customText;
      const res = await fetch('/api/tts/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        previewStatus.textContent = err.error || 'Preview failed.';
        return;
      }
      const blob = await res.blob();
      previewPlayer.src = URL.createObjectURL(blob);
      previewPlayer.style.display = 'block';
      previewPlayer.play();
      previewStatus.textContent = customText ? 'Playing your first line' : '';
    } catch (e) {
      previewStatus.textContent = 'Network error.';
    } finally {
      previewBtn.disabled = false;
      if (psBtn) psBtn.disabled = false;
    }
  }
  previewBtn.addEventListener('click', () => runPreview(null));
  const previewScriptBtn = document.getElementById('preview-script-btn');
  if (previewScriptBtn) {
    previewScriptBtn.addEventListener('click', () => {
      const raw = (document.getElementById('single-text') || {}).value || '';
      const first = raw.split(/[\n.?!۔؟]/).map(s => s.trim()).filter(Boolean)[0];
      if (!first) {
        previewStatus.textContent = 'Type some script first.';
        return;
      }
      runPreview(first.slice(0, 200));
    });
  }

  // ---- Single generation ----
  const singleText = document.getElementById('single-text');
  const charCount = document.querySelector('[data-char-count]');
  const durationEst = document.querySelector('[data-duration-est]');
  const generateSingleBtn = document.getElementById('generate-single-btn');
  const singleStatus = document.querySelector('[data-single-status]');
  const singleResult = document.getElementById('single-result');
  const historyList = document.getElementById('history-list');

  function updateSingleMeta() {
    const text = singleText.value;
    const len = text.length;
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    charCount.textContent = `${len} chars`;
    durationEst.textContent = `~${(words / 2.5).toFixed(1)}s`;
    // Mixed script / Roman Urdu tip
    const tip = document.getElementById('script-tip');
    if (tip) {
      const hasUrdu = /[\u0600-\u06FF]/.test(text);
      const hasDeva = /[\u0900-\u097F]/.test(text);
      const hasLatin = /[A-Za-z]{4,}/.test(text);
      const lang = (langSelect.value || '').toLowerCase();
      if ((lang.includes('urdu') || lang.includes('hindi')) && hasLatin && !hasUrdu && !hasDeva && words > 3) {
        tip.style.display = '';
        tip.textContent = 'Tip: For clearer Urdu/Hindi pronunciation, write in native script (Nastaliq / Devanagari) instead of Roman letters.';
      } else if (hasUrdu && hasLatin) {
        tip.style.display = '';
        tip.textContent = 'Mixed Urdu + English detected — preview a short line to check pronunciation of English words.';
      } else {
        tip.style.display = 'none';
        tip.textContent = '';
      }
    }
    const budget = document.getElementById('char-budget-warn');
    if (budget) {
      if (len > 2500) {
        budget.style.display = '';
        budget.textContent = 'Long script — consider generating in sections for better control.';
      } else {
        budget.style.display = 'none';
      }
    }
  }
  singleText.addEventListener('input', updateSingleMeta);
  updateSingleMeta();

  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem('voxcraft_history') || '[]');
    } catch (e) {
      return [];
    }
  }
  function saveHistory(items) {
    localStorage.setItem('voxcraft_history', JSON.stringify(items.slice(0, 8)));
  }
  function renderHistory() {
    const items = loadHistory();
    if (!items.length) { historyList.innerHTML = ''; return; }
    historyList.innerHTML = `
      <div class="history">
        <div class="history__head">
          <span class="panel__label" style="margin:0;">Recent generations</span>
          <button type="button" class="history__clear" id="history-clear">Clear</button>
        </div>
        <div class="history__list">
          ${items.map((item) => `
            <div class="history-item">
              <div class="history-item__text">${item.text || ''}</div>
              <div class="history-item__meta">${item.size_kb} KB · ${item.time}</div>
              <audio controls src="data:audio/mpeg;base64,${item.audio_b64}"></audio>
            </div>
          `).join('')}
        </div>
      </div>`;
    const clearBtn = document.getElementById('history-clear');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        localStorage.removeItem('voxcraft_history');
        renderHistory();
      });
    }
  }
  renderHistory();

  const stickyGen = document.getElementById('generate-single-sticky');
  if (stickyGen) stickyGen.addEventListener('click', () => generateSingleBtn && generateSingleBtn.click());
  generateSingleBtn.addEventListener('click', () => {
    if (!singleText.value.trim()) {
      singleStatus.textContent = 'Please enter some text first.';
      return;
    }
    window.VoxCraftAds.showInterstitial(runSingleGeneration);
  });

  async function runSingleGeneration() {
    generateSingleBtn.disabled = true;
    generateSingleBtn.classList.add('is-loading');
    singleStatus.textContent = 'Rendering your voiceover…';
    singleResult.innerHTML = '';
    const progress = document.getElementById('single-progress');
    if (progress) { progress.classList.add('is-active'); progress.setAttribute('aria-hidden', 'false'); }
    const started = Date.now();
    try {
      const res = await fetch('/api/tts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: applyLocalPron(singleText.value.trim()),
          voice_id: voiceSelect.value,
          speed_pct: parseInt(speedSlider.value, 10),
          ssml_mode: ssmlToggle.checked,
          normalize: !!(document.getElementById('normalize-toggle') || {}).checked,
          export_format: (document.getElementById('export-format') || {}).value || 'mp3',
          auto_pause: !!(document.getElementById('auto-pause-toggle') || {}).checked,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const msg = data.error || 'Something went wrong.';
        // Friendlier limit messaging for a premium feel
        if (res.status === 429 || /limit|quota|daily/i.test(msg)) {
          singleStatus.innerHTML = '';
          singleResult.innerHTML = `<div class="limit-toast">${msg} <a href="/pricing" style="color:var(--brass-hi);margin-left:6px;">Upgrade for unlimited →</a></div>`;
        } else {
          singleStatus.textContent = msg;
        }
        return;
      }
      const secs = ((Date.now() - started) / 1000).toFixed(1);
      singleStatus.textContent = `Ready · ${data.size_kb} KB · ${secs}s`;
      const ext = (document.getElementById('export-format') || {}).value === 'wav' ? 'wav' : 'mp3';
      const mime = ext === 'wav' ? 'audio/wav' : 'audio/mpeg';
      const secTag = (activeSection && activeSection !== 'none') ? ('-' + activeSection) : '';
      const fname = (data.filename || ('VoxCraft-Narration' + secTag + '.mp3')).replace(/\.mp3$/i, secTag + '.' + ext).replace(/--+/g, '-');
      // Persist for "Send to another tool" handoff (tools.js reads this key)
      try {
        sessionStorage.setItem('voxcraft_transfer_v1', JSON.stringify({
          b64: data.audio_b64,
          filename: fname,
          mime: mime,
          ts: Date.now(),
        }));
      } catch (e) {
        // sessionStorage full (large WAV) — handoff still works if user
        // re-downloads; banner on tool page will simply not appear
      }
      singleResult.innerHTML = `
        <div class="result-panel">
          <div class="result-panel__label">Your narration</div>
          <audio controls src="data:${mime};base64,${data.audio_b64}"></audio>
          <div class="result-panel__actions" style="display:flex;flex-wrap:wrap;gap:8px;">
            <a class="btn btn--brass btn--sm" download="${fname}" href="data:${mime};base64,${data.audio_b64}">Download</a>
            <button type="button" class="btn btn--ghost btn--sm" onclick="this.closest('.result-panel').querySelector('audio').play()">Play again</button>
          </div>
          <div class="result-panel__next">
            <span class="result-panel__next-label">Send to another tool</span>
            <div class="result-panel__next-links">
              <a class="btn btn--ghost btn--sm" data-send-tool="trim-cut-audio" href="/tools/trim-cut-audio">Trim</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="remove-background-noise" href="/tools/remove-background-noise">Denoise</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="normalize-audio-volume" href="/tools/normalize-audio-volume">Normalize</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="merge-audio-files" href="/tools/merge-audio-files">Merge</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="convert-audio-format" href="/tools/convert-audio-format">Convert</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="change-audio-speed" href="/tools/change-audio-speed">Speed</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="fade-audio" href="/tools/fade-audio">Fade</a>
            </div>
          </div>
        </div>
      `;
      const items = loadHistory();
      items.unshift({
        text: singleText.value.trim().slice(0, 80),
        size_kb: data.size_kb,
        time: new Date().toLocaleTimeString(),
        audio_b64: data.audio_b64,
      });
      saveHistory(items);
      renderHistory();
    } catch (e) {
      singleStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      generateSingleBtn.disabled = false;
      generateSingleBtn.classList.remove('is-loading');
      if (progress) { progress.classList.remove('is-active'); progress.setAttribute('aria-hidden', 'true'); }
    }
  }

  // ---- Batch generation ----
  const batchText = document.getElementById('batch-text');
  const lineCount = document.querySelector('[data-line-count]');
  const generateBatchBtn = document.getElementById('generate-batch-btn');
  const batchStatus = document.querySelector('[data-batch-status]');
  const batchResult = document.getElementById('batch-result');
  const BATCH_MAX = parseInt(lineCount.textContent.split('/')[1], 10) || 20;

  function getLines() {
    return batchText.value.split('\n').map(l => l.trim()).filter(Boolean);
  }
  function updateLineCount() {
    lineCount.textContent = `${getLines().length} / ${BATCH_MAX} lines`;
  }
  batchText.addEventListener('input', updateLineCount);
  updateLineCount();

  generateBatchBtn.addEventListener('click', async () => {
    const lines = getLines();
    if (!lines.length) {
      batchStatus.textContent = 'Add at least one line.';
      return;
    }
    generateBatchBtn.disabled = true;
    generateBatchBtn.classList.add('is-loading');
    batchStatus.textContent = `Rendering ${lines.length} clips…`;
    batchResult.innerHTML = '';
    const started = Date.now();
    try {
      const res = await fetch('/api/tts/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lines,
          voice_id: voiceSelect.value,
          speed_pct: parseInt(speedSlider.value, 10),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const msg = data.error || 'Something went wrong.';
        if (res.status === 429 || /limit|quota|daily/i.test(msg)) {
          batchStatus.textContent = '';
          batchResult.innerHTML = `<div class="limit-toast">${msg} <a href="/pricing" style="color:var(--brass-hi);margin-left:6px;">Upgrade →</a></div>`;
        } else {
          batchStatus.textContent = msg;
        }
        return;
      }
      const secs = ((Date.now() - started) / 1000).toFixed(1);
      batchStatus.textContent = `${data.clips.length} clips ready · ${secs}s`;
      batchResult.innerHTML = `
        <div class="result-panel">
          <div class="result-panel__label">${data.clips.length} narrations</div>
          <div class="batch-clips">
            ${data.clips.map(c => `
              <div class="batch-clip">
                <div class="batch-clip__idx">Clip ${c.idx}</div>
                <div class="batch-clip__text">“${(c.text || '').slice(0, 100)}${(c.text || '').length > 100 ? '…' : ''}”</div>
                <audio controls src="data:audio/mpeg;base64,${c.audio_b64}"></audio>
                <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
                   download="${c.filename || ('clip-' + c.idx + '.mp3')}" href="data:audio/mpeg;base64,${c.audio_b64}">Download MP3</a>
              </div>
            `).join('')}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;">
            ${data.zip_b64 ? `<a class="btn btn--brass btn--sm" download="${data.zip_filename || 'voxcraft-batch.zip'}" href="data:application/zip;base64,${data.zip_b64}">Download all as ZIP</a>` : ''}
            ${data.merged_b64 ? `<a class="btn btn--ghost btn--sm" download="${data.merged_filename || 'voxcraft-batch-merged.mp3'}" href="data:audio/mpeg;base64,${data.merged_b64}">Download merged MP3</a>` : ''}
          </div>
        </div>
      `;
    } catch (e) {
      batchStatus.textContent = 'Network error — check your connection and try again.';
    } finally {
      generateBatchBtn.disabled = false;
      generateBatchBtn.classList.remove('is-loading');
    }
  });
})();
