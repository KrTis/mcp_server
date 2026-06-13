from mcp_server.server import mcp
from mcp_server.news.scraper import scrape_website, scrape_all, fetch_article_text
from mcp_server.news.sources import SOURCES
from mcp_server.news.db import (
    init_db,
    get_topics,
    get_articles_by_topic,
    get_topic_timeline,
    upsert_article,
)
from mcp.server.fastmcp import Image
from datetime import date
import os
import json
import requests
from bs4 import BeautifulSoup

_LMS_URL = os.environ.get("LMS_API_URL", "http://localhost:1234/v1")
_LMS_KEY = os.environ.get("LMS_API_KEY", "")
_LMS_MODEL = os.environ.get("LMS_SUMMARY_MODEL", "mistralai/ministral-3-3b")


def _content_prompt(text):
    existing_topics = get_topics()
    return f"""
Return ONLY valid JSON.

{{
  "summary": "3 sentence summary",
  "sentiment": "positive|negative|neutral",
  "topic": "topic name"
}}

Existing topics:
{existing_topics}

Use an existing topic if appropriate.
Create a new one only if none fit.
All topics must be in English.
Never use Croatian topic names.
If a matching topic already exists, reuse it exactly.

Article:
{text}
"""
import json
import re

def _parse_llm_response(content: str):

    content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        pass

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        content,
        re.DOTALL
    )

    if match:
        return json.loads(match.group(1))

    raise ValueError(
        f"LLM did not return valid JSON:\n{content}"
    )

def _summarize(text: str) -> dict:
    r = requests.post(
        f"{_LMS_URL}/chat/completions",
        headers={"Authorization": f"Bearer {_LMS_KEY}"},
        json={
            "model": _LMS_MODEL,
            "messages": [{"role": "user", "content": _content_prompt(text)}],
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=60,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"].strip()


    return _parse_llm_response(content)

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
    max_items = 10

    for source, data in scrape_all().items():
        items = data.get("items", [])

        for item in items[:max_items]:
            if isinstance(item, dict):
                title = item.get("title")
                url = item.get("url")
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
def get_news_briefing(
    source: list[str] | None = None,
    limit: int = 10,
) -> str:

    if source:
        sources = {s: SOURCES[s] for s in source if s in SOURCES}
    else:
        sources = SOURCES

    init_db()
    results = []

    for name, base_url in sources.items():
        try:
            headlines = scrape_website(base_url, limit=limit)
        except Exception as e:
            results.append(f"**{name}**: error - {e}")
            continue

        for item in headlines.get("items", []):
            if item["url"]:
                try:
                    text = fetch_article_text(item["url"])
                    analysis = _summarize(text)

                    summary = analysis["summary"]
                    sentiment = analysis["sentiment"]
                    topic = analysis["topic"]

                    upsert_article(
                        url=item["url"],
                        date=date.today().isoformat(),
                        source=name,
                        title=item["title"],
                        summary=summary,
                        sentiment=sentiment,
                        topic=topic,
                    )

                    formatted = (
                        f"**{item['title']}** ({name})\n"
                        f"Topic: {topic}\n"
                        f"Sentiment: {sentiment}\n\n"
                        f"{summary}\n"
                        f"{item['url']}"
                    )

                except Exception as e:
                    formatted = f"**{item['title']}** ({name})\n(failed: {e})"
            else:
                formatted = f"**{item['title']}** ({name})\n(no url)"

            results.append(formatted)

    return "\n\n---\n\n".join(results)


@mcp.tool()
def list_topics():
    return get_topics()


@mcp.tool()
def get_topic_articles(topic: str):
    return get_articles_by_topic(topic)


@mcp.tool()
def get_topic_sentiment_timeline(topic: str):
    return get_topic_timeline(topic)


@mcp.tool()
def get_felix_comic(comic_date: str | None = None) -> Image:
    from datetime import date

    d = comic_date or date.today().isoformat()
    page_url = f"https://www.vecernji.hr/zabava/felix/{d}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    r = requests.get(page_url, headers=headers, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    img_link = soup.find(
        "a",
        href=lambda h: h and h.startswith("/media/img/")
        and (h.endswith(".jpeg") or h.endswith(".png"))
    )

    if not img_link:
        raise ValueError(f"Felix comic image not found on page for {d}")

    img_url = "https://www.vecernji.hr" + img_link["href"]
    fmt = "png" if img_link["href"].endswith(".png") else "jpeg"

    img_r = requests.get(img_url, headers=headers, timeout=10)
    img_r.raise_for_status()

    return Image(data=img_r.content, format=fmt)
