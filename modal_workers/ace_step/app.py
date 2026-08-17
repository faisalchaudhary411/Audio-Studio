"""
modal_workers/ace_step/app.py — ACE-Step 1.5 self-hosted music generation on
Modal GPU.

CHANGED: migrated off Replicate's hosted ACE-Step (music_engine.py previously
called lucataco/ace-step via the Replicate API, billed ~$0.02-0.03 per
generation regardless of GPU load). Self-hosting here means you only pay for
the GPU-seconds this container actually runs — Modal scales the container to
zero when idle, same pattern already proven in this project for Chatterbox
voice cloning (see modal_workers/chatterbox/app.py).

The old music_engine.py docstring ruled out self-hosting ACE-Step v1 on
Render/VPS because its repo needs a git-clone-and-build install with a
local-path dependency (nano-vllm) — doesn't fit a plain `pip install -r
requirements.txt` buildpack, and a 1 vCPU / 2GB VPS has no GPU anyway. Same
is true of v1.5 (worse, actually — it now bundles an LLM stage too). So this
follows the same architecture as Chatterbox: the model runs on Modal's GPU
containers, the VPS just makes an HTTP call to it (see music_client.py).

MODEL: ACE-Step 1.5 (Apache 2.0 — code and weights, genuinely commercial-
safe, same as v1). v1.5 adds a language-model stage on top of the diffusion
(DiT) audio model: the LM auto-enhances prompts, detects language, and infers
BPM/key. Two models are loaded into this container, not one.

Built directly off Modal's own reference example for this exact model:
https://modal.com/docs/examples/generate_music
(https://github.com/modal-labs/modal-examples/blob/main/06_gpu_and_ml/text-to-audio/generate_music.py)
— adapted from that example's modal.method()/local_entrypoint() pattern to
match this project's existing HTTP-endpoint pattern (modal.fastapi_endpoint,
same as modal_workers/chatterbox/app.py), since music_engine.py calls this
over plain HTTP from a background thread, not via the Modal SDK.

GPU: L40S (48GB) — the tier Modal's own example uses. ACE-Step 1.5's default
LM checkpoint (acestep-5Hz-lm-4B) plus the DiT model plus vLLM's KV-cache
overhead don't comfortably fit a 24GB A10G. If you want to cut GPU cost,
try swapping LM_MODEL_NAME to the smaller "acestep-5Hz-lm-0.6B" checkpoint on
an A10G — untested here, watch your Modal logs for CUDA OOM on first deploy.

COLD START: the very first request after a scale-to-zero has to load both
models (and, on the very first deploy ever, download ~15-20GB of weights
into the cached Volume). That can take a couple of minutes. Once warm,
generation itself is fast (ACE-Step 1.5 turbo is sub-2s/song on an A100-class
GPU per the model card) — most of the wall-clock time you'll see is the
container spin-up, not the actual generation. music_client.py's timeout is
set generously to cover this.

Requires two Modal secrets/tokens set as GitHub Actions repo secrets
(MODAL_TOKEN_ID / MODAL_TOKEN_SECRET) — see
.github/workflows/deploy-modal-music-worker.yml for the one-time setup.

BUG FIX: `seed` was originally typed `int = None`, which Pydantic v2
validates as a plain `int` field that merely defaults to None — it does NOT
accept an incoming `null` in the request body. music_client.py always sends
`"seed": null` when no seed is chosen, so every request failed Pydantic
validation before generation even started, returned as HTTP 422 with no
useful body. Fixed by typing it `Optional[int] = None`, which explicitly
allows None as a valid value, not just as a default.
"""

import base64
import traceback
from pathlib import Path
from typing import Optional

import modal
from pydantic import BaseModel

# ── Image ────────────────────────────────────────────────────────────────
# ACE-Step 1.5 declares a local-path dependency (nano-vllm) inside its own
# repo, so — same as Modal's reference example — we clone the repo first and
# let `uv` resolve everything (including the CUDA-enabled torch build and
# the local nano-vllm package) from that checkout. A plain
# `pip install git+https://...` will NOT resolve the local path dependency.
image = (
    modal.Image.from_registry(
        "nvidia/cuda:13.0.0-cudnn-devel-ubuntu22.04", add_python="3.12"
    )
    .apt_install("git", "ffmpeg")
    .run_commands(
        "git clone --branch v0.1.6 --depth 1 https://github.com/ace-step/ACE-Step-1.5.git /opt/ace-step",
    )
    .uv_pip_install(
        "/opt/ace-step",
        "hf_transfer==0.1.9",
        "torchcodec==0.10.0",
        "torch~=2.10.0",
        "fastapi[standard]",
        "pydantic",
    )
    .entrypoint([])
)

