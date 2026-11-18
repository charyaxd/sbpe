SBPE for macOS - StarBreak Plugin Engine
=========================================

Zoom, map, objective arrows, custom HUD, fps counter, player list and more
for the Mac version of StarBreak. Works on Apple Silicon (through Rosetta,
like StarBreak itself) and should work on Intel Macs.


INSTALL
-------

1. Unzip this anywhere, for example in Documents or on the Desktop.
2. Start Steam (StarBreak must be installed through Steam).
3. Double-click "run.command".

   The first time, macOS may say it can't verify the file. Then:
   right-click run.command -> Open -> Open. After that a double-click works.

4. If SBPE asks for Apple's "Command Line Tools", click Install in the
   window that appears, wait until it finishes (a few minutes), and
   double-click run.command again. This is a free, one-time install from
   Apple. It provides the Python that SBPE runs on.

Always start the game with run.command, not with Steam's Play button,
otherwise SBPE is not loaded.

The first start takes about a minute longer: SBPE generates smoother
(mipmapped) textures in the game folder. You can turn this off with
"mipmaps = no" in config.ini.


SETTINGS AND CONTROLS
---------------------

The first start creates "config.ini" next to run.command. Open it with
TextEdit (right-click -> Open With -> TextEdit). In TextEdit, turn off
Settings -> Smart quotes, and save with Cmd+S.

Controls are in the [plugin_keybinds] section, one per line, for example:

    zoom level toggle -1 3000 = Z
    map visible hold yes no = Right Option

Changes apply within a few seconds while the game is running. Mac keys are
named "Left Option", "Right Option", "Left Command", "Right Command"; Mac
laptops have no keypad and no Right Ctrl, so change the default binds that
use them. The full list of key names and options is in config.ini and
README.md.

If StarBreak is installed in a different Steam library (e.g. an external
drive), set "game =" in config.ini to the path of MVMMOClient.app.


PROBLEMS
--------

Logs are written next to run.command:
  remote.log  - SBPE and plugin messages and errors
  crash.log   - details if the game crashes
  game.log    - the game's own output (contains your Steam ID, don't post
                it publicly)

If the files in this folder were modified, or your Mac has a different
Python version than the prebuilt files expect, run.command rebuilds SBPE
automatically (this needs the Command Line Tools and an internet connection
the first time).


Original SBPE by atomizer: https://github.com/atomizer/sbpe (ISC license,
see README.md). macOS port: see the "macOS" section in README.md.
