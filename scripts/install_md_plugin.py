"""Register the MCP listener with Marvelous Designer's plugin system.

Writes (or updates) `pluginSettings.json` in MD's Plugins folder so that the
listener appears under `Plugins ▸ Plug-in ▸ md_start_listener` the next time MD
starts. Equivalent to `Plug-in Manager ▸ +ADD`, just scripted -- no clicking.

Run once, then start MD (or use `Plug-in Manager ▸ Refresh Plug-in` if MD is
already open).

    uv run python scripts/install_md_plugin.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "md_start_listener.py"

if sys.platform == "win32":
    MD_PLUGINS = Path(r"C:\Users\Public\Documents\MarvelousDesigner\Plugins")
else:
    MD_PLUGINS = Path.home() / "Documents" / "MarvelousDesigner" / "Plugins"

SETTINGS = MD_PLUGINS / "pluginSettings.json"

ENTRY_TITLE = "md_start_listener"


def main() -> int:
    if not SCRIPT.exists():
        print(f"error: launcher script not found: {SCRIPT}", file=sys.stderr)
        return 1
    if not MD_PLUGINS.exists():
        print(f"error: MD Plugins folder not found: {MD_PLUGINS}", file=sys.stderr)
        print("(Is Marvelous Designer installed and has been launched at least once?)",
              file=sys.stderr)
        return 1

    script_path = str(SCRIPT).replace("\\", "/")

    if SETTINGS.exists():
        try:
            data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"error: existing pluginSettings.json is not valid JSON ({e})", file=sys.stderr)
            print("Move it aside and rerun, or fix it by hand.", file=sys.stderr)
            return 1
    else:
        data = {"plugins": [], "version": 2}

    plugins = data.setdefault("plugins", [])
    for existing in plugins:
        if existing.get("m_SourcePath", "").replace("\\", "/").lower() == script_path.lower():
            print(f"already registered: {script_path}")
            print(f"  ({SETTINGS})")
            return 0

    plugins.append({
        "m_AddingPositionIndex": len(plugins) + 1,
        "m_BaseMenuTreeByObjectName": "Plugins / Plug-in",
        "m_PlugInFileName": script_path,
        "m_PlugInIconFileName": "",
        "m_PlugInTitle": ENTRY_TITLE,
        "m_SourcePath": script_path,
        "m_SourceType": "script",
    })
    SETTINGS.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"registered: {script_path}")
    print(f"updated   : {SETTINGS}")
    print()
    print("Next:")
    print("  1. Start (or restart) Marvelous Designer")
    print(f"  2. Click  Plugins ▸ Plug-in ▸ {ENTRY_TITLE}  to start the MCP listener")
    print("     (MD's GUI will freeze while the listener runs -- that's expected;")
    print("      the `shutdown_listener` MCP tool releases it.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
