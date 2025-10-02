import os
import time
import random
import logging
import asyncio
import socket
from typing import Optional, Dict, Any, Tuple, List
from yt_dlp import YoutubeDL
import yt_dlp

# Compatibility placeholder: HTTP proxy config (not used anymore in rotation)
# Kept to avoid breaking auxiliary scripts that import PROXY_CONFIG
PROXY_CONFIG = {
    'http': None,
    'https': None,
}

# SOCKS5 ports for rotation (server-provided proxies only)
SOCKS5_PORTS: List[int] = [1081, 1082, 1083, 1084, 1085, 1086, 1087, 1088]

# Allow disabling SOCKS rotation or overriding ports via environment
# YOUTUBE_ENABLE_SOCKS: set to '0' or 'false' to disable SOCKS usage
# YOUTUBE_SOCKS_PORTS: comma-separated list of ports (e.g., "1081,1082")
# YOUTUBE_SINGLE_PROXY: set to specific proxy URL for testing (e.g., "socks5://127.0.0.1:1082")
ENABLE_SOCKS = os.getenv('YOUTUBE_ENABLE_SOCKS', '1').lower() not in ('0', 'false')
SINGLE_PROXY = os.getenv('YOUTUBE_SINGLE_PROXY')
_socks_env = os.getenv('YOUTUBE_SOCKS_PORTS')
if _socks_env:
    try:
        SOCKS5_PORTS = [int(p.strip()) for p in _socks_env.split(',') if p.strip()]
    except Exception:
        pass

# Failure tracking and temporary disable store
_failure_counts: Dict[str, int] = {}
_disabled_until: Dict[str, float] = {}

# Add SOCKS5 ports to failure tracking
for port in SOCKS5_PORTS:
    _failure_counts[f'socks5_{port}'] = 0
    _disabled_until[f'socks5_{port}'] = 0.0

# Simple UA pool
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Player client rotation per attempt (smart fallback: ios → android → web)
_PLAYER_CLIENTS = ["ios", "android", "web"]

# Logger configuration
os.makedirs('./logs', exist_ok=True)
proxy_logger = logging.getLogger('youtube_proxy_rotator')
proxy_handler = logging.FileHandler('./logs/youtube_proxy_rotator.log', encoding='utf-8')
proxy_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
proxy_handler.setFormatter(proxy_formatter)
if not proxy_logger.handlers:
    proxy_logger.addHandler(proxy_handler)
proxy_logger.setLevel(logging.INFO)


def _server_only_guard() -> None:
    """Enforce server-only execution via environment/hostname checks.
    Allows execution only if one of these is set:
    - RUN_ENV in {"server", "prod", "production"}
    - IS_SERVER == "1"
    - YOUTUBE_SERVER_ONLY == "1"
    """
    env = (os.getenv('RUN_ENV', '') or '').lower()
    is_server = (
        env in {'server', 'prod', 'production'} or
        os.getenv('IS_SERVER', '0') == '1' or
        os.getenv('YOUTUBE_SERVER_ONLY', '0') == '1'
    )
    if not is_server:
        raise RuntimeError('Server-only download module: set RUN_ENV=server or IS_SERVER=1')


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


def _iterate_socks_proxies() -> List[Tuple[str, str]]:
    """Return sequential list of available SOCKS5 proxies: (proxy_key, proxy_url)."""
    proxies: List[Tuple[str, str]] = []
    # If a single proxy is forced, use only that
    if SINGLE_PROXY:
        proxies.append(('single_proxy', SINGLE_PROXY))
        return proxies
    if not ENABLE_SOCKS:
        return proxies
    for port in SOCKS5_PORTS:
        # Skip temporarily disabled ports
        key = f'socks5_{port}'
        if _is_port_available(key):
            proxies.append((key, f'socks5h://127.0.0.1:{port}'))
    return proxies


def _headers() -> Dict[str, str]:
    ua = random.choice(_USER_AGENTS)
    return {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.youtube.com/',
        'Origin': 'https://www.youtube.com',
    }


