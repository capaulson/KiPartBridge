#!/bin/bash
set -e
cd "$(dirname "$0")"

# Activate venv
source venv/bin/activate

# Ensure PyInstaller is installed
pip install "pyinstaller>=6.0"

# Build the sidecar binary
cd src/python
python -m PyInstaller --name kipartbridge-sidecar \
  --distpath ../../dist/python \
  --workpath ../../build/python \
  --specpath ../../build \
  --noconfirm --onedir --console \
  --hidden-import=extractors \
  --hidden-import=extractors.base \
  --hidden-import=extractors.ultra_librarian \
  --hidden-import=extractors.snapeda \
  --hidden-import=extractors.samacsys \
  --hidden-import=extractors.easyeda \
  --hidden-import=extractors.generic \
  --hidden-import=provider_classifier \
  --hidden-import=normalizer \
  --hidden-import=library_injector \
  --hidden-import=database \
  --hidden-import=models \
  --paths=. \
  main.py

echo ""
echo "Build complete: dist/python/kipartbridge-sidecar/"
echo "Binary: dist/python/kipartbridge-sidecar/kipartbridge-sidecar"
