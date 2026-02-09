#!/usr/bin/env bash
# Download Pillow wheels for all supported platforms.
# Run this before building the Blender extension package.
#
# Usage: ./download_wheels.sh [pillow_version]
#   e.g.: ./download_wheels.sh 11.1.0

set -euo pipefail

VERSION="${1:-11.1.0}"
PYTHON_VERSION="3.11"
DEST="./wheels"

PLATFORMS=(
    "manylinux_2_28_x86_64"
    "win_amd64"
    "macosx_11_0_arm64"
)

rm -rf "$DEST"
mkdir -p "$DEST"

for platform in "${PLATFORMS[@]}"; do
    echo "Downloading Pillow ${VERSION} for ${platform}..."
    pip download \
        "Pillow==${VERSION}" \
        --dest "$DEST" \
        --python-version "$PYTHON_VERSION" \
        --only-binary=:all: \
        --platform "$platform" \
        --no-deps
done

echo ""
echo "Downloaded wheels:"
ls -1 "$DEST"/*.whl

echo ""
echo "Update blender_manifest.toml 'wheels' list if filenames changed:"
for whl in "$DEST"/*.whl; do
    echo "    \"./$whl\","
done
