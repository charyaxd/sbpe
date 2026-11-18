#!/bin/bash
# Build a downloadable macOS release zip in release/ (prebuilt, players only
# need Steam + Apple's Command Line Tools). Usage: ./make_release_mac.sh v1.7.0-mac1
set -euo pipefail
cd "$(dirname "$0")"
VERSION="${1:?usage: $0 VERSION}"
NAME="sbpe-mac"
OUT="release/$NAME-$VERSION.zip"

./build_mac.sh

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
# everything except personal/runtime files and build intermediates
rsync -a \
    --exclude config.ini --exclude '*.log' --exclude symbols.json \
    --exclude '__pycache__' --exclude .DS_Store --exclude .git --exclude release \
    --exclude 'build/*' --exclude '*.o' --exclude 'rectbinpack/_rbp.cpp' \
    --exclude pypy --exclude '*.out' \
    ./ "$STAGE/$NAME/"
mkdir -p "$STAGE/$NAME/build"
cp build/remote.bin build/python_version "$STAGE/$NAME/build/"

# pip's install records list local cache paths; not needed at runtime
find "$STAGE/$NAME/site-packages" -name RECORD -path '*.dist-info/*' -delete

# refuse to ship anything that mentions this machine's user
if grep -rlaiq -- "$USER" "$STAGE/$NAME"; then
    echo "error: files mention '$USER':" >&2
    grep -rlai -- "$USER" "$STAGE/$NAME" >&2
    exit 1
fi

mkdir -p release
rm -f "$OUT"
ditto -c -k --keepParent "$STAGE/$NAME" "$OUT"
echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"
