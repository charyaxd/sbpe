import configparser
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time

if platform.system() == 'Windows':
    from mayhem.proc import ProcessError
    from mayhem.proc.native import NativeProcess

import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

BASE = 0x400000
DEFAULTGAMEPATH = {
    'Windows': 'c:\\Program Files (x86)\\Steam\\SteamApps\\common\\StarBreak\\mvmmoclient.exe',
    'Linux': os.path.expanduser('~/.steam/steam/steamapps/common/StarBreak/mvmmoclient'),
    'Darwin': os.path.expanduser('~/Library/Application Support/Steam/steamapps/common/StarBreak/MVMMOClient.app')
}[platform.system()]

SCRIPTPATH = os.path.dirname(__file__) or os.getcwd()
REMOTEPATH = os.path.normpath(os.path.join(SCRIPTPATH, 'build/remote.bin'))
SYMQPATH = 'symquery/{}/bin/symquery'.format(platform.system())
SYMQPATH = os.path.normpath(os.path.join(SCRIPTPATH, SYMQPATH))
CONFFILE = os.path.join(SCRIPTPATH, 'config.ini')
CONF_TEMPLATE = os.path.join(SCRIPTPATH, 'config_template.ini')
SYMFILE = os.path.join(SCRIPTPATH, 'symbols.json')
GAMELOG = os.path.join(SCRIPTPATH, 'game.log')

# only needed for remote thread injection on Windows
STARTUP_OFFSET = None
if platform.system() == 'Windows':
    STARTUP_OFFSET = subprocess.check_output([
        SYMQPATH, '-e', REMOTEPATH, '-s', 'kickstart'])
    STARTUP_OFFSET = int(STARTUP_OFFSET.strip(), 16)


def resolveExePath(path):
    '''accept either the .app bundle or the binary inside it (macOS)'''
    path = os.path.expanduser(path)
    if path.endswith('.app') or os.path.isdir(path):
        path = os.path.join(path, 'Contents', 'MacOS', 'mvmmoclient')
    return path

def findGameDarwin():
    '''look for MVMMOClient.app: Steam libraries, then Spotlight'''
    import re
    candidates = [DEFAULTGAMEPATH]
    # every Steam library folder (other drives, etc.)
    vdf = os.path.expanduser(
        '~/Library/Application Support/Steam/steamapps/libraryfolders.vdf')
    try:
        with open(vdf, 'r', errors='replace') as f:
            for lib in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                candidates.append(os.path.join(
                    lib, 'steamapps', 'common', 'StarBreak', 'MVMMOClient.app'))
    except OSError:
        pass
    # anywhere else Spotlight knows about (copied or other Steam installs)
    try:
        out = subprocess.check_output(
            ['mdfind', "kMDItemCFBundleIdentifier == 'com.crunchy.mvmmoclient'"],
            stderr=subprocess.DEVNULL, timeout=10).decode()
        candidates += [l for l in out.splitlines() if l.endswith('.app')]
    except Exception:
        pass
    for c in candidates:
        if os.access(resolveExePath(c), os.X_OK):
            return c
    return None


def askGameDarwin():
    '''let the player pick MVMMOClient.app in a normal Mac file dialog'''
    script = (
        'POSIX path of (choose file of type {"app"} with prompt '
        '"SBPE could not find StarBreak. Please select MVMMOClient.app '
        '(usually in Steam/steamapps/common/StarBreak)" '
        'default location (path to home folder))')
    try:
        out = subprocess.check_output(
            ['osascript', '-e', script], stderr=subprocess.DEVNULL)
    except Exception:
        return None  # cancelled
    path = out.decode().strip().rstrip('/')
    return path if os.access(resolveExePath(path), os.X_OK) else None


