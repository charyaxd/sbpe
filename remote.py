import configparser
import importlib
import json
import logging
import os
import platform
import sys
import time

from _remote import ffi, lib

util = None

VERSION = 'v1.7.0'
LOGFILE = 'remote.log'
CONFIGFILE = 'config.ini'

# non-function imported symbol types
SYMTYPES = {
    'stage': 'struct Stage **',
    'window_': 'void **',
    'canvasW_': 'int *',
    'canvasH_': 'int *',
    'userData_': 'void **',
    'WorldClient::handleWindowEvent': 'void *',
    'UIElementContainer::handleWindowEvent': 'void *'
}


class dotdict(dict):
    '''dict with dot notation accessors'''
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# various references to pass around (symbols, constants, etc)
refs = dotdict(
    tops=[],  # collection of direct children of stage
    topTypes=[],  # the class names of tops
    MainMenu=ffi.NULL,
    GameClient=ffi.NULL,
    WorldClient=ffi.NULL,
    ClientWorld=ffi.NULL,
    WorldView=ffi.NULL,
    overrideW=0, overrideH=0,  # fake values to return from XDL_GetWindowSize
    windowW=0, windowH=0,  # current window size
    scaleX=1, scaleY=1,    # current window scale
    lastMove=0  # timestamp of last mouse movement
)

refs.VERSION = VERSION
refs.SYSINFO = '{0} v{1} {2} @ {3}'.format(
    platform.python_implementation(), platform.python_version(),
    platform.architecture()[0], platform.platform())

refs.config = configparser.ConfigParser()
refs.config.optionxform = str

refs.manager = None


# hooks ######################################################################

ORIGS = {}


@ffi.def_extern()
def hook_DoEvents():
    refs.manager.run()
    refs.manager.runCallbacks('beforeUpdate')
    ORIGS['XDL_DoEvents']()


@ffi.def_extern()
def hook_Clear(color):
    util.updateState()
    refs.manager.runCallbacks('afterUpdate')
    ORIGS['XDL_Clear'](refs.stage[0].backgroundColor)


@ffi.def_extern()
def hook_Present():
    refs.manager.runCallbacks('onPresent')
    ORIGS['XDL_Present']()


@ffi.def_extern()
def hook_GetWindowSize(wptr, hptr):
    if refs.overrideW > 0:
        wptr[0] = refs.overrideW
        hptr[0] = refs.overrideH
    else:
        lib.SDL_GetWindowSize(refs.window_[0], wptr, hptr)


@ffi.def_extern()
def hook_TrackGAEvent(category, action, label, value):
    pass
    # logging.debug('GA: {}.{} "{}" {}'.format(
    #     ffi.string(category).decode(), ffi.string(action).decode(),
    #     ffi.string(label).decode(), value))


@ffi.def_extern()
def hook_mouseMove(x, y, userData):
    x = round(x * refs.scaleX)
    y = round(y * refs.scaleY)
    ORIGS['mouseMoveCallback'](x, y, userData)
    refs.lastMove = time.perf_counter()


@ffi.def_extern()
def hook_mouseButton(x, y, button, down, userData):
    x = round(x * refs.scaleX)
    y = round(y * refs.scaleY)
    ORIGS['mouseButtonCallback'](x, y, button, down, userData)


@ffi.def_extern()
def hook_LoadTextureFile(name, callback, userData):
    refs._tfname = ffi.string(name).decode()

    hook = lib.subhook_new(callback, lib.hook_textureCallback, 1)
    refs._orig_callback = ffi.cast(
        'XDL_LoadTextureDoneCallback', lib.subhook_get_trampoline(hook))

    lib.subhook_install(hook)
    ORIGS['XDL_LoadTextureFile'](name, callback, userData)
    lib.subhook_remove(hook)
    lib.subhook_free(hook)


@ffi.def_extern()
def hook_textureCallback(texture, sptr):
    refs._orig_callback(texture, sptr)

    tname = refs._tfname.split('/')
    pname, sid = tname[1].split('.', 1)
    sid = sid.split('.')
    if tname[0] != 'texture' or sid[0] != 'm0':
        return
    util.loadMipmaps(pname, sid[1])


def initHooks():
    def addhook(fname, hookfunc, ret=False):
        hook = lib.subhook_new(refs[fname], hookfunc, 1)
        orig = ffi.cast('p' + fname, lib.subhook_get_trampoline(hook))
        logging.debug('{}: src {} trampoline {}'.format(fname, refs[fname], orig))
        if orig != ffi.NULL:
            ORIGS[fname] = orig
        else:
            logging.info('{}: no trampoline, using fallback'.format(fname))

            def call_orig(*args):
                lib.subhook_remove(hook)
                res = refs[fname](*args)
                lib.subhook_install(hook)
                if ret:
                    return res

            ORIGS[fname] = call_orig

        lib.subhook_install(hook)
        if not lib.subhook_is_installed(hook):
            logging.error('failed to hook {}'.format(fname))

    addhook('XDL_DoEvents', lib.hook_DoEvents)
    addhook('XDL_Clear', lib.hook_Clear)
    addhook('XDL_Present', lib.hook_Present)
    addhook('XDL_GetWindowSize', lib.hook_GetWindowSize)
    addhook('XDL_TrackGAEvent', lib.hook_TrackGAEvent)
    addhook('mouseMoveCallback', lib.hook_mouseMove)
    addhook('mouseButtonCallback', lib.hook_mouseButton)

    if refs.config.getboolean('general', 'mipmaps', fallback=False):
        addhook('XDL_LoadTextureFile', lib.hook_LoadTextureFile)


