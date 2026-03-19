"""
뉴스 수집 서비스
한국경제, 연합뉴스, 매일경제, Bloomberg RSS를 feedparser로 수집합니다.
중복 URL은 건너뛰고 DB에 저장합니다.
"""
import logging
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.news import NewsItem

logger = logging.getLogger(__name__)

# 수집 대상 RSS 피드 목록
RSS_FEEDS = [
    {
        "name": "한국경제",
        "url": "https://www.hankyung.com/feed/economy",
    },
    {
        "name": "연합뉴스",
        "url": "https://www.yonhapnewstv.co.kr/RSS/economy.xml",
    },
    {
        "name": "매일경제",
        "url": "https://www.mk.co.kr/rss/30100041/",
    },
    {
        "name": "Bloomberg",
        "url": "https://feeds.bloomberg.com/markets/news.rss",
    },
]


def _parse_published_at(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """RSS 엔트리에서 발행 시각을 파싱합니다."""
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            import time
            return datetime(*entry.published_parsed[:6])
    except Exception:
        pass
    return None


def _extract_summary(entry: feedparser.FeedParserDict) -> str:
    """RSS 엔트리에서 요약문을 추출합니다. (최대 500자)"""
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary
    elif hasattr(entry, "description"):
        summary = entry.description

    # HTML 태그 간단 제거
    import re
    summary = re.sub(r"<[^>]+>", "", summary)
    return summary[:500].strip()


async def collect_news() -> int:
    """
    모든 RSS 피드에서 뉴스를 수집하고 DB에 저장합니다.
    반환값: 새로 저장된 뉴스 수
    """
    total_saved = 0

    async with AsyncSessionLocal() as db:
        for feed_info in RSS_FEEDS:
            try:
                saved = await _collect_from_feed(db, feed_info["name"], feed_info["url"])
                total_saved += saved
                logger.info(f"[{feed_info['name']}] {saved}개 새 뉴스 저장")
            except Exception as e:
                logger.error(f"[{feed_info['name']}] 수집 실패: {e}")

        await db.commit()

    logger.info(f"뉴스 수집 완료: 총 {total_saved}개 저장")
    return total_saved


async def _collect_from_feed(db: AsyncSession, source: str, feed_url: str) -> int:
    """
    단일 RSS 피드에서 뉴스를 수집합니다.
    반환값: 저장된 뉴스 수
    """
    saved_count = 0

    # feedparser는 동기 라이브러리이므로 httpx로 먼저 내용 받아서 파싱
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                feed_url,
                headers={"User-Agent": "NewsAlpha/1.0 RSS Reader"},
            )
            response.raise_for_status()
            raw_content = response.text
    except httpx.HTTPError as e:
        logger.warning(f"RSS 다운로드 실패 [{source}]: {e}")
        return 0

    feed = feedparser.parse(raw_content)

    for entry in feed.entries:
        url = getattr(entry, "link", None)
        title = getattr(entry, "title", None)

        # URL 또는 제목이 없으면 건너뜀
        if not url or not title:
            continue

        # 중복 URL 체크
        result = await db.execute(select(NewsItem).where(NewsItem.url == url))
        existing = result.scalar_one_or_none()
        if existing:
            continue

        # 새 뉴스 저장
        news_item = NewsItem(
            title=title.strip(),
            url=url,
            source=source,
            content_summary=_extract_summary(entry),
            published_at=_parse_published_at(entry),
        )
        db.add(news_item)
        saved_count += 1

    return saved_count
