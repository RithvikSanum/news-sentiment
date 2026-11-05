"""SQLite storage for articles and your ratings."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "news.db"

POSITIVE, NEGATIVE = 1, 0


def _now():
    return datetime.now(timezone.utc).isoformat()


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            link        TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            summary     TEXT,
            source      TEXT,
            category    TEXT,
            published   TEXT,
            fetched_at  TEXT NOT NULL,
            user_label  INTEGER,          -- 1 positive, 0 negative, NULL unrated
            rated_at    TEXT
        )
    """)
    conn.commit()
    return conn


def add_articles(conn, articles):
    """Insert new articles, ignoring ones already stored. Returns number added."""
    before = conn.total_changes
    now = _now()
    conn.executemany(
        """INSERT OR IGNORE INTO articles
           (link, title, summary, source, category, published, fetched_at)
           VALUES (:link, :title, :summary, :source, :category, :published, :fetched_at)""",
        [{**a, "fetched_at": now} for a in articles],
    )
    conn.commit()
    return conn.total_changes - before


def get_articles(conn, categories=None, rated=None):
    """Return articles, newest first. rated=True/False filters by whether you rated them."""
    query, params = "SELECT * FROM articles WHERE 1=1", []
    if categories:
        query += f" AND category IN ({','.join('?' * len(categories))})"
        params += list(categories)
    if rated is True:
        query += " AND user_label IS NOT NULL"
    elif rated is False:
        query += " AND user_label IS NULL"
    query += " ORDER BY COALESCE(published, fetched_at) DESC"
    return [dict(r) for r in conn.execute(query, params)]


def set_label(conn, link, label):
    """Save your rating (POSITIVE, NEGATIVE, or None to clear it)."""
    conn.execute(
        "UPDATE articles SET user_label = ?, rated_at = ? WHERE link = ?",
        (label, _now() if label is not None else None, link),
    )
    conn.commit()


def ratings_version(conn):
    """A cheap fingerprint that changes whenever ratings change (used to retrain)."""
    row = conn.execute(
        "SELECT COUNT(user_label), MAX(rated_at), SUM(user_label) FROM articles"
    ).fetchone()
    return tuple(row)
