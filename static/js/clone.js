// ===== VoxCraft — Clone a voice (Pro) =====
(function () {
  const fileInput = document.getElementById('clone-file-input');
  const uploadStatus = document.querySelector('[data-clone-upload-status]');
  const cloneText = document.getElementById('clone-text');
  const generateBtn = document.getElementById('clone-generate-btn');
  const cloneStatus = document.querySelector('[data-clone-status]');
  const cloneResult = document.getElementById('clone-result');

  let referenceId = null;

  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    uploadStatus.textContent = 'Uploading reference clip…';
    const form = new FormData();
    form.append('reference_audio', file);
    try {
      const res = await fetch('/api/clone/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) {
        uploadStatus.textContent = data.error || 'Upload failed.';
        return;
      }
      referenceId = data.reference_id;
      uploadStatus.textContent = `Reference clip ready: ${file.name}`;
    } catch (e) {
      uploadStatus.textContent = 'Network error during upload.';
    }
  });

  async function pollJob(jobId) {
    const res = await fetch(`/api/clone/status/${jobId}`);
    const data = await res.json();
    if (data.status === 'done') {
      cloneStatus.textContent = 'Done.';
      const ts = new Date().toISOString().slice(0,16).replace(/[-:T]/g,'');
      const fname = `VoxCraft-Clone-${ts}.wav`;
      // Persist for cross-tool "Send to …" handoff (tools.js reads this key)
      try {
        sessionStorage.setItem('voxcraft_transfer_v1', JSON.stringify({
          b64: data.audio_b64,
          filename: fname,
          mime: 'audio/wav',
          ts: Date.now(),
        }));
      } catch (e) {}
      cloneResult.innerHTML = `
        <div class="result-panel">
          <audio controls style="width:100%;" src="data:audio/wav;base64,${data.audio_b64}"></audio>
          <div class="result-panel__actions" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
            <a class="btn btn--brass btn--sm" download="${fname}" href="data:audio/wav;base64,${data.audio_b64}">Download WAV</a>
          </div>
          <div class="result-panel__next" style="margin-top:10px;">
            <span class="result-panel__next-label">Send to another tool</span>
            <div class="result-panel__next-links" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
              <a class="btn btn--ghost btn--sm" data-send-tool="trim-cut-audio" href="/tools/trim-cut-audio">Trim</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="remove-background-noise" href="/tools/remove-background-noise">Denoise</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="normalize-audio-volume" href="/tools/normalize-audio-volume">Normalize</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="merge-audio-files" href="/tools/merge-audio-files">Merge</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="convert-audio-format" href="/tools/convert-audio-format">Convert</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="change-audio-speed" href="/tools/change-audio-speed">Speed</a>
              <a class="btn btn--ghost btn--sm" data-send-tool="fade-audio" href="/tools/fade-audio">Fade</a>
            </div>
          </div>
        </div>`;
      generateBtn.disabled = false;
      return;
    }
    if (data.status === 'error') {
      cloneStatus.textContent = data.error || 'Generation failed.';
      generateBtn.disabled = false;
      return;
    }
    const label = { queued: 'Queued…', loading_model: 'Loading model (first run only, can take a minute)…', generating: 'Generating…' }[data.status] || data.status;
    cloneStatus.textContent = label;
    setTimeout(() => pollJob(jobId), 2000);
  }

  generateBtn.addEventListener('click', async () => {
    if (!referenceId) {
      cloneStatus.textContent = 'Upload a reference clip first.';
      return;
    }
    if (!cloneText.value.trim()) {
      cloneStatus.textContent = 'Enter some text first.';
      return;
    }
    generateBtn.disabled = true;
    cloneResult.innerHTML = '';
    cloneStatus.textContent = 'Starting…';
    try {
      const res = await fetch('/api/clone/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cloneText.value.trim(), reference_id: referenceId }),
      });
      const data = await res.json();
      if (!res.ok) {
        cloneStatus.textContent = data.error || 'Something went wrong.';
        generateBtn.disabled = false;
        return;
      }
      pollJob(data.job_id);
    } catch (e) {
      cloneStatus.textContent = 'Network error.';
      generateBtn.disabled = false;
    }
  });
})();
