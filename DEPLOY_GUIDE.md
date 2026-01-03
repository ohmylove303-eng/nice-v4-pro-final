# 🚀 US Market Dashboard 배포 & 자동화 가이드 (V2)

이 가이드는 사용자님의 PC에 있는 주식 분석 시스템을 **"24시간 살아있는 클라우드 서버"**로 만드는 전체 과정을 담고 있습니다.

---

## 🏗️ 1단계: GitHub에 코드 저장하기
먼저 코드를 인터넷 저장소(GitHub)로 옮겨야 합니다.

1. **GitHub 로그인:** [github.com](https://github.com) 접속.
2. **새 저장소 생성:** 
   - 우측 상단 `+` 버튼 -> **New repository** 클릭.
   - **Repository name:** `us-market-dashboard` 입력.
   - **Public** 체크 (무료 배포를 위해 Public 추천).
   - **Create repository** 클릭.
3. **코드 업로드 (터미널 명령어):**
   사용자님의 PC 터미널(VS Code 하단)에서 아래 명령어를 한 줄씩 복사해서 실행하세요.
   ```bash
   git init
   git add .
   git commit -m "첫 배포: 월스트리트 시스템 가동"
   git branch -M main
   # 아래 주소는 사용자님 ID로 바꿔야 합니다! (GitHub 화면에 보이는 주소 복사)
   git remote add origin https://github.com/사용자ID/us-market-dashboard.git
   git push -u origin main
   ```

---

## 🏛️ 2단계: Render에 배포하기 (무료 서버)
GitHub에 있는 코드를 서버로 띄우는 과정입니다.

1. **Render 접속:** [dashboard.render.com](https://dashboard.render.com) 로그인 (GitHub 계정 연동 추천).
2. **새 웹 서비스 생성:**
   - 우측 상단 **New +** -> **Web Service** 클릭.
   - **Build and deploy from a Git repository** 선택 -> **Next** 클릭.
   - 방금 올린 `us-market-dashboard` 옆의 **Connect** 클릭.
3. **설정값 입력 (중요!):**
   - **Name:** `my-stock-dashboard` (원하는 이름)
   - **Region:** `Singapore` (한국과 가까움) 또는 `Oregon` (미국).
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn flask_app:app`
   - **Plan:** **Free** 선택.
4. **환경 변수 설정 (Environment Variables):**
   - 화면 아래쪽 **Advanced** 버튼이나 **Environment Variables** 탭을 찾으세요.
   - **Add Environment Variable** 클릭.
     - Key: `GOOGLE_API_KEY`
     - Value: `(사용자님의 Gemini API 키 붙여넣기)`
     - Key: `DATA_DIR`
     - Value: `./data`
   - **Create Web Service** 클릭!
   
   👉 약 3~5분 뒤 배포가 완료되면 상단에 `https://my-stock-dashboard.onrender.com` 주소가 생깁니다. 접속해보세요!

---

## ⚙️ 3단계: 매일 아침 자동 업데이트 (GitHub Secrets) 🌟
**"매일 아침 7시, 자율 주행 모드"**를 켜는 핵심 단계입니다.

1. **GitHub 저장소로 돌아가기:** [github.com/사용자ID/us-market-dashboard](https://github.com)
2. **설정 메뉴 진입:** 상단 메뉴 탭에서 **Settings(⚙️)** 클릭.
3. **Secrets 메뉴 찾기:**
   - 왼쪽 사이드바 메뉴를 아래로 스크롤.
   - **Security** 항목 아래 **Secrets and variables** 클릭 -> **Actions** 선택.
4. **API 키 등록:**
   - 우측 상단 초록색 버튼 **[New repository secret]** 클릭.
   - **입력:**
     - **Name:** `GOOGLE_API_KEY`
     - **Secret:** `(Gemini API 키 붙여넣기)`
   - **Add secret** 버튼 클릭.
   - (선택) `FRED_API_KEY`도 있다면 똑같이 추가.
   
✅ **끝났습니다!**
이제 매일 한국 시간 오전 7시, GitHub Actions가 깨어나서:
1. 최신 주가를 크롤링하고,
2. AI가 시장을 분석하고,
3. 결과(JSON)를 저장소에 커밋하면,
4. Render가 이를 감지하고 서버를 최신 상태로 업데이트합니다.

즐거운 투자 되십시오.