def saveGamePath(path):
    '''write game = PATH into config.ini, keeping all comments'''
    try:
        with open(CONFFILE, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.split('=')[0].strip() == 'game':
                lines[i] = 'game = {}\n'.format(path)
                break
        else:
            lines.insert(1, 'game = {}\n'.format(path))
        with open(CONFFILE, 'w') as f:
            f.writelines(lines)
    except OSError as e:
        logging.error('could not save game path: {}'.format(e))


# offsets of these symbols will be passed to the remote
SYMLIST = '''
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


def resolveSymbols(exepath):
    offsets = {}
    lines = subprocess.check_output([SYMQPATH, '-e', exepath, '--list'])
    lines = lines.decode().splitlines()
    for line in lines:
        line = line.split()
        if line[0] not in SYMLIST:
            continue
        sname = line[0]
        SYMLIST.remove(sname)
        off = line[1].split('-')[0]
        try:
            off = BASE + int(off, 16)
        except ValueError:
            logging.error('invalid offset "{0}" for "{1}"'.format(off, sname))
            return None
        offsets[sname] = off

    if len(SYMLIST) > 0:
        logging.error('could not find symbols: ' + ' '.join(SYMLIST))
        return None

    # with io.open('symbols.json', 'w') as f:
    #     json.dump(offsets, f, sort_keys=True, indent=2)
    return offsets


LOGDIR = os.path.join(SCRIPTPATH, 'logs')
LOGFILES = ('remote.log', 'crash.log', 'game.log')
KEEP_SESSIONS = 5


def rotateLogs():
    '''move the previous session's logs to logs/<date time>/, keep a few'''
    old = [f for f in LOGFILES if os.path.exists(os.path.join(SCRIPTPATH, f))]
    if not old:
        return
    try:
        stamp = max(os.path.getmtime(os.path.join(SCRIPTPATH, f)) for f in old)
        dest = os.path.join(LOGDIR, time.strftime(
            '%Y-%m-%d %H.%M.%S', time.localtime(stamp)))
        os.makedirs(dest, exist_ok=True)
        for f in old:
            shutil.move(os.path.join(SCRIPTPATH, f), os.path.join(dest, f))
        sessions = sorted(
            d for d in os.listdir(LOGDIR)
            if os.path.isdir(os.path.join(LOGDIR, d)))
        for d in sessions[:-KEEP_SESSIONS]:
            shutil.rmtree(os.path.join(LOGDIR, d), ignore_errors=True)
    except Exception as e:
        logging.warning('could not keep old logs: {}'.format(e))


def gameEnv():
    '''environment for the game process'''
    env = os.environ.copy()
    # on Linux and MacOS, use ld/dyld
    if platform.system() == 'Linux':
        env['LD_PRELOAD'] = REMOTEPATH
    if platform.system() == 'Darwin':
        # the game binary is unsigned (no hardened runtime), so dyld honors
        # this; the dylib interposes SDL_Init via __DATA,__interpose
        env['DYLD_INSERT_LIBRARIES'] = REMOTEPATH
        env.pop('DYLD_FORCE_FLAT_NAMESPACE', None)
        # the embedded interpreter needs _cffi_backend etc. before remote.py
        # gets a chance to extend sys.path
        sitedir = os.path.join(SCRIPTPATH, 'site-packages')
        env['PYTHONPATH'] = os.pathsep.join(
            [SCRIPTPATH, sitedir] + sys.path[1:])
    return env


def describeExit(code):
    if code is None:
        return 'still running'
    if code < 0:
        import signal
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = 'signal {}'.format(-code)
        hint = {
            'SIGSEGV': 'crash (invalid memory access)',
            'SIGBUS': 'crash (invalid memory access)',
            'SIGILL': 'crash (invalid instruction)',
            'SIGABRT': 'crash (the game aborted itself)',
            'SIGKILL': 'killed (by macOS, e.g. out of memory, or force quit)',
            'SIGTERM': 'asked to quit',
        }.get(name, 'stopped by a signal')
        return '{} ({}, code {})'.format(hint, name, code)
    return 'normal exit (code {})'.format(code)


def recordExit(code, started):
    '''append how the game ended to game.log'''
    try:
        with open(GAMELOG, 'a') as f:
            f.write('\n[sbpe] {}: game ended after {:.0f} min: {}\n'.format(
                time.strftime('%Y-%m-%d %H:%M:%S'),
                (time.time() - started) / 60, describeExit(code)))
    except OSError:
        pass


def watch(exepath):
    '''
    (macOS/Linux) run the game and wait for it, in a helper process that
    outlives the loader and its Terminal window, so the exit is recorded
    '''
    started = time.time()
    with open(GAMELOG, 'wb') as gout:
        gpop = subprocess.Popen(
            [exepath], stderr=subprocess.STDOUT, stdout=gout,
            cwd=os.path.dirname(exepath), env=gameEnv())
        code = gpop.wait()
    recordExit(code, started)


def launch(exepath, keepopen=False):
    if platform.system() != 'Windows' and not keepopen:
        # the game logs a lot to stderr (glog): a pipe nobody drains would
        # eventually block it, and SIGPIPE would kill it once the loader
        # exits, so it goes to game.log; a detached helper waits for it
        helper = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), '--watch', exepath],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
            cwd=SCRIPTPATH)
        return helper

    # start the game
    if platform.system() == 'Windows':
        gout = subprocess.PIPE
    else:
        gout = open(GAMELOG, 'wb')
    gpop = subprocess.Popen(
        [exepath], stderr=subprocess.STDOUT,
        stdout=gout, cwd=os.path.dirname(exepath), env=gameEnv())

    # on Windows, inject into the running process
    if platform.system() == 'Windows':
        try:
            proc = NativeProcess(pid=gpop.pid)
            lib_h = proc.load_library(REMOTEPATH)
            # start remote thread
            addr = lib_h + STARTUP_OFFSET
            thr = proc.start_thread(addr)
            logging.info('starting from 0x{:x}'.format(addr))
            proc.join_thread(thr)
        except ProcessError as error:
            gpop.kill()
            logging.error(error.msg)
            return False

    return gpop


