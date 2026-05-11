"""Paste this whole file into Marvelous Designer's Python Editor and run it.

It starts the MCP listener (blocking) on 127.0.0.1:7421. MD's GUI will be
unresponsive while it runs. To stop it, have a connected client call the
`shutdown_listener` MCP tool, or just close Marvelous Designer.

Re-running this file after editing md_listener.py is safe -- it reloads the
module, so you don't need to restart MD.
"""
import sys

_ADDON_DIR = r"C:\Users\azoo\git\marvelous-designer-mcp\md_addon"
if _ADDON_DIR not in sys.path:
    sys.path.insert(0, _ADDON_DIR)

import importlib
import md_listener
importlib.reload(md_listener)

md_listener.serve_forever()
