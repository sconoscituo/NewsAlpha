"""Personalized newsletter generator based on user keyword preferences."""
import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NewsletterItem:
    title: str
    summary: str
    link: str
    source: str
    investment_score: int
    sentiment: str
    keywords: List[str]


@dataclass
class Newsletter:
    user_id: int
    generated_at: datetime
    items: List[NewsletterItem]
    total_articles: int
    top_sectors: List[str]


def _matches_keywords(item_keywords: List[str], user_keywords: List[str]) -> bool:
    """Check if any user keyword matches article keywords (case-insensitive)."""
    user_kw_lower = {kw.lower() for kw in user_keywords}
    return any(kw.lower() in user_kw_lower for kw in item_keywords)


def build_newsletter(
    user_id: int,
    summarized_articles: List[dict],
    user_keywords: Optional[List[str]] = None,
    min_score: int = 5,
    max_items: int = 10,
) -> Newsletter:
    """
    Build a personalized newsletter for a user.

    Args:
        user_id: Target user ID.
        summarized_articles: List of dicts from NewsSummarizer (with raw article attached).
        user_keywords: User's interest keywords for filtering.
        min_score: Minimum investment_score to include.
        max_items: Maximum number of articles in the newsletter.
    """
    filtered = []
    for item in summarized_articles:
        score = item.get("investment_score", 0)
        if score < min_score:
            continue
        article = item.get("_article")
        if user_keywords and article:
            all_kw = item.get("keywords", []) + getattr(article, "tags", [])
            if not _matches_keywords(all_kw, user_keywords):
                continue
        filtered.append(item)

    # Sort by investment_score descending
    filtered.sort(key=lambda x: x.get("investment_score", 0), reverse=True)
    filtered = filtered[:max_items]

    items: List[NewsletterItem] = []
    sector_count: dict = {}
    for item in filtered:
        article = item.get("_article")
        for sector in item.get("key_sectors", []):
            sector_count[sector] = sector_count.get(sector, 0) + 1
        items.append(
            NewsletterItem(
                title=article.title if article else "",
                summary=item.get("summary", ""),
                link=article.link if article else "",
                source=article.source if article else "",
                investment_score=item.get("investment_score", 0),
                sentiment=item.get("sentiment", "neutral"),
                keywords=item.get("keywords", []),
            )
        )

    top_sectors = sorted(sector_count, key=lambda s: sector_count[s], reverse=True)[:5]

    return Newsletter(
        user_id=user_id,
        generated_at=datetime.utcnow(),
        items=items,
        total_articles=len(items),
        top_sectors=top_sectors,
    )


def newsletter_to_html(newsletter: Newsletter) -> str:
    """Render a Newsletter as a simple HTML email body."""
    rows = ""
    for item in newsletter.items:
        sentiment_color = {"positive": "#2ecc71", "negative": "#e74c3c"}.get(
            item.sentiment, "#95a5a6"
        )
        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #eee;">
            <a href="{item.link}" style="font-weight:bold;color:#2c3e50;">{item.title}</a>
            <p style="color:#555;margin:6px 0;">{item.summary}</p>
            <span style="background:{sentiment_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{item.sentiment}</span>
            <span style="margin-left:8px;font-size:12px;color:#888;">Score: {item.investment_score}/10 | {item.source}</span>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
      <h2 style="color:#2c3e50;">NewsAlpha 투자 뉴스레터</h2>
      <p style="color:#888;">생성 시각: {newsletter.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
      <p>주요 섹터: <strong>{', '.join(newsletter.top_sectors) or '없음'}</strong></p>
      <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
      <p style="color:#aaa;font-size:11px;margin-top:20px;">NewsAlpha | AI 뉴스 투자 인사이트</p>
    </body></html>
    """
