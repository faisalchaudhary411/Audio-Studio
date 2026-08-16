# RunPod serverless worker — Chatterbox-Turbo voice cloning.
#
# Build & push happens automatically via .github/workflows/build-clone-worker.yml
# on every push to this folder — no local Docker needed.
#
# Then in the RunPod dashboard: Serverless -> New Endpoint -> Custom Source ->
# paste the ghcr.io image URL. Pick a GPU tier with at least 8GB VRAM
# (Chatterbox-Turbo is small - an RTX 4000/A4000-class GPU is plenty).
# Copy the endpoint ID into RUNPOD_CLONE_ENDPOINT_ID on the VPS once deployed.

FROM runpod/base:0.6.2-cuda12.1.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# chatterbox-tts (as published on PyPI) pulls in a dependency called
# pkuseg (Chinese word segmentation, used only by the multilingual variant
# we don't need) that fails to compile from source on most Linux/Docker
# environments -- a known, still-open upstream packaging bug:
#   https://github.com/resemble-ai/chatterbox/issues/231
#   https://github.com/resemble-ai/chatterbox/issues/237
#   https://github.com/resemble-ai/chatterbox/issues/367
# The documented community workaround (issue #240) is to install from
# source with pkuseg stripped out of pyproject.toml before installing --
# that's what the next step does. If `pip install chatterbox-tts` starts
# working cleanly again in a future release, this whole block can be
# replaced with a normal requirements.txt pin.
RUN git clone --depth 1 https://github.com/resemble-ai/chatterbox.git /opt/chatterbox \
    && cd /opt/chatterbox \
    && sed -i '/pkuseg/d' pyproject.toml \
    && pip install --no-cache-dir -e .

COPY handler.py .

CMD ["python3", "-u", "handler.py"]
