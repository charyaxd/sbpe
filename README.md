# SBPE for Mac

**Extra features for StarBreak on Mac:** zoom in and out, a map, arrows that
point to the next door and secrets, a cleaner health bar, an FPS counter, a
list of players online, an option to hide other players' clutter, and more.

### [⬇️ Download SBPE for Mac](https://github.com/charyaxd/sbpe/releases/latest/download/sbpe-mac-v1.7.0-mac1.zip)

Works on Macs with Apple chips (M1, M2, M3, M4, …). StarBreak has to be
installed through Steam.

---

## How to install

1. **Download** SBPE with the button above.
2. **Unzip it:** open your Downloads folder and double-click the file you
   downloaded. A folder called **sbpe-mac** appears. Move it somewhere easy
   to find, like your Desktop.
3. **Open Steam** and make sure you're signed in.
4. **Open the sbpe-mac folder and double-click `run.command`.**
   The game starts with SBPE. The very first start takes about a minute
   longer than usual.
5. **(OPTIONAL) Make run.cmd easier to find** Open your sbpe-mac folder and click the 3 dots at the top right of the folder. Sort By —> Kind.
Now run.cmd will always be at the bottom of your folder

That's it. **From now on, always start StarBreak by double-clicking
`run.command`.** If you press Play in Steam instead, the game starts without
SBPE.

### If your Mac shows a warning the first time

- **"run.command cannot be opened" or "Apple could not verify…"**: this
  happens with files downloaded from the internet. Click **Done** (or OK),
  then open **System Settings → Privacy & Security**, scroll down, and click
  **Open Anyway** next to the message about run.command. Then double-click
  run.command again. On older macOS versions you can instead right-click
  run.command and choose **Open**, then **Open** again. You only need to do
  this once.
- **"…requires the command line developer tools"**: click **Install** and
  wait until it says it's done (a few minutes). This is a free, one-time
  install from Apple that SBPE needs. Then double-click run.command again.

---

## How to change the controls and settings

All settings are in the file **`config.ini`** inside the sbpe-mac folder (it
appears after the first start).

1. Right-click `config.ini` and choose **Open With → TextEdit**.
2. Find the line `[plugin_keybinds]`. Below it, each line is one control. The
   key is after the `=` sign. For example:

   ```
   zoom level toggle -1 3000 = z
   map visible hold yes no = f
   playerlist visible hold yes no = V
   ```

   This means: **Z** switches zoom, holding **F** shows the map, and holding
   **V** shows the player list. Change the key after `=` to the key you want.

   The controls you start with:

   | Key | What it does |
   |-----|--------------|
   | **Z** | zoom out / back in |
   | **F** (hold) | show the map |
   | **V** (hold) | show the list of players |
   | **9** | switch camera centering |
   | **B** | show monsters' health numbers |
   | **X** | hide other players' names, health bars, attacks and effects |
   | **0** | hide / show the chat |
3. Save with **Cmd + S**. Changes work right away, even while the game is
   running.

Good to know:

- Mac keys are called `Left Option`, `Right Option`, `Left Command` and
  `Right Command`. Letters and numbers are just the letter or number (`Z`,
  `7`). Mac laptops have no number pad and no right Control key, so change
  any controls that use `Keypad …` or `Right Ctrl`.
- If you type a key name that doesn't exist, the game shows it in red in the
  top left corner for a few seconds.
- In TextEdit, turn off **Edit → Substitutions → Smart Quotes**, otherwise
  TextEdit may change characters and break the settings file.
- Other settings in `config.ini` use `yes` and `no`, for example
  `hide_chat = yes`. Each one has a short explanation above it.

---

## Something not working?

- **The game starts, but nothing from SBPE shows up:** you probably started
  it from Steam. Close the game and start it with `run.command`.
- **StarBreak is installed in a different place** (for example on an
  external drive): open `config.ini` and change the line that starts with
  `game =` to the location of `MVMMOClient.app`.
