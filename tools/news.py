from mcp_server.server import mcp
from mcp_server.news.scraper import scrape_website, scrape_all
from mcp_server.news.sources import SOURCES
from mcp.server.fastmcp import Image
import requests
from bs4 import BeautifulSoup

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

@mcp.tool()
def get_felix_comic(comic_date: str | None = None) -> Image:
    """
    Fetch today's (or a specific date's) Felix comic from vecernji.hr.
    comic_date: ISO date string YYYY-MM-DD, defaults to today.
    """
    from datetime import date
    d = comic_date or date.today().isoformat()
    page_url = f"https://www.vecernji.hr/zabava/felix/{d}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    r = requests.get(page_url, headers=headers, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    img_link = soup.find("a", href=lambda h: h and h.startswith("/media/img/") and (h.endswith(".jpeg") or h.endswith(".png")))
    if not img_link:
        raise ValueError(f"Felix comic image not found on page for {d}")

    img_url = "https://www.vecernji.hr" + img_link["href"]
    fmt = "png" if img_link["href"].endswith(".png") else "jpeg"
    img_r = requests.get(img_url, headers=headers, timeout=10)
    img_r.raise_for_status()

    return Image(data=img_r.content, format=fmt)
