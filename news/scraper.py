import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from .sources import SOURCES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    """Fetch and return the main text of a news article, truncated to max_chars."""
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for tag in soup(["nav", "footer", "aside", "script", "style", "figure"]):
        tag.decompose()

    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 30:
            continue
        paragraphs.append(text)

    return " ".join(paragraphs)[:max_chars]


def scrape_website(base_url, limit=10):
    r = requests.get(base_url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(" ", strip=True)

        if not text:
            continue
        if len(text) < 25:
            continue
        if re.fullmatch(r"\d{1,2}:\d{2}", text):
            continue

        parent_link = tag.find_parent("a")
        url = urljoin(base_url, parent_link["href"]) if parent_link and parent_link.get("href") else None

        results.append({"title": text, "url": url})

    seen = set()
    clean = []

    for item in results:
        if item["title"] in seen:
            continue
        seen.add(item["title"])
        clean.append(item)

        if len(clean) >= limit:
            break

    return {"count": len(clean), "items": clean}


def scrape_all(limit_per_site=5):
    results = {}

    for name, url in SOURCES.items():
        try:
            results[name] = scrape_website(url, limit=limit_per_site)
        except Exception as e:
            results[name] = {"count": 0, "items": [], "error": str(e)}

    return results
