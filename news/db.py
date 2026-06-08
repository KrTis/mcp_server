import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "news.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS articles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT UNIQUE NOT NULL,
                date       TEXT NOT NULL,
                source     TEXT NOT NULL,
                title      TEXT NOT NULL,
                summary    TEXT,
                sentiment  TEXT,
                topic_id   INTEGER REFERENCES topics(id)
            );
        """)


def get_topics() -> list[str]:
    with _conn() as con:
        return [r["name"] for r in con.execute("SELECT name FROM topics ORDER BY name").fetchall()]


def get_or_create_topic(name: str) -> int:
    with _conn() as con:
        row = con.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = con.execute("INSERT INTO topics (name) VALUES (?)", (name,))
        return cur.lastrowid


def upsert_article(url: str, date: str, source: str, title: str,
                   summary: str, sentiment: str, topic: str):
    topic_id = get_or_create_topic(topic)
    with _conn() as con:
        con.execute("""
            INSERT INTO articles (url, date, source, title, summary, sentiment, topic_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                date=excluded.date, source=excluded.source, title=excluded.title,
                summary=excluded.summary, sentiment=excluded.sentiment, topic_id=excluded.topic_id
        """, (url, date, source, title, summary, sentiment, topic_id))


def get_articles_by_topic(topic: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT a.date, a.source, a.title, a.url, a.sentiment
            FROM articles a
            JOIN topics t ON t.id = a.topic_id
            WHERE t.name = ?
            ORDER BY a.date DESC
        """, (topic,)).fetchall()
        return [dict(r) for r in rows]


def get_topic_timeline(topic: str) -> list[dict]:
    """Returns date + summary + sentiment for trend analysis."""
    with _conn() as con:
        rows = con.execute("""
            SELECT a.date, a.summary, a.sentiment
            FROM articles a
            JOIN topics t ON t.id = a.topic_id
            WHERE t.name = ?
            ORDER BY a.date ASC
        """, (topic,)).fetchall()
        return [dict(r) for r in rows]
