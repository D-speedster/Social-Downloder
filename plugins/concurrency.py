import os
import asyncio
from typing import Dict

# Global semaphore to limit concurrent heavy downloads/transcodes
DEFAULT_CAPACITY = max(2, min(4, (os.cpu_count() or 2)//2))
MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', str(DEFAULT_CAPACITY)))
_download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

_active = 0
_waiting = 0
_user_active: Dict[str, int] = {}

async def acquire_slot():
    global _waiting, _active
    _waiting += 1
    await _download_semaphore.acquire()
    _waiting -= 1
    _active += 1

def release_slot():
    global _active
    _active = max(0, _active - 1)
    _download_semaphore.release()

def get_queue_stats() -> Dict[str, int]:
    available = max(0, MAX_CONCURRENT_DOWNLOADS - _active)
    return {
        'capacity': MAX_CONCURRENT_DOWNLOADS,
        'active': _active,
        'waiting': _waiting,
        'available': available,
    }


def reserve_user(user_id, max_per_user: int = int(os.getenv('MAX_DOWNLOADS_PER_USER', '2'))) -> bool:
    key = str(user_id)
    count = _user_active.get(key, 0)
    if count >= max_per_user:
        return False
    _user_active[key] = count + 1
    return True


def release_user(user_id) -> None:
    key = str(user_id)
    if key in _user_active:
        new = max(0, _user_active[key] - 1)
        if new:
            _user_active[key] = new
        else:
            _user_active.pop(key, None)


def get_user_active(user_id) -> int:
    return _user_active.get(str(user_id), 0)