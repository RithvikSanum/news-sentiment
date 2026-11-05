"""Fetch the latest headlines from free RSS feeds."""

import html
import re
from datetime import datetime, timezone

import feedparser
import requests

FEEDS = {
    "Financial": {
        "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "Guardian Business": "https://www.theguardian.com/business/rss",
    },
    "General": {
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "BBC Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "Guardian World": "https://www.theguardian.com/world/rss",
        "NPR": "https://feeds.npr.org/1001/rss.xml",
        "BBC Sport": "http://feeds.bbci.co.uk/sport/rss.xml",
    },
}

HEADERS = {"User-Agent": "Mozilla/5.0 (news-sentiment learning project)"}
TAG_RE = re.compile(r"<[^>]+>")


def clean(text):
    """Strip HTML tags and entities and collapse whitespace."""
    text = TAG_RE.sub(" ", text or "")
    return " ".join(html.unescape(text).split())


def _published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return None


def fetch_feed(source, url, category, timeout=10):
    """Return a list of article dicts from one RSS feed."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    articles = []
    for entry in feed.entries:
        link = entry.get("link")
        title = clean(entry.get("title"))
        if not link or not title:
            continue
        articles.append({
            "link": link,
            "title": title,
            "summary": clean(entry.get("summary")),
            "source": source,
            "category": category,
            "published": _published(entry),
        })
    return articles


def fetch_all(categories):
    """Fetch every feed in the given categories. Returns (articles, errors)."""
    articles, errors = [], []
    for category in categories:
        for source, url in FEEDS[category].items():
            try:
                articles.extend(fetch_feed(source, url, category))
            except Exception as exc:  # one broken feed shouldn't stop the rest
                errors.append(f"{source}: {exc}")
    return articles, errors
