"""
뉴스 라우터
뉴스 목록/검색, 알파 시그널 조회, 수혜주별 뉴스 조회 API를 제공합니다.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models.news import NewsItem
from app.models.alpha import AlphaSignal
from app.models.user import User
from app.schemas.news import NewsResponse, NewsListResponse, AlphaSignalResponse, StockInfo
from app.utils.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/news", tags=["뉴스"])
settings = get_settings()


@router.get("/", response_model=NewsListResponse)
async def get_news_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    source: Optional[str] = Query(None, description="뉴스 출처 필터"),
    sector: Optional[str] = Query(None, description="섹터 필터"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    뉴스 목록을 페이지네이션으로 반환합니다.
    무료 사용자는 하루 {FREE_DAILY_LIMIT}개까지 조회 가능합니다.
    """
    # 무료 사용자 일일 한도 체크
    if not current_user.can_use_today(settings.free_daily_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"무료 사용자는 하루 {settings.free_daily_limit}개까지 조회 가능합니다. 프리미엄으로 업그레이드하세요.",
        )

    # 기본 쿼리 (최신순)
    query = select(NewsItem).order_by(NewsItem.collected_at.desc())

    # 출처 필터
    if source:
        query = query.where(NewsItem.source == source)

    # 섹터 필터 (AlphaSignal 조인 필요)
    if sector:
        query = query.join(AlphaSignal).where(AlphaSignal.sector == sector)

    # 전체 수 카운트
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    news_items = result.scalars().all()

    # 무료 사용자 카운트 증가
    if not current_user.is_premium:
        current_user.daily_usage_count += 1

    # 응답 변환 (alpha_signal 포함)
    items = []
    for news in news_items:
        item = await _build_news_response(news, db)
        items.append(item)

    return NewsListResponse(total=total, page=page, size=size, items=items)


@router.get("/search", response_model=NewsListResponse)
async def search_news(
    q: str = Query(..., min_length=2, description="검색어"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """뉴스 제목/요약에서 키워드 검색"""
    if not current_user.can_use_today(settings.free_daily_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="일일 조회 한도를 초과했습니다.",
        )

    query = (
        select(NewsItem)
        .where(
            or_(
                NewsItem.title.contains(q),
                NewsItem.content_summary.contains(q),
            )
        )
        .order_by(NewsItem.collected_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    news_items = result.scalars().all()

    if not current_user.is_premium:
        current_user.daily_usage_count += 1

    items = [await _build_news_response(n, db) for n in news_items]
    return NewsListResponse(total=total, page=page, size=size, items=items)


@router.get("/by-stock/{stock_code}", response_model=NewsListResponse)
async def get_news_by_stock(
    stock_code: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    특정 종목코드가 수혜주/피해주로 포함된 뉴스를 조회합니다.
    """
    # AlphaSignal JSON에서 종목코드 검색
    result = await db.execute(
        select(AlphaSignal).where(
            or_(
                AlphaSignal.beneficiary_stocks_json.contains(stock_code),
                AlphaSignal.victim_stocks_json.contains(stock_code),
            )
        )
        .order_by(AlphaSignal.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    signals = result.scalars().all()

    news_ids = [s.news_id for s in signals]
    if not news_ids:
        return NewsListResponse(total=0, page=page, size=size, items=[])

    news_result = await db.execute(
        select(NewsItem).where(NewsItem.id.in_(news_ids))
    )
    news_items = news_result.scalars().all()

    items = [await _build_news_response(n, db) for n in news_items]
    return NewsListResponse(total=len(items), page=page, size=size, items=items)


@router.get("/{news_id}/alpha", response_model=AlphaSignalResponse)
async def get_alpha_signal(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """특정 뉴스의 알파 시그널(수혜주/피해주 분석)을 조회합니다."""
    result = await db.execute(
        select(AlphaSignal).where(AlphaSignal.news_id == news_id)
    )
    signal = result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="해당 뉴스의 분석 결과가 없습니다.")

    return _build_alpha_response(signal)


async def _build_news_response(news: NewsItem, db: AsyncSession) -> NewsResponse:
    """NewsItem을 NewsResponse 스키마로 변환합니다."""
    # alpha_signal lazy 로딩
    result = await db.execute(
        select(AlphaSignal).where(AlphaSignal.news_id == news.id)
    )
    signal = result.scalar_one_or_none()

    alpha_resp = _build_alpha_response(signal) if signal else None

    return NewsResponse(
        id=news.id,
        title=news.title,
        url=news.url,
        source=news.source,
        content_summary=news.content_summary,
        published_at=news.published_at,
        collected_at=news.collected_at,
        is_analyzed=news.is_analyzed,
        alpha_signal=alpha_resp,
    )


def _build_alpha_response(signal: AlphaSignal) -> AlphaSignalResponse:
    """AlphaSignal을 AlphaSignalResponse 스키마로 변환합니다."""
    return AlphaSignalResponse(
        id=signal.id,
        news_id=signal.news_id,
        beneficiary_stocks=[StockInfo(**s) for s in signal.get_beneficiary_stocks()],
        victim_stocks=[StockInfo(**s) for s in signal.get_victim_stocks()],
        impact_score=signal.impact_score,
        impact_reason=signal.impact_reason,
        sector=signal.sector,
        created_at=signal.created_at,
    )
