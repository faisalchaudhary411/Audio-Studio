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
      cloneResult.innerHTML = `<audio controls style="width:100%;" src="data:audio/wav;base64,${data.audio_b64}"></audio>`;
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
