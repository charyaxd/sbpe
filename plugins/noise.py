import time

from _remote import ffi, lib
from manager import PluginBase
import util

# a large number that fits in int32 and also unlikely to overflow
OFFSET = 1 << 29


class Plugin(PluginBase):
    def onInit(self):
        self.config.options('bool', {
            'hide_shells': False,
            'hide_names': False,
            'hide_factions': False,
            'hide_healthbars': False,
            'hide_ally_objects': False,
            'hide_effects': False,
            'hide_own_effects': False,
            'hide_chat': False,
        })
        self.config.option('damage_flash_intensity', 1, 'float')

        self.hidden = set()
        self.oldbits = []
        self._mineByClass = {}  # vtable address -> is own object
        self.myWorldId = None

        self.config.option('replace_shake', True, 'bool')
        self._shake = 0
        self._flash = 0
        self.shaketxt = util.PlainText(size=30, color=0xffffff00)

    def afterUpdate(self):
        gc = self.refs.GameClient
        if gc != ffi.NULL and gc.chatWindow != ffi.NULL:
            if self.config.hide_chat:
                ffi.cast('struct UIElement *', gc.chatWindow).x = -9000
            else:
                ffi.cast('struct UIElement *', gc.chatWindow).x = 0

        cw = self.refs.ClientWorld
        wv = self.refs.WorldView
        if cw == ffi.NULL or wv == ffi.NULL:
            return

        # other players
        allies = util.vec2list(cw.allies, 'struct WorldObject *')
        for obj in allies:
            props = obj.props
            if self.config.hide_shells:
                # fail: triggers game's "unknown object" box drawing
                util.clearstr(props.vid)

            if self.config.hide_names:
                # remember and remove relevant bits; also hides factions
                bits = props._has_bits[0] & 0x300000
                props._has_bits[0] ^= bits
                self.oldbits.append((obj, bits))
            elif self.config.hide_factions:
                # hide only faction names by zeroing faction name length
                if props.playerdata != ffi.NULL:
                    fname = props.playerdata.factionname
                    util.clearstr(fname)

            if self.config.hide_healthbars:
                # not sure if this breaks anything
                props.hitpoints = props.maxhitpoints

        if self.config.hide_ally_objects:
            worlds = util.sVecMap2list(
                cw.clientSubWorlds, 'struct ForeignSubWorld *')
            for csubworld in worlds:
                for obj in util.worldobjects(csubworld):
                    #if obj in allies:
                        # shells are treated separately
                        #continue
                    if obj.props.terraintype > 0:
                        # anything that acts like terrain (macrons)
                        continue
                    if util.getstr(obj.props.vid)[:5] == 'timer':
                        # macron timer
                        continue
                    self.hide(obj)

        # reduce damage flash time
        rt = round((1 - self.config.damage_flash_intensity) * 132)
        rt = max(0, min(132, rt))
        if rt > 0:
            # server world time
            swt = ffi.cast('struct SubWorld *', cw.serverSubWorld).t
            # skip the beginning since lastDamageT is 0 by default
            if swt > 132:
                for obj in util.worldobjects(cw.serverSubWorld):
                    dt = swt - obj.lastDamageT
                    if dt < rt:
                        obj.lastDamageT = swt - rt

        self.updateEffects(cw, wv)

        if self.config.replace_shake:
            ct = time.perf_counter()
            if wv.shakePos < wv.shakeDuration and wv.shakeMagnitude > 0:
                self._shake = max(self._shake, ct + wv.shakeDuration / 1000)
            wv.shakeMagnitude = 0

            flashduration = wv.flashStart + wv.flashHold + wv.flashEnd
            if wv.flashPos < flashduration and wv.flashColor != 0:
                self._flash = max(self._flash, ct + flashduration / 1000)
            wv.flashColor = 0

    def isMine(self, obj):
        '''objects of the own character (player, own bullets etc.) are
        ClientObjects; those of mobs and other players are ForeignObjects'''
        if obj == ffi.NULL:
            return False
        vt = int(ffi.cast('uintptr_t *', obj)[0])
        mine = self._mineByClass.get(vt)
        if mine is None:
            name = util.getClassName(obj)
            mine = name == 'ClientObject' or \
                name in self.refs.CASTABLE.get('ClientObject', ())
            self._mineByClass[vt] = mine
        return mine

    def effectFilter(self, kind, obj, srcWorldId):
        '''True = hide the effects created for this object/event'''
        if self.config.hide_own_effects:
            return True
        if self.isMine(obj):
            return False  # own character/objects, or own character was hit
        if kind == 'damage' and self.myWorldId is not None and \
                srcWorldId == self.myWorldId:
            return False  # hits dealt by own character
        return True

    def updateEffects(self, cw, wv):
        refs = self.refs
        if not self.config.hide_effects:
            refs.effectFilter = None
            refs.hiddenEffects.clear()
            return

        if not refs.effectHooks:
            # no effect hooks (e.g. 32-bit builds): hide all effects
            for graphic in util.vec2list(wv.dynamicGraphics):
                if util.getClassName(graphic) == 'AnimationGraphic':
                    ffi.cast('struct AnimationGraphic *', graphic).startTime = 0
            return

        self.myWorldId = cw.asWorld.id
        refs.effectFilter = self.effectFilter
        refs.effectFilterTime = time.perf_counter()

        # hide the remembered effects that still exist; forget the rest
        hidden = refs.hiddenEffects
        if not hidden:
            return
        alive = {}
        for g in util.vec2list(wv.dynamicGraphics, 'uintptr_t'):
            anim = hidden.get(g)
            if anim is None:
                continue
            ag = ffi.cast('struct AnimationGraphic *', g)
            if ag.animation != anim:
                continue  # address reused by a different graphic
            ag.startTime = 0
            alive[g] = anim
        hidden.clear()
        hidden.update(alive)

    def hide(self, obj):
        obj.props.xmp -= OFFSET
        self.hidden.add(obj)

    def onPresent(self):
        # unhide
        for obj in self.hidden:
            obj.props.xmp += OFFSET
        self.hidden.clear()

        # fix bits
        for obj, bits in self.oldbits:
            obj.props._has_bits[0] |= bits
        self.oldbits = []

        if self.config.replace_shake:
            ct = time.perf_counter()
            s = []
            if self._shake > ct:
                s = ['SHAKE']
            if self._flash > ct:
                s += ['FLASH']
            if len(s) > 0:
                self.shaketxt.text = '[{}]'.format(', '.join(s))
                self.shaketxt.draw(self.refs.windowW // 2, 20, anchorX=0.5)
