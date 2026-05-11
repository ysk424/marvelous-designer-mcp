"""Start the MCP listener inside Marvelous Designer.

Two ways to use this file:

  A) Python Editor — paste this whole file into MD's `Plugins > Python Editor`
     and run it.

  B) Plug-in (recommended for day-to-day use) — register this file via
     `Plugins > Plug-in Manager > +ADD`, then click it under `Plugins > Plug-in`.
     One click instead of opening the editor and pasting.

Either way it starts a blocking socket listener on 127.0.0.1:7421. **MD's GUI
freezes while the listener runs** -- that is expected. Stop it by having a
connected client call the `shutdown_listener` MCP tool (or by closing MD).

Re-running picks up edits to md_listener.py (the module is reloaded), so you do
not need to restart MD after changing it.

Status / errors are appended to ~/md_mcp_listener.log -- useful in Plug-in mode,
where stdout may not be visible anywhere.
"""
import os
import sys
import traceback

_LOG_PATH = os.path.expanduser(r"~\md_mcp_listener.log")


def _log(msg: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# Locate the md_addon directory (where md_listener.py lives). When this file runs
# as a script/plugin, __file__ is usually set; fall back to a hard-coded path that
# you can edit if your clone is elsewhere.
try:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _ADDON_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "md_addon"))
except NameError:
    _ADDON_DIR = r"C:\Users\azoo\git\marvelous-designer-mcp\md_addon"  # <-- edit if needed

if not os.path.isdir(_ADDON_DIR):
    _ADDON_DIR = r"C:\Users\azoo\git\marvelous-designer-mcp\md_addon"  # <-- edit if needed

if _ADDON_DIR not in sys.path:
    sys.path.insert(0, _ADDON_DIR)

_log(f"--- md-mcp listener launch; addon dir = {_ADDON_DIR} ---")
try:
    import importlib
    import md_listener
    importlib.reload(md_listener)
    _log("starting serve_forever() -- MD GUI will be frozen until a client sends 'shutdown'")
    md_listener.serve_forever()
    _log("serve_forever() returned -- listener stopped, GUI released")
except Exception:
    _log("LISTENER LAUNCH FAILED:\n" + traceback.format_exc())
    raise
