"""
main.py - Gemini 사용량 한도 '메시지형' 조회기 (콘솔 게이지 + 윈도우 메시지 박스)

    python main.py                 # 모든 계정 조회 → 콘솔 출력 + 요약 알림창
    python main.py --login         # 계정별 브라우저 창을 띄워 로그인 세션 저장
    python main.py --account 여분계정1 --no-popup
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import unicodedata
from datetime import datetime

import collector
from collector import AccountUsage

BAR_WIDTH = 10
LINE_WIDTH = 64


# ─────────────────────────────────────────────────────────────
# 콘솔 유틸
# ─────────────────────────────────────────────────────────────
def setup_console() -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def disp_width(s: str) -> int:
    """한글(전각) 문자는 2칸으로 계산한 화면 표시 폭."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s: str, width: int) -> str:
    return s + " " * max(0, width - disp_width(s))


# ─────────────────────────────────────────────────────────────
# 포맷터 (GUI 버전에서도 재사용 가능)
# ─────────────────────────────────────────────────────────────
def gauge(percent, width: int = BAR_WIDTH) -> str:
    """64 → '[██████░░░░]'"""
    if percent is None:
        return "[" + "?" * width + "]"
    p = max(0.0, min(100.0, float(percent)))
    filled = int(round(p / 100 * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def fmt_pct(percent) -> str:
    if percent is None:
        return "  --"
    if float(percent).is_integer():
        return f"{int(percent):>3}%"
    return f"{float(percent):>5.1f}%"


def metric_line(label: str, percent, reset) -> str:
    reset_txt = f"초기화: {reset}" if reset else "초기화: -"
    return f"    {pad(label, 13)}{gauge(percent)} {fmt_pct(percent)}   {reset_txt}"


def print_report(results: list[AccountUsage]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print()
    print("=" * LINE_WIDTH)
    print(f"  Gemini 사용량 한도 조회   ({now})")
    print("=" * LINE_WIDTH)
    for r in results:
        print(f"  [{r.account}]")
        if r.ok:
            print(metric_line("현재 사용량", r.current_percent, r.current_reset))
            print(metric_line("주간 한도", r.weekly_percent, r.weekly_reset))
        else:
            print(f"    ✖ {r.error}")
        print("-" * LINE_WIDTH)
    ok = sum(1 for r in results if r.ok)
    print(f"  조회 성공 {ok}/{len(results)}개 계정")
    print()


def build_summary(results: list[AccountUsage]) -> str:
    lines = []
    for r in results:
        lines.append(f"■ {r.account}")
        if r.ok:
            lines.append(f"   현재  {gauge(r.current_percent)} {fmt_pct(r.current_percent).strip()}"
                         f"   ({r.current_reset or '-'} 초기화)")
            lines.append(f"   주간  {gauge(r.weekly_percent)} {fmt_pct(r.weekly_percent).strip()}"
                         f"   ({r.weekly_reset or '-'} 초기화)")
        else:
            lines.append(f"   ✖ {r.error}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ─────────────────────────────────────────────────────────────
# 메시지 박스
# ─────────────────────────────────────────────────────────────
def show_message_box(title: str, text: str, warning: bool = False) -> None:
    if os.name == "nt":
        try:
            import ctypes
            MB_OK, MB_ICONINFO, MB_ICONWARN = 0x0, 0x40, 0x30
            MB_SETFOREGROUND, MB_TOPMOST = 0x10000, 0x40000
            flags = MB_OK | (MB_ICONWARN if warning else MB_ICONINFO) | MB_SETFOREGROUND | MB_TOPMOST
            ctypes.windll.user32.MessageBoxW(None, text, title, flags)
            return
        except Exception:
            pass
    try:  # 비 Windows 환경 대비
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        (messagebox.showwarning if warning else messagebox.showinfo)(title, text, parent=root)
        root.destroy()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 실행 모드
# ─────────────────────────────────────────────────────────────
def run_login(config: dict, accounts: list[str]) -> int:
    print()
    print("=" * LINE_WIDTH)
    print("  최초 로그인 설정")
    print("=" * LINE_WIDTH)
    print("  계정마다 브라우저 창이 열립니다.")
    print("  1) 해당 구글 계정으로 로그인")
    print("  2) '사용량 한도' 화면이 보이는지 확인")
    print("  3) 이 콘솔 창으로 돌아와 Enter → 세션 저장 후 다음 계정으로 이동")
    print(f"  대상 URL: {config['target_url']}")
    print("-" * LINE_WIDTH)

    def wait_for_user(account: str) -> None:
        input(f"\n  ▶ [{account}] 로그인/화면 확인 후 Enter를 누르세요... ")

    def on_result(r: AccountUsage) -> None:
        if r.ok:
            print(f"  ✔ [{r.account}] 세션 저장 완료 - 미리보기:")
            print(metric_line("현재 사용량", r.current_percent, r.current_reset))
            print(metric_line("주간 한도", r.weekly_percent, r.weekly_reset))
        else:
            print(f"  ✔ [{r.account}] 세션 저장 완료 (미리보기 파싱 실패: {r.error})")

    collector.login_accounts(config, wait_for_user, accounts=accounts, on_result=on_result)
    print("\n  모든 계정 설정이 끝났습니다. 이제 2_한도조회_메시지형.bat 을 실행하세요.\n")
    return 0


def run_check(config: dict, accounts: list[str], popup: bool, show_browser: bool) -> int:
    def on_progress(i: int, total: int, account: str) -> None:
        print(f"  ({i}/{total}) {account} 조회 중...", flush=True)

    print()
    results = collector.collect_all(
        config,
        accounts=accounts,
        on_progress=on_progress,
        headless=False if show_browser else None,
    )
    print_report(results)

    if popup:
        has_error = any(not r.ok for r in results)
        show_message_box("Gemini 사용량 한도 요약", build_summary(results), warning=has_error)
    return 0 if all(r.ok for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    setup_console()
    logging.basicConfig(level=logging.WARNING, format="  [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Gemini 사용량 한도 메시지형 조회기")
    parser.add_argument("--login", action="store_true", help="브라우저 창을 띄워 계정별 로그인 세션 저장")
    parser.add_argument("--account", action="append", help="특정 계정만 처리 (여러 번 지정 가능)")
    parser.add_argument("--config", help="설정 파일 경로 (기본: config.json)")
    parser.add_argument("--no-popup", action="store_true", help="요약 메시지 박스 표시 안 함")
    parser.add_argument("--show", action="store_true", help="조회 시에도 브라우저 창 표시 (디버깅용)")
    args = parser.parse_args(argv)

    config = collector.load_config(args.config)
    accounts = args.account or list(config.get("accounts", []))
    if not accounts:
        print("  config.json 의 accounts 목록이 비어 있습니다.")
        return 2

    try:
        if args.login:
            return run_login(config, accounts)
        return run_check(config, accounts, popup=not args.no_popup, show_browser=args.show)
    except KeyboardInterrupt:
        print("\n  중단되었습니다.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

