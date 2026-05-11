import os

MD_HOST = os.environ.get("MD_MCP_HOST", "127.0.0.1")
MD_PORT = int(os.environ.get("MD_MCP_PORT", "7421"))
# Generous default: most calls return in <1s, but heavy ops (export of a large
# .zprj, simulation, rendering) can take much longer. Raise MD_MCP_TIMEOUT for
# very long renders. The MD GUI is frozen for the whole call regardless.
MD_TIMEOUT = float(os.environ.get("MD_MCP_TIMEOUT", "120.0"))