def _is_proxy_available(proxy_type: str) -> bool:
    """Check if a proxy type is available (not disabled)"""
    return _disabled_until.get(proxy_type, 0.0) <= _now()


def _mark_proxy_result(proxy_type: str, success: bool):
    """Mark proxy result and disable if too many failures"""
    if success:
        _failure_counts[proxy_type] = 0
        return
    _failure_counts[proxy_type] = _failure_counts.get(proxy_type, 0) + 1
    if _failure_counts[proxy_type] >= 3:
        _disabled_until[proxy_type] = _now() + 60.0
        proxy_logger.warning(f"Proxy {proxy_type} disabled for 60s due to 3 consecutive failures")
        _failure_counts[proxy_type] = 0


def _get_all_available_proxies() -> List[Tuple[str, str]]:
    """Get all available SOCKS5 proxies sequentially."""
    return _iterate_socks_proxies()

def _needs_cookie(err: Exception) -> bool:
    msg = str(err).lower()
    return any(h in msg for h in [
        'login required', 'sign in', 'age', 'restricted', 'private', 'consent', 'verify your age', 'this video is'  # common yt errors
    ])

def _fetch_cookie_from_pool(prev_cookie_id: Optional[int] = None) -> Tuple[Optional[str], Optional[int]]:
    try:
        from .cookie_manager import get_rotated_cookie_file
        return get_rotated_cookie_file(prev_cookie_id)
    except Exception:
        return None, None

def _mark_cookie_usage(cookie_id: Optional[int], success: bool) -> None:
    if cookie_id is None:
        return
    try:
        from .cookie_manager import mark_cookie_used
        mark_cookie_used(cookie_id, success)
    except Exception:
        pass


def _choose_proxy() -> Optional[Tuple[str, str]]:
    """Choose the first available SOCKS5 proxy."""
    proxies = _iterate_socks_proxies()
    return proxies[0] if proxies else None


