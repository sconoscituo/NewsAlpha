"""
환경 변수 설정 모듈
pydantic-settings를 사용해 .env 파일에서 설정값을 로드합니다.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini AI 설정
    gemini_api_key: str = ""

    # 데이터베이스 설정
    database_url: str = "sqlite+aiosqlite:///./newsalpha.db"

    # JWT 설정
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24시간

    # 텔레그램 봇 설정
    telegram_bot_token: str = ""

    # 앱 설정
    debug: bool = True
    app_name: str = "NewsAlpha"
    app_version: str = "1.0.0"

    # 뉴스 수집 설정
    collect_interval_minutes: int = 30  # 30분마다 수집

    # 무료 사용자 일일 한도
    free_daily_limit: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글턴 반환 (캐싱으로 재사용)"""
    return Settings()
