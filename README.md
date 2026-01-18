# 🇺🇸 US Market Dashboard

미국 주식 시장 분석 대시보드 - Smart Money 추적 및 AI 기반 투자 분석

## 📊 라이브 대시보드

| 서비스 | URL |
|--------|-----|
| **🖥️ Next.js 대시보드** | [us-market-next.onrender.com](https://us-market-next.onrender.com) |
| **⚙️ Flask API 백엔드** | [us-market-dashboard-jsh.onrender.com](https://us-market-dashboard-jsh.onrender.com) |

---

## 🔄 GitHub Actions 자동 데이터 업데이트

### 📅 자동 실행 스케줄

이 프로젝트는 **GitHub Actions**를 사용하여 매일 자동으로 데이터를 업데이트합니다.

| 시간대 | 실행 시간 | 설명 |
|--------|----------|------|
| **UTC** | 09:00 | GitHub Actions 기준 시간 |
| **🇰🇷 한국 (KST)** | **18:00** | 미국장 개장 전 |
| **🇺🇸 미국 동부 (EST)** | 04:00 | 프리마켓 시작 전 |

### 🔧 워크플로우 동작 방식

```
┌─────────────────────────────────────────────────────────────┐
│  1️⃣  GitHub Actions 트리거 (매일 09:00 UTC)                 │
├─────────────────────────────────────────────────────────────┤
│  2️⃣  Python 환경 설정 및 의존성 설치                        │
├─────────────────────────────────────────────────────────────┤
│  3️⃣  데이터 수집 스크립트 실행                              │
│      • Smart Money Screener v2                              │
│      • ETF Fund Flows 분석                                  │
│      • Market Gate 데이터 수집                              │
│      • AI 분석 리포트 생성                                   │
├─────────────────────────────────────────────────────────────┤
│  4️⃣  결과 데이터 자동 커밋 & 푸시                          │
├─────────────────────────────────────────────────────────────┤
│  5️⃣  Render 자동 재배포 트리거                             │
└─────────────────────────────────────────────────────────────┘
```

### 📁 업데이트되는 파일들

| 파일 | 설명 |
|------|------|
| `data/smart_money_current.json` | Smart Money Top 10 종목 |
| `data/smart_money_picks_v2.csv` | 상세 스크리닝 결과 |
| `data/etf_flows.json` | ETF 자금 흐름 데이터 |
| `data/sp500_list.json` | S&P 500 종목 리스트 |

### 🚀 수동 실행 방법

데이터를 즉시 업데이트하고 싶다면:

1. [Actions 페이지](https://github.com/ohmylove303-eng/-/actions) 접속
2. **"Daily Data Update"** 워크플로우 선택
3. **"Run workflow"** 버튼 클릭
4. 약 6-7분 후 업데이트 완료

### 🔐 필요한 Secrets

워크플로우 실행을 위해 다음 API 키가 Repository Secrets에 등록되어 있어야 합니다:

| Secret 이름 | 용도 |
|------------|------|
| `ALPHA_VANTAGE_API_KEY` | 주가 데이터 |
| `FINNHUB_API_KEY` | 실시간 시장 데이터 |
| `FRED_API_KEY` | 경제 지표 데이터 |
| `OPENAI_API_KEY` | AI 분석 |
| `PERPLEXITY_API_KEY` | AI 검색 |
| `GOOGLE_API_KEY` | Gemini AI |

---

## 🛠️ 로컬 개발 환경

### 설치

```bash
# 저장소 클론
git clone https://github.com/ohmylove303-eng/-.git
cd -

# 가상환경 생성 & 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력
```

### 실행

```bash
# Flask 서버 실행
python flask_app.py

# 데이터 업데이트 (수동)
python scripts/update_all.py
```

---

## 📈 주요 기능

- **Smart Money Tracking**: 기관 투자자 매매 동향 분석
- **AI 투자 분석**: GPT/Gemini 기반 종목 분석
- **ETF Fund Flows**: ETF 자금 흐름 모니터링
- **Market Map**: 섹터별 시장 히트맵
- **Closing Bell**: 장 마감 전 투자 추천

---

## 📜 라이선스

MIT License

---

*마지막 업데이트: 2026-01-18*
