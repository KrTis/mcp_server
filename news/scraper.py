import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from .sources import SOURCES
def scrape_website(base_url, limit=10):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    r = requests.get(base_url, headers=headers, timeout=10)
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

        results.append({
            "title": text,
            "url": url
        })

    seen = set()
    clean = []

    for item in results:
        if item["title"] in seen:
            continue
        seen.add(item["title"])
        clean.append(item)

        if len(clean) >= limit:
            break

    return {
        "count": len(clean),
        "items": clean
    }

def scrape_all(limit_per_site=5):
    results = {}

    for name, url in SOURCES.items():
        try:
            data = scrape_website(url, limit=limit_per_site)

            results[name] = data   # <-- FIX: do NOT rewrap

        except Exception as e:
            results[name] = {
                "count": 0,
                "items": [],
                "error": str(e)
            }

    return results