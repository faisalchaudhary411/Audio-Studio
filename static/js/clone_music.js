// ===== VoxCraft clone_music.js =====
// Only loaded for Pro+ sessions (see studio.html) — handles the Clone Voice
// and Music Generation tabs. Both submit a job and poll a status endpoint,
// since GPU generation takes 20-90+ seconds and the backend deliberately
// doesn't hold the HTTP request open that whole time (see clone_engine.py /
// music_engine.py). Polling stops on done/error or after ~10 minutes
// (raised from 3 min so long Urdu/Hindi scripts + Modal cold-start don't
// silently time out before the audio is ready).
(function () {
  const POLL_INTERVAL_MS = 2500;
  const POLL_TIMEOUT_MS = 10 * 60 * 1000;  // 10 minutes — long scripts need this

  async function pollJob(statusUrl, onTick) {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    let lastStatus = '';
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      try {
        const res = await fetch(statusUrl);
        const data = await res.json();
        if (!res.ok) return { status: 'error', error: data.error || 'Something went wrong.' };
        if (data.status === 'done' || data.status === 'error') return data;
        if (onTick) {
          lastStatus = data.status;
          onTick(data.status, data);
        }
      } catch (netErr) {
        // Transient network blip — keep polling instead of failing the whole job
        if (onTick) onTick('working', {});
      }
    }
    return {
      status: 'error',
      error: 'Timed out waiting for generation (took longer than 10 minutes). The job may still finish on the server — try generating again with a shorter script or refresh the page.'
    };
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
  const cloneVoiceSelect = document.getElementById('clone-voice-select');
  const cloneDeleteBtn = document.getElementById('clone-delete-voice-btn');
  const cloneUploadRow = document.getElementById('clone-upload-row');
  const cloneEngineSelect = document.getElementById('clone-engine-select');
  const cloneEngineHint = document.getElementById('clone-engine-hint');
  const cloneRefTextRow = document.getElementById('clone-ref-text-row');
  const cloneRefText = document.getElementById('clone-ref-text');
  const cloneRefTextHint = document.getElementById('clone-ref-text-hint');
  const cloneAutoTranscribeBtn = document.getElementById('clone-auto-transcribe-btn');
  const cloneSaveBtn = document.getElementById('clone-save-voice-btn');
  const cloneSaveHint = document.getElementById('clone-save-hint');
  const consentModal = document.getElementById('clone-consent-modal');
  const consentNameInput = document.getElementById('clone-voice-name');
  const consentCheckbox = document.getElementById('clone-consent-checkbox');
  const consentConfirmBtn = document.getElementById('clone-consent-confirm');
  const consentCancelBtn = document.getElementById('clone-consent-cancel');
  const consentError = document.getElementById('clone-consent-error');

  if (cloneText && cloneCharCount) {
    const limit = parseInt(cloneText.getAttribute('maxlength'), 10) || 2000;
    const updateCount = () => {
      cloneCharCount.textContent = `${cloneText.value.length} / ${limit} characters`;
      cloneCharCount.style.color = cloneText.value.length >= limit ? 'var(--brass-hi)' : 'var(--text-dim)';
      if (cloneLangDetect) cloneLangDetect.textContent = detectScriptLabel(cloneText.value);
      updateEngineHint();
    };
    cloneText.addEventListener('input', updateCount);
    updateCount();
  }

  function updateEngineHint() {
    if (cloneRefTextRow) {
      cloneRefTextRow.style.display = (cloneEngineSelect && cloneEngineSelect.value === 'f5tts') ? '' : 'none';
    }
    if (!cloneEngineSelect || !cloneEngineHint) return;
    if (cloneEngineSelect.value === 'f5tts' && detectScriptShort(cloneText.value) === 'English') {
      cloneEngineHint.textContent = 'This text looks like English — F5-TTS only supports Hindi/Urdu, switch to Chatterbox.';
      cloneEngineHint.style.color = 'var(--brass-hi)';
    } else {
      cloneEngineHint.textContent = cloneEngineSelect.value === 'f5tts'
        ? 'Slower, flow-matching model — good for Hindi/Urdu narration.'
        : '';
      cloneEngineHint.style.color = 'var(--text-dim)';
    }
  }
  if (cloneEngineSelect) {
    cloneEngineSelect.addEventListener('change', updateEngineHint);
    cloneEngineSelect.addEventListener('change', () => {
      // Catches the case where a clip/saved-voice was picked while
      // Chatterbox was selected, then the person switches to F5-TTS —
      // the ref_text box just became visible and empty, so fill it now
      // instead of leaving it for them to notice and click manually.
      if (cloneEngineSelect.value === 'f5tts' && cloneRefText && !cloneRefText.value.trim()) {
        if (usingSavedVoice() || (cloneRefInput && cloneRefInput.files.length)) {
          autoFillRefText();
        }
      }
    });
    updateEngineHint();
  }
  const cloneStatus = document.querySelector('[data-clone-status]');
  const cloneResult = document.getElementById('clone-result');

  // Tracks the reference_id from the most recent /api/clone/upload call for
  // the file currently sitting in cloneRefInput, so "Save this voice" and
  // "Clone & generate" don't each upload the same clip separately.
  let pendingReferenceId = null;
  // voice_id -> ref_text, populated from /api/clone/voices so picking a
  // saved voice can auto-fill the box instead of making the user retype
  // the same Devanagari line every single generation.
  const savedVoiceRefText = {};

  async function refreshSavedVoices(selectId) {
    if (!cloneVoiceSelect) return;
    try {
      const res = await fetch('/api/clone/voices');
      if (!res.ok) return;
      const data = await res.json();
      const voices = data.voices || [];
      cloneVoiceSelect.innerHTML = '<option value="">Upload a new reference clip…</option>';
      voices.forEach((v) => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = v.name;
        cloneVoiceSelect.appendChild(opt);
        savedVoiceRefText[v.id] = v.ref_text || '';
      });
      if (selectId) cloneVoiceSelect.value = selectId;
    } catch (e) {
      // Saved-voice list is a convenience, not required for cloning to
      // work — a failed fetch here shouldn't block the upload flow.
    }
  }
  refreshSavedVoices();

  function usingSavedVoice() {
    return cloneVoiceSelect && cloneVoiceSelect.value !== '';
  }

  if (cloneVoiceSelect && cloneUploadRow) {
    cloneVoiceSelect.addEventListener('change', () => {
      cloneUploadRow.style.display = usingSavedVoice() ? 'none' : '';
      if (cloneDeleteBtn) cloneDeleteBtn.style.display = usingSavedVoice() ? '' : 'none';
      cloneStatus.textContent = '';
      // Auto-fill the cached ref_text for this saved voice, if it has one —
      // still editable in case the saved transcript needs a correction.
      if (cloneRefText && usingSavedVoice()) {
        const cached = savedVoiceRefText[cloneVoiceSelect.value] || '';
        cloneRefText.value = cached;
        // Older saved voices predate ref_text caching and have nothing
        // stored — transcribe on the fly instead of leaving it blank.
        if (!cached && cloneEngineSelect && cloneEngineSelect.value === 'f5tts') {
          autoFillRefText();
        }
      }
    });
  }

  if (cloneDeleteBtn) {
    cloneDeleteBtn.addEventListener('click', async () => {
      const voiceId = cloneVoiceSelect.value;
      if (!voiceId) return;
      const voiceName = cloneVoiceSelect.options[cloneVoiceSelect.selectedIndex].textContent;
      if (!window.confirm(`Delete "${voiceName}"? This can't be undone.`)) return;
      cloneDeleteBtn.disabled = true;
      try {
        const res = await fetch(`/api/clone/voices/${voiceId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok || !data.deleted) {
          cloneStatus.textContent = data.error || 'Could not delete this voice.';
          return;
        }
        cloneDeleteBtn.style.display = 'none';
        cloneUploadRow.style.display = '';
        cloneStatus.textContent = `Deleted "${voiceName}".`;
        await refreshSavedVoices();
      } catch (e) {
        cloneStatus.textContent = 'Network error — check your connection.';
      } finally {
        cloneDeleteBtn.disabled = false;
      }
    });
  }

  if (cloneRefInput && cloneSaveBtn) {
    cloneRefInput.addEventListener('change', async () => {
      pendingReferenceId = null;
      cloneSaveBtn.disabled = !cloneRefInput.files.length;
      if (cloneSaveHint) cloneSaveHint.textContent = cloneRefInput.files.length
        ? 'Uploads the clip, then asks for your consent before saving.'
        : 'Upload a clip first, then save it to reuse later.';
      if (cloneRefText) cloneRefText.value = '';
      const qw = document.getElementById('clone-quality-warn');
      if (qw) { qw.style.display = 'none'; qw.innerHTML = ''; }
      // Eager upload for quality feedback
      if (cloneRefInput.files.length) {
        try {
          const form = new FormData();
          form.append('reference_audio', cloneRefInput.files[0]);
          const uploadRes = await fetch('/api/clone/upload', { method: 'POST', body: form });
          const uploadData = await uploadRes.json();
          if (uploadRes.ok) {
            pendingReferenceId = uploadData.reference_id;
            if (qw && uploadData.quality && uploadData.quality.warnings && uploadData.quality.warnings.length) {
              qw.style.display = '';
              qw.innerHTML = uploadData.quality.warnings.map(w => '• ' + w).join('<br>');
            }
          }
        } catch (e) {}
      }
      // Auto-transcribe as soon as a new clip is picked, so by the time the
      // person is ready to generate, the Devanagari box is already filled
      // in — they only need to skim and correct it, not type it from
      // scratch. Only worth doing when F5-TTS is actually selected, since
      // that's the only engine that reads ref_text.
      if (cloneRefInput.files.length && cloneEngineSelect && cloneEngineSelect.value === 'f5tts') {
        autoFillRefText();
      }
    });
  }

  async function autoFillRefText() {
    if (!cloneRefText || !cloneAutoTranscribeBtn) return;
    if (!usingSavedVoice() && !cloneRefInput.files.length) return;
    cloneAutoTranscribeBtn.disabled = true;
    const originalHint = cloneRefTextHint ? cloneRefTextHint.textContent : '';
    if (cloneRefTextHint) cloneRefTextHint.textContent = 'Listening to the reference clip…';
    try {
      let body;
      if (usingSavedVoice()) {
        body = { saved_voice_id: cloneVoiceSelect.value };
      } else {
        if (!pendingReferenceId) {
          const form = new FormData();
          form.append('reference_audio', cloneRefInput.files[0]);
          const uploadRes = await fetch('/api/clone/upload', { method: 'POST', body: form });
          const uploadData = await uploadRes.json();
          if (!uploadRes.ok) {
            if (cloneRefTextHint) cloneRefTextHint.textContent = uploadData.error || 'Upload failed.';
            return;
          }
          pendingReferenceId = uploadData.reference_id;
        }
        body = { reference_id: pendingReferenceId };
      }
      const res = await fetch('/api/clone/reference/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        if (cloneRefTextHint) cloneRefTextHint.textContent = data.error || 'Could not auto-transcribe this clip — type it manually.';
        return;
      }
      cloneRefText.value = data.text || '';
      if (cloneRefTextHint) {
        cloneRefTextHint.textContent = data.text
          ? 'Auto-filled from the clip — please check it reads correctly before generating.'
          : 'Could not make out any speech in the clip — please type it manually.';
      }
    } catch (e) {
      if (cloneRefTextHint) cloneRefTextHint.textContent = 'Network error — type the transcript manually.';
    } finally {
      cloneAutoTranscribeBtn.disabled = false;
      setTimeout(() => {
        if (cloneRefTextHint) cloneRefTextHint.textContent = originalHint;
      }, 6000);
    }
  }

  if (cloneAutoTranscribeBtn) {
    cloneAutoTranscribeBtn.addEventListener('click', autoFillRefText);
  }

  function openConsentModal() {
    if (!consentModal) return;
    consentNameInput.value = '';
    consentCheckbox.checked = false;
    consentConfirmBtn.disabled = true;
    consentError.textContent = '';
    consentModal.style.display = 'flex';
  }
  function closeConsentModal() {
    if (consentModal) consentModal.style.display = 'none';
  }
  if (consentCheckbox && consentConfirmBtn) {
    consentCheckbox.addEventListener('change', () => {
      consentConfirmBtn.disabled = !consentCheckbox.checked;
    });
  }
  if (consentCancelBtn) consentCancelBtn.addEventListener('click', closeConsentModal);

  if (cloneSaveBtn) {
    cloneSaveBtn.addEventListener('click', async () => {
      if (!cloneRefInput.files.length) return;
      cloneSaveBtn.disabled = true;
      const originalHint = cloneSaveHint ? cloneSaveHint.textContent : '';
      if (cloneSaveHint) cloneSaveHint.textContent = 'Uploading…';
      try {
        if (!pendingReferenceId) {
          const form = new FormData();
          form.append('reference_audio', cloneRefInput.files[0]);
          const uploadRes = await fetch('/api/clone/upload', { method: 'POST', body: form });
          const uploadData = await uploadRes.json();
          if (!uploadRes.ok) {
            if (cloneSaveHint) cloneSaveHint.textContent = uploadData.error || 'Upload failed.';
            return;
          }
          pendingReferenceId = uploadData.reference_id;
        }
        if (cloneSaveHint) cloneSaveHint.textContent = originalHint;
        openConsentModal();
      } catch (e) {
        if (cloneSaveHint) cloneSaveHint.textContent = 'Network error — check your connection.';
      } finally {
        cloneSaveBtn.disabled = false;
      }
    });
  }

  if (consentConfirmBtn) {
    consentConfirmBtn.addEventListener('click', async () => {
      const name = consentNameInput.value.trim();
      if (!name) {
        consentError.textContent = 'Give this voice a name.';
        return;
      }
      if (!consentCheckbox.checked || !pendingReferenceId) {
        consentError.textContent = 'Please confirm the consent statement above.';
        return;
      }
      consentConfirmBtn.disabled = true;
      consentError.textContent = '';
      try {
        const res = await fetch('/api/clone/voices/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            reference_id: pendingReferenceId,
            name,
            consent: true,
            ref_text: cloneRefText ? cloneRefText.value.trim() : '',
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          consentError.textContent = data.error || 'Could not save this voice.';
          consentConfirmBtn.disabled = false;
          return;
        }
        closeConsentModal();
        savedVoiceRefText[data.id] = cloneRefText ? cloneRefText.value.trim() : '';
        await refreshSavedVoices(data.id);
        cloneUploadRow.style.display = 'none';
        if (cloneDeleteBtn) cloneDeleteBtn.style.display = '';
        cloneStatus.textContent = `Saved as "${data.name}" — selected for generation.`;
      } catch (e) {
        consentError.textContent = 'Network error — check your connection.';
        consentConfirmBtn.disabled = false;
      }
    });
  }

  if (cloneBtn) {
    cloneBtn.addEventListener('click', async () => {
      const genConsent = document.getElementById('clone-gen-consent');
      if (genConsent && !genConsent.checked) {
        cloneStatus.textContent = 'Confirm you have permission to clone this voice before generating.';
        return;
      }
      const savedVoiceId = usingSavedVoice() ? cloneVoiceSelect.value : null;
      if (!savedVoiceId && !cloneRefInput.files.length) {
        cloneStatus.textContent = 'Upload a reference clip or pick a saved voice first.';
        return;
      }
      if (!cloneText.value.trim()) {
        cloneStatus.textContent = 'Enter some text to speak.';
        return;
      }
      const engine = cloneEngineSelect ? cloneEngineSelect.value : 'chatterbox';
      if (engine === 'f5tts' && detectScriptShort(cloneText.value) === 'English') {
        cloneStatus.textContent = 'F5-TTS only supports Hindi/Urdu text — switch to Chatterbox for English.';
        return;
      }
      cloneBtn.disabled = true;
      cloneResult.innerHTML = '';
      const progressLabel = document.getElementById('clone-progress-label');
      try {
        let referenceId = null;
        if (!savedVoiceId) {
          cloneStatus.textContent = 'Uploading reference clip…';
          if (progressLabel) progressLabel.textContent = 'Step 1/3 — Upload';
          if (pendingReferenceId) {
            referenceId = pendingReferenceId;
          } else {
            const form = new FormData();
            form.append('reference_audio', cloneRefInput.files[0]);
            const uploadRes = await fetch('/api/clone/upload', { method: 'POST', body: form });
            const uploadData = await uploadRes.json();
            if (!uploadRes.ok) {
              cloneStatus.textContent = uploadData.error || 'Upload failed.';
              return;
            }
            referenceId = uploadData.reference_id;
            pendingReferenceId = referenceId;
            // Surface quality warnings from server
            const qw = document.getElementById('clone-quality-warn');
            if (qw && uploadData.quality && uploadData.quality.warnings && uploadData.quality.warnings.length) {
              qw.style.display = '';
              qw.innerHTML = uploadData.quality.warnings.map(w => '• ' + w).join('<br>');
            } else if (qw) {
              qw.style.display = 'none';
              qw.innerHTML = '';
            }
          }
        }

        cloneStatus.textContent = 'Submitting cloning job…';
        if (progressLabel) progressLabel.textContent = 'Step 2/3 — Queue on GPU';
        const refText = (engine === 'f5tts' && cloneRefText) ? cloneRefText.value.trim() : '';
        const genRes = await fetch('/api/clone/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            savedVoiceId
              ? { text: cloneText.value.trim(), saved_voice_id: savedVoiceId, engine, ref_text: refText }
              : { text: cloneText.value.trim(), reference_id: referenceId, engine, ref_text: refText }
          ),
        });
        const genData = await genRes.json();
        if (!genRes.ok) {
          cloneStatus.textContent = genData.error || 'Could not start cloning.';
          return;
        }

        const result = await pollJob(`/api/clone/status/${genData.job_id}`, (status, data) => {
          const lang = detectScriptShort(cloneText.value);
          const pl = document.getElementById('clone-progress-label');
          if (status === 'generating') {
            cloneStatus.textContent = `Generating on GPU (${lang})… long scripts can take 1–4 minutes. Keep this tab open.`;
            if (pl) {
              const n = (data && data.chunks_generated) ? ` · chunk progress noted` : '';
              pl.textContent = 'Step 3/3 — Generating' + n;
            }
          } else if (status === 'queued') {
            cloneStatus.textContent = 'Queued… waiting for a free GPU worker.';
            if (pl) pl.textContent = 'Step 2/3 — Queued';
          } else {
            cloneStatus.textContent = 'Still working… please wait (do not close this tab).';
            if (pl) pl.textContent = 'Step 3/3 — Working…';
          }
        });
        if (result.status === 'done') {
          cloneStatus.textContent = 'Done.';
          const pl = document.getElementById('clone-progress-label');
          if (pl) pl.textContent = 'Complete';
          const ts = new Date().toISOString().slice(0,16).replace(/[-:T]/g,'');
          const cloneName = `VoxCraft-Clone-${ts}.wav`;
          cloneResult.innerHTML = `
            <audio controls style="width:100%;" src="data:audio/wav;base64,${result.audio_b64}"></audio>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
              <a class="btn btn--brass btn--sm" download="${cloneName}" href="data:audio/wav;base64,${result.audio_b64}">Download WAV</a>
              <a class="btn btn--ghost btn--sm" href="/tools/trim-cut-audio">Send to Trim →</a>
              <a class="btn btn--ghost btn--sm" href="/tools/remove-background-noise">Send to Denoise →</a>
              <a class="btn btn--ghost btn--sm" href="/tools/merge-audio-files">Send to Merge →</a>
            </div>
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
          musicStatus.textContent = status === 'generating'
            ? 'Generating music… this can take up to a couple of minutes. Keep this tab open.'
            : 'Still working… please wait.';
        });
        if (result.status === 'done') {
          musicStatus.textContent = 'Done.';
          const mts = new Date().toISOString().slice(0,16).replace(/[-:T]/g,'');
          const musicName = `VoxCraft-Music-${mts}.wav`;
          musicResult.innerHTML = `
            <audio controls style="width:100%;" src="data:audio/wav;base64,${result.audio_b64}"></audio>
            <a class="btn btn--ghost btn--sm" style="margin-top:8px;display:inline-flex;"
               download="${musicName}" href="data:audio/wav;base64,${result.audio_b64}">Download</a>
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
