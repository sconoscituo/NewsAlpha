"""
뉴스 및 알파 시그널 Pydantic 스키마
API 요청/응답 직렬화에 사용합니다.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class StockInfo(BaseModel):
    """수혜주/피해주 개별 종목 정보"""
    code: str           # 종목코드 (예: "005930")
    name: str           # 종목명 (예: "삼성전자")
    reason: str         # 영향 이유


class AlphaSignalResponse(BaseModel):
    """알파 시그널 응답 스키마"""
    id: int
    news_id: int
    beneficiary_stocks: list[StockInfo]   # 수혜주 목록
    victim_stocks: list[StockInfo]         # 피해주 목록
    impact_score: float                    # -10 ~ +10
    impact_reason: Optional[str]
    sector: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NewsResponse(BaseModel):
    """뉴스 아이템 응답 스키마"""
    id: int
    title: str
    url: str
    source: str
    content_summary: Optional[str]
    published_at: Optional[datetime]
    collected_at: datetime
    is_analyzed: int                        # 0: 미분석, 1: 완료, 2: 실패
    alpha_signal: Optional[AlphaSignalResponse] = None

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    """뉴스 목록 페이지네이션 응답"""
    total: int
    page: int
    size: int
    items: list[NewsResponse]


class WatchlistUpdate(BaseModel):
    """위시리스트 업데이트 요청 스키마"""
    stocks: list[str]   # 종목코드 배열 (예: ["005930", "000660"])


class UserCreate(BaseModel):
    """회원가입 요청 스키마"""
    email: str
    password: str


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    email: str
    password: str


class UserResponse(BaseModel):
    """사용자 정보 응답 스키마"""
    id: int
    email: str
    is_premium: bool
    telegram_chat_id: Optional[str]
    watchlist: list[str]
    daily_usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT 토큰 응답 스키마"""
    access_token: str
    token_type: str = "bearer"


class TelegramConnect(BaseModel):
    """텔레그램 chat_id 연동 요청"""
    telegram_chat_id: str
