from __future__ import annotations
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from plugins.db_wrapper import DB
from plugins import constant
from utils.util import convert_size

# Configure Dashboard logger
os.makedirs('./logs', exist_ok=True)
dashboard_logger = logging.getLogger('dashboard_main')
dashboard_logger.setLevel(logging.DEBUG)

dashboard_handler = logging.FileHandler('./logs/dashboard_main.log', encoding='utf-8')
dashboard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
dashboard_handler.setFormatter(dashboard_formatter)
dashboard_logger.addHandler(dashboard_handler)

PATH = constant.PATH
TXT = constant.TEXT


def _human_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return "نامشخص"
    try:
        return convert_size(2, size_bytes)
    except Exception:
        try:
            # Fallback: MB with 2 decimals
            return f"{(size_bytes/1024/1024):.2f} MB"
        except Exception:
            return "نامشخص"


def _fa_status(status: Optional[str]) -> str:
    s = (status or '').lower()
    mapping = {
        'pending': 'در صف',
        'downloading': 'در حال دانلود',
        'ready': 'آماده',
        'completed': 'تکمیل‌شده',
        'failed': 'ناموفق'
    }
    return mapping.get(s, s or '-')


def _shorten(s: Optional[str], max_len: int = 120) -> str:
    if not s:
        return "-"
    try:
        s = str(s)
        if len(s) <= max_len:
            return s
        head = max_len // 2 - 2
        tail = max_len - head - 3
        if head < 0 or tail <= 0:
            return s[:max_len]
        return s[:head] + "..." + s[-tail:]
    except Exception:
        return (s or "-")[:max_len]


def _format_items(items: List[Dict]) -> str:
    if not items:
        return TXT['dashboard_empty']
    lines: List[str] = []
    for it in items[:5]:
        title = _shorten((it.get('title') or 'بدون عنوان'), 80)
        status = _fa_status(it.get('status'))
        size_str = _human_size(it.get('size_bytes'))
        # لینک‌ها بر اساس نیاز جدید حذف شدند
        lines.append(f"• {title}\n  وضعیت: {status}\n  حجم: {size_str}")
    return "\n\n".join(lines)


def _build_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TXT['refresh'], callback_data='dash_refresh')],
        [InlineKeyboardButton(TXT['close'], callback_data='dash_close')]
    ])


async def _render_dashboard(user_id: int) -> str:
    db = DB()
    pending = db.get_recent_jobs(user_id, ['pending', 'downloading'], limit=5)
    ready = db.get_recent_jobs(user_id, ['ready', 'completed'], limit=5)

    parts: List[str] = [
        TXT['dashboard_title'],
        '',
        TXT['dashboard_pending'],
        _format_items(pending),
        '',
        TXT['dashboard_ready'],
        _format_items(ready)
    ]
    text = "\n".join(parts)

    # تلگرام حداکثر ~۴۰۹۶ کاراکتر. برای اطمینان محدود می‌کنیم
    if len(text) > 3900:
        # کوتاه‌تر کردن عنوان‌ها برای ایمنی بیشتر
        def shrink_block(block: str) -> str:
            lines = block.split('\n\n')
            out = []
            for ln in lines:
                if ln.startswith('• '):
                    try:
                        first_line, rest = ln.split('\n', 1)
                    except ValueError:
                        first_line, rest = ln, ''
                    title = first_line[2:]
                    title = _shorten(title, 60)
                    out.append('• ' + title + ('\n' + rest if rest else ''))
                else:
                    out.append(ln)
            return '\n\n'.join(out)

        parts = [
            TXT['dashboard_title'],
            '',
            TXT['dashboard_pending'],
            shrink_block(_format_items(pending)),
            '',
            TXT['dashboard_ready'],
            shrink_block(_format_items(ready))
        ]
        text = "\n".join(parts)

    return text


@Client.on_message(filters.command(['dash', 'dashboard']) & filters.private)
async def dashboard_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    text = await _render_dashboard(user_id)
    await message.reply_text(text, reply_markup=_build_markup(), disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^dash_(refresh|close)$"))
async def dashboard_cb(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    action = callback_query.data
    if action == 'dash_close':
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        try:
            await callback_query.answer("بسته شد")
        except Exception:
            pass
        return

    # refresh
    text = await _render_dashboard(user_id)
    try:
        await callback_query.edit_message_text(text, reply_markup=_build_markup(), disable_web_page_preview=True)
    except Exception:
        # Fallback to sending a new message if cannot edit
        await callback_query.message.reply_text(text, reply_markup=_build_markup(), disable_web_page_preview=True)
    try:
        await callback_query.answer("بروز شد")
    except Exception:
        pass