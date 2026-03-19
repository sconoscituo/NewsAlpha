"""
데이터베이스 연결 및 세션 관리
SQLAlchemy 비동기 엔진을 사용합니다.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# 비동기 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 디버그 모드에서 SQL 로그 출력
    future=True,
)

# 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """모든 모델의 기반 클래스"""
    pass


async def init_db() -> None:
    """앱 시작 시 테이블 생성"""
    # 모든 모델을 임포트해야 테이블이 생성됨
    from app.models import user, news, alpha  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI 의존성 주입용 DB 세션 제공"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
