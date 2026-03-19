"""
사용자 모델
회원 정보, 프리미엄 여부, 텔레그램 연동, 위시리스트를 관리합니다.
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 기본 인증 정보
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # 프리미엄 구독 여부
    is_premium = Column(Boolean, default=False, nullable=False)

    # 텔레그램 연동 (프리미엄 전용 알림)
    telegram_chat_id = Column(String(50), nullable=True)

    # 위시리스트 (JSON 배열로 종목코드 저장, 예: ["005930", "000660"])
    watchlist_json = Column(Text, default="[]", nullable=False)

    # 오늘 사용한 무료 분석 횟수 (일일 초기화)
    daily_usage_count = Column(Integer, default=0, nullable=False)
    daily_usage_reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 계정 상태
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def get_watchlist(self) -> list[str]:
        """위시리스트 JSON을 파이썬 리스트로 반환"""
        try:
            return json.loads(self.watchlist_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_watchlist(self, stocks: list[str]) -> None:
        """위시리스트를 JSON 문자열로 저장"""
        self.watchlist_json = json.dumps(stocks, ensure_ascii=False)

    def can_use_today(self, free_limit: int) -> bool:
        """오늘 무료 사용 한도를 초과하지 않았는지 확인"""
        if self.is_premium:
            return True
        # 날짜가 바뀌었으면 카운트 초기화
        now = datetime.utcnow()
        if self.daily_usage_reset_at.date() < now.date():
            self.daily_usage_count = 0
            self.daily_usage_reset_at = now
        return self.daily_usage_count < free_limit

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} premium={self.is_premium}>"
