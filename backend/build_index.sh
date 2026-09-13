#!/usr/bin/env sh
# =============================================================================
# build_index.sh - Phase 1 pre-build command (vector database creation)
#
# The ONE command that both environments share, so a change to the pre-build
# steps lands in exactly one place:
#
#   - Docker           : the builder stage runs `./build_index.sh` (Dockerfile)
#   - GitHub Actions   : the ci/cd backend-image jobs build the image, so this
#                        same script runs on every build via the Dockerfile
#
# It:
#   1. loads ./data docs -> chunks -> embeddings -> persisted Chroma DB
#   2. saves the embedding model locally (no HuggingFace at serving time)
#   3. cleans the HuggingFace download cache so it never reaches the image
#
# Local pre-build (outside Docker):
#     cd backend && bash build_index.sh
#
# Needs the phase-1 requirements installed (see requirements.txt).
# =============================================================================

set -eu

# Run from the backend directory no matter where the script is invoked.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

echo "[build-index] Phase 1: creating vector database from ./data ..."
python build_index.py

echo "[build-index] Cleaning HuggingFace download cache ..."
rm -rf "${HF_HOME:-/tmp/hf}"

echo "[build-index] Done."