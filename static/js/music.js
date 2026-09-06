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

  async function pollJob(jobId) {
    const res = await fetch(`/api/music/status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done') {
      status.textContent = 'Done.';
      const fname = `VoxCraft-Music-${new Date().toISOString().slice(0,16).replace(/[-:T]/g,'')}.wav`;
      // Shared handoff so Ace-Step music can be sent to Trim/Denoise/etc.
      if (typeof voxAudioPlayerHtml === 'function') {
        result.innerHTML = voxAudioPlayerHtml(data.audio_b64, fname, 'audio/wav');
      } else {
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
            <audio controls style="width:100%;" src="data:audio/wav;base64,${data.audio_b64}"></audio>
            <div class="result-panel__actions" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
              <a class="btn btn--brass btn--sm" download="${fname}" href="data:audio/wav;base64,${data.audio_b64}">Download</a>
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
    const labels = { queued: 'Queued…', starting: 'Starting…', generating: 'Generating (usually 30-60s)…' };
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