def runLoader(exepath=''):
    mipmaps = False

    # ensure config exists
    if not os.path.exists(CONFFILE):
        logging.info('config not found, copying from template')
        try:
            shutil.copy(CONF_TEMPLATE, CONFFILE)
        except Exception:
            logging.error('failed to copy config!')
            return False

    conf = configparser.ConfigParser()
    conf.read(CONFFILE)
    exepath = resolveExePath(conf.get('general', 'game', fallback=exepath))
    if platform.system() == 'Darwin' and not os.access(exepath, os.X_OK):
        # not set yet (or the template's windows path), or the game moved
        found = findGameDarwin()
        if found is None:
            logging.info('StarBreak not found, asking where it is')
            found = askGameDarwin()
        if found is not None:
            logging.info('found StarBreak: ' + found)
            saveGamePath(found)
            exepath = resolveExePath(found)
    mipmaps = conf.getboolean('general', 'mipmaps', fallback=False)
    keepopen = conf.getboolean('general', 'keep_open', fallback=False)

    # ensure the binary exists
    if not os.path.isfile(exepath):
        if platform.system() == 'Darwin':
            logging.error(
                'StarBreak was not found. Install it in Steam (on this Mac '
                'user account), or set "game =" in config.ini to the location '
                'of MVMMOClient.app')
        else:
            logging.error('put the path to the game executable in ' + CONFFILE)
        return False

    # resolve symbols and prepare environment
    if platform.system() == 'Darwin':
        offsets = {}  # resolved inside the game process (see remote.py)
    else:
        offsets = resolveSymbols(exepath)
    if offsets is not None:
        logging.info('symbols ok')
    else:
        logging.error('symbols not ok')
        return False

    with open(SYMFILE, 'wb') as f:
        f.write(json.dumps(offsets).encode('utf-8'))

    os.environ['SBPE_SYMFILE'] = SYMFILE

    # texture dir and dataVersion paths
    gdir = os.path.dirname(os.path.abspath(exepath))
    tdir = os.path.join(gdir, 'data', 'texture')

    dvpath = os.path.join(tdir, 'dataVersion.bpb')
    dvmpath = os.path.join(tdir, 'dataVersion.m.bpb')
    dvbak = os.path.join(tdir, 'dataVersion.bpb.bak')

    if not os.path.exists(dvbak):
        # create a backup of the original file if there is none
        shutil.copy(dvpath, dvbak)
    else:
        # otherwise restore from backup to reset state
        shutil.copy(dvbak, dvpath)

    # generate mipmaps if needed
    if mipmaps:
        logging.info('checking mipmaps...')

        import genmipmaps
        genmipmaps.BASEPATH = tdir
        mn = conf.getint('general', 'mipmap_maxlevel', fallback=2)
        genmipmaps.main(tdir, mipmaps=mn)

    # overwrite dataVersion
    if mipmaps:
        shutil.copy(dvmpath, dvpath)

    # keep the previous sessions' logs (logs/), start with fresh ones
    rlog = None
    rlogpath = os.path.join(SCRIPTPATH, 'remote.log')
    rotateLogs()

    # start the game
    started = time.time()
    gpop = launch(exepath, keepopen)

    if not gpop:
        logging.error('failed to launch')
        return False

    if platform.system() != 'Windows' and not keepopen:
        logging.info('game started (logs: game.log, remote.log, crash.log; '
                     'older sessions in logs/)')
    else:
        logging.info('game pid {}'.format(gpop.pid))

    # exit here to close the console window
    if not keepopen:
        return True

    # mirror log
    while not os.path.exists(rlogpath) and gpop.poll() is None:
        logging.info('waiting for log')
        time.sleep(0.5)

    if os.path.exists(rlogpath):
        rlog = open(rlogpath, 'r')
        logging.info('following remote.log...')

    try:
        while gpop.poll() is None:
            while rlog is not None:
                s = rlog.read()
                if len(s) == 0:
                    break
                sys.stdout.write(s)
            time.sleep(0.5)
    except Exception:
        gpop.kill()

    logging.info('game closed: ' + describeExit(gpop.returncode))
    if platform.system() != 'Windows':
        recordExit(gpop.returncode, started)

    # dump stdout
    if platform.system() == 'Windows':
        stdo = gpop.communicate()[0].decode()
    else:
        with open(GAMELOG, 'rb') as f:
            stdo = f.read().decode(errors='replace')

    if len(stdo) > 0:
        logging.info('stdout:')
        print(stdo)

    return True


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--watch':
        watch(sys.argv[2])
        sys.exit(0)
    logging.info('SBPE loader')
    if runLoader(DEFAULTGAMEPATH) is False:
        input('\npress ENTER to exit')
