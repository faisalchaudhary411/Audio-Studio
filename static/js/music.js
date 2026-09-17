// ===== VoxCraft — Music generator (Pro) =====
(function () {
  const tagsInput = document.getElementById('music-tags');
  const instrumentalCheck = document.getElementById('music-instrumental');
  const lyricsWrap = document.getElementById('music-lyrics-wrap');
  const lyricsInput = document.getElementById('music-lyrics');
  const durationSlider = document.getElementById('music-duration');
  const durationLabel = document.getElementById('music-duration-label');
  const generateBtn = document.getElementById('music-generate-btn');
  const status = document.querySelector('[data-music-status]');
  const result = document.getElementById('music-result');

  if (!generateBtn) return; // not on this page (free user / panel absent)

  instrumentalCheck.addEventListener('change', () => {
    lyricsWrap.style.display = instrumentalCheck.checked ? 'none' : 'block';
  });

  durationSlider.addEventListener('input', () => {
    durationLabel.textContent = durationSlider.value;
  });

  const musicProgressBar = document.getElementById('music-progress');
  // Align with music_client 12-min ceiling + job max age. Cold starts after
  // scale-to-zero can take several minutes; give the GPU worker room before
  // the UI gives up.
  const POLL_TIMEOUT_MS = 12 * 60 * 1000;
  const pollDeadline = { value: 0 };

  async function pollJob(jobId) {
    const res = await fetch(`/api/music/status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done') {
      status.textContent = 'Done.';
      if (status) status.classList.add('studio-status-ready');
      if (typeof voxButtonSuccess === 'function') voxButtonSuccess(generateBtn);
      const fname = `VoxCraft-Music-${new Date().toISOString().slice(0,16).replace(/[-:T]/g,'')}.wav`;
      // Shared handoff so Ace-Step music can be sent to Trim/Denoise/etc.
      if (typeof voxAudioPlayerHtml === 'function') {
        // Normal path: main.js loaded fine, this already hydrates off the
        // main thread via the audio worker (see voxHydrateAudioResult).
        result.innerHTML = voxAudioPlayerHtml(data.audio_b64, fname, 'audio/wav');
      } else {
        // Defensive fallback only — main.js failed to load/define the
        // helper. Still avoid freezing the main thread on a big base64
        // string: use the worker-backed decode if it's reachable, and
        // only fall back to a raw data: URL as a last resort.
        try {
          sessionStorage.setItem('voxcraft_transfer_v1', JSON.stringify({
            b64: data.audio_b64,
            filename: fname,
            mime: 'audio/wav',
            ts: Date.now(),
          }));
        } catch (e) {}
        result.innerHTML = `
          <div class="result-panel">
            <audio controls style="width:100%;" data-music-fallback-audio></audio>
            <div class="result-panel__actions" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
              <a class="btn btn--brass btn--sm" download="${fname}" data-music-fallback-dl disabled>Preparing download…</a>
            </div>
            <div class="result-panel__next" style="margin-top:10px;">
              <span class="result-panel__next-label">Send to another tool</span>
              <div class="result-panel__next-links" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
                <a class="btn btn--ghost btn--sm" data-send-tool="trim-cut-audio" href="/tools/trim-cut-audio">Trim</a>
                <a class="btn btn--ghost btn--sm" data-send-tool="remove-background-noise" href="/tools/remove-background-noise">Denoise</a>
                <a class="btn btn--ghost btn--sm" data-send-tool="normalize-audio-volume" href="/tools/normalize-audio-volume">Normalize</a>
                <a class="btn btn--ghost btn--sm" data-send-tool="merge-audio-files" href="/tools/merge-audio-files">Merge</a>
                <a class="btn btn--ghost btn--sm" data-send-tool="convert-audio-format" href="/tools/convert-audio-format">Convert</a>
              </div>
            </div>
          </div>
        `;
        (async () => {
          const audioEl = result.querySelector('[data-music-fallback-audio]');
          const dlEl = result.querySelector('[data-music-fallback-dl]');
          try {
            if (typeof voxB64ToObjectURL === 'function') {
              const url = await voxB64ToObjectURL(data.audio_b64, 'audio/wav');
              audioEl.src = url;
              dlEl.href = url;
            } else {
              // True last resort: small enough files, main-thread atob.
              audioEl.src = `data:audio/wav;base64,${data.audio_b64}`;
              dlEl.href = `data:audio/wav;base64,${data.audio_b64}`;
            }
          } catch (e) {
            console.warn('[voxcraft] music fallback hydrate failed', e);
            audioEl.src = `data:audio/wav;base64,${data.audio_b64}`;
            dlEl.href = `data:audio/wav;base64,${data.audio_b64}`;
          }
          dlEl.removeAttribute('disabled');
        })();
      }
      voxSetBusy(generateBtn, false);
      voxShowProgress(musicProgressBar, false);
      return;
    }
    if (data.status === 'error') {
      status.textContent = data.error || 'Generation failed.';
      voxSetBusy(generateBtn, false);
      voxShowProgress(musicProgressBar, false);
      return;
    }
    if (Date.now() > pollDeadline.value) {
      status.textContent = 'Timed out after 12 minutes. Cold starts can be slow — try Generate again; a warm run is usually much faster.';
      voxSetBusy(generateBtn, false);
      voxShowProgress(musicProgressBar, false);
      return;
    }
    const elapsedMin = Math.floor((Date.now() - (pollDeadline.value - POLL_TIMEOUT_MS)) / 60000);
    const labels = {
      queued: 'Queued…',
      starting: 'Starting GPU worker…',
      generating: elapsedMin >= 2
        ? `Still generating (${elapsedMin} min) — cold starts can take several minutes…`
        : 'Generating… (warm runs ~1 min; first run after idle may take longer)',
    };
    status.textContent = labels[data.status] || data.status;
    setTimeout(() => pollJob(jobId), 2500);
  }

  generateBtn.addEventListener('click', async () => {
    if (!tagsInput.value.trim()) {
      status.textContent = 'Describe the style first (e.g. "lofi, chill, piano").';
      return;
    }
    voxSetBusy(generateBtn, true);
    voxShowProgress(musicProgressBar, true);
    result.innerHTML = '';
    status.textContent = 'Starting…';
    pollDeadline.value = Date.now() + POLL_TIMEOUT_MS;
    try {
      const res = await fetch('/api/music/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tags: tagsInput.value.trim(),
          lyrics: lyricsInput.value.trim(),
          instrumental: instrumentalCheck.checked,
          duration: parseInt(durationSlider.value, 10),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        status.textContent = data.error || 'Something went wrong.';
        voxSetBusy(generateBtn, false);
        voxShowProgress(musicProgressBar, false);
        return;
      }
      pollJob(data.job_id);
    } catch (e) {
      status.textContent = 'Network error.';
      voxSetBusy(generateBtn, false);
      voxShowProgress(musicProgressBar, false);
    }
  });
})();