async def extract_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                max_attempts: int = 2) -> Dict[str, Any]:
    """
    Attempt to extract info via yt-dlp using a dynamically detected proxy.
    - Proactively finds the best available proxy (HTTP or SOCKS5).
    - If a proxy is found, uses it for the download.
    - If no proxy is found, attempts a direct download.
    - Timeout 8–12 seconds (socket_timeout randomized)
    - Standard browser headers
    - Logs each attempt and response time
    """
    _server_only_guard()
    last_error: Optional[Exception] = None

    # Proactive cookie attach if requested via env
    cookie_id_used: Optional[int] = None
    if cookiefile is None and os.getenv('YOUTUBE_ALWAYS_USE_COOKIES', '0') == '1':
        cookiefile, cookie_id_used = _fetch_cookie_from_pool(None)
        if cookiefile:
            proxy_logger.debug(f"Cookie pool proactively attached for extract: id={cookie_id_used}, path={cookiefile}")

    # Iterate proxies sequentially; retry per proxy
    proxies = _get_all_available_proxies()
    if not proxies:
        raise RuntimeError('No SOCKS5 proxies available (1081–1088). Configure server proxies.')

    attempt_logs: List[str] = []

    for proxy_type, proxy_url in proxies:
        for retry in range(1, max_attempts + 1):
            timeout = random.randint(8, 12)
            opts = dict(base_opts)
            opts['socket_timeout'] = timeout
            opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
            opts['proxy'] = proxy_url
            opts['geo_bypass'] = True
            # Rotate player_client for resilience
            client_choice = _PLAYER_CLIENTS[(retry - 1) % len(_PLAYER_CLIENTS)]
            ex_args = opts.get('extractor_args', {})
            yt_args = ex_args.get('youtube', {})
            yt_args['player_client'] = [client_choice]
            ex_args['youtube'] = yt_args
            opts['extractor_args'] = ex_args

            if cookiefile:
                opts['cookiefile'] = cookiefile

            start = _now()
            try:
                result = await asyncio.to_thread(lambda: YoutubeDL(opts).extract_info(url, download=False))
                duration = _now() - start
                proxy_logger.info(f"OK-EX url={url} proxy={proxy_url} client={client_choice} retry={retry} time={duration:.2f}s")
                _mark_proxy_result(proxy_type, True)
                attempt_logs.append(f"{proxy_url}#{client_choice}@{duration:.2f}s:OK")
                _mark_cookie_usage(cookie_id_used, True)
                # Summary
                proxy_logger.info(f"SUMMARY-EX success via {proxy_url} after {retry} attempt(s)")
                return result
            except Exception as e:
                duration = _now() - start
                proxy_logger.error(f"ERR-EX url={url} proxy={proxy_url} client={client_choice} retry={retry} time={duration:.2f}s err={str(e)}")
                _mark_proxy_result(proxy_type, False)
                attempt_logs.append(f"{proxy_url}#{client_choice}@{duration:.2f}s:ERR {str(e)[:80]}")
                last_error = e

                # If cookie may be required and we haven't attached one yet, retry once with cookie
                if cookiefile is None and _needs_cookie(e):
                    cookiefile, cookie_id_used = _fetch_cookie_from_pool(cookie_id_used)
                    if cookiefile:
                        opts2 = dict(opts)
                        opts2['cookiefile'] = cookiefile
                        start2 = _now()
                        try:
                            result = await asyncio.to_thread(lambda: YoutubeDL(opts2).extract_info(url, download=False))
                            duration2 = _now() - start2
                            proxy_logger.info(f"OK-EX-COOKIE url={url} proxy={proxy_url} client={client_choice} time={duration2:.2f}s")
                            _mark_proxy_result(proxy_type, True)
                            attempt_logs.append(f"{proxy_url}#{client_choice}@{duration2:.2f}s:OK-C")
                            _mark_cookie_usage(cookie_id_used, True)
                            proxy_logger.info(f"SUMMARY-EX success via {proxy_url} with cookie after failure")
                            return result
                        except Exception as e2:
                            duration2 = _now() - start2
                            proxy_logger.error(f"ERR-EX-COOKIE url={url} proxy={proxy_url} client={client_choice} time={duration2:.2f}s err={str(e2)}")
                            _mark_cookie_usage(cookie_id_used, False)
                            last_error = e2

    # Final failure: no direct connection allowed
    proxy_logger.warning(f"SUMMARY-EX failed for {url}; attempts: {len(attempt_logs)}; last_err={str(last_error)[:120]}")
    raise last_error or RuntimeError('All SOCKS5 proxy attempts failed for extraction')


async def download_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                 max_attempts: int = 2) -> None:
    """
    Attempt to download using yt-dlp with a dynamically detected proxy.
    - Proactively finds the best available proxy (HTTP or SOCKS5).
    - If a proxy is found, uses it for the download.
    - If no proxy is found, attempts a direct download.
    On success returns None; on failure raises the last encountered exception.
    """
    _server_only_guard()
    last_error: Optional[Exception] = None

    # Proactive cookie attach if requested via env
    cookie_id_used: Optional[int] = None
    if cookiefile is None and os.getenv('YOUTUBE_ALWAYS_USE_COOKIES', '0') == '1':
        cookiefile, cookie_id_used = _fetch_cookie_from_pool(None)
        if cookiefile:
            proxy_logger.debug(f"Cookie pool proactively attached for download: id={cookie_id_used}, path={cookiefile}")

    proxies = _get_all_available_proxies()
    if not proxies:
        raise RuntimeError('No SOCKS5 proxies available (1081–1088). Configure server proxies.')

    attempt_logs: List[str] = []

    for proxy_type, proxy_url in proxies:
        for retry in range(1, max_attempts + 1):
            timeout = random.randint(8, 12)
            opts = dict(base_opts)
            opts['socket_timeout'] = timeout
            opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
            opts['proxy'] = proxy_url
            opts['geo_bypass'] = True
            # Rotate player_client for resilience
            client_choice = _PLAYER_CLIENTS[(retry - 1) % len(_PLAYER_CLIENTS)]
            ex_args = opts.get('extractor_args', {})
            yt_args = ex_args.get('youtube', {})
            yt_args['player_client'] = [client_choice]
            ex_args['youtube'] = yt_args
            opts['extractor_args'] = ex_args

            if cookiefile:
                opts['cookiefile'] = cookiefile

            start = _now()
            try:
                await asyncio.to_thread(lambda: YoutubeDL(opts).download([url]))
                duration = _now() - start
                proxy_logger.info(f"OK-DL url={url} proxy={proxy_url} client={client_choice} retry={retry} time={duration:.2f}s")
                _mark_proxy_result(proxy_type, True)
                attempt_logs.append(f"{proxy_url}#{client_choice}@{duration:.2f}s:OK")
                _mark_cookie_usage(cookie_id_used, True)
                proxy_logger.info(f"SUMMARY-DL success via {proxy_url} after {retry} attempt(s)")
                return
            except Exception as e:
                duration = _now() - start
                proxy_logger.error(f"ERR-DL url={url} proxy={proxy_url} client={client_choice} retry={retry} time={duration:.2f}s err={str(e)}")
                _mark_proxy_result(proxy_type, False)
                attempt_logs.append(f"{proxy_url}#{client_choice}@{duration:.2f}s:ERR {str(e)[:80]}")
                last_error = e

                # If cookie may be required and we haven't attached one yet, retry once with cookie
                if cookiefile is None and _needs_cookie(e):
                    cookiefile, cookie_id_used = _fetch_cookie_from_pool(cookie_id_used)
                    if cookiefile:
                        opts2 = dict(opts)
                        opts2['cookiefile'] = cookiefile
                        start2 = _now()
                        try:
                            await asyncio.to_thread(lambda: YoutubeDL(opts2).download([url]))
                            duration2 = _now() - start2
                            proxy_logger.info(f"OK-DL-COOKIE url={url} proxy={proxy_url} client={client_choice} time={duration2:.2f}s")
                            _mark_proxy_result(proxy_type, True)
                            attempt_logs.append(f"{proxy_url}#{client_choice}@{duration2:.2f}s:OK-C")
                            _mark_cookie_usage(cookie_id_used, True)
                            proxy_logger.info(f"SUMMARY-DL success via {proxy_url} with cookie after failure")
                            return
                        except Exception as e2:
                            duration2 = _now() - start2
                            proxy_logger.error(f"ERR-DL-COOKIE url={url} proxy={proxy_url} client={client_choice} time={duration2:.2f}s err={str(e2)}")
                            _mark_cookie_usage(cookie_id_used, False)
                            last_error = e2

    proxy_logger.warning(f"SUMMARY-DL failed for {url}; attempts: {len(attempt_logs)}; last_err={str(last_error)[:120]}")
    raise last_error or RuntimeError('All SOCKS5 proxy attempts failed for download')


def probe_ports_status(timeout_seconds: float = 0.8) -> List[Dict[str, Any]]:
    """
    Probe local proxy ports to check basic liveness.
    - Checks TCP connect to 127.0.0.1:port
    - Optionally attempts external reachability via requests + socks (if available)
    Returns list of dicts with per-port status.
    """
    results: List[Dict[str, Any]] = []
    try:
        import requests  # type: ignore
    except Exception:
        requests = None  # fallback without external probe

    # Remove HTTP probe; only SOCKS5 ports are considered

    # Check SOCKS5 ports
    for port in SOCKS5_PORTS:
        local_ok = False
        external_ok = None  # None means skipped
        # Local TCP check
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout_seconds)
                local_ok = s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            local_ok = False

        # External probe via socks if requests available and local is OK
        if requests and local_ok:
            try:
                proxies = {
                    'http': f'socks5h://127.0.0.1:{port}',
                    'https': f'socks5h://127.0.0.1:{port}',
                }
                # Use lightweight connectivity endpoint
                resp = requests.get('https://www.youtube.com/generate_204', timeout=3, proxies=proxies)
                external_ok = resp.status_code in (200, 204)
            except Exception:
                external_ok = False

        results.append({
            'port': port,
            'type': 'socks5',
            'local_ok': local_ok,
            'external_ok': external_ok,
        })

    return results