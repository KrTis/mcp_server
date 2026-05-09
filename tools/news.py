from mcp_server.server import mcp
from mcp_server.news.scraper import scrape_website, scrape_all
from mcp_server.news.sources import SOURCES

@mcp.tool()
def get_headlines_jutarnji():
    return scrape_website(SOURCES["jutarnji"])

@mcp.tool()
def get_headlines_vecernji():
    return scrape_website(SOURCES["vecernji"])

@mcp.tool()
def get_headlines_index():
    return scrape_website(SOURCES["index"])

@mcp.tool()
def get_headlines_tportal():
    return scrape_website(SOURCES["tportal"])

@mcp.tool()
def get_headlines_all():
    return scrape_all()

@mcp.tool()
def summarize_headlines():
    summary = []
    max_items=10
    for source, data in scrape_all().items():

        items = data.get("items", [])

        for item in items[:max_items]:

            # CASE 1: structured dict
            if isinstance(item, dict):
                title = item.get("title")
                url = item.get("url")

            # CASE 2: plain string (your current case)
            else:
                title = item
                url = None

            summary.append({
                "source": source,
                "title": title,
                "url": url
            })

    return {
        "total": len(summary),
        "items": summary
    }
