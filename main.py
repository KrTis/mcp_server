from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from mcp_server.server import mcp

# Import tools so decorators execute
import mcp_server.tools.stopwatch
import mcp_server.tools.news
import mcp_server.tools.vikunja

if __name__ == "__main__":
    mcp.run(transport="stdio")