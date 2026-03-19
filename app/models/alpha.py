"""
알파 시그널 모델
Gemini AI가 분석한 수혜주/피해주 정보를 저장합니다.
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class AlphaSignal(Base):
    __tablename__ = "alpha_signals"

    id = Column(Integer, primary_key=True, index=True)

    # 연결된 뉴스 (FK)
    news_id = Column(Integer, ForeignKey("news_items.id"), nullable=False, index=True)
    news_item = relationship("NewsItem", back_populates="alpha_signal")

    # 수혜주 목록 (JSON 배열: [{"code": "005930", "name": "삼성전자", "reason": "..."}])
    beneficiary_stocks_json = Column(Text, default="[]", nullable=False)

    # 피해주 목록 (JSON 배열: 동일 구조)
    victim_stocks_json = Column(Text, default="[]", nullable=False)

    # 주가 영향 점수 (-10 ~ +10, 양수=긍정, 음수=부정)
    impact_score = Column(Float, default=0.0, nullable=False)

    # 영향 이유 (Gemini 분석 요약)
    impact_reason = Column(Text, nullable=True)

    # 섹터 분류 (예: "반도체", "바이오", "에너지")
    sector = Column(String(100), nullable=True)

    # 분석 생성 시각
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def get_beneficiary_stocks(self) -> list[dict]:
        """수혜주 JSON을 파이썬 리스트로 반환"""
        try:
            return json.loads(self.beneficiary_stocks_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def get_victim_stocks(self) -> list[dict]:
        """피해주 JSON을 파이썬 리스트로 반환"""
        try:
            return json.loads(self.victim_stocks_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def set_beneficiary_stocks(self, stocks: list[dict]) -> None:
        """수혜주 리스트를 JSON 문자열로 저장"""
        self.beneficiary_stocks_json = json.dumps(stocks, ensure_ascii=False)

    def set_victim_stocks(self, stocks: list[dict]) -> None:
        """피해주 리스트를 JSON 문자열로 저장"""
        self.victim_stocks_json = json.dumps(stocks, ensure_ascii=False)

    def all_stock_codes(self) -> list[str]:
        """수혜주 + 피해주 종목코드 전체 반환 (알림 매칭용)"""
        beneficiaries = [s.get("code", "") for s in self.get_beneficiary_stocks()]
        victims = [s.get("code", "") for s in self.get_victim_stocks()]
        return [c for c in beneficiaries + victims if c]

    def __repr__(self) -> str:
        return f"<AlphaSignal id={self.id} news_id={self.news_id} score={self.impact_score}>"
