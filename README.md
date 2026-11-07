Markdown
# Google Quota Checker (Gemini Multi-Account Monitor)

[English] An automated monitoring utility built with Python and Playwright to track Google Gemini usage limits, active quotas, and reset schedules across multiple accounts.

[한국어] Playwright와 Python을 기반으로 여러 구글 계정의 Gemini 사용량 한도, 잔여량, 초기화 일정을 한 번에 확인하고 실시간 알림을 제공하는 모니터링 도구입니다.

---

## 📌 Features / 주요 기능

- **Multi-Account Tracking / 다중 계정 모니터링**  
  Check usage quotas and reset schedules across multiple Google accounts in a single run.  
  (여러 구글 계정의 실시간 한도 및 초기화 시점을 일괄 조회)

- **Visual Dashboard & Alert / 시각화 게이지 및 팝업 알림**  
  Displays ASCII progress bars in the console and triggers a clean desktop summary dialog.  
  (콘솔 진행률 바 및 윈도우 시스템 요약 팝업 지원)

- **Automated Refresh Loop / 자동 갱신 루프**  
  Periodically updates quota data in the background (default: 20 mins) with manual key-press refresh.  
  (20분 주기 자동 백그라운드 갱신 및 키보드 즉시 새로고침 지원)

- **Isolated Local Sessions / 안전한 로컬 세션 분리**  
  Stores browser profile cookies locally without saving plaintext passwords.  
  (비밀번호를 저장하지 않고 로컬 브라우저 세션/쿠키만 안전하게 보존)

---

## 🛠️ Prerequisites / 요구사항

- **OS**: Windows 10 / 11
- **Python**: Python 3.10 or higher
- **Browser**: Chromium (Playwright)

---

## 📦 Installation / 설치 방법

### 1. Clone Repository / 저장소 복제
```bash
git clone [https://github.com/91hbkim-blip/Google-Quota-Checker.git](https://github.com/91hbkim-blip/Google-Quota-Checker.git)
cd Google-Quota-Checker
2. Install Python Dependencies / 파이썬 패키지 설치
Bash
pip install -r requirements.txt
3. Install Playwright Browsers / Playwright 브라우저 바이너리 설치
Bash
python -m playwright install
⚙️ Configuration & Setup / 설정 및 실행 방법
Step 1. Prepare Configuration / 설정 파일 준비
Copy config.example.json and rename it to config (or config.json). Add your account nicknames:

config.example.json 파일의 이름을 config(또는 config.json)로 변경한 뒤 조회할 계정 별칭을 등록합니다.

JSON
{
  "accounts": [
    "account_1",
    "account_2"
  ]
}
Step 2. Prepare Batch Files / 배치 파일 준비
Remove the .example extension from the batch script files:

제공된 예시 배치 파일의 .example을 지워 실행 파일로 만듭니다.

1_최초로그인_설정.example.bat ➔ 1_최초로그인_설정.bat

2_한도조회_메시지형.example.bat ➔ 2_한도조회_메시지형.bat

Step 3. Initial Login Setup / 최초 로그인 세션 저장
Run 1_최초로그인_설정.bat. A browser window will open for each account. Log in to your Google accounts, navigate to the quota screen, and press Enter in the console to save your sessions.

1_최초로그인_설정.bat을 실행해 열리는 브라우저에서 계정별로 로그인한 뒤, 콘솔 창에서 Enter를 눌러 세션을 저장합니다.

Step 4. Run Quota Checker / 한도 모니터링 실행
Run 2_한도조회_메시지형.bat to fetch usage metrics and launch the automated 20-minute refresh loop.

2_한도조회_메시지형.bat을 실행하여 실시간 사용량을 조회하고 자동 갱신 모니터링을 시작합니다.

📂 Project Structure / 프로젝트 구조
Plaintext
Google_Quota_Checker/
├── .gitignore                          # Exclude private cookies, sessions, and logs
├── requirements.txt                    # Python library dependencies
├── main.py                             # Execution entry point & CLI dashboard
├── collector.py                        # Playwright scraping & quota extraction logic
├── config.example.json                 # Sample account configuration
├── 1_최초로그인_설정.example.bat         # Login session generator template
└── 2_한도조회_메시지형.example.bat      # Monitoring execution batch template
🔒 Security & Privacy / 보안 주의사항
Never share or commit the profiles/ directory. It stores active browser session cookies that grant direct account access without passwords.

(profiles/ 폴더에는 로그인 세션 쿠키가 포함되어 있으므로 절대로 Git 저장소에 커밋하거나 공유하지 마십시오.)

Real account credentials and webhook tokens should remain in your local config file only.

(실제 계정 정보는 로컬 config 파일에만 보관하고 Git 추적에서 제외하십시오.)

📄 License / 라이선스
Distributed under the MIT License. See LICENSE for more information.
