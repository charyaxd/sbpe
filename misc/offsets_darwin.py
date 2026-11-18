'''print struct offsets as seen by the macOS cdefs: Struct.field ...'''
import os, sys
import cffi
R = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
ffi = cffi.FFI()
for n in 'internals_libcxx generated_darwin SDL XDL'.split():
    ffi.cdef(open(os.path.join(R, 'cdefs', n + '.h')).read())
for spec in sys.argv[1:]:
    s, _, f = spec.partition('.')
    if f:
        print('{:40} {:#x}'.format(spec, ffi.offsetof('struct ' + s, f)))
    else:
        print('{:40} sizeof {:#x}'.format(spec, ffi.sizeof('struct ' + s)))
