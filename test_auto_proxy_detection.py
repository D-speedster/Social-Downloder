#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import socket
import yt_dlp

# --- پیکربندی ---
# لیستی از پورت‌ها برای تست، با اولویت بالاتر برای 10808
POTENTIAL_PORTS = [10808] + list(range(1081, 1089))
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley
CONNECTION_TIMEOUT = 1.5

# --- کدهای رنگی ---
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

def print_header(title):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}🔎 {title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def check_port_open(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(CONNECTION_TIMEOUT)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def test_proxy(proxy_url, proxy_type, port):
    print(f"  {YELLOW}▶ در حال تست پورت {port} به عنوان {proxy_type}...{RESET}", end='\r')
    ydl_opts = {
        'proxy': proxy_url,
        'quiet': True,
        'no_warnings': True,
        'simulate': True,
        'forceurl': True,
        'youtube_skip_dash_manifest': True,
        'retries': 1, # فقط یک بار تلاش کن
        'socket_timeout': 10, # زمان انتظار برای پاسخ
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(TEST_URL, download=False)
            print(f"  {GREEN}✅ پورت {port} به عنوان {proxy_type} با موفقیت کار کرد.{RESET}     ")
            return True
    except Exception:
        print(f"  {RED}❌ پورت {port} به عنوان {proxy_type} کار نکرد.{RESET}             ")
        return False

def main():
    print_header("تشخیص خودکار و تست نوع پروکسی")
    
    found_working_proxy = False
    
    for port in POTENTIAL_PORTS:
        if found_working_proxy:
            break
            
        print(f"\n{CYAN}--- بررسی پورت {port} ---{RESET}")
        if not check_port_open(port):
            print(f"  {RED}پورت {port} بسته است. رد شدن...{RESET}")
            continue
        
        print(f"  {GREEN}پورت {port} باز است. شروع تست نوع پروکسی...{RESET}")
        
        # 1. اولویت با HTTP
        http_proxy_url = f"http://127.0.0.1:{port}"
        if test_proxy(http_proxy_url, "HTTP", port):
            print_header("نتیجه نهایی")
            print(f"{GREEN}🎉 پروکسی کارآمد پیدا شد!{RESET}")
            print(f"   - آدرس: {CYAN}{http_proxy_url}{RESET}")
            print(f"   - نوع: {CYAN}HTTP{RESET}")
            found_working_proxy = True
            continue # برو به پورت بعدی (یا پایان حلقه)

        # 2. اگر HTTP کار نکرد، SOCKS5 را تست کن
        socks5_proxy_url = f"socks5://127.0.0.1:{port}"
        if test_proxy(socks5_proxy_url, "SOCKS5", port):
            print_header("نتیجه نهایی")
            print(f"{GREEN}🎉 پروکسی کارآمد پیدا شد!{RESET}")
            print(f"   - آدرس: {CYAN}{socks5_proxy_url}{RESET}")
            print(f"   - نوع: {CYAN}SOCKS5{RESET}")
            found_working_proxy = True

    if not found_working_proxy:
        print_header("نتیجه نهایی")
        print(f"{RED}⚠️ متاسفانه هیچ پروکسی کارآمدی در پورت‌های مشخص شده یافت نشد.{RESET}")

if __name__ == "__main__":
    main()