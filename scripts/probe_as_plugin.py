"""Probe: test whether MD API symbols are exposed in Plug-in Manager context.

Register this file via MD's Plugin tab -> Plug-in Manager -> +ADD,
then run it from the Plugin tab. Output is written to a file because
the plugin console sink may differ from Script->Python's.
"""
import os
import sys
import traceback
import builtins as real_b

LOG_PATH = os.path.expanduser(r"~\md_plugin_probe.txt")


def write_log() -> str:
    lines: list[str] = []

    def out(s: str = "") -> None:
        lines.append(str(s))

    out("=== Plugin context probe ===")
    out(f"pid: {os.getpid()}")
    out(f"argv: {sys.argv}")
    out(f"python: {sys.version}")
    out(f"executable: {sys.executable}")
    out(f"prefix: {sys.prefix}")

    out("\n=== globals() callables ===")
    g = globals()
    callables = sorted(n for n in g if callable(g[n]) and not n.startswith("_"))
    out(f"total: {len(callables)}")
    for prefix in [
        "Get", "Set", "Add", "Export", "Import",
        "Create", "Delete", "Remove", "Is", "Has", "Select",
    ]:
        matched = [n for n in callables if n.startswith(prefix)]
        out(f"  {prefix}* ({len(matched)}): {matched[:30]}")

    out("\n=== full callable list (sorted) ===")
    for c in callables:
        out(f"  {c}")

    out("\n=== sys.modules MD-related ===")
    for m in sorted(sys.modules.keys()):
        if any(k in m.lower() for k in
               ["md", "marvelous", "clo", "fabric", "pattern", "garment"]):
            try:
                attrs = [a for a in dir(sys.modules[m]) if not a.startswith("_")]
                out(f"  {m}: {len(attrs)} attrs, sample: {attrs[:10]}")
            except Exception as e:
                out(f"  {m}: err {e}")

    out("\n=== __builtins__ extras ===")
    std = set(dir(real_b))
    cur = set(dir(__builtins__)) if not isinstance(__builtins__, dict) \
        else set(__builtins__.keys())
    out(f"  extras: {sorted(cur - std)}")

    out("\n=== If API exists, sanity calls ===")
    for fn_name in ["GetPatternCount", "GetFabricCount", "GetAvatarCount"]:
        if fn_name in g:
            try:
                if fn_name == "GetFabricCount":
                    out(f"  {fn_name}(True) = {g[fn_name](True)}")
                else:
                    out(f"  {fn_name}() = {g[fn_name]()}")
            except Exception:
                out(f"  {fn_name}: " + traceback.format_exc())
        else:
            out(f"  {fn_name}: NOT IN GLOBALS")

    return "\n".join(lines)


try:
    content = write_log()
except Exception:
    content = "PROBE FAILED:\n" + traceback.format_exc()

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"[MCP Probe] log written to: {LOG_PATH}")
print(content[:500] + ("\n... (truncated, see file)" if len(content) > 500 else ""))
