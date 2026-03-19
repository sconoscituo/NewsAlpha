"""
NewsAlpha 기본 통합 테스트
헬스 체크, 회원가입/로그인, 뉴스 조회 흐름을 검증합니다.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db
from app.config import get_settings

# 테스트용 인메모리 SQLite DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """테스트용 DB 세션 오버라이드"""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """각 테스트 전 테이블 생성, 후 삭제"""
    from app.models import user, news, alpha  # noqa: F401
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    """비동기 테스트 클라이언트"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """헬스 체크 엔드포인트가 200을 반환해야 합니다."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "NewsAlpha"


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """루트 엔드포인트가 앱 정보를 반환해야 합니다."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "NewsAlpha" in response.json()["message"]


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    """회원가입 후 로그인이 정상 작동해야 합니다."""
    # 회원가입
    reg_response = await client.post(
        "/users/register",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == "test@example.com"
    assert user_data["is_premium"] is False

    # 로그인
    login_response = await client.post(
        "/users/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """중복 이메일 가입은 400을 반환해야 합니다."""
    payload = {"email": "dup@example.com", "password": "pass123"}
    await client.post("/users/register", json=payload)
    response = await client.post("/users/register", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """잘못된 비밀번호 로그인은 401을 반환해야 합니다."""
    await client.post(
        "/users/register",
        json={"email": "user@example.com", "password": "correct"},
    )
    response = await client.post(
        "/users/login",
        json={"email": "user@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    """인증된 사용자 정보 조회가 정상 작동해야 합니다."""
    await client.post(
        "/users/register",
        json={"email": "me@example.com", "password": "mypass123"},
    )
    login = await client.post(
        "/users/login",
        json={"email": "me@example.com", "password": "mypass123"},
    )
    token = login.json()["access_token"]

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_news_list_requires_auth(client: AsyncClient):
    """인증 없이 뉴스 조회는 401을 반환해야 합니다."""
    response = await client.get("/news/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_watchlist_requires_premium(client: AsyncClient):
    """일반 사용자의 위시리스트 업데이트는 403을 반환해야 합니다."""
    await client.post(
        "/users/register",
        json={"email": "free@example.com", "password": "pass123"},
    )
    login = await client.post(
        "/users/login",
        json={"email": "free@example.com", "password": "pass123"},
    )
    token = login.json()["access_token"]

    response = await client.put(
        "/users/watchlist",
        json={"stocks": ["005930"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
