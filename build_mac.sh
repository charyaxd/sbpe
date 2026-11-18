#!/bin/bash
# Build SBPE for macOS. Needs the Xcode Command Line Tools (xcode-select --install).
# StarBreak's mac client is x86_64, so everything is built for x86_64 and the
# game (and the loader) run under Rosetta on Apple Silicon.
set -euo pipefail
cd "$(dirname "$0")"

if ! xcode-select -p >/dev/null 2>&1; then
    echo "Command Line Tools missing: run 'xcode-select --install' first" >&2
    exit 1
fi

PY=(arch -x86_64 /Library/Developer/CommandLineTools/usr/bin/python3)

# subhook needs x86_64 fixes (near trampolines, instruction decoder)
if ! grep -q "sbpe:" libs/subhook/subhook_x86.c; then
    echo "patching libs/subhook"
    patch -p1 -N -d libs/subhook < patches/subhook-x86_64-fixes.patch
fi

export PYTHONPATH="$PWD/site-packages"
if ! "${PY[@]}" -c "import cffi, PIL, google.protobuf" 2>/dev/null; then
    echo "installing python modules into site-packages/"
    "${PY[@]}" -m pip install --disable-pip-version-check -q --target site-packages \
        cffi Pillow "protobuf==3.20.3"
fi

echo "testing subhook decoder"
mkdir -p build
clang -arch x86_64 -w patches/test_subhook_disasm.c -o build/test_subhook_disasm
arch -x86_64 build/test_subhook_disasm > /dev/null

echo "building rectbinpack"
(cd rectbinpack && "${PY[@]}" rbp_builder.py > ../build/rbp.log 2>&1) \
    || { tail -20 build/rbp.log; exit 1; }

echo "building remote.bin"
"${PY[@]}" builder.py > build/build.log 2>&1 || { grep -E "error" build/build.log; exit 1; }
# drop debug info (it records local build paths), then ad-hoc sign so macOS
# is happy to load the freshly built code
strip -S build/remote.bin rectbinpack/_rbp*.so
codesign -f -s - build/remote.bin rectbinpack/_rbp*.so 2>/dev/null || true
"${PY[@]}" -c 'import sys; print("%d.%d" % sys.version_info[:2])' > build/python_version

[ -f config.ini ] || {
    sed -e "s|^game = .*|game = ~/Library/Application Support/Steam/steamapps/common/StarBreak/MVMMOClient.app|" \
        config_template.ini > config.ini
    echo "created config.ini"
}
echo "done: start the game with ./run.command (Steam must be running)"
