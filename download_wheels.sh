#!/usr/bin/env bash
# Download Pillow wheels for all supported platforms.
# Run this before building the Blender extension package.
#
# Usage: ./download_wheels.sh [pillow_version] [python_version]
#   e.g.: ./download_wheels.sh 11.1.0 3.11

set -euo pipefail

VERSION="${1:-11.1.0}"
PYTHON_VERSION="${2:-3.11}"
DEST="wheels"

PLATFORMS=(
    "manylinux_2_28_x86_64"
    "win_amd64"
    "macosx_11_0_arm64"
    "macosx_10_10_x86_64"
)

rm -rf "$DEST"
mkdir -p "$DEST"

for platform in "${PLATFORMS[@]}"; do
    echo "Downloading Pillow ${VERSION} for ${platform} (cp${PYTHON_VERSION//./})..."
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

# Auto-update blender_manifest.toml wheels list
MANIFEST="blender_manifest.toml"
if [ -f "$MANIFEST" ]; then
    # Build the new wheels list
    WHEELS_TOML="wheels = ["
    first=true
    for whl in "$DEST"/*.whl; do
        if [ "$first" = true ]; then
            first=false
            WHEELS_TOML+=$'\n'
        fi
        WHEELS_TOML+="    \"./${whl}\","$'\n'
    done
    WHEELS_TOML+="]"

    # Replace everything from 'wheels = [' to the closing ']'
    # Use python for reliable multiline replacement
    python3 -c "
import re, sys
manifest = open('$MANIFEST').read()
new_wheels = '''$WHEELS_TOML'''
updated = re.sub(r'wheels\s*=\s*\[.*?\]', new_wheels, manifest, flags=re.DOTALL)
open('$MANIFEST', 'w').write(updated)
"
    echo ""
    echo "Updated $MANIFEST wheels list."
fi
