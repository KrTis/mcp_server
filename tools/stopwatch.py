from mcp_server.server import mcp
from mcp_server.state.stopwatch_state import Stopwatch, stopwatches


@mcp.tool()
def start_stopwatch(name: str) -> str:
    sw = Stopwatch()
    sw.start()
    stopwatches[name] = sw
    return f"Stopwatch '{name}' started."


@mcp.tool()
def stop_stopwatch(name: str, save: bool = True) -> str:
    if name not in stopwatches:
        return f"Stopwatch '{name}' does not exist."

    duration = stopwatches[name].stop()

    if not save:
        del stopwatches[name]

    return f"Stopwatch '{name}' stopped. Duration: {duration:.2f} seconds."


@mcp.tool()
def list_stopwatches() -> list[str]:
    return list(stopwatches.keys())