# Single Volume for both the DiT and LM model weights, persisted across
# deploys/cold-starts so you only pay the multi-GB download cost once.
checkpoints_dir = "/opt/ace-step/checkpoints"
model_cache = modal.Volume.from_name("voxcraft-ace-step-model-cache", create_if_missing=True)

image = image.env(
    {"ACESTEP_PROJECT_ROOT": "/opt/ace-step", "HF_HUB_ENABLE_HF_TRANSFER": "1"}
)

app = modal.App("voxcraft-music-worker", image=image)

LM_MODEL_NAME = "acestep-5Hz-lm-4B"
# Sanity cap independent of MUSIC_MAX_DURATION_SEC in the main app's app.py —
# belt-and-suspenders in case this worker is ever called directly.
MAX_DURATION_SEC = 240


class MusicRequest(BaseModel):
    prompt: str
    lyrics: str = ""
    duration: float = 60.0
    seed: Optional[int] = None  # was `int = None` — Pydantic v2 rejected an incoming null; see module docstring
    audio_format: str = "wav"  # "wav" or "mp3" — kept "wav" by default to match the frontend's <audio> mime type


class MusicResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""
    duration_seconds: float = 0.0


@app.cls(
    gpu="L40S",
    image=image,
    volumes={checkpoints_dir: model_cache},
    timeout=900,  # generous — covers first-ever cold start incl. model download
    scaledown_window=300,
)
class ACEStepWorker:
    @modal.enter()
    def load_model(self):
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.model_downloader import ensure_lm_model, ensure_main_model

        # Downloads into the Volume if not already cached there.
        ensure_main_model(checkpoints_dir=checkpoints_dir)
        ensure_lm_model(model_name=LM_MODEL_NAME, checkpoints_dir=checkpoints_dir)

        # DiT (audio diffusion) model. "turbo" config trades a small amount
        # of quality for a large speed win — matches Modal's own example
        # and keeps generation time (and GPU cost) down.
        self.dit_handler = AceStepHandler()
        init_status, enable_generate = self.dit_handler.initialize_service(
            project_root="/opt/ace-step",
            config_path="acestep-v15-turbo",
            device="cuda",
        )
        if not enable_generate:
            raise RuntimeError(f"DiT model initialization failed: {init_status}")

        # LM stage — prompt enhancement, language detection, BPM/key inference.
        self.llm_handler = LLMHandler()
        lm_status, lm_success = self.llm_handler.initialize(
            checkpoint_dir=checkpoints_dir,
            lm_model_path=LM_MODEL_NAME,
            backend="vllm",
            device="cuda",
        )
        if not lm_success:
            raise RuntimeError(f"LM initialization failed: {lm_status}")

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: MusicRequest):
        from acestep.inference import GenerationConfig, GenerationParams, generate_music

        prompt = (req.prompt or "").strip()
        # ACE-Step's convention for "no vocals" is a literal [Instrumental]
        # lyrics tag, not an empty string.
        lyrics = (req.lyrics or "").strip() or "[Instrumental]"
        duration = min(max(req.duration, 5.0), MAX_DURATION_SEC)
        audio_format = req.audio_format if req.audio_format in ("wav", "mp3") else "wav"

        if not prompt:
            return MusicResponse(success=False, error="No prompt provided.").model_dump()

        try:
            params = GenerationParams(
                caption=prompt,
                lyrics=lyrics,
                duration=duration,
                thinking=True,  # let the LM stage enhance the prompt / infer BPM+key
            )
            config = GenerationConfig(
                audio_format=audio_format,
                batch_size=1,
                seeds=[req.seed] if req.seed is not None else None,
                use_random_seed=req.seed is None,
            )
            result = generate_music(
                self.dit_handler,
                self.llm_handler,
                params,
                config,
                save_dir="/dev/shm",  # tmpfs — avoids disk I/O for a short-lived file
            )
            if not result.success:
                return MusicResponse(
                    success=False, error=result.error or "Generation failed."
                ).model_dump()

            out_path = Path(result.audios[0]["path"])
            audio_bytes = out_path.read_bytes()
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

            try:
                out_path.unlink()
            except Exception:
                pass  # /dev/shm is wiped with the container anyway — not fatal if this fails

            return MusicResponse(
                success=True,
                audio_b64=audio_b64,
                duration_seconds=duration,
            ).model_dump()

        except Exception as exc:
            tb = traceback.format_exc()
            return MusicResponse(success=False, error=f"{exc}\n\n{tb}").model_dump()
