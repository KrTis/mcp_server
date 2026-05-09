from mcp_server.server import mcp

# Import tools so decorators execute
import mcp_server.tools.stopwatch
import mcp_server.tools.news

if __name__ == "__main__":
    mcp.run(transport="stdio")