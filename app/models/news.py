"""
뉴스 아이템 모델
RSS 수집된 뉴스 기사를 저장합니다.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)

    # 기사 기본 정보
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False, index=True)  # 중복 방지용 인덱스
    source = Column(String(100), nullable=False)  # 예: "한국경제", "연합뉴스", "Bloomberg"

    # 기사 내용 요약 (원문이 길 경우 앞부분만 저장)
    content_summary = Column(Text, nullable=True)

    # 발행 시각 (RSS에서 파싱한 원본 시각)
    published_at = Column(DateTime, nullable=True)

    # 수집 시각 (우리 시스템이 저장한 시각)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # AI 분석 완료 여부
    is_analyzed = Column(Integer, default=0, nullable=False)  # 0: 미분석, 1: 분석완료, 2: 분석실패

    # 알파 시그널 (1:1 관계)
    alpha_signal = relationship("AlphaSignal", back_populates="news_item", uselist=False)

    # 복합 인덱스: 최신 뉴스 조회 최적화
    __table_args__ = (
        Index("idx_news_source_published", "source", "published_at"),
        Index("idx_news_collected", "collected_at"),
    )

    def __repr__(self) -> str:
        return f"<NewsItem id={self.id} source={self.source} title={self.title[:30]}>"
