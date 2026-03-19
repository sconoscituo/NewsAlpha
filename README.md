# NewsAlpha

> AI 뉴스 분석으로 주식 Alpha 찾기 - 수혜주/피해주 자동 추출

경제/기업 뉴스를 실시간 수집하고 Gemini AI가 주가 영향도를 분석해 수혜주/피해주를 자동으로 추출합니다.
개인 투자자가 기관보다 빠르게 정보를 파악할 수 있도록 도움을 줍니다.

## 주요 기능

- **실시간 뉴스 수집**: 한국경제, 연합뉴스, 매일경제, Bloomberg RSS 자동 수집
- **AI 분석**: Gemini AI로 뉴스별 수혜주/피해주/섹터/영향도 자동 추출
- **텔레그램 알림**: 위시리스트 종목 관련 뉴스 발생 시 즉시 알림
- **구독 모델**: 무료(하루 10개), 프리미엄(실시간 무제한 + 알림 + 위시리스트)

## 수익 구조

| 구분 | 무료 | 프리미엄 |
|------|------|---------|
| 뉴스 분석 | 하루 10개 | 실시간 무제한 |
| 텔레그램 알림 | - | O |
| 종목 위시리스트 | - | O |
| 수혜주/피해주 조회 | O | O |

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
uvicorn app.main:app --reload
```

### 4. Docker로 실행

```bash
docker-compose up -d
```

## API 문서

서버 실행 후 http://localhost:8000/docs 접속

## 환경 변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| GEMINI_API_KEY | Google Gemini API 키 | O |
| DATABASE_URL | 데이터베이스 연결 URL | O |
| SECRET_KEY | JWT 시크릿 키 | O |
| TELEGRAM_BOT_TOKEN | 텔레그램 봇 토큰 | O |
| DEBUG | 디버그 모드 | - |

## 프로젝트 구조

```
[NewsAlpha]/
├── app/
│   ├── main.py               # FastAPI 앱 + APScheduler
│   ├── config.py             # 환경 변수 설정
│   ├── database.py           # DB 연결 설정
│   ├── models/               # SQLAlchemy 모델
│   ├── schemas/              # Pydantic 스키마
│   ├── routers/              # API 라우터
│   ├── services/             # 비즈니스 로직
│   └── utils/                # 유틸리티
├── tests/                    # 테스트
└── docker-compose.yml
```
