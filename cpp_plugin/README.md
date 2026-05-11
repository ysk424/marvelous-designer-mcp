# C++ plugin (experimental, CLO 3D only)

> **Status:** does **not** work in Marvelous Designer. Kept here for CLO 3D
> users and for the day MD ships a C++ plugin loader.

This folder is the v0.2 attempt at a non-freezing listener: a `LibraryWindowInterface`
plugin DLL whose `DoFunctionStartUp()` hook starts a worker-thread socket server
and marshals each request to MD's main thread via `Qt::BlockingQueuedConnection`.
The plan was sound; the host turned out to be the wrong product.

## What we found

Marvelous Designer's plugin loader scans **only `.py` files**. It does not auto-discover
`.dll` plugins (the CLO 3D feature "DLL discovery still scans the main Plugins folder"
is not present in MD), and the `Plug-in Manager ▸ +ADD` file dialog filters to
`Plug-in File (*.py)`. We verified this empirically with `probe.cpp`, a no-deps DLL
that logs in `DllMain`: dropped into `C:\Users\Public\Documents\MarvelousDesigner\Plugins\`,
it produced no log line and never appeared in MD's loaded modules. MD's own
`api_plugin_log.txt` only mentions Python folder scans.

So: **on MD this code is dead weight today.** On CLO 3D (which does have the C++
SDK plugin loader) the same code should load and run, since the SDK headers and
APIs are identical.

## Files

| File | Purpose |
|---|---|
| `CMakeLists.txt` | Build config; defaults `QTDIR=C:/Qt/6.10.3/msvc2022_64` and `CLO_SDK=C:/Users/azoo/SDK/CLO_SDK_v2026.0.238/CLO_SDK_v2026.0.238_Win` (override on the command line). |
| `MdMcpPlugin.{h,cpp}` | `LibraryWindowInterface` subclass with all library-UI hooks stubbed; `IsPluginEnabled() = true` so the host treats it as a regular plugin; `DoFunctionStartUp()` instantiates `MdMcpServer`. |
| `MdMcpServer.{h,cpp}` | Worker-thread WinSock accept loop + `Q_INVOKABLE handleRequestOnMain` slot dispatched via `Qt::BlockingQueuedConnection`. Calls the CLO API singletons (`APICommand::getInstance().Get<*>API()`). Speaks the same JSON-line protocol as the Python listener — `bridge.py` / `server.py` work unchanged. |
| `probe.cpp` | Zero-dep diagnostic DLL (logs `DllMain` calls to `~/md_mcp_probe.log`); used to prove MD doesn't load arbitrary plugins. |
| `dllmain.cpp / stdafx.{h,cpp} / targetver.h` | Standard Win32 boilerplate from the SDK samples. |
| `build.bat` | Wraps `vcvars64.bat` + `cmake` for one-step Release builds. |

## Build (Windows, CLO 3D users)

Prereqs: VS2022 Community (Desktop C++ workload), Qt 6.10.x (msvc2022_64),
the CLO 3D C++ SDK.

```powershell
.\build.bat
# or:
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DQTDIR=... -DCLO_SDK=...
cmake --build build --config Release
```

Output: `build\Release\MdMcpPlugin.dll`. Drop it into CLO's Plugins folder
(`C:\Users\Public\Documents\CLO\Plugins\`) and restart CLO.

## Untested on CLO 3D

The CLO 3D-side load path has not been tested by us (we only have MD). If anyone
runs it on CLO, please open an issue with whatever appears in
`~/md_mcp_listener.log` and `api_plugin_log.txt`.

## Could MD be made to load this someday?

Two scenarios:

1. **CLO Virtual Fashion adds C++ plugin support to MD.** Drop the DLL into the
   Plugins folder, done.
2. **An MD-specific Python C API bridge.** A future iteration could embed Python
   in the plugin DLL (`Py_GetGlobalState` + `PyGILState_Ensure` + `PyRun_String`)
   so the C++ side calls MD's `import fabric_api; ...` directly, without any
   CLO C++ SDK dependency. This would still require MD to load the DLL — which
   it doesn't today. So this approach is also blocked behind scenario 1.

The reason both options are blocked is the same root cause: **MD's loader does
not look for `.dll` files at all**, anywhere we could find. There's no clever
trick on the Python side that fixes this.
