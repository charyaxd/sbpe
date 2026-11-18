import configparser
import logging
import time

from _remote import ffi, lib
from manager import PluginBase
import util


class Plugin(PluginBase):
    def readBinds(self):
        '''keybind lines exactly as they are in the config file now'''
        # read the file directly: the shared config only ever adds keys on
        # reload, so deleted/renamed binds would otherwise stay active
        parser = configparser.ConfigParser()
        parser.optionxform = str
        try:
            parser.read(self.refs.CONFIGFILE)
            if parser.has_section('plugin_keybinds'):
                return list(parser['plugin_keybinds'].items())
        except configparser.Error as e:
            logging.error('keybinds: could not read config: {}'.format(e))
        return list(self.config._section.items())

    def updateBinds(self):
        self.binds = {}
        bad = []
        for desc, key in self.readBinds():
            desc = desc.split()
            if len(desc) < 4:
                continue
            k = lib.SDL_GetScancodeFromName(key.encode())
            if k == 0:
                logging.error('key name not recognized: "{}"'.format(key))
                bad.append(key)
                continue
            b = {
                'plugin': 'plugin_' + desc[0],
                'option': desc[1],
                'type': desc[2],
                'values': desc[3:]
            }
            if k in self.binds:
                self.binds[k].append(b)
            else:
                self.binds[k] = [b]
        logging.info('keybinds: {} keys bound'.format(len(self.binds)))
        if bad:
            # show it in game, otherwise a typo just silently does nothing
            self.error.text = 'keybinds: unknown key name: ' + ', '.join(
                '"{}"'.format(b) for b in bad)
            self.error_time = time.perf_counter()
        else:
            self.error.text = ''

    def onInit(self):
        num = ffi.new('int *')
        self.keyStates = lib.SDL_GetKeyboardState(num)
        self.numKeys = num[0]
        self.oldKeys = ffi.new('uint8_t[]', self.numKeys)

        self.config.option('info_time', 2, 'float')
        self.info = util.PlainText(size=16)
        self.error = util.PlainText(size=16, color=0xff6060)
        self.error_time = 0
        self.last_change = 0

        self.updateBinds()
        self.config_mtime = self.refs.manager._mtimes.get('config')

    def checkConfig(self):
        '''re-read binds whenever the manager reloads config.ini'''
        mtime = self.refs.manager._mtimes.get('config')
        if mtime != self.config_mtime:
            self.config_mtime = mtime
            self.updateBinds()

    def beforeUpdate(self):
        if not lib.SDL_IsTextInputActive():
            ffi.memmove(self.oldKeys, self.keyStates, self.numKeys)

    def afterUpdate(self):
        self.checkConfig()
        if lib.SDL_IsTextInputActive():
            return

        plugs = self.refs.manager._active  # yeahhhh this kinda sucks

        for k in self.binds:
            diff = self.keyStates[k] - self.oldKeys[k]
            if diff == 0:
                continue

            for bind in self.binds[k]:
                pname = bind['plugin']
                if pname not in plugs:
                    continue
                conf = plugs[pname].config
                opt = bind['option']
                if opt not in conf._schema:
                    logging.error('no option "{}" in "{}"'.format(opt, pname))
                    continue
                t = bind['type']
                vals = bind['values']
                val = None
                if t == 'set' and diff > 0:
                    val = vals[0]
                elif t == 'hold':
                    if diff > 0:
                        val = vals[0]
                    else:
                        val = vals[1]
                elif t == 'toggle' and diff > 0:
                    i = 0
                    try:
                        i = vals.index(conf._section[opt]) + 1
                    except ValueError:
                        pass
                    if i >= len(vals):
                        i = 0
                    val = vals[i]

                if val is not None:
                    conf._section[opt] = val
                    if opt in conf._cache:
                        del conf._cache[opt]
                    self.info.text = '{}.{} = {}'.format(pname[7:], opt, val)
                    self.last_change = time.perf_counter()

    def onPresent(self):
        if self.error.text and time.perf_counter() - self.error_time < 10:
            self.error.draw(4, 24)
        if self.config.info_time == 0:
            return
        f = (time.perf_counter() - self.last_change) / self.config.info_time
        if f >= 0 and f < 1:
            self.info.alpha = 1 - f
            self.info.draw(4, 4)
