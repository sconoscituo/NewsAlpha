"""
사용자 라우터
회원가입, 로그인, 위시리스트 관리, 텔레그램 연동 API를 제공합니다.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.news import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    WatchlistUpdate, TelegramConnect,
)
from app.utils.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user,
)

router = APIRouter(prefix="/users", tags=["사용자"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """회원가입"""
    # 이메일 중복 체크
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.flush()  # ID 할당을 위해 flush

    return _build_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """이메일/비밀번호 로그인 후 JWT 토큰 반환"""
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_my_info(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return _build_user_response(current_user)


@router.put("/watchlist", response_model=UserResponse)
async def update_watchlist(
    watchlist_data: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    위시리스트 종목 업데이트 (프리미엄 전용)
    종목코드 배열로 전체 교체합니다.
    """
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="위시리스트 기능은 프리미엄 구독자 전용입니다.",
        )

    # 종목코드 유효성 검사 (간단 체크)
    for code in watchlist_data.stocks:
        if not code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 종목코드는 허용되지 않습니다.",
            )

    current_user.set_watchlist(watchlist_data.stocks)
    return _build_user_response(current_user)


@router.post("/telegram", response_model=UserResponse)
async def connect_telegram(
    telegram_data: TelegramConnect,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    텔레그램 chat_id 연동 (프리미엄 전용)
    텔레그램 봇에서 /start 명령으로 받은 chat_id를 입력합니다.
    """
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="텔레그램 알림 기능은 프리미엄 구독자 전용입니다.",
        )

    current_user.telegram_chat_id = telegram_data.telegram_chat_id
    return _build_user_response(current_user)


@router.delete("/telegram", response_model=UserResponse)
async def disconnect_telegram(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """텔레그램 알림 연동 해제"""
    current_user.telegram_chat_id = None
    return _build_user_response(current_user)


def _build_user_response(user: User) -> UserResponse:
    """User 모델을 UserResponse 스키마로 변환합니다."""
    return UserResponse(
        id=user.id,
        email=user.email,
        is_premium=user.is_premium,
        telegram_chat_id=user.telegram_chat_id,
        watchlist=user.get_watchlist(),
        daily_usage_count=user.daily_usage_count,
        created_at=user.created_at,
    )
