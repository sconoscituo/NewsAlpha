"""
텔레그램 알림 서비스
사용자 위시리스트 종목이 수혜주/피해주에 포함될 때 텔레그램으로 알립니다.
프리미엄 사용자 전용 기능입니다.
"""
import logging
from datetime import datetime, timedelta

from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.alpha import AlphaSignal
from app.models.news import NewsItem

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_alert_message(
    news: NewsItem,
    alpha: AlphaSignal,
    matched_stocks: list[dict],
    match_type: str,
) -> str:
    """텔레그램 알림 메시지를 생성합니다."""
    emoji = "🟢" if match_type == "수혜주" else "🔴"
    stock_names = ", ".join(f"{s['name']}({s['code']})" for s in matched_stocks)

    return (
        f"{emoji} *NewsAlpha 알림*\n\n"
        f"*{match_type} 감지됨:* {stock_names}\n\n"
        f"*뉴스:* {news.title}\n"
        f"*출처:* {news.source}\n"
        f"*영향도:* {alpha.impact_score:+.1f} ({alpha.sector})\n"
        f"*분석:* {alpha.impact_reason or '정보 없음'}\n\n"
        f"🔗 {news.url}"
    )


async def notify_watchlist_users() -> int:
    """
    최근 분석된 알파 시그널을 확인하고,
    위시리스트 종목이 포함된 사용자에게 텔레그램 알림을 보냅니다.
    반환값: 전송된 알림 수
    """
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN이 설정되지 않아 알림을 건너뜁니다.")
        return 0

    bot = Bot(token=settings.telegram_bot_token)
    sent_count = 0

    async with AsyncSessionLocal() as db:
        # 최근 30분 이내에 생성된 알파 시그널 조회
        since = datetime.utcnow() - timedelta(minutes=settings.collect_interval_minutes + 5)
        result = await db.execute(
            select(AlphaSignal)
            .where(AlphaSignal.created_at >= since)
            .order_by(AlphaSignal.created_at.desc())
        )
        recent_signals = result.scalars().all()

        if not recent_signals:
            return 0

        # 텔레그램 연동된 프리미엄 사용자 조회
        user_result = await db.execute(
            select(User).where(
                User.is_premium == True,
                User.telegram_chat_id.isnot(None),
                User.is_active == True,
            )
        )
        premium_users = user_result.scalars().all()

        for signal in recent_signals:
            # 뉴스 정보 조회
            news_result = await db.execute(
                select(NewsItem).where(NewsItem.id == signal.news_id)
            )
            news = news_result.scalar_one_or_none()
            if not news:
                continue

            beneficiaries = signal.get_beneficiary_stocks()
            victims = signal.get_victim_stocks()

            for user in premium_users:
                watchlist = user.get_watchlist()
                if not watchlist:
                    continue

                # 수혜주 매칭
                matched_beneficiaries = [
                    s for s in beneficiaries if s.get("code") in watchlist
                ]
                # 피해주 매칭
                matched_victims = [
                    s for s in victims if s.get("code") in watchlist
                ]

                # 수혜주 알림 전송
                if matched_beneficiaries:
                    try:
                        msg = _build_alert_message(news, signal, matched_beneficiaries, "수혜주")
                        await bot.send_message(
                            chat_id=user.telegram_chat_id,
                            text=msg,
                            parse_mode="Markdown",
                        )
                        sent_count += 1
                    except TelegramError as e:
                        logger.error(f"텔레그램 전송 실패 (user={user.id}): {e}")

                # 피해주 알림 전송
                if matched_victims:
                    try:
                        msg = _build_alert_message(news, signal, matched_victims, "피해주")
                        await bot.send_message(
                            chat_id=user.telegram_chat_id,
                            text=msg,
                            parse_mode="Markdown",
                        )
                        sent_count += 1
                    except TelegramError as e:
                        logger.error(f"텔레그램 전송 실패 (user={user.id}): {e}")

    logger.info(f"텔레그램 알림 전송 완료: {sent_count}건")
    return sent_count