# symbols (macOS) ############################################################

# same list as loader.py; on macOS the symbols are looked up in the game's
# in-memory symbol table instead of using symquery on the file
DARWIN_SYMLIST = '''
stage window_ canvasW_ canvasH_
mouseMoveCallback mouseButtonCallback windowEventCallback
userData_

XDL_GetWindowSize
XDL_DoEvents XDL_Clear XDL_Present
XDL_DrawPoint XDL_DrawLine XDL_DrawRect XDL_DrawTri XDL_FillRect XDL_FillTri
XDL_LoadTextFile XDL_LoadTextureFile XDL_CreateTextTexture
XDL_CalculateTextWidth XDL_LineSpacing
XDL_QueryTexture XDL_DrawTexture
XDL_GetNumberDict XDL_DrawFromNumberDict XDL_SizeFromNumberDict
XDL_DestroyTexture
XDL_TrackGAEvent

flags::drawHUD
flags::drawTiles
flags::drawEdge
flags::drawScatter
flags::drawUniform
flags::drawHitBoxes
flags::drawBoxes

WorldClient::handleWindowEvent
UIElementContainer::handleWindowEvent
'''.split()


def _manglePrefixes(name):
    '''Itanium-mangled name prefixes that a (simple) C++ name can have'''
    parts = name.split('::')
    if len(parts) > 1:
        nested = ''.join('{}{}'.format(len(p), p) for p in parts)
        return ['_ZN' + nested + 'E']
    n = '{}{}'.format(len(name), name)
    # file-static first (_ZL), then global function/variable, then plain C
    return ['_ZL' + n, '_Z' + n, name]


def resolveSymbolsDarwin():
    offsets = {}
    missing = []
    count = ffi.new('int *')
    for sname in DARWIN_SYMLIST:
        addr = 0
        for prefix in _manglePrefixes(sname):
            a = lib.sbpe_find_symbol(prefix.encode(), count)
            if count[0] == 1:
                addr = a
                break
            if count[0] > 1:
                logging.error('ambiguous symbol {} ({} matches for {})'.format(
                    sname, count[0], prefix))
                return None
        if not addr:
            missing.append(sname)
            continue
        offsets[sname] = addr
    if missing:
        logging.error('could not find symbols: ' + ' '.join(missing))
        return None
    return offsets


# startup ####################################################################

@ffi.def_extern()
def kickstart():
    global refs, util

    SYMFILE = os.environ['SBPE_SYMFILE']

    if platform.system() == 'Darwin':
        offsets = None  # resolved in-process below, after logging is up
    else:
        with open(SYMFILE, 'rb') as f:
            offsets = json.loads(f.read().decode('utf-8'))

    refs.SCRIPTPATH = os.path.dirname(SYMFILE)
    sys.path.insert(1, refs.SCRIPTPATH)
    sys.path.insert(1, os.path.join(refs.SCRIPTPATH, 'pypy', 'site-packages'))
    sys.path.insert(1, os.path.join(refs.SCRIPTPATH, 'site-packages'))

    logging.basicConfig(
        level=logging.DEBUG if os.environ.get('SBPE_DEBUG') else logging.INFO,
        filename=os.path.join(refs.SCRIPTPATH, LOGFILE), filemode='w',
        format='%(asctime)s %(module)s [%(levelname)s] %(message)s')

    # dump python tracebacks of all threads on fatal signals (segfaults etc.)
    try:
        import faulthandler
        refs._crashlog = open(os.path.join(refs.SCRIPTPATH, 'crash.log'), 'w')
        faulthandler.enable(file=refs._crashlog, all_threads=True)
        if platform.system() == 'Darwin':
            refs._crashlog.write('')
            refs._crashlog.flush()
            lib.sbpe_install_crash_handler(refs._crashlog.fileno())
    except Exception:
        pass

    logging.info('SBPE ' + refs.VERSION)
    logging.info('platform: ' + refs.SYSINFO)

    refs.CONFIGFILE = os.path.join(refs.SCRIPTPATH, CONFIGFILE)
    refs.config.read(refs.CONFIGFILE)

    if offsets is None:
        offsets = resolveSymbolsDarwin()
        if offsets is None:
            logging.error('symbols not ok, not starting')
            return 1
        logging.info('symbols ok (exe slide 0x{:x})'.format(lib.sbpe_exe_slide()))

    # import native functions/objects
    for sname in offsets:
        offset = offsets[sname]
        if sname in SYMTYPES:
            # objects, variables
            refs[sname] = ffi.cast(SYMTYPES[sname], offset)
        elif sname.startswith('flags::'):
            # flags
            refs[sname[7:]] = ffi.cast('uint8_t *', offset)
        else:
            # functions
            refs[sname] = ffi.cast('p' + sname, offset)

    # import object inheritance info
    with open(os.path.join(refs.SCRIPTPATH, 'cdefs/proto.json'), 'r') as f:
        d = json.load(f)
        refs.CHAINS = d['chains']
        refs.CASTABLE = d['castable']

    # import util
    util = importlib.import_module('util')
    util.refs = refs

    # import plugins
    plugpath = os.path.join(refs.SCRIPTPATH, 'plugins')
    man = importlib.import_module('manager')
    refs.manager = man.Manager(path=plugpath, refs=refs)

    # init hooks
    initHooks()

    logging.info('startup ok')
    return 0
