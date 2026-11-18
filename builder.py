import cffi
import glob
import platform

SYSTEM = platform.system()

# relative to build dir
LIB_BASE = '../libs/'
# compiling libraries statically to get a single binary
EXTRA_SRC = [LIB_BASE + 'subhook/subhook.c']

pltsysname = {'Windows': 'win32', 'Darwin': 'osx', 'Linux': 'elf'}
pltsrc = pltsysname[SYSTEM]
pltsrc = LIB_BASE + 'plthook/plthook_{}.c'.format(pltsrc)
# EXTRA_SRC.append(pltsrc)  # disabled until it is actually useful

LIBDIRS = []
LIBRARIES = ['SDL2']
EXTRA_COMPILE = []
EXTRA_LINK = []
if SYSTEM == 'Windows':
    LIBDIRS.append('../libs/SDL/lib/x86/')

CDEFS = 'generated internals SDL XDL subhook xternPython'.split()

if SYSTEM == 'Darwin':
    # 64-bit clang/libc++ build of the game: different STL layouts and
    # tail-padding-aware struct definitions (see misc/fix_layout_darwin.py)
    CDEFS = ('generated_darwin internals_libcxx SDL XDL subhook xternPython '
             'darwin').split()
    # the game is x86_64 only (runs under Rosetta on Apple Silicon)
    EXTRA_COMPILE += ['-arch', 'x86_64']
    # SDL comes from the game's own bundled libSDL2, resolved at load time
    LIBRARIES = []
    EXTRA_LINK += ['-arch', 'x86_64', '-undefined', 'dynamic_lookup']
    # libpython of the building interpreter (e.g. the Command Line Tools'
    # Python3.framework, whose install name is @rpath/Python3.framework/...)
    import os
    import sys
    LIBDIRS.append(os.path.join(sys.base_prefix, 'lib'))
    fwdir = sys.base_prefix.split('/Python3.framework/')[0]
    if fwdir != sys.base_prefix:
        EXTRA_LINK += ['-Wl,-rpath,' + fwdir]


def readfile(name):
    with open(name, 'r') as f:
        content = f.read()
    return content


def build():
    ffibuilder = cffi.FFI()

    # internals first: generated.h refers to the STL helper structs
    order = sorted(CDEFS, key=lambda n: 0 if n.startswith('internals') else 1)
    for fname in order:
        ffibuilder.cdef(readfile('cdefs/{}.h'.format(fname)))

    ffibuilder.embedding_api('uint32_t kickstart();')
    ffibuilder.embedding_init_code(readfile('remote.py'))

    ffibuilder.set_source(
        '_remote', readfile('cdefs/remote.c'), sources=EXTRA_SRC,
        libraries=LIBRARIES, library_dirs=LIBDIRS,
        extra_compile_args=EXTRA_COMPILE, extra_link_args=EXTRA_LINK,
        define_macros=[('SUBHOOK_STATIC', None)])

    ffibuilder.compile(tmpdir='build', target='remote.bin', verbose=True)


if __name__ == '__main__':
    if SYSTEM == 'Darwin':
        import runpy
        runpy.run_path('misc/fix_layout_darwin.py', run_name='__main__')
    build()
