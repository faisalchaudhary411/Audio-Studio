// ===== VoxCraft clone_music.js =====
// Only loaded for Pro+ sessions (see studio.html) — handles the Clone Voice
// and Music Generation tabs. Both submit a job and poll a status endpoint,
// since GPU generation takes 20-90+ seconds and the backend deliberately
// doesn't hold the HTTP request open that whole time (see clone_engine.py /
// music_engine.py). Polling stops on done/error or after ~3 minutes.
(function () {
  const POLL_INTERVAL_MS = 3000;
  const POLL_TIMEOUT_MS = 3 * 60 * 1000;

  async function pollJob(statusUrl, onTick) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      const res = await fetch(statusUrl);
      const data = await res.json();
      if (!res.ok) return { status: 'error', error: data.error || 'Something went wrong.' };
      if (data.status === 'done' || data.status === 'error') return data;
      if (onTick) onTick(data.status);
    }
    return { status: 'error', error: 'Timed out waiting for generation.' };
  }

  // Display-only script detection — mirrors the logic in
  // urdu_transliteration.py's prepare_text_for_tts(), but this copy exists
  // purely to show the user what will happen before they hit generate.
  // The backend re-detects independently and is the actual source of
  // truth; a mismatch here would only affect the preview label, never the
  // real generation, since the server never trusts this client-side guess.
  const URDU_SCRIPT_RE = /[\u0600-\u06FF\u0750-\u077F]/;
  const DEVANAGARI_RE = /[\u0900-\u097F]/;
  function detectScriptLabel(text) {
    if (URDU_SCRIPT_RE.test(text)) return 'Urdu detected — will generate with Hindi pronunciation';
    if (DEVANAGARI_RE.test(text)) return 'Hindi detected';
    if (text.trim()) return 'English detected';
    return '';
  }
  function detectScriptShort(text) {
    if (URDU_SCRIPT_RE.test(text)) return 'Hindi pronunciation';
    if (DEVANAGARI_RE.test(text)) return 'Hindi';
    return 'English';
  }

  // ---- Clone voice ----
  const cloneRefInput = document.getElementById('clone-ref-audio');
  const cloneText = document.getElementById('clone-text');
  const cloneBtn = document.getElementById('generate-clone-btn');
  const cloneCharCount = document.getElementById('clone-char-count');
  const cloneLangDetect = document.getElementById('clone-lang-detect');

  if (cloneText && cloneCharCount) {
    const limit = parseInt(cloneText.getAttribute('maxlength'), 10) || 2000;
    const updateCount = () => {
      cloneCharCount.textContent = `${cloneText.value.length} / ${limit} characters`;
      cloneCharCount.style.color = cloneText.value.length >= limit ? 'var(--brass-hi)' : 'var(--text-dim)';
      if (cloneLangDetect) cloneLangDetect.textContent = detectScriptLabel(cloneText.value);
    };
    cloneText.addEventListener('input', updateCount);
    updateCount();
  }
  const cloneStatus = document.querySelector('[data-clone-status]');
  const cloneResult = document.getElementById('clone-result');

  if (cloneBtn) {
    cloneBtn.addEventListener('click', async () => {
      if (!cloneRefInput.files.length) {
        cloneStatus.textContent = 'Upload a reference clip first.';
        return;
      }
      if (!cloneText.value.trim()) {
        cloneStatus.textContent = 'Enter some text to speak.';
        return;
      }
      cloneBtn.disabled = true;
      cloneResult.innerHTML = '';
      cloneStatus.textContent = 'Uploading reference clip…';
      try {
        const form = new FormData();
        form.append('reference_audio', cloneRefInput.files[0]);
        const uploadRes = await fetch('/api/clone/upload', { method: 'POST', body: form });
        const uploadData = await uploadRes.json();
        if (!uploadRes.ok) {
          cloneStatus.textContent = uploadData.error || 'Upload failed.';
          return;
        }

        cloneStatus.textContent = 'Submitting cloning job…';
        const genRes = await fetch('/api/clone/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: cloneText.value.trim(), reference_id: uploadData.reference_id }),
        });
        const genData = await genRes.json();
        if (!genRes.ok) {
          cloneStatus.textContent = genData.error || 'Could not start cloning.';
          return;
        }

        const result = await pollJob(`/api/clone/status/${genData.job_id}`, (status) => {
          cloneStatus.textContent = status === 'generating'
            ? `Generating on GPU (${detectScriptShort(cloneText.value)})… this can take up to a minute.`
            : 'Working…';
        });
        if (result.status === 'done') {
          cloneStatus.textContent = 'Done.';
          cloneResult.innerHTML = `
            <audio controls style="width:100%;" src="data:audio/wav;base64,${result.audio_b64}"></audio>
            <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
               download="cloned-voice.wav" href="data:audio/wav;base64,${result.audio_b64}">Download WAV</a>
          `;
        } else {
          cloneStatus.textContent = result.error || 'Generation failed.';
        }
      } catch (e) {
        cloneStatus.textContent = 'Network error — check your connection.';
      } finally {
        cloneBtn.disabled = false;
      }
    });
  }

  // ---- Music generation ----
  const musicPrompt = document.getElementById('music-prompt');
  const musicDurationSlider = document.getElementById('music-duration-slider');
  const musicDurationLabel = document.getElementById('music-duration-label');
  const musicBtn = document.getElementById('generate-music-btn');
  const musicStatus = document.querySelector('[data-music-status]');
  const musicResult = document.getElementById('music-result');

  if (musicDurationSlider) {
    musicDurationSlider.addEventListener('input', () => {
      musicDurationLabel.textContent = musicDurationSlider.value + 's';
    });
  }

  if (musicBtn) {
    musicBtn.addEventListener('click', async () => {
      if (!musicPrompt.value.trim()) {
        musicStatus.textContent = 'Describe the music you want first.';
        return;
      }
      musicBtn.disabled = true;
      musicResult.innerHTML = '';
      musicStatus.textContent = 'Starting generation…';
      try {
        const genRes = await fetch('/api/music/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tags: musicPrompt.value.trim(),
            duration: parseInt(musicDurationSlider.value, 10),
            instrumental: true,
          }),
        });
        const genData = await genRes.json();
        if (!genRes.ok) {
          musicStatus.textContent = genData.error || 'Could not start generation.';
          return;
        }

        const result = await pollJob(`/api/music/status/${genData.job_id}`, (status) => {
          musicStatus.textContent = status === 'generating' ? 'Generating… this can take up to a minute.' : 'Working…';
        });
        if (result.status === 'done') {
          musicStatus.textContent = 'Done.';
          musicResult.innerHTML = `
            <audio controls style="width:100%;" src="data:audio/wav;base64,${result.audio_b64}"></audio>
            <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
               download="generated-music.wav" href="data:audio/wav;base64,${result.audio_b64}">Download</a>
          `;
        } else {
          musicStatus.textContent = result.error || 'Generation failed.';
        }
      } catch (e) {
        musicStatus.textContent = 'Network error — check your connection.';
      } finally {
        musicBtn.disabled = false;
      }
    });
  }
})();
