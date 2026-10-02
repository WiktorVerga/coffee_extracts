#!/bin/bash
# Cloud environment setup script (paste it into the "Setup script" field of the
# environment on claude.ai/code). Installs Playwright and the browser used for rendering.
set -e
pip install --break-system-packages playwright || pip install playwright
python3 -m playwright install --with-deps chromium || echo "Chromium download failed: the render will try a system Chrome."
