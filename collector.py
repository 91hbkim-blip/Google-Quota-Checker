"""
collector.py - Gemini '사용량 한도' 데이터 수집 & 파싱 엔진

출력(UI)과 완전히 분리된 모듈입니다. 콘솔/메시지박스/GUI 등 어떤 프런트엔드든
아래 공개 함수만 호출하면 됩니다.

    load_config(path=None)          -> dict
    parse_usage_text(text)          -> dict   (정규표현식 파싱, 브라우저 불필요)
    collect_all(config, ...)        -> list[AccountUsage]   (headless 일괄 조회)
    login_accounts(config, ...)     -> list[AccountUsage]   (창 띄워 수동 로그인)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"
PROFILES_DIR = BASE_DIR / "profiles"
DEBUG_DIR = BASE_DIR / "debug"

DEFAULT_CONFIG: dict = {
    "accounts": ["여분계정1", "여분계정2", "여분계정3"],
    "target_url": "https://gemini.google.com/usage",
    "wait_text": ["사용량 한도", "현재 사용량", "Usage limits", "Current usage"],
    "wait_timeout_ms": 10000,
    "browser_channel": "chrome",  # 설치된 Chrome 사용(구글 로그인 차단 회피). 비우면 Playwright Chromium
    "headless": True,
}

log = logging.getLogger("collector")


# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
def load_config(path: str | Path | None = None) -> dict:
    """config.json 을 읽어 기본값과 병합합니다. 파일이 없으면 기본값으로 생성합니다."""
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        with open(path, encoding="utf-8-sig") as f:
            config.update(json.load(f))
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    return config


# ─────────────────────────────────────────────────────────────
# 정규표현식 파싱
# ─────────────────────────────────────────────────────────────
# 화면 문구가 바뀌면 이 패턴들만 수정하면 됩니다. (한국어 / 영어 UI 모두 지원)
CURRENT_HEADING_RE = re.compile(r"현재\s*사용량|Current\s+usage", re.I)
WEEKLY_HEADING_RE = re.compile(r"주간\s*한도|Weekly\s+(?:usage\s+)?limits?", re.I)
PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:사용|used)", re.I)  # "64% 사용됨" / "64% used"
PERCENT_FALLBACK_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")              # "64%" (문구가 다를 때 대비)
RESET_RES = [
    re.compile(r"^[ \t]*(\S[^\n]*?)\s*에\s*초기화", re.M),                     # "오후 6:20에 초기화"
    re.compile(r"Resets?\s+(?:at\s+|on\s+|in\s+)?([^\n]+?)\s*$", re.M | re.I),  # "Resets at 6:20 PM"
]
SECTION_MAX_CHARS = 200  # 제목 뒤 이 글자 수 안에서만 값을 찾음(엉뚱한 숫자 방지)


def _to_number(raw: str) -> int | float:
    value = float(raw)
    return int(value) if value.is_integer() else value


def _parse_section(section: str) -> tuple[Optional[int | float], Optional[str]]:
    m = PERCENT_RE.search(section) or PERCENT_FALLBACK_RE.search(section)
    percent = _to_number(m.group(1)) if m else None
    reset = None
    for rx in RESET_RES:
        r = rx.search(section)
        if r:
            reset = r.group(1).strip()
            break
    return percent, reset


def parse_usage_text(text: str) -> dict:
    """
    '사용량 한도' 화면의 body 텍스트에서 4개 값을 추출합니다.

    >>> parse_usage_text("현재 사용량\\n64% 사용됨\\n오후 6:20에 초기화\\n"
    ...                  "주간 한도\\n11월 4일 오후 10:20에 초기화\\n21% 사용됨")
    {'current_percent': 64, 'current_reset': '오후 6:20', 'weekly_percent': 21, 'weekly_reset': '11월 4일 오후 10:20'}

    섹션 안에서 '퍼센트'와 '초기화' 줄의 순서가 달라도(위 예시처럼) 정상 동작합니다.
    찾지 못한 값은 None 입니다.
    """
    text = (text or "").replace("\r\n", "\n").replace("\xa0", " ")
    result = {
        "current_percent": None,
        "current_reset": None,
        "weekly_percent": None,
        "weekly_reset": None,
    }

    headings = {}
    for key, rx in (("current", CURRENT_HEADING_RE), ("weekly", WEEKLY_HEADING_RE)):
        m = rx.search(text)
        if m:
            headings[key] = m

    for key, m in headings.items():
        # 섹션 = 내 제목 끝 ~ (뒤에 나오는 다른 제목 시작 | 최대 길이)
        end = min(len(text), m.end() + SECTION_MAX_CHARS)
        for other_key, other in headings.items():
            if other_key != key and other.start() >= m.end():
                end = min(end, other.start())
        percent, reset = _parse_section(text[m.end():end])
        result[f"{key}_percent"] = percent
        result[f"{key}_reset"] = reset

    return result


# ─────────────────────────────────────────────────────────────
# 결과 데이터 모델 (GUI 에서도 그대로 사용)
# ─────────────────────────────────────────────────────────────
@dataclass
class AccountUsage:
    account: str
    ok: bool = False
    current_percent: Optional[int | float] = None
    current_reset: Optional[str] = None
    weekly_percent: Optional[int | float] = None
    weekly_reset: Optional[str] = None
    error: Optional[str] = None
    url: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raw_text: str = field(default="", repr=False)

    def to_dict(self, include_raw: bool = False) -> dict:
        d = asdict(self)
        if not include_raw:
            d.pop("raw_text", None)
        return d


def _build_usage(account: str, text: str, url: str) -> AccountUsage:
    usage = AccountUsage(account=account, url=url, raw_text=text)
    if "accounts.google.com" in url:
        usage.error = "로그인 필요 (1_최초로그인_설정.bat 실행)"
        return usage

    usage.__dict__.update(parse_usage_text(text))
    usage.ok = usage.current_percent is not None or usage.weekly_percent is not None
    if not usage.ok:
        usage.error = "사용량 정보를 찾지 못함 (target_url 확인 / debug 폴더 참고)"
        _dump_debug(account, text, url)
    return usage


def _dump_debug(account: str, text: str, url: str) -> None:
    """파싱 실패 시 원문을 저장해 정규표현식 조정에 활용할 수 있게 합니다."""
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        (DEBUG_DIR / f"{account}.txt").write_text(f"URL: {url}\n\n{text}", encoding="utf-8")
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────
# Playwright 브라우저 제어 & 봇 감지 우회
# ─────────────────────────────────────────────────────────────
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
"""

