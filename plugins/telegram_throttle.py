"""
Global Telegram send throttle wrappers to control outbound concurrency
and handle FloodWait with minimal retries.
"""
import asyncio
import os
import io
import time
from typing import Any, Callable, Optional

from pyrogram.errors import FloodWait

try:
    from config import TELEGRAM_THROTTLING
except Exception:
    TELEGRAM_THROTTLING = {
        'max_concurrent_transmissions': 4,
        'flood_sleep_threshold': 60,
    }

# Module-level semaphore initialized lazily
_transmit_sem: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _transmit_sem
    if _transmit_sem is None:
        limit = int(TELEGRAM_THROTTLING.get('max_concurrent_transmissions', 4))
        _transmit_sem = asyncio.Semaphore(max(1, limit))
    return _transmit_sem


async def _run_with_slot(coro: Callable[[], Any]):
    sem = _get_semaphore()
    await sem.acquire()
    try:
        return await coro()
    finally:
        sem.release()


async def _send_with_retry(send_func: Callable[..., Any], *args, **kwargs):
    max_retries = int(kwargs.pop('max_retries', 2))
    attempt = 0
    while True:
        try:
            return await send_func(*args, **kwargs)
        except FloodWait as e:
            sleep_s = int(getattr(e, 'value', getattr(e, 'seconds', 30)))
            sleep_s = min(sleep_s, int(TELEGRAM_THROTTLING.get('flood_sleep_threshold', 60)))
            await asyncio.sleep(max(1, sleep_s))
            attempt += 1
            if attempt > max_retries:
                raise
        except Exception as ex:
            msg = str(ex).lower()
            # quick retry on transient network hiccups
            if attempt < max_retries and any(k in msg for k in ['timeout', 'connection reset', 'temporarily unavailable']):
                attempt += 1
                await asyncio.sleep(0.5)
                continue
            raise


def _estimate_size_bytes(media: Any) -> Optional[int]:
    try:
        if isinstance(media, (str, bytes)):
            if isinstance(media, str) and os.path.exists(media):
                return os.path.getsize(media)
            if isinstance(media, bytes):
                return len(media)
        if isinstance(media, io.BytesIO):
            try:
                # Avoid copying; use buffer if available
                buf = media.getbuffer()
                return buf.nbytes
            except Exception:
                # Fallback: tell() with seek
                pos = media.tell()
                media.seek(0, os.SEEK_END)
                size = media.tell()
                media.seek(pos, os.SEEK_SET)
                return size
    except Exception:
        return None
    return None


async def send_video_throttled(client, chat_id: int, video: Any, **kwargs):
    start = time.time()
    async def _do():
        return await _send_with_retry(client.send_video, chat_id=chat_id, video=video, **kwargs)
    result = await _run_with_slot(_do)
    _log_speed('video', video, start)
    return result


async def send_audio_throttled(client, chat_id: int, audio: Any, **kwargs):
    start = time.time()
    async def _do():
        return await _send_with_retry(client.send_audio, chat_id=chat_id, audio=audio, **kwargs)
    result = await _run_with_slot(_do)
    _log_speed('audio', audio, start)
    return result


async def send_document_throttled(client, chat_id: int, document: Any, **kwargs):
    start = time.time()
    async def _do():
        return await _send_with_retry(client.send_document, chat_id=chat_id, document=document, **kwargs)
    result = await _run_with_slot(_do)
    _log_speed('document', document, start)
    return result


async def send_photo_throttled(client, chat_id: int, photo: Any, **kwargs):
    start = time.time()
    async def _do():
        return await _send_with_retry(client.send_photo, chat_id=chat_id, photo=photo, **kwargs)
    result = await _run_with_slot(_do)
    _log_speed('photo', photo, start)
    return result


def _log_speed(kind: str, media: Any, start_ts: float):
    try:
        elapsed = time.time() - start_ts
        size_b = _estimate_size_bytes(media) or 0
        if elapsed > 0 and size_b > 0:
            mbps = (size_b / (1024 * 1024)) / elapsed
            if mbps < 2.0 and (size_b / (1024 * 1024)) > 10:
                print(f"⚠️ Slow {kind} upload: {mbps:.2f} MB/s")
    except Exception:
        pass