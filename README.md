# marvelous-designer-mcp

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets an
LLM (e.g. Claude) drive **Marvelous Designer** (and CLO, which shares the same
Python API) by running code inside MD's embedded Python interpreter.

It does **not** need the C++ SDK, a plugin build, or a CLO-SET API key — just MD's
built-in Python Editor.

## How it works

```
LLM  ──MCP(stdio)──▶  MCP server (this repo, FastMCP)
                          │  JSON-per-line over TCP 127.0.0.1:7421
                          ▼
                      md_listener.py  (you paste it into MD's Python Editor)
                          │  exec() in MD's interpreter
                          ▼
                      MD Python API:  import_api / export_api / fabric_api /
                                      pattern_api / utility_api / ...
```

MD's embedded Python (3.11) does **not** schedule background threads, so the
listener is a plain blocking accept loop that runs on MD's GUI thread. **While the
listener is running, MD's window is unresponsive** — that's expected. Stop it with
the `shutdown_listener` tool (or by closing MD).

## Requirements

- Marvelous Designer 2026 (or CLO 2026) — `Plugins ▸ Python Editor` must be available
- Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) on the machine running the MCP server
- The MCP server and MD run on the **same machine** (the listener binds `127.0.0.1`)

## Setup

```powershell
git clone https://github.com/ysk424/marvelous-designer-mcp.git
cd marvelous-designer-mcp
uv sync
```

## Running

### 1. Start the listener inside Marvelous Designer

Open `Plugins ▸ Python Editor` in MD, then paste **the whole contents of
`scripts/md_start_listener.py`** and run it. (Pasting line-by-line into the editor
can mangle indentation — copy the file in a text editor and paste it in one go.)

You should see `[md-mcp] listening (blocking) on 127.0.0.1:7421 ...` and MD will
freeze. That's the ready state.

> If the path in `md_start_listener.py` doesn't match where you cloned the repo,
> edit the `_ADDON_DIR` line at the top of that file.

### 2. Start the MCP server

```powershell
uv run python -m marvelous_designer_mcp
```

Or let Claude Desktop launch it (below).

### 3. Claude Desktop config

Add to `claude_desktop_config.json`
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "marvelous-designer": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\you\\git\\marvelous-designer-mcp",
        "python",
        "-m",
        "marvelous_designer_mcp"
      ]
    }
  }
}
```

Restart Claude Desktop. The MD listener must already be running (step 1) for the
tools to work.

## Tools

| Tool | What it does |
|---|---|
| `ping` | Check the listener is reachable. |
| `execute_python(code)` | Run arbitrary Python in MD's interpreter. `import` the `*_api` modules; bind your return value to a name called `result`. Returns `{stdout, stderr, result, error}`. |
| `shutdown_listener()` | Stop the listener loop and release the MD GUI. |
| `scene_info()` | Project name/path, MD version, pattern & fabric counts. |
| `list_patterns()` | Pattern pieces: index, name, assigned fabric index. |
| `list_fabrics()` | Fabrics: index, name (+ fabric-style list). |
| `assign_fabric(fabric_index, pattern_index, face=2)` | `fabric_api.AssignFabricToPattern`. |
| `import_project(path)` | Open a `.zprj` / `.zpac` / `.obj` / `.fbx` / ... by absolute path (`import_api.ImportFile`). |
| `export_project(path)` | Save the scene as a `.zprj` (`export_api.ExportZPrjW`). |
| `simulate(steps=1)` | `utility_api.Simulate(int)`. |
| `md_api(module, contains="")` | List a module's functions; substring-filtered. Discover signatures by calling a function with wrong args and reading the `TypeError`. |

Anything not covered by a wrapper: use `execute_python` directly.

## Caveats

- **MD freezes while the listener runs.** Use `shutdown_listener` when you want the
  GUI back. For an LLM-driven workflow this is usually fine — Claude does the work.
- **Modal-dialog deadlock.** Any API call that pops a modal dialog (unsaved-changes
  prompt, error popup, file picker) hangs the listener forever, because MD's GUI
  thread is stuck in our loop. Recovery: close MD. The wrappers pick dialog-free
  call variants where possible.
- **Heavy ops are slow.** Exporting a large `.zprj` (e.g. with an embedded Alembic
  animation), simulation and rendering can take a long time; the bridge timeout
  defaults to 120s — raise `MD_MCP_TIMEOUT` (seconds) for very long renders.
- **localhost only.** The listener binds `127.0.0.1`; it is not exposed to the network.
- Generated MD code must `import` the `*_api` module(s) it uses (they are not
  globals) and bind output to `result`. The API is pybind11-based.

## Config (environment variables)

| Var | Default | Meaning |
|---|---|---|
| `MD_MCP_HOST` | `127.0.0.1` | listener host the bridge connects to |
| `MD_MCP_PORT` | `7421` | listener port |
| `MD_MCP_TIMEOUT` | `120.0` | bridge socket timeout, seconds |

(The listener side's host/port are constants in `md_addon/md_listener.py` — keep
them in sync if you change the defaults.)

## Uninstall

There's nothing installed inside MD — just stop the listener (`shutdown_listener`
or close MD) and remove the Claude Desktop config entry. Delete the repo to remove
the rest.

## License

MIT — see `LICENSE`.
