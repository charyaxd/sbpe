'''
Produce cdefs/generated_darwin.h from cdefs/generated.h for the 64-bit
macOS client (clang, Itanium C++ ABI, libc++).

generated.h models inheritance as "first member is the base struct":

    struct Derived {
      struct Base asBase;
      int ownField;
    };

That is only correct when the base has no tail padding. Under the Itanium
ABI the fields of a derived class are laid out starting at the base's
*data size* (dsize: size without tail padding) when the base is non-POD,
i.e. they may live inside the base's tail padding. With 8-byte pointers
this happens a lot (e.g. a base ending in `int; bool;`).

For such classes this script emits

    struct Derived {
      union {
        struct Base asBase;
        struct {
          char _sbpe_base_Derived[DSIZE_OF_BASE];
          int ownField;
        };
      };
    };

which keeps `.asBase`, casts and field names working while matching the
real layout. Iterates to a fixed point because rewriting a class changes
the sizes of everything derived from it.

usage: python misc/fix_layout_darwin.py   (run from the repo root)
'''

import os
import re
import sys

import cffi

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'cdefs', 'generated.h')
DST = os.path.join(ROOT, 'cdefs', 'generated_darwin.h')
INTERNALS = os.path.join(ROOT, 'cdefs', 'internals_libcxx.h')

STRUCT_RE = re.compile(r'^struct (\w+) \{\n(.*?)^\};\n', re.M | re.S)
BASE_RE = re.compile(r'^  struct (\w+) as(\w+);')
FIELD_NAME_RE = re.compile(r'(\w+)(?:\[\d+\])*;')

# non-trivial library types: a class containing these is not POD
NONPOD_TYPES = {'STDString', 'STDVector', 'STDUMap', 'STDUSet', 'STDDeque',
                'STDFunction', 'RepeatedPtrField', 'RepeatedField_int'}


def read(p):
    with open(p) as f:
        return f.read()


class Struct(object):
    def __init__(self, name, body):
        self.name = name
        lines = [l for l in body.split('\n') if l.strip()]
        self.base = None
        m = BASE_RE.match(lines[0]) if lines else None
        if m and m.group(1) == m.group(2):
            self.base = m.group(1)
            lines = lines[1:]
        self.own = lines        # own member lines (without the base line)
        self.pad = 0            # >0 -> emitted in union form

    def own_field_names(self):
        res = []
        for l in self.own:
            code = l.split('//')[0].strip()
            m = FIELD_NAME_RE.search(code)
            if m:
                res.append(m.group(1))
        return res

    def render(self):
        if self.base is None:
            return 'struct {} {{\n{}\n}};\n'.format(
                self.name, '\n'.join(self.own))
        if not self.pad or not self.own:
            body = ['  struct {0} as{0};'.format(self.base)] + self.own
            return 'struct {} {{\n{}\n}};\n'.format(self.name, '\n'.join(body))
        inner = '\n'.join('      ' + l.strip() for l in self.own)
        return (
            'struct {n} {{\n'
            '  union {{\n'
            '    struct {b} as{b};\n'
            '    struct {{\n'
            '      char _sbpe_base_{n}[{p}];\n'
            '{inner}\n'
            '    }};\n'
            '  }};\n'
            '}};\n').format(n=self.name, b=self.base, p=self.pad, inner=inner)


def main():
    src = read(SRC)
    internals = read(INTERNALS)

    structs = {}
    order = []
    pieces = []   # either str (verbatim text) or Struct
    pos = 0
    for m in STRUCT_RE.finditer(src):
        pieces.append(src[pos:m.start()])
        s = Struct(m.group(1), m.group(2))
        structs[s.name] = s
        order.append(s.name)
        pieces.append(s)
        pos = m.end()
    pieces.append(src[pos:])

    def render_all():
        return ''.join(p if isinstance(p, str) else p.render() for p in pieces)

    def has_vptr(name):
        s = structs.get(name)
        if s is None:
            return False
        if s.base:
            return has_vptr(s.base)
        return any('classptr' in l for l in s.own[:1])

    def is_pod(name):
        s = structs.get(name)
        if s is None:
            return name not in NONPOD_TYPES
        if has_vptr(name):
            return False
        if s.base and not is_pod(s.base):
            return False
        for l in s.own:
            code = l.split('//')[0]
            for t in re.findall(r'struct (\w+)(?! ?\*)\b', code):
                if '*' in code.split(t, 1)[1].split(';')[0]:
                    continue
                if not is_pod(t):
                    return False
        return True

    iteration = 0
    while True:
        iteration += 1
        text = render_all()
        ffi = cffi.FFI()
        ffi.cdef(internals)
        ffi.cdef(text)

        dsize_memo = {}

        def field_type(sname, fname):
            # works for fields flattened out of anonymous structs/unions
            for n, f in ffi.typeof('struct ' + sname).fields:
                if n == fname:
                    return f.type
            raise KeyError((sname, fname))

        def dsize2(name):
            if name in dsize_memo:
                return dsize_memo[name]
            s = structs.get(name)
            if s is None:
                res = ffi.sizeof('struct ' + name)
            else:
                end = dsize2(s.base) if s.base else 0
                for fname in s.own_field_names():
                    off = ffi.offsetof('struct ' + name, fname)
                    end = max(end, off + ffi.sizeof(field_type(name, fname)))
                res = end
            dsize_memo[name] = res
            return res

        changed = 0
        for name in order:
            s = structs[name]
            if not s.base or not s.own:
                continue
            b = s.base
            want = 0
            if not is_pod(b):
                bd = dsize2(b)
                if bd < ffi.sizeof('struct ' + b):
                    want = bd
            if want != s.pad:
                s.pad = want
                changed += 1

        print('iteration {}: {} structs changed'.format(iteration, changed))
        if not changed:
            break
        if iteration > 50:
            sys.exit('layout did not converge')

    hdr = ('// GENERATED by misc/fix_layout_darwin.py from generated.h\n'
           '// x86_64 / Itanium ABI tail-padding aware layout. Do not edit.\n')
    with open(DST, 'w') as f:
        f.write(hdr + text)
    n = sum(1 for s in structs.values() if s.pad)
    print('wrote {} ({} structs use base tail padding)'.format(DST, n))


if __name__ == '__main__':
    main()
