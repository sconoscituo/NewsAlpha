"""
NewsAlpha FastAPI 앱 진입점
APScheduler로 30분마다 뉴스 수집 + AI 분석 + 텔레그램 알림을 실행합니다.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database import init_db
from app.routers import news, users, trending

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI 뉴스 분석으로 주식 Alpha 찾기 - 수혜주/피해주 자동 추출",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정 (개발 환경용 전체 허용, 운영 시 origins 제한 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(news.router)
app.include_router(users.router)
app.include_router(trending.router, prefix="/api/v1")

# APScheduler 인스턴스
scheduler = AsyncIOScheduler()


async def scheduled_job():
    """
    30분마다 실행되는 스케줄 작업:
    1. RSS 뉴스 수집
    2. 미분석 뉴스 AI 분석
    3. 위시리스트 텔레그램 알림
    """
    from app.services.news_collector import collect_news
    from app.services.alpha_analyzer import analyze_pending_news
    from app.services.notifier import notify_watchlist_users

    logger.info("스케줄 작업 시작")
    try:
        # Step 1: 뉴스 수집
        saved = await collect_news()
        logger.info(f"뉴스 수집: {saved}개 저장")

        # Step 2: AI 분석 (새 뉴스가 있을 때만)
        if saved > 0:
            analyzed = await analyze_pending_news()
            logger.info(f"AI 분석: {analyzed}개 완료")

            # Step 3: 텔레그램 알림
            sent = await notify_watchlist_users()
            logger.info(f"텔레그램 알림: {sent}건 전송")
    except Exception as e:
        logger.error(f"스케줄 작업 오류: {e}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 DB 초기화 및 스케줄러 등록"""
    logger.info(f"{settings.app_name} v{settings.app_version} 시작")

    # DB 테이블 생성
    await init_db()
    logger.info("데이터베이스 초기화 완료")

    # 스케줄러 등록: 30분마다 실행
    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(minutes=settings.collect_interval_minutes),
        id="news_collect_analyze",
        name="뉴스 수집 및 AI 분석",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"스케줄러 시작: {settings.collect_interval_minutes}분마다 실행")

    # 앱 시작 시 최초 1회 즉시 실행
    await scheduled_job()


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 스케줄러 정지"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info(f"{settings.app_name} 종료")


@app.get("/health", tags=["시스템"])
async def health_check():
    """헬스 체크 엔드포인트 (Docker healthcheck, 모니터링용)"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "scheduler_running": scheduler.running,
    }


@app.get("/", tags=["시스템"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"{settings.app_name} API 서버",
        "docs": "/docs",
        "version": settings.app_version,
    }
