# NewsAlpha - AI 뉴스 분석 서비스

## 필요한 API 키 및 환경변수

| 환경변수 | 설명 | 발급 URL |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini AI API 키 (뉴스 요약/분석용) | https://aistudio.google.com/app/apikey |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 (알림 전송용) | https://t.me/BotFather |
| `SECRET_KEY` | JWT 토큰 서명용 시크릿 키 (임의 문자열) | - |
| `DATABASE_URL` | 데이터베이스 연결 URL (기본: SQLite) | - |
| `COLLECT_INTERVAL_MINUTES` | 뉴스 수집 주기 (분, 기본: `30`) | - |
| `FREE_DAILY_LIMIT` | 무료 사용자 일일 뉴스 조회 한도 (기본: `10`) | - |

## GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|---|---|
| `GEMINI_API_KEY` | Gemini API 키 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `SECRET_KEY` | JWT 시크릿 키 (랜덤 32자 이상 문자열) |

## 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/sconoscituo/NewsAlpha.git
cd NewsAlpha

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 아래 항목 입력:
# GEMINI_API_KEY=your_gemini_api_key
# SECRET_KEY=your_random_secret_key
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token (알림 기능 사용 시)

# 5. 서버 실행
uvicorn app.main:app --reload
```

서버 기동 후 http://localhost:8000/docs 에서 API 문서를 확인할 수 있습니다.

## Docker로 실행

```bash
docker-compose up --build
```

## 텔레그램 봇 설정 방법

1. 텔레그램에서 `@BotFather`를 검색합니다.
2. `/newbot` 명령어로 새 봇을 생성합니다.
3. 봇 이름과 사용자명을 설정하면 토큰이 발급됩니다.
4. 발급된 토큰을 `TELEGRAM_BOT_TOKEN` 환경변수에 입력합니다.

## 주요 기능 사용법

### 뉴스 자동 수집
- `feedparser`를 사용해 RSS 피드에서 뉴스를 자동으로 수집합니다.
- 수집 주기: 기본 30분 (`COLLECT_INTERVAL_MINUTES` 설정 가능)

### AI 뉴스 요약/분석
- Gemini AI가 수집된 뉴스를 요약하고 핵심 인사이트를 추출합니다.
- 무료 사용자: 일일 10건 조회 제한
- 프리미엄 사용자: 무제한 조회

### 텔레그램 알림
- 관심 키워드가 포함된 뉴스가 수집되면 텔레그램으로 즉시 알림을 전송합니다.
- `aiosmtplib`을 사용한 이메일 알림도 지원합니다.

### 인증
- JWT 기반 인증 (토큰 유효기간: 24시간)
- `/api/auth/register` - 회원가입
- `/api/auth/login` - 로그인 및 토큰 발급

## 프로젝트 구조

```
NewsAlpha/
├── app/
│   ├── config.py       # 환경변수 설정
│   ├── database.py     # DB 연결 관리
│   ├── main.py         # FastAPI 앱 진입점
│   ├── models/         # SQLAlchemy 모델
│   ├── routers/        # API 라우터
│   ├── schemas/        # Pydantic 스키마
│   ├── services/       # 뉴스 수집/분석 서비스
│   └── utils/          # 유틸리티 함수
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
