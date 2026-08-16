# RunPod serverless worker — Chatterbox-Turbo voice cloning.
#
# Build & push (from this runpod_workers/chatterbox/ directory):
#   docker build -t <your-dockerhub-username>/voxcraft-clone-worker:latest .
#   docker push <your-dockerhub-username>/voxcraft-clone-worker:latest
#
# Then in the RunPod dashboard: Serverless → New Endpoint → Custom Source →
# paste that image name. Pick a GPU tier with at least 8GB VRAM (Chatterbox-
# Turbo is small — an RTX 4000/A4000-class GPU is plenty, no need for
# anything bigger). Copy the endpoint ID into RUNPOD_CLONE_ENDPOINT_ID on
# the VPS once it's deployed.

FROM runpod/base:0.6.2-cuda12.1.0

WORKDIR /app

COPY requirements.txt .
# NOTE: pip package name/version for the "Turbo" Chatterbox variant may have
# shifted since this was written — if the build fails on `chatterbox-tts`,
# check https://github.com/resemble-ai/chatterbox for the current install
# instructions (it may need `pip install git+https://github.com/resemble-ai/chatterbox.git`
# instead of a PyPI pin).
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

CMD ["python3", "-u", "handler.py"]
