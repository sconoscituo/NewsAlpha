"""Multi-source RSS feed collector and parser."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import feedparser
import httpx

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "yonhap": "https://www.yonhapnewstv.co.kr/RSS/news.xml",
    "hankyung": "https://www.hankyung.com/feed/all-news",
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
}


@dataclass
class RSSArticle:
    title: str
    link: str
    summary: str
    published: Optional[datetime] = None
    source: str = ""
    tags: List[str] = field(default_factory=list)


async def fetch_feed(source: str, url: str) -> List[RSSArticle]:
    """Fetch and parse a single RSS feed asynchronously."""
    articles: List[RSSArticle] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            raw = resp.text
    except Exception as exc:
        logger.warning("Failed to fetch feed %s (%s): %s", source, url, exc)
        return articles

    feed = feedparser.parse(raw)
    for entry in feed.entries:
        published: Optional[datetime] = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        tags = [t.get("term", "") for t in getattr(entry, "tags", [])]
        articles.append(
            RSSArticle(
                title=entry.get("title", "").strip(),
                link=entry.get("link", ""),
                summary=entry.get("summary", entry.get("description", "")).strip(),
                published=published,
                source=source,
                tags=tags,
            )
        )
    logger.info("Collected %d articles from %s", len(articles), source)
    return articles


async def collect_all_feeds(
    feeds: Optional[dict] = None,
) -> List[RSSArticle]:
    """Collect articles from all configured RSS feeds."""
    import asyncio

    feeds = feeds or RSS_FEEDS
    tasks = [fetch_feed(name, url) for name, url in feeds.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_articles: List[RSSArticle] = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)
    # Deduplicate by link
    seen = set()
    unique: List[RSSArticle] = []
    for article in all_articles:
        if article.link not in seen:
            seen.add(article.link)
            unique.append(article)
    return unique
