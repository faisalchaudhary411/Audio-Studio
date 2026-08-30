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
  const progress = document.getElementById('music-progress');

  if (!generateBtn) return; // not on this page (free user / panel absent)

  function setLoading(on) {
    generateBtn.disabled = !!on;
    generateBtn.classList.toggle('is-loading', !!on);
    if (progress) {
      progress.classList.toggle('is-active', !!on);
      progress.setAttribute('aria-hidden', on ? 'false' : 'true');
    }
  }

  if (instrumentalCheck && lyricsWrap) {
    instrumentalCheck.addEventListener('change', () => {
      lyricsWrap.style.display = instrumentalCheck.checked ? 'none' : 'block';
    });
  }

  if (durationSlider && durationLabel) {
    durationSlider.addEventListener('input', () => {
      durationLabel.textContent = durationSlider.value;
    });
  }

  async function pollJob(jobId) {
    const res = await fetch(`/api/music/status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done') {
      if (status) status.textContent = 'Done.';
      if (result) {
        result.innerHTML = `
          <div class="result-panel">
            <div class="result-panel__label">Generated track</div>
            <audio controls src="data:audio/wav;base64,${data.audio_b64}"></audio>
            <div class="result-panel__actions">
              <a class="btn btn--ghost btn--sm" download="voxcraft-track-${Date.now()}.wav"
                 href="data:audio/wav;base64,${data.audio_b64}">Download</a>
            </div>
          </div>
        `;
      }
      setLoading(false);
      return;
    }
    if (data.status === 'error') {
      if (status) status.textContent = data.error || 'Generation failed.';
      setLoading(false);
      return;
    }
    const labels = {
      queued: 'Queued…',
      starting: 'Starting…',
      generating: 'Generating (usually 30–60s)… keep this tab open.',
    };
    if (status) status.textContent = labels[data.status] || data.status;
    setTimeout(() => pollJob(jobId), 2500);
  }

  generateBtn.addEventListener('click', async () => {
    if (!tagsInput || !tagsInput.value.trim()) {
      if (status) status.textContent = 'Describe the style first (e.g. "lofi, chill, piano").';
      return;
    }
    setLoading(true);
    if (result) result.innerHTML = '';
    if (status) status.textContent = 'Starting…';
    try {
      const res = await fetch('/api/music/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tags: tagsInput.value.trim(),
          lyrics: lyricsInput && instrumentalCheck && !instrumentalCheck.checked ? lyricsInput.value.trim() : '',
          duration: durationSlider ? parseInt(durationSlider.value, 10) : 60,
          instrumental: instrumentalCheck ? !!instrumentalCheck.checked : true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (status) status.textContent = data.error || 'Could not start generation.';
        setLoading(false);
        return;
      }
      pollJob(data.job_id);
    } catch (e) {
      if (status) status.textContent = 'Network error — check your connection.';
      setLoading(false);
    }
  });
})();
