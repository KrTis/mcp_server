from mcp_server.server import mcp
from mcp_server.news.scraper import scrape_website, scrape_all, fetch_article_text
from mcp_server.news.sources import SOURCES
from mcp.server.fastmcp import Image
import os
import requests
from bs4 import BeautifulSoup

_LMS_URL = os.environ.get("LMS_API_URL", "http://localhost:1234/v1")
_LMS_KEY = os.environ.get("LMS_API_KEY", "")
_LMS_MODEL = os.environ.get("LMS_SUMMARY_MODEL", "mistralai/ministral-3-3b")


def _summarize(text: str) -> str:
    # Use whichever model is currently loaded in LM Studio
    try:
        models = requests.get(
            f"{_LMS_URL}/models",
            headers={"Authorization": f"Bearer {_LMS_KEY}"},
            timeout=5,
        ).json()["data"]
        model = next((m["id"] for m in models if "embed" not in m["id"].lower()), _LMS_MODEL)
    except Exception:
        model = _LMS_MODEL

    r = requests.post(
        f"{_LMS_URL}/chat/completions",
        headers={"Authorization": f"Bearer {_LMS_KEY}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": f"Summarize this news article in 3 sentences:\n\n{text}"}],
            "max_tokens": 200,
            "temperature": 0.3,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

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
def get_detailed_headlines(
    source: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Fetch headlines and open each article to extract its full text.
    source: list of sources to include, e.g. ["jutarnji", "index"]. Available: jutarnji, vecernji, index, tportal. Omit or pass null for all.
    limit: max articles per source (keep low, e.g. 3).
    Returns list of {source, title, url, text}.
    """
    if source:
        sources = {s: SOURCES[s] for s in source if s in SOURCES}
    else:
        sources = SOURCES

    results = []
    for name, base_url in sources.items():
        try:
            headlines = scrape_website(base_url, limit=limit)
        except Exception as e:
            results.append({"source": name, "error": str(e)})
            continue

        for item in headlines.get("items", []):
            entry = {"source": name, "title": item["title"], "url": item["url"]}
            if item["url"]:
                try:
                    text = fetch_article_text(item["url"])
                    entry["summary"] = _summarize(text)
                except Exception as e:
                    entry["summary"] = f"(failed: {e})"
            results.append(entry)

    return results


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
