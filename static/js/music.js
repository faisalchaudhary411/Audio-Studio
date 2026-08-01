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

  async function pollJob(jobId) {
    const res = await fetch(`/api/music/status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done') {
      status.textContent = 'Done.';
      result.innerHTML = `
        <audio controls style="width:100%;" src="data:audio/wav;base64,${data.audio_b64}"></audio>
        <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
           download="voxcraft-track-${Date.now()}.wav" href="data:audio/wav;base64,${data.audio_b64}">Download</a>
      `;
      generateBtn.disabled = false;
      return;
    }
    if (data.status === 'error') {
      status.textContent = data.error || 'Generation failed.';
      generateBtn.disabled = false;
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
    generateBtn.disabled = true;
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
        generateBtn.disabled = false;
        return;
      }
      pollJob(data.job_id);
    } catch (e) {
      status.textContent = 'Network error.';
      generateBtn.disabled = false;
    }
  });
})();
