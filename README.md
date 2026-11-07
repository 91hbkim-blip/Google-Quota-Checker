# Google Quota Checker (Gemini Multi-Account Monitor)

[English] An automated tool built with Python and Playwright to monitor Google Gemini usage quotas, reset schedules, and limits across multiple accounts simultaneously.

[한국어] Playwright와 Python 기반으로 여러 구글 계정의 Gemini 사용량 한도, 잔여량, 초기화 일정을 한눈에 모니터링하고 알림을 제공하는 자동화 도구입니다.

---

## 📌 Features / 주요 기능

- **Multi-Account Monitoring / 다중 계정 조회**: Check usage and limits across multiple Google accounts in a single run. (여러 구글 계정의 사용 현황을 한 번에 확인)
- **Visual Progress & Alerts / 시각적 게이지 및 알림**: Displays ASCII progress bars in console and triggers a summary desktop alert. (콘솔 진행률 바 및 윈도우 팝업 요약 창 지원)
- **Auto-Refresh Loop / 자동 갱신**: Periodically refreshes quotas in background with keyboard refresh support. (백그라운드 20분 주기 자동 갱신 및 즉시 새로고침 지원)
- **Persistent Sessions / 안전한 세션 관리**: Retains browser login states locally without hardcoding passwords. (비밀번호 저장 없이 브라우저 쿠키/세션을 로컬에 안전하게 보존)

---

## 🛠️ Prerequisites / 필수 요구사항

- Python 3.10+
- Google Chrome / Chromium (Playwright)

---

## 📦 Installation / 설치 방법

1. **Clone the repository / 저장소 복제**
   ```bash
   git clone [https://github.com/91hbkim-blip/Google-Quota-Checker.git](https://github.com/91hbkim-blip/Google-Quota-Checker.git)
   cd Google-Quota-Checker
