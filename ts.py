#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Full Connectivity & Bot Validation Test
"""

import os
import sys
import socket
import asyncio
import aiohttp
from pyrogram import Client
from pyrogram.errors import RPCError
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

DC_LIST = [
    "149.154.167.40",
    "149.154.167.91",
    "149.154.167.223",
    "149.154.175.50",
    "149.154.175.100",
    "149.154.175.147",  # نمونه DC که ممکنه Timeout بده
]

TCP_PORT = 443

# -------------------------
# Utility Functions
# -------------------------

async def test_rest_api(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return True, data["result"]
                return False, await resp.text()
    except Exception as e:
        return False, str(e)

async def test_mtproto(bot_token, api_id, api_hash):
    try:
        async with Client(":memory:", bot_token=bot_token, api_id=api_id, api_hash=api_hash) as app:
            me = await app.get_me()
            return True, me
    except RPCError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def test_tcp(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

# -------------------------
# Main Test Runner
# -------------------------

async def main():
    print("=== Telegram Full Connectivity Test ===\n")

    # REST API Test
    print("[1] Testing REST API (bot token) ...")
    rest_ok, rest_data = await test_rest_api(BOT_TOKEN)
    if rest_ok:
        print(f"✅ REST API OK: Bot connected as @{rest_data['username']} ({rest_data['first_name']})\n")
    else:
        print(f"❌ REST API failed: {rest_data}\n")

    # MTProto Test
    print("[2] Testing MTProto (Pyrogram)...")
    mt_ok, mt_data = await test_mtproto(BOT_TOKEN, int(API_ID), API_HASH)
    if mt_ok:
        print(f"✅ MTProto OK: Bot connected as @{mt_data.username} ({mt_data.first_name})\n")
    else:
        print(f"❌ MTProto failed: {mt_data}\n")

    # TCP Test
    print("[3] Testing TCP connections to Telegram DCs (port 443)...")
    for dc in DC_LIST:
        ok = test_tcp(dc, TCP_PORT)
        status = "✅ TCP OK" if ok else "❌ TCP FAILED"
        print(f"{status}: {dc}:{TCP_PORT}")

    print("\n=== Test Completed ===")

if __name__ == "__main__":
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("❌ Please set BOT_TOKEN, API_ID, and API_HASH in .env or environment variables")
        sys.exit(1)
    asyncio.run(main())