- **Still stuck?** [Open an issue](https://github.com/charyaxd/sbpe/issues)
  and attach the files `remote.log` and `crash.log` from the sbpe-mac folder.
  Please **don't** share `game.log` publicly, it contains your Steam ID.

**On Windows?** This download is for Mac only. Windows players can use the
original SBPE: https://github.com/atomizer/sbpe/releases

---

# Technical details

Everything below is the original SBPE documentation plus notes on the Mac
port. You don't need it to play. Original SBPE by
[atomizer](https://github.com/atomizer/sbpe).

## StarBreak Plugin Engine (SBPE)

## Features

- zoom
- arrows pointing towards objectives, trigger indicators
- hide visual noise, with granular configuration
- custom status hud and healthbar
- map
- player list
- 2 modes of centered camera
- borderless windowed mode, but also works with in-game fullscreen
- fps, net lag indicators
- mipmapping (smooth seamless textures when zooming)
- various minor tweaks (disables autokick, autohides mouse cursor, etc)
- most tweaks are configurable and keybindable

## OS support

- Windows: yes
- Mac: yes (tested on Apple Silicon via Rosetta; Intel untested; see "macOS" below)
- Linux: no

## Download

https://github.com/atomizer/sbpe/releases

## Run

- set correct game path in `config.ini`
- on windows, start `run.bat`

## macOS

Build once (needs the Xcode Command Line Tools: `xcode-select --install`):

    ./build_mac.sh

Then, with Steam running, start the game through SBPE by double-clicking
`run.command` (or running it from Terminal). `game` in `config.ini` may point
either at `MVMMOClient.app` or at the `mvmmoclient` binary inside it.

Notes:

- The mac client is an x86_64 binary, so SBPE is built for x86_64 and runs
  under Rosetta on Apple Silicon, using the Command Line Tools' Python 3.9.
  Python modules are installed into `site-packages/` next to the scripts.
- The library is injected with `DYLD_INSERT_LIBRARIES` (the game is not
  code-signed) and starts by interposing `SDL_Init`. Game symbols are looked up
  in the running game's own symbol table, so `symquery` is not needed.
- The game's output goes to `game.log`; crashes are written to `crash.log`
  (native and python backtraces). Set `SBPE_DEBUG=1` for verbose `remote.log`.
- The mac client is 64-bit clang/libc++, so `cdefs/internals_libcxx.h` holds
  libc++ STL layouts and `cdefs/generated_darwin.h` is generated from
  `generated.h` by `misc/fix_layout_darwin.py` (Itanium ABI tail padding).
  `misc/offsets_darwin.py Struct.field ...` prints offsets for checking
  against the disassembly (`otool -tV`).
- `libs/subhook` needs `patches/subhook-x86_64-fixes.patch` (applied by
  `build_mac.sh`): trampolines are allocated within 2GB of the hooked code,
  and three x86_64 instruction decoding bugs are fixed.

## Configure

Copy `config-template.ini` to `config.ini` if you don't have a config file yet.

### config file basics

Use a modern editor, like [Sublime Text](https://www.sublimetext.com/) or [Notepad++](https://notepad-plus-plus.org/)

For booleans, only use values `yes` and `no`.

For colors, use hexadecimal `rgb` or `rrggbb` or `aarrggbb`, where `a` is alpha. Use value `0` for "fully transparent"; `000` and `000000` are "opaque black".

Text sizes can be set to 0 to hide the corresponding element.

You can fully disable any plugin by adding `enabled = no` to the corresponding section, or by adding an underscore to the beginning of the file name, or by removing the file from `plugins/`.

Most options will take effect whenever the config file is changed, otherwise you'll need to restart the game to see the effect.

Sections of the config:

### `[general]`

- `game`: the path to `mvmmoclient.exe` (macOS: `MVMMOClient.app`)
- `mipmaps`: whether to use mipmapping at all. Recommended to leave enabled, but turn off if you have any problems. Also, see below section "mipmaps and sprite editing".
- `mipmap_maxlevel`: integer, default: 2, recommended sane range: 0 to 4. Determines the maximum mipmap level that will be generated. Increasing this makes sense if you intend to zoom more than 4 times further than your native resolution. Increasing this also increases the amount of sprite sheets and video memory requirements. If you are interested, you can read more about mipmapping on the internet.
- `keep_open`: if `yes`, the command line window will stay open and show the log in real time. Useful for debugging.

### `[manager]`

- `period`: polling period in seconds between live reload checks. All plugins and the config can be edited while the game is running, and the changes should in theory be applied in real time. Some settings, like window size and mipmaps, require restart.
- `priority`: priority queue for the plugins. The specified plugin's callbacks will be executed first, then all the rest. Can be tweaked to change draw order.

### `[plugin_zoom]` - zoom

- `fast`: whether to use fast method or slow but correct method. Fast method has some minor inaccuracies: some background visual elements can change position when zooming (most prominently, the ai statue in eschaton), and the "outside" of "underground" rooms can be empty when zooming out instead of being filled with tiles. Recommended to enable if you can survive the above.
- `level`: zoom level, represents internal canvas width in pixels. `-1` means the native 1:1 scale. Recommended to leave at `-1` and set keybind(s) for the level(s) you want. See `[plugin_keybinds]` for info about keybinds.
- `time`: transition time, set to 0 for instant. If using slow method, 0 is recommended.

### `[plugin_misc]` - window management and miscellaneous

- `fixed_window`: use borderless windowed mode with predefined location and size.
- `window_*`: window coordinates and size for `fixed_window`.
- `centered`: center camera on the player. 0 = disabled (default camera), 1 = center when possible, but not go outside of the world border, 2 = center always.
- `max_bg_value`: if background color is brighter than this value, it is reduced to match. Useful when `drawUniform = no` (see below).
- `hide_cursor_after`: inactivity time in seconds when mouse cursor is hidden.
- `draw*`: booleans that control different debug modes that are built into the game.

### `[plugin_fps]` - fps and network lag

- `size`, `color`: parameters of the fps indicator text.
- `update`: how often the indicator should update, in seconds.
- `average`: the indicator value is an average over this period of time, in seconds. More - less variation, less - faster convergence.
- `res_size`, `res_color`: parameters of the net lag indicator (the "res" value from in-game performance overlay).
- `res_warning`: whenever res value dips below 900, the color of the indicator will be changed to this. If the res value is very unstable, you should consider homing.

### `[plugin_hud]` - custom status hud

- `x`, `y` - coordinates of the top-mid point between hp and hpmax indicators.
- `spacing`: this value is added between the lines. With big font sizes, negative values might be preferable.
- `size_*`, `color_*`: font size and color of various elements.
- `outline`: outline size.
- `bar_width`, `bar_height`: size of the health bar in pixels. Set to 0 to disable.
- `bar_y`: vertical offset of the health bar from the top of the character.
- `bar_background`, `bar_outline`, `bar_color`: health bar colors.
- `bar_notches`: color of 25HP interval markers on the empty health.

### `[plugin_map]` - (mini)map

- `visible`: is the map visible. Recommended to leave disabled and make a keybind.
- `small_room`: makes the map hide automatically if the fraction of the room that is visible is more in both dimensions than this value. For example, if `small_room` is 2 and half or more of the room is visible, the map is hidden. Only makes sense if you keep the map always visible, otherwise leave at 0.
- `px`, `py`: map position relative to window frame, 0 to 1. 0 = top/left, 1 = bottom/right, 0.5 = center.
- `w`, `h`: maximum relative part of the screen occupied by the map (1 = all available space). The map is reduced automatically to the lowest scale that makes it fit, preserving aspect ratio.
- `hide_outside_zones`: hide in lobby, home and bosses. Again, only useful if you keep the map always visible.

Rest of the options are element colors. Remember that you can set color to 0 to hide the corresponding element.

### `[plugin_extra_info]` - extra information

- `trigger_color`, `trigger_frame`: shows rectangles that represent invisible triggers that the game uses to react to players (most prominently in TL and FB, but also pretty much everywhere in doors etc.)
- `show_hp`: display health and armor on top of objects. Other players' numbers are left out while `[plugin_noise]` `hide_shells` or `hide_healthbars` is on. Yellow numbers are positive, blue - negative. Turns out to be mostly useless, since most bosses don't report their HP to the clients - it just goes negative and doesn't actually represent internal state.
- `show_uses`: show portal player counts and key counts on the depository.
- `show_room_id`: display zone name and floor number in bottom right corner.

Arrow-related options:

- `arrows`: which arrow types are enabled. Available types:
  - `door`: next door (additionally, teleporters and mid door in GY)
  - `shop`: shop key or shop door
  - `secret`: secrets
  - `arcade`: arcades in GY and TL, waves in UB, miner in FF
  - `hp`: health (when not full)
  - `boost`: boosts (that are needed)
  - `player`: other players

Options that begin with `arrows_` apply to all types. Options that begin with `arrow_TYPE_` apply to the specified type. For example, `arrow_door_color` changes color of arrows of type `door`.

These sub-options are:

- `color`: the arrow color and the color of the frame that is drawn when the target is visible.
- `length`, `width`, `outline`: arrow geometry, in pixels.
- `frame`: width of the frame, 0 to hide.
- `fade`: distance in pixels when the frame/arrow start to fade out.
- `blink`: blinking period in seconds, 0 to disable.

### `[plugin_noise]` - hide visual noise

- `damage_flash_intensity`: 0 to 1, scales the intensity of the white flash effect when objects receive damage.
- `hide_shells`: hide other players. Actually bugged at the moment, will replace other players with yellow rectangles.
- `hide_names`, `hide_factions`, `hide_healthbars`: hide various elements of other players. `hide_names` will also hide factions due to the way it works.
- `hide_ally_objects`: hide all objects created by other players, except for macrons. This includes, but not limited to: bullets, grenades, fire, blasts, rockets.
- `hide_effects`: hide damage effects (flashes/explosion sprites), death animations, particle trails (smoke trails, warp particles).
- `replace_shake`: replace screen shake and flash effects with an indicator in top middle of the screen.
- `hide_chat`: completely hide chat.

### `[plugin_playerlist]` - player list

- `visible`: recommended to keep disabled and add a keybind. Default key is V.
- `size`: font size.

### `[plugin_keybinds]` - bind keys to plugin options

- `info_time`: if > 0, shows debug info about which keybind was triggered in the top left corner.

Keybinds are re-read whenever `config.ini` changes, so they can be edited while the game is running. Unknown key names are shown in red in the top left corner. On macOS the modifier keys are named `Left Option`, `Right Option`, `Left Command`, `Right Command`.

Rest of the options are keybinds. The format is:

`PLUGIN OPTION TYPE VALUE [VALUE...] = KEY`

Valid types are:

- `set`: set the option to `value1` on press
- `hold`: set the option to `value1` when held, to `value2` when released
- `toggle`: cycle the option to the next value every press

Valid key names are listed here (first column, case sensitive): https://wiki.libsdl.org/SDL_Scancode

One key can be bound to any amount of options, and one option can be changed by any amount of keybinds.

## Sprite editing

SBPE is compatible with sprite editing. Edit the original sprite sheets (images with long names in `data/texture/`). If enabled, mipmaps are re-generated automatically on restart whenever the original sprites are changed.

(Since this uses "last modified" time of the files, if you replace your sheets with a backup, it might not trigger. In this case, delete the corresponding `.m.bpb` file to re-generate that particular pack. (For example, to re-generate `base`, delete `base.m.bpb`.))

## Compiling

performance is way better when compiled and run with pypy (which is the default in prebuilt release). Portable pypy is straight up unpacked into `pypy/` directory.

Make sure all dependencies are in place:

- python 3.5+ or pypy3
- C/C++ compiler that can be found by disttools
- update submodules: `git submodule update --init --recursive`
- python modules: `cffi` (built-in on pypy), `Pillow`, `protobuf`
- SDL: install [development libraries](https://libsdl.org/download-2.0.php) for the version used by the game
    - Windows: unzip [this](https://libsdl.org/release/SDL2-devel-2.0.4-VC.zip) into `libs/SDL`
    - Linux: install `libsdl2-dev`
- symquery: download DrMemory release for the appropriate platform and copy symquery to `symquery/{Windows,Linux,Darwin}/bin`

to compile, run `rectbinpack/rbp_builder.py` and `builder.py`.

To make linux binaries distributable, need to set relative RUNPATH:
```
patchelf --set-rpath $ORIGIN/../pypy/lib build/remote.bin
patchelf --set-rpath $ORIGIN/../pypy/lib rectbinpack/_rbp.so
```

## Writing plugins

There is live-reloading for plugins. In case of uncaught exceptions, traceback is written to `remote.log`. The plugin that caused the error is unloaded until it is edited.

for plugin ideas see `notes.txt`

## External resources

- pypy: https://pypy.org
- cffi: https://cffi.readthedocs.io
- symquery: part of https://github.com/DynamoRIO/drmemory
- mayhem: https://github.com/zeroSteiner/mayhem
- subhook: https://github.com/Zeex/subhook
- plthook: https://github.com/kubo/plthook
- rectbinpack: based on https://github.com/juj/RectangleBinPack

## Thanks

Thanks to Crunchy Games for not stripping symbols from the binary, would probably never make this without them.

## License

ISC on my code; see appropriate readmes or links above for licenses for other projects.

Copyright 2018 atomizer

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