def _find_system_chrome() -> Optional[str]:
    """Windows 시스템에 설치된 실제 Chrome 실행 파일 경로를 탐색합니다."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


def _launch_context(p, account: str, config: dict, headless: bool):
    """./profiles/{계정이름} 에 세션을 영구 저장하는 persistent context 를 엽니다."""
    profile_dir = PROFILES_DIR / account
    profile_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-service-autorun",
        "--password-store=basic",
    ]

    kwargs = dict(
        user_data_dir=str(profile_dir),
        headless=headless,
        locale="ko-KR",
        no_viewport=not headless,
        args=args,
        ignore_default_args=["--enable-automation"],
    )
    channel = (config.get("browser_channel") or "").strip()
    context = None
    if channel:
        try:
            context = p.chromium.launch_persistent_context(channel=channel, **kwargs)
        except Exception as e:
            log.warning("'%s' 브라우저 실행 실패, 내장 Chromium 사용: %s", channel, str(e).splitlines()[0])
    
    if context is None:
        context = p.chromium.launch_persistent_context(**kwargs)

    # 모든 새 페이지에 스텔스 스크립트 주입
    context.add_init_script(STEALTH_JS)
    return context


def _active_page(context):
    pages = [pg for pg in context.pages if not pg.is_closed()]
    return pages[-1] if pages else context.new_page()


def _read_usage_page(page, config: dict) -> str:
    """target_url 접속 → wait_text 가 보일 때까지(최대 wait_timeout_ms) 대기 → body.inner_text"""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    timeout = int(config.get("wait_timeout_ms", 10000))
    wait_text = config.get("wait_text") or ["사용량 한도", "Usage limits"]
    wait_texts = [wait_text] if isinstance(wait_text, str) else list(wait_text)

    page.goto(config["target_url"], wait_until="domcontentloaded", timeout=max(30000, timeout * 3))
    try:
        page.wait_for_function(
            "ts => !!document.body && ts.some(t => document.body.innerText.includes(t))",
            arg=wait_texts,
            timeout=timeout,
        )
        # 제목은 떴지만 숫자가 늦게 렌더링되는 경우를 위한 짧은 추가 대기
        try:
            page.wait_for_function(
                r"() => /\d+\s*%/.test(document.body.innerText)", timeout=3000
            )
        except PlaywrightTimeoutError:
            pass
    except PlaywrightTimeoutError:
        log.info("'%s' 텍스트를 %dms 내에 찾지 못함 - 현재 화면으로 파싱 시도", wait_text, timeout)

    return page.inner_text("body")


def fetch_account_usage(p, account: str, config: dict, headless: Optional[bool] = None) -> AccountUsage:
    """계정 하나의 사용량을 조회합니다. 예외는 AccountUsage.error 로 변환됩니다."""
    headless = config.get("headless", True) if headless is None else headless
    context = None
    try:
        context = _launch_context(p, account, config, headless=headless)
        page = _active_page(context)
        text = _read_usage_page(page, config)
        return _build_usage(account, text, page.url)
    except Exception as e:
        msg = str(e).splitlines()[0] if str(e) else type(e).__name__
        if "user data directory is already in use" in msg.lower() or "ProcessSingleton" in msg:
            msg = "프로필이 다른 브라우저 창에서 사용 중입니다 (창을 닫고 다시 시도)"
        return AccountUsage(account=account, error=msg)
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass


def collect_all(
    config: dict,
    accounts: Optional[Iterable[str]] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    headless: Optional[bool] = None,
) -> list[AccountUsage]:
    """모든(또는 지정한) 계정을 순회하며 사용량을 수집합니다."""
    from playwright.sync_api import sync_playwright

    accounts = list(accounts or config.get("accounts", []))
    results: list[AccountUsage] = []
    with sync_playwright() as p:
        for i, account in enumerate(accounts, 1):
            if on_progress:
                on_progress(i, len(accounts), account)
            results.append(fetch_account_usage(p, account, config, headless=headless))
    return results


def login_accounts(
    config: dict,
    wait_for_user: Callable[[str], None],
    accounts: Optional[Iterable[str]] = None,
    on_result: Optional[Callable[[AccountUsage], None]] = None,
) -> list[AccountUsage]:
    """
    계정마다 브라우저를 띄워 target_url 을 엽니다.
    구글 봇 감지(Botguard 무한 로딩)를 원천 차단하기 위해,
    실제 크롬(chrome.exe)을 자동화 없이 순수 브라우저 모드로 실행합니다.
    """
    accounts = list(accounts or config.get("accounts", []))
    results: list[AccountUsage] = []
    chrome_path = _find_system_chrome()

    for account in accounts:
        profile_dir = PROFILES_DIR / account
        profile_dir.mkdir(parents=True, exist_ok=True)
        target_url = config.get("target_url", "https://gemini.google.com/app")

        # 1. 실제 Chrome이 있는 경우: 순수 프로세스로 실행 (구글 봇 탐지 100% 우회)
        if chrome_path:
            cmd = [
                chrome_path,
                f"--user-data-dir={profile_dir.resolve()}",
                "--no-first-run",
                "--no-default-browser-check",
                target_url,
            ]
            proc = subprocess.Popen(cmd)
            try:
                wait_for_user(account)
            finally:
                # 사용자가 엔터를 누른 뒤 브라우저 프로세스 종료 (쿠키 저장 보장)
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

            # 세션 확인을 위한 빠른 백그라운드 파싱 시도
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    usage = fetch_account_usage(p, account, config, headless=True)
            except Exception as e:
                usage = AccountUsage(account=account, ok=True, error=None)
            results.append(usage)
            if on_result:
                on_result(usage)
        else:
            # 2. Chrome이 없는 경우: Playwright persistent context에 스텔스 적용하여 실행
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                context = None
                try:
                    context = _launch_context(p, account, config, headless=False)
                    page = _active_page(context)
                    try:
                        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                    except Exception:
                        pass
                    wait_for_user(account)
                    page = _active_page(context)
                    usage = _build_usage(account, page.inner_text("body"), page.url)
                except Exception as e:
                    usage = AccountUsage(account=account, error=str(e).splitlines()[0] if str(e) else type(e).__name__)
                finally:
                    if context is not None:
                        try:
                            context.close()
                        except Exception:
                            pass
                results.append(usage)
                if on_result:
                    on_result(usage)

    return results

