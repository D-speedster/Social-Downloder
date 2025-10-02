#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import socket
import yt_dlp

# --- پیکربندی -- -
PROXY_PORTS_TO_TEST = range(1081, 1089)  # تست پورت‌های 1081 تا 1088
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
CONNECTION_TIMEOUT = 2  # زمان انتظار برای اتصال به پورت

# --- کدهای رنگی برای خروجی -- -
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(title):
    """Prints a formatted header to the console."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🧪 {title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def check_port_open(port):
    """بررسی می‌کند که آیا یک پورت TCP باز است یا خیر."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(CONNECTION_TIMEOUT)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0


def test_proxy(proxy_url, proxy_type):
    """
    یک پروکسی را با تلاش برای دانلود اطلاعات ویدیو تست می‌کند.
    """
    print(f"\n{YELLOW}▶️ در حال تست پروکسی {proxy_type}: {proxy_url}{RESET}")
    ydl_opts = {
        'proxy': proxy_url,
        'quiet': True,
        'no_warnings': True,
        'simulate': True,       # شبیه‌سازی دانلود
        'forceurl': True,
        'youtube_skip_dash_manifest': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(TEST_URL, download=False)
            title = info.get('title', ' عنوانی یافت نشد')
            print(f"  {GREEN}✅ موفقیت آمیز:{RESET} عنوان ویدیو با موفقیت دریافت شد: '{title}'")
            return True
    except Exception as e:
        # نمایش خطای خلاصه‌شده برای خوانایی بهتر
        error_message = str(e).replace('\n', ' ').strip()
        print(f"  {RED}❌ ناموفق:{RESET} دریافت اطلاعات ویدیو ممکن نبود. خطا: {error_message[:200]}...")
        return False


def main():
    """
    تابع اصلی برای اسکن پورت‌ها و تست پروکسی‌های فعال.
    """
    print_header("تست محدوده پروکسی (پورت‌های 1081-1088)")

    # مرحله 1: اسکن پورت‌ها
    print("🔄 در حال اسکن برای یافتن پورت‌های باز...")
    active_ports = {port for port in PROXY_PORTS_TO_TEST if check_port_open(port)}

    if not active_ports:
        print(f"\n{RED}هیچ پورت بازی در محدوده {min(PROXY_PORTS_TO_TEST)}-{max(PROXY_PORTS_TO_TEST)} یافت نشد. پایان اسکریپت.{RESET}")
        return

    print(f"🔎 پورت‌های باز یافت شده: {GREEN}{sorted(list(active_ports))}{RESET}")

    # مرحله 2: تست هر پورت به عنوان پروکسی HTTP و SOCKS5
    print_header("تست انواع پروکسی روی پورت‌های فعال")

    results = {"http": [], "socks5": []}
    success_count = 0
    failure_count = 0

    for port in sorted(list(active_ports)):
        # تست به عنوان پروکسی HTTP
        http_proxy_url = f"http://127.0.0.1:{port}"
        if test_proxy(http_proxy_url, f"HTTP (پورت {port})"):
            results["http"].append(port)
            success_count += 1
        else:
            failure_count += 1

        # تست به عنوان پروکسی SOCKS5
        socks5_proxy_url = f"socks5://127.0.0.1:{port}"
        if test_proxy(socks5_proxy_url, f"SOCKS5 (پورت {port})"):
            results["socks5"].append(port)
            success_count += 1
        else:
            failure_count += 1

    # خلاصه نهایی
    print_header("نتایج نهایی")
    print(f"تعداد کل تست‌ها: {success_count + failure_count}")
    print(f"{GREEN}پروکسی‌های HTTP موفق: {results['http'] or 'هیچکدام'}{RESET}")
    print(f"{GREEN}پروکسی‌های SOCKS5 موفق: {results['socks5'] or 'هیچکدام'}{RESET}")

    if success_count > 0:
        print(f"\n{GREEN}🎉 حداقل یک پروکسی به درستی کار می‌کند!{RESET}")
    else:
        print(f"\n{RED}⚠️ هیچ یک از پورت‌های فعال برای دانلود از یوتیوب به عنوان پروکسی کار نمی‌کنند.{RESET}")


if __name__ == "__main__":
    main()