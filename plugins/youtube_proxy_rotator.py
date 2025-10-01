import os
import time
import random
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from yt_dlp import YoutubeDL

# Ports pool on localhost for SOCKS5 proxies
PORTS: List[int] = [1081, 1082, 1083, 1084, 1085, 1086, 1087, 1088]

# Failure tracking and temporary disable store
_failure_counts: Dict[int, int] = {p: 0 for p in PORTS}
_disabled_until: Dict[int, float] = {p: 0.0 for p in PORTS}

# Simple UA pool
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Logger configuration
os.makedirs('./logs', exist_ok=True)
proxy_logger = logging.getLogger('youtube_proxy_rotator')
proxy_handler = logging.FileHandler('./logs/youtube_proxy_rotator.log', encoding='utf-8')
proxy_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
proxy_handler.setFormatter(proxy_formatter)
if not proxy_logger.handlers:
    proxy_logger.addHandler(proxy_handler)
proxy_logger.setLevel(logging.INFO)


def is_enabled() -> bool:
    """Toggle via environment variable YOUTUBE_PROXY_ROTATION."""
    return os.environ.get('YOUTUBE_PROXY_ROTATION', '0') == '1'


def _now() -> float:
    return time.time()


def _is_port_available(port: int) -> bool:
    return _disabled_until.get(port, 0.0) <= _now()


def _mark_result(port: int, success: bool):
    if success:
        _failure_counts[port] = 0
        return
    _failure_counts[port] = _failure_counts.get(port, 0) + 1
    if _failure_counts[port] >= 3:
        _disabled_until[port] = _now() + 60.0
        proxy_logger.warning(f"Port {port} disabled for 60s due to 3 consecutive failures")
        _failure_counts[port] = 0


def _choose_port(excluded: set) -> Optional[int]:
    candidates = [p for p in PORTS if p not in excluded and _is_port_available(p)]
    if not candidates:
        return None
    return random.choice(candidates)


def _headers() -> Dict[str, str]:
    ua = random.choice(_USER_AGENTS)
    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }


async def extract_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                max_attempts: int = 3) -> Dict[str, Any]:
    """
    Attempt to extract info via yt-dlp using SOCKS5H proxy rotation over localhost ports.
    - Random port each attempt, avoiding previously tried ports
    - Timeout 8–12 seconds (socket_timeout randomized)
    - Standard browser headers
    - DNS via proxy by using socks5h scheme
    - Logs each attempt and response time
    """
    last_error: Optional[Exception] = None
    tried: set = set()
    for attempt in range(1, max_attempts + 1):
        port = _choose_port(tried)
        if port is None:
            break
        tried.add(port)

        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['proxy'] = f'socks5h://127.0.0.1:{port}'
        if cookiefile:
            opts['cookiefile'] = cookiefile

        start = _now()
        result: Optional[Dict[str, Any]] = None
        error: Optional[Exception] = None
        try:
            result = await asyncio.to_thread(lambda: YoutubeDL(opts).extract_info(url, download=False))
        except Exception as e:
            error = e

        duration = _now() - start
        if error is None and isinstance(result, dict):
            _mark_result(port, True)
            proxy_logger.info(f"OK url={url} port={port} time={duration:.2f}s")
            return result
        else:
            _mark_result(port, False)
            msg = str(error) if error else 'invalid_response'
            # Handle rate-limit hints
            if '429' in msg or 'rate' in msg.lower():
                proxy_logger.warning(f"Rate-limit detected on port={port}; slowing next attempt")
                await asyncio.sleep(2.0)
            proxy_logger.error(f"ERR url={url} port={port} time={duration:.2f}s err={msg}")
            last_error = error or Exception('Invalid response from yt-dlp')

    if last_error:
        raise last_error
    raise Exception('No available proxy ports for rotation')


async def download_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                 max_attempts: int = 3) -> None:
    """
    Attempt to download using yt-dlp with SOCKS5H proxy rotation.
    On success returns None; on failure raises the last encountered exception.
    """
    last_error: Optional[Exception] = None
    tried: set = set()
    for attempt in range(1, max_attempts + 1):
        port = _choose_port(tried)
        if port is None:
            break
        tried.add(port)

        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['proxy'] = f'socks5h://127.0.0.1:{port}'
        if cookiefile:
            opts['cookiefile'] = cookiefile

        start = _now()
        error: Optional[Exception] = None
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            error = e

        duration = _now() - start
        if error is None:
            _mark_result(port, True)
            proxy_logger.info(f"OK-DL url={url} port={port} time={duration:.2f}s")
            return
        else:
            _mark_result(port, False)
            msg = str(error)
            if '429' in msg or 'rate' in msg.lower():
                proxy_logger.warning(f"Rate-limit detected on port={port}; slowing next attempt")
                await asyncio.sleep(2.0)
            proxy_logger.error(f"ERR-DL url={url} port={port} time={duration:.2f}s err={msg}")
            last_error = error

    if last_error:
        raise last_error
    raise Exception('No available proxy ports for rotation')