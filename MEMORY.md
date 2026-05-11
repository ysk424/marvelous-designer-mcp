# MEMORY.md — project context handoff

A snapshot of what this repo is, what works, and what's been ruled out — so a
future session (you, or a different person, or a future Claude) can pick up
without re-discovering everything.

Last update: 2026-05-12, tag `v0.2.0`.

---

## What this project is

An MCP server that lets an LLM drive Marvelous Designer (MD) by running code
inside MD's embedded Python interpreter. Architecture:

```
LLM ──MCP/stdio──▶ src/marvelous_designer_mcp (FastMCP)
                         │ JSON-per-line, TCP 127.0.0.1:7421
                         ▼
                   md_addon/md_listener.py (running inside MD's Python Editor)
                         │ exec()
                         ▼
                   MD Python API: import_api / export_api / fabric_api /
                                  pattern_api / utility_api
```

## Status

| Component | State |
|---|---|
| Python listener (v0.1.0) | **Works.** Blocking main-thread server. MD's GUI freezes while running; `shutdown_listener` releases it. |
| Plug-in auto-registration (`scripts/install_md_plugin.py`, v0.2.0) | **Works.** Idempotently writes MD's `pluginSettings.json` so the launcher appears under `Plugins ▸ Plug-in`. |
| MCP tool wrappers | 10 typed tools (`scene_info`, `list_patterns`, `list_fabrics`, `assign_fabric`, `import_project`, `export_project`, `simulate`, `md_api`, plus `ping`, `shutdown_listener`) + `execute_python` for arbitrary code. All verified live against `HarukoMD2.zprj` (7 patterns, 2 fabrics, Alembic avatar). |
| C++ non-freezing plugin (`cpp_plugin/`) | **Code builds, doesn't load in MD.** Reserved for CLO 3D and for a hypothetical future MD that adds DLL loading. See `cpp_plugin/README.md`. |

## Key non-obvious facts (do not re-derive — verified empirically)

1. **MD's embedded Python doesn't schedule background threads.** A
   `threading.Thread(daemon=True)` is `is_alive() == True` but never executes.
   This is why the listener has to be a blocking main-thread loop and why MD's
   GUI freezes while it runs.
2. **MD's plugin loader scans `.py` files only.** It does not auto-discover
   `.dll`s anywhere we could find, and `Plug-in Manager ▸ +ADD` filters to
   `Plug-in File (*.py)`. The CLO 3D feature "DLL discovery still scans the
   main Plugins folder" is not present in MD. Verified with a zero-dep probe
   DLL (`cpp_plugin/probe.cpp`) that never logged and never appeared in MD's
   loaded modules. MD's own `New Assets/api_plugin_log.txt` only mentions
   Python folder scans.
3. **MD doesn't load `CLOAPIInterface.dll`** at all — the bridge that the CLO
   C++ SDK is built around. So even if MD started loading DLLs, plugins built
   against the CLO SDK would fail at first API call. A future C++ path on MD
   would need to use MD's embedded Python via the Python C API instead
   (`PyGILState_Ensure` + `PyRun_String`), not the CLO SDK.
4. **MD API is exposed as Python modules**: `import import_api / export_api /
   fabric_api / pattern_api / utility_api`. NOT as builtins/globals. Generated
   MD code must `import` what it needs and bind output to `result`. `avatar_api
   / animation_api / rendering_api / techpack_api / simulation_api` do **not**
   exist as separate modules — those functions live inside the existing five
   modules (e.g. `import_api.ImportAvatar`, `export_api.ExportAnimationVideo`).
5. **MD API is pybind11.** Call with wrong/no args and the `TypeError` lists
   the accepted signatures verbatim — free signature discovery via
   `md_api(module, contains)` then `execute_python` with wrong args.
6. **One JSON request per TCP connection.** Pipelining caused
   `WinError 10053` on Windows; the bridge opens a fresh socket per call.
7. **Modal dialog deadlock.** Any MD API that pops a modal dialog hangs the
   listener forever (the GUI thread is stuck in our accept loop). The wrappers
   pick dialog-free call variants where possible. Recovery: close MD.
8. **Heavy operations are slow.** Exporting a 400+ MB `.zprj` with embedded
   Alembic animation took 10–30 s in our test. Bridge timeout defaults to 120 s
   (`MD_MCP_TIMEOUT`).

## Target environment

| Item | Value |
|---|---|
| MD version | 2026.0.239 Personal (Personal license verified to work for the Python route) |
| MD Python | 3.11.8 (64-bit), embedded; prefix `C:/Users/Public/Documents/MarvelousDesigner/Configuration/python311` |
| OS | Windows 11 |
| MCP server Python | 3.10+ (`uv` for deps) |
| MD plugins folder | `C:\Users\Public\Documents\MarvelousDesigner\Plugins\` |
| MD plugin log | `C:\Users\Public\Documents\MarvelousDesigner\New Assets\api_plugin_log.txt` |
| Listener log | `~/md_mcp_listener.log` |
| CLO C++ SDK (installed but MD-incompatible) | `C:\Users\azoo\SDK\CLO_SDK_v2026.0.238\CLO_SDK_v2026.0.238_Win\` |
| Qt for C++ build | `C:\Qt\6.10.3\msvc2022_64\` (only relevant for CLO 3D) |

## Repo layout

```
src/marvelous_designer_mcp/
├── __main__.py    `python -m marvelous_designer_mcp` entry
├── server.py      FastMCP tools (11 total)
├── bridge.py      TCP JSON-line client
└── config.py      HOST / PORT / TIMEOUT (env-overridable)
md_addon/
└── md_listener.py the in-MD blocking server
scripts/
├── md_start_listener.py    paste-or-register-as-plugin launcher
├── install_md_plugin.py    auto-write pluginSettings.json
└── probe_as_plugin.py      (legacy) Plug-in Manager API probe
cpp_plugin/                  experimental C++ plugin (CLO 3D only)
README.md
MEMORY.md                    this file
pyproject.toml / uv.lock
```

## What to do next (when picking this up)

- Operational changes (more tools, ergonomics, docs): edit `src/.../server.py`
  for tools, `scripts/install_md_plugin.py` for setup, `README.md`.
- A new MD release: re-test the Python route end-to-end first; the API surface
  changes between MD versions (function names, signatures, new modules).
  `execute_python` lets you `import xxx_api; print(dir(xxx_api))` to map the
  delta.
- The C++ path: only worth resurrecting if (a) CLO Virtual Fashion adds DLL
  loading to MD, or (b) the goal moves to CLO 3D. The existing `cpp_plugin/`
  builds and is set up to receive new wrapper methods one by one.
- Areas not implemented and not gated on MD limitations: rendering wrappers
  (`export_api.ExportTurntableImages` etc), techpack export, multi-colorway
  handling, avatar import flows.

## Things explicitly tried and ruled out

- **Daemon thread socket server in the Python listener** — threads don't get
  CPU in MD's embedded interpreter (#1 above). Abandoned in v0.1.0.
- **Qt-driven main-thread pump from the Python side** — MD doesn't expose
  PySide/PyQt/sip; no Qt bindings reachable from MD's Python.
- **CLO Event Plugin** as a non-freezing path — C++ only, mouse-drop events
  only, no idle/tick hook. Not useful as a server vehicle.
- **C++ plugin DLL in MD's Plugins folder** (`cpp_plugin/`) — MD ignores
  `.dll`s entirely (#2). Code preserved for CLO 3D / future MD support.
- **Pipelined requests on a single TCP connection** — `WinError 10053` on
  Windows (#6). The bridge uses one connection per call.

## Glossary of files outside the repo we care about

| Path | Purpose |
|---|---|
| `C:\Users\Public\Documents\MarvelousDesigner\Plugins\pluginSettings.json` | MD's plugin registry; the auto-installer edits it |
| `C:\Users\Public\Documents\MarvelousDesigner\New Assets\api_plugin_log.txt` | MD's own plugin loader log — useful when nothing seems to happen |
| `~/md_mcp_listener.log` | Our listener's status / errors (Python + C++ both append here) |
| `~/md_mcp_probe.log` | Output from the C++ probe DLL diagnostic (not produced on MD) |
