#!/bin/bash
# SBPE for macOS: double-click in Finder (or run from Terminal) with Steam running.
#
# The game is x86_64, and site-packages holds x86_64 modules, so the loader
# runs under Rosetta with the Python of Apple's Command Line Tools, the same
# Python that build/remote.bin is linked against.
cd "$(dirname "$0")"

CLT_PY=/Library/Developer/CommandLineTools/usr/bin/python3

pause_exit() {
    echo
    read -n 1 -s -r -p "press any key to close"
    echo
    exit "${1:-1}"
}

# 1. Apple's Command Line Tools provide the Python that SBPE runs on
if [ ! -x "$CLT_PY" ] || ! xcode-select -p >/dev/null 2>&1; then
    echo "SBPE needs Apple's Command Line Tools (free, one-time install)."
    echo "A window will open: click Install, wait for it to finish,"
    echo "then double-click run.command again."
    xcode-select --install 2>/dev/null
    pause_exit 1
fi

# 2. Rosetta runs the x86_64 game and SBPE on Apple Silicon
if [ "$(uname -m)" = "arm64" ] && ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    echo "Rosetta is needed to run StarBreak and SBPE. Installing it now..."
    softwareupdate --install-rosetta --agree-to-license || pause_exit 1
fi

PY=(arch -x86_64 "$CLT_PY")

# 3. files downloaded from the internet are quarantined, and macOS refuses to
#    load quarantined libraries into the game; clear it for this folder only
xattr -dr com.apple.quarantine . 2>/dev/null

# 4. the prebuilt files must match this Mac's Python; rebuild if they don't
WANT="$(cat build/python_version 2>/dev/null)"
HAVE="$("${PY[@]}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ ! -f build/remote.bin ] || [ "$WANT" != "$HAVE" ]; then
    echo "prebuilt SBPE is for Python ${WANT:-?}, this Mac has $HAVE: rebuilding"
    ./build_mac.sh || pause_exit 1
fi

if ! pgrep -xq steam_osx; then
    echo "warning: Steam does not seem to be running; start Steam first"
fi

export PYTHONNOUSERSITE=1
export PYTHONPATH="$PWD/site-packages"
"${PY[@]}" loader.py || pause_exit 1
