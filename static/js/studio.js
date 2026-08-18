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
  langSelect.addEventListener('change', populateVoices);
  populateVoices();

  speedSlider.addEventListener('input', () => {
    speedLabel.textContent = speedSlider.value + '%';
  });

  // ---- Tabs ----
  const tabButtons = {
    single: document.getElementById('tab-single-btn'),
    batch: document.getElementById('tab-batch-btn'),
    clone: document.getElementById('tab-clone-btn'),
    music: document.getElementById('tab-music-btn'),
  };
  const tabPanels = {
    single: document.getElementById('tab-single'),
    batch: document.getElementById('tab-batch'),
    clone: document.getElementById('tab-clone'),
    music: document.getElementById('tab-music'),
  };
  function showTab(name) {
    Object.keys(tabPanels).forEach((key) => {
      if (!tabPanels[key] || !tabButtons[key]) return;
      const active = key === name;
      tabPanels[key].style.display = active ? '' : 'none';
      tabButtons[key].className = active ? 'btn btn--sm btn--brass' : 'btn btn--sm btn--ghost';
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
  if (initialTab && tabPanels[initialTab]) {
    showTab(initialTab);
  }

  // ---- SSML toggle ----
  const ssmlToggle = document.getElementById('ssml-toggle');
  const ssmlCheatsheet = document.getElementById('ssml-cheatsheet');
  ssmlToggle.addEventListener('change', () => {
    ssmlCheatsheet.style.display = ssmlToggle.checked ? 'block' : 'none';
  });

  // ---- Preview ----
  const previewBtn = document.getElementById('preview-btn');
  const previewPlayer = document.getElementById('preview-player');
  const previewStatus = document.querySelector('[data-preview-status]');
  previewBtn.addEventListener('click', async () => {
    previewBtn.disabled = true;
    previewStatus.textContent = 'Loading preview…';
    try {
      const res = await fetch('/api/tts/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: langSelect.value,
          voice_id: voiceSelect.value,
          speed_pct: parseInt(speedSlider.value, 10),
        }),
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
      previewStatus.textContent = '';
    } catch (e) {
      previewStatus.textContent = 'Network error.';
    } finally {
      previewBtn.disabled = false;
    }
  });

  // ---- Single generation ----
  const singleText = document.getElementById('single-text');
  const charCount = document.querySelector('[data-char-count]');
  const durationEst = document.querySelector('[data-duration-est]');
  const generateSingleBtn = document.getElementById('generate-single-btn');
  const singleStatus = document.querySelector('[data-single-status]');
  const singleResult = document.getElementById('single-result');
  const historyList = document.getElementById('history-list');

  function updateSingleMeta() {
    const len = singleText.value.length;
    const words = singleText.value.trim().split(/\s+/).filter(Boolean).length;
    charCount.textContent = `${len} chars`;
    durationEst.textContent = `~${(words / 2.5).toFixed(1)}s`;
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
    historyList.innerHTML = '<p class="panel__label">Recent generations</p>' + items.map((item, i) => `
      <div style="border-top:1px solid var(--line);padding:10px 0;">
        <div style="font-size:0.88rem;color:var(--text-mid);overflow-wrap:anywhere;word-break:break-word;">${item.text}</div>
        <div style="font-family:var(--mono);font-size:0.72rem;color:var(--text-dim);margin:4px 0 6px;">${item.size_kb} KB · ${item.time}</div>
        <audio controls style="width:100%;" src="data:audio/mpeg;base64,${item.audio_b64}"></audio>
      </div>
    `).join('');
  }
  renderHistory();

  generateSingleBtn.addEventListener('click', () => {
    if (!singleText.value.trim()) {
      singleStatus.textContent = 'Please enter some text first.';
      return;
    }
    window.VoxCraftAds.showInterstitial(runSingleGeneration);
  });

  async function runSingleGeneration() {
    generateSingleBtn.disabled = true;
    singleStatus.textContent = 'Generating…';
    singleResult.innerHTML = '';
    try {
      const res = await fetch('/api/tts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: singleText.value.trim(),
          voice_id: voiceSelect.value,
          speed_pct: parseInt(speedSlider.value, 10),
          ssml_mode: ssmlToggle.checked,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        singleStatus.textContent = data.error || 'Something went wrong.';
        return;
      }
      singleStatus.textContent = `Generated · ${data.size_kb} KB`;
      singleResult.innerHTML = `
        <audio controls style="width:100%;" src="data:audio/mpeg;base64,${data.audio_b64}"></audio>
        <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
           download="${data.filename}" href="data:audio/mpeg;base64,${data.audio_b64}">Download MP3</a>
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
      singleStatus.textContent = 'Network error — check your connection.';
    } finally {
      generateSingleBtn.disabled = false;
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
    batchStatus.textContent = `Generating ${lines.length} clips…`;
    batchResult.innerHTML = '';
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
        batchStatus.textContent = data.error || 'Something went wrong.';
        return;
      }
      batchStatus.textContent = `${data.clips.length} clip(s) ready`;
      const clipsHtml = data.clips.map(c => `
        <div style="border-top:1px solid var(--line);padding:10px 0;">
          <div style="font-size:0.85rem;color:var(--brass-hi);font-family:var(--mono);">CLIP ${c.idx}</div>
          <div style="font-size:0.88rem;color:var(--text-mid);font-style:italic;margin:4px 0;overflow-wrap:anywhere;word-break:break-word;">"${c.text.slice(0,80)}"</div>
          <audio controls style="width:100%;" src="data:audio/mpeg;base64,${c.audio_b64}"></audio>
        </div>
      `).join('');
      batchResult.innerHTML = clipsHtml + `
        <a class="btn btn--brass btn--sm" style="margin-top:14px;display:inline-flex;"
           download="${data.zip_filename}" href="data:application/zip;base64,${data.zip_b64}">Download all as ZIP</a>
      `;
    } catch (e) {
      batchStatus.textContent = 'Network error — check your connection.';
    } finally {
      generateBatchBtn.disabled = false;
    }
  });
})();
