import os
import time
import random
import logging
import asyncio
import socket
from typing import Optional, Dict, Any, Tuple, List
from yt_dlp import YoutubeDL

# Proxy configuration - HTTP proxy on port 10808 (V2Ray)
PROXY_CONFIG = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808'
}

# Fallback SOCKS5 ports (if HTTP proxy fails)
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
_failure_counts: Dict[str, int] = {'http_proxy': 0}
_disabled_until: Dict[str, float] = {'http_proxy': 0.0}

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
    """Get all available proxies in sequential order. Returns list of (proxy_type, proxy_url)"""
    proxies = []
    
    # If single proxy is specified, use only that
    if SINGLE_PROXY:
        proxies.append(('single_proxy', SINGLE_PROXY))
        return proxies
    
    # Try HTTP proxy first
    if _is_proxy_available('http_proxy'):
        proxies.append(('http_proxy', PROXY_CONFIG['http']))
    
    # Then try SOCKS5 ports in sequential order (only if enabled)
    if ENABLE_SOCKS:
        for port in SOCKS5_PORTS:
            if _is_proxy_available(f'socks5_{port}'):
                proxies.append((f'socks5_{port}', f'socks5h://127.0.0.1:{port}'))
    
    return proxies


def _choose_proxy() -> Optional[Tuple[str, str]]:
    """Choose an available proxy. Returns (proxy_type, proxy_url) or None"""
    # If single proxy is specified, use only that
    if SINGLE_PROXY:
        return ('single_proxy', SINGLE_PROXY)
    
    # Try HTTP proxy first
    if _is_proxy_available('http_proxy'):
        return ('http_proxy', PROXY_CONFIG['http'])
    
    # Fallback to SOCKS5 ports (sequential order) if enabled
    if ENABLE_SOCKS:
        available_socks = [port for port in SOCKS5_PORTS if _is_proxy_available(f'socks5_{port}')]
        if available_socks:
            # Use first available port (sequential order) instead of random
            port = available_socks[0]
            return (f'socks5_{port}', f'socks5h://127.0.0.1:{port}')
    
    return None


async def extract_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                max_attempts: int = 3) -> Dict[str, Any]:
    """
    Attempt to extract info via yt-dlp using all available proxies in sequential order, then no proxy.
    - HTTP proxy on port 10808 (primary)
    - SOCKS5H proxy rotation in sequential order (1081, 1082, 1083, ...)
    - No proxy as final fallback
    - Timeout 8–12 seconds (socket_timeout randomized)
    - Standard browser headers
    - Logs each attempt and response time
    """
    last_error: Optional[Exception] = None
    
    # Get all available proxies in sequential order
    available_proxies = _get_all_available_proxies()
    
    # Try each proxy in sequential order
    for attempt, (proxy_type, proxy_url) in enumerate(available_proxies, 1):

        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['proxy'] = proxy_url
        opts['geo_bypass'] = True

        # Remove player client rotation to avoid proxy conflicts
        # Using default client works better with proxies
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
            _mark_proxy_result(proxy_type, True)
            proxy_logger.info(f"OK url={url} proxy={proxy_type} time={duration:.2f}s")
            return result
        else:
            _mark_proxy_result(proxy_type, False)
            msg = str(error) if error else 'invalid_response'
            # Handle rate-limit hints
            if '429' in msg or 'rate' in msg.lower():
                proxy_logger.warning(f"Rate-limit detected on proxy={proxy_type}; slowing next attempt")
                await asyncio.sleep(2.0)
            proxy_logger.error(f"ERR url={url} proxy={proxy_type} time={duration:.2f}s err={msg}")
            last_error = error or Exception('Invalid response from yt-dlp')

    # Final fallback: try without proxy
    proxy_logger.warning(f"All proxies failed for {url}, trying without proxy as final fallback")
    try:
        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['geo_bypass'] = True
        # Remove any proxy setting
        opts.pop('proxy', None)
        
        # Use default client for no-proxy attempt (better compatibility)
        if cookiefile:
            opts['cookiefile'] = cookiefile

        start = _now()
        result = await asyncio.to_thread(lambda: YoutubeDL(opts).extract_info(url, download=False))
        duration = _now() - start
        
        if isinstance(result, dict):
            proxy_logger.info(f"OK url={url} proxy=none time={duration:.2f}s (fallback success)")
            return result
    except Exception as e:
        duration = _now() - start
        proxy_logger.error(f"ERR url={url} proxy=none time={duration:.2f}s err={str(e)} (fallback failed)")
        last_error = e

    if last_error:
        raise last_error
    raise Exception('All proxy attempts and no-proxy fallback failed')


async def download_with_rotation(url: str, base_opts: Dict[str, Any], cookiefile: Optional[str] = None,
                                 max_attempts: int = 3) -> None:
    """
    Attempt to download using yt-dlp with all available proxies in sequential order, then no proxy.
    On success returns None; on failure raises the last encountered exception.
    """
    last_error: Optional[Exception] = None
    
    # Get all available proxies in sequential order
    available_proxies = _get_all_available_proxies()
    
    # Try each proxy in sequential order
    for attempt, (proxy_type, proxy_url) in enumerate(available_proxies, 1):

        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['proxy'] = proxy_url
        opts['geo_bypass'] = True

        # Remove player client rotation to avoid proxy conflicts
        # Using default client works better with proxies
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
            _mark_proxy_result(proxy_type, True)
            proxy_logger.info(f"OK-DL url={url} proxy={proxy_type} time={duration:.2f}s")
            return
        else:
            _mark_proxy_result(proxy_type, False)
            msg = str(error)
            if '429' in msg or 'rate' in msg.lower():
                proxy_logger.warning(f"Rate-limit detected on proxy={proxy_type}; slowing next attempt")
                await asyncio.sleep(2.0)
            proxy_logger.error(f"ERR-DL url={url} proxy={proxy_type} time={duration:.2f}s err={msg}")
            last_error = error

    # Final fallback: try without proxy
    proxy_logger.warning(f"All proxies failed for download {url}, trying without proxy as final fallback")
    try:
        timeout = random.randint(8, 12)
        opts = dict(base_opts)
        opts['socket_timeout'] = timeout
        opts['http_headers'] = {**_headers(), **(base_opts.get('http_headers') or {})}
        opts['geo_bypass'] = True
        # Remove any proxy setting
        opts.pop('proxy', None)
        
        # Use default client for no-proxy attempt (better compatibility)
        if cookiefile:
            opts['cookiefile'] = cookiefile

        start = _now()
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        duration = _now() - start
        
        proxy_logger.info(f"OK-DL url={url} proxy=none time={duration:.2f}s (fallback success)")
        return
    except Exception as e:
        duration = _now() - start
        proxy_logger.error(f"ERR-DL url={url} proxy=none time={duration:.2f}s err={str(e)} (fallback failed)")
        last_error = e

    if last_error:
        raise last_error
    raise Exception('All proxy attempts and no-proxy fallback failed')


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

    # Check HTTP proxy first
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_seconds)
            local_ok = s.connect_ex(('127.0.0.1', 10808)) == 0
        
        external_ok = None
        if requests and local_ok:
            try:
                proxies = {
                    'http': 'http://127.0.0.1:10808',
                    'https': 'http://127.0.0.1:10808',
                }
                resp = requests.get('https://www.youtube.com/generate_204', timeout=3, proxies=proxies)
                external_ok = resp.status_code in (200, 204)
            except Exception:
                external_ok = False
        
        results.append({
            'port': 10808,
            'type': 'http',
            'local_ok': local_ok,
            'external_ok': external_ok,
        })
    except Exception:
        results.append({
            'port': 10808,
            'type': 'http',
            'local_ok': False,
            'external_ok': None,
        })

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