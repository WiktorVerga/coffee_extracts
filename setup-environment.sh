#!/bin/bash
# Cloud environment setup script (paste it into the "Setup script" field of the
# environment on claude.ai/code). Installs Playwright and the browser used for rendering.
set -e
pip install --break-system-packages playwright || pip install playwright
python3 -m playwright install --with-deps chromium || echo "Chromium download failed: the render will try a system Chrome."

# --- Animated reels (HyperFrames) ---------------------------------------
# Voice (Kokoro, voice af_heart), numpy for the audio mix, ffmpeg, HyperFrames CLI
pip install --break-system-packages numpy kokoro-onnx soundfile || pip install numpy kokoro-onnx soundfile || echo "Voice packages failed: reels will be skipped."
command -v ffmpeg >/dev/null 2>&1 || (apt-get update -y && apt-get install -y ffmpeg) || echo "ffmpeg missing: reels will be skipped."
npm install -g hyperframes@0.8.137 || echo "HyperFrames install failed: the routine will try npx."
# Download the voice model now, so the runs don't have to
hyperframes tts "ready" --voice af_heart --output /tmp/warmup.wav || echo "Voice warm-up failed: the first reel will download the model."
