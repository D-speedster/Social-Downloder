#!/usr/bin/env python3
"""
بررسی وضعیت پروکسی‌ها
Check proxy status and availability
"""

import socket
import time
from plugins.youtube_proxy_rotator import probe_ports_status, SOCKS5_PORTS, PROXY_CONFIG

def check_single_proxy(host, port, timeout=2):
    """بررسی یک پروکسی واحد"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def main():
    print("🔍 Checking proxy availability...")
    print("=" * 60)
    
    # بررسی HTTP proxy
    print("📡 HTTP Proxy (10808):")
    http_available = check_single_proxy('127.0.0.1', 10808)
    print(f"   Status: {'✅ Available' if http_available else '❌ Not available'}")
    
    print("\n🧦 SOCKS5 Proxies:")
    available_socks = []
    for port in SOCKS5_PORTS:
        is_available = check_single_proxy('127.0.0.1', port)
        status = '✅ Available' if is_available else '❌ Not available'
        print(f"   Port {port}: {status}")
        if is_available:
            available_socks.append(port)
    
    print("\n📊 Summary:")
    print(f"   HTTP proxy (10808): {'Available' if http_available else 'Not available'}")
    print(f"   Available SOCKS5 ports: {available_socks if available_socks else 'None'}")
    print(f"   Total available proxies: {(1 if http_available else 0) + len(available_socks)}")
    
    if not http_available and not available_socks:
        print("\n⚠️  WARNING: No proxies are currently available!")
        print("   The bot will use direct connection (no proxy)")
        print("   This explains why the rotation system worked - it fell back to no proxy")
    
    print("\n🔧 Using built-in probe function:")
    try:
        probe_results = probe_ports_status(timeout_seconds=2.0)
        for result in probe_results:
            proxy_type = result.get('proxy_type', 'unknown')
            status = result.get('status', 'unknown')
            port = result.get('port', 'N/A')
            print(f"   {proxy_type} (port {port}): {status}")
    except Exception as e:
        print(f"   Error running probe: {e}")

if __name__ == "__main__":
    main()