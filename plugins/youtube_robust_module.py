import os
import asyncio
import logging
import socket
import tempfile
from typing import Optional, Tuple, List, Dict, Any

import yt_dlp

# Reuse existing logger file target to keep logs unified
os.makedirs('./logs', exist_ok=True)
_proxy_logger = logging.getLogger('youtube_proxy_rotator')
if not _proxy_logger.handlers:
    handler = logging.FileHandler('./logs/youtube_proxy_rotator.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    _proxy_logger.addHandler(handler)
_proxy_logger.setLevel(logging.INFO)


# Common helper: classify recoverable errors that suggest cookie retry
def _needs_cookie(err: Exception) -> bool:
    msg = str(err).lower()
    hints = ['login required', 'sign in', 'age', 'restricted', 'private', 'consent', 'verify your age']
    return any(h in msg for h in hints)


def _detect_proxy_scheme(port: int, timeout: float = 0.8) -> Optional[str]:
    """
    Try to detect whether a local proxy listening on `port` is SOCKS5 or HTTP.
    - If socket connect fails, returns None.
    - If SOCKS5 handshake succeeds (version byte == 0x05), returns 'socks5h'.
    - If we receive an HTTP-like response, returns 'http'.
    - Otherwise returns None.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return None
            # Try SOCKS5 greeting
            try:
                s.sendall(b"\x05\x01\x00")  # version 5, 1 method, no auth
                resp = s.recv(2)
                if len(resp) == 2 and resp[0] == 0x05:
                    return 'socks5h'
            except Exception:
                pass
        # If SOCKS check didn't confirm, attempt a lightweight HTTP probe
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as hs:
                hs.settimeout(timeout)
                if hs.connect_ex(('127.0.0.1', port)) != 0:
                    return None
                hs.sendall(b"GET / HTTP/1.0\r\nHost: youtube.com\r\n\r\n")
                resp = hs.recv(8)
                if resp.startswith(b"HTTP/"):
                    return 'http'
        except Exception:
            pass
    except Exception:
        return None
    return None


def _build_proxy_list(ports: List[int]) -> List[Tuple[str, str]]:
    """Return (scheme, url) for available proxies among given ports."""
    available: List[Tuple[str, str]] = []
    for p in ports:
        scheme = _detect_proxy_scheme(p)
        if not scheme:
            _proxy_logger.debug(f"Preflight: port {p} not available or unknown protocol")
            continue
        url = f"{scheme}://127.0.0.1:{p}"
        available.append((scheme, url))
    return available


class RobustYouTubeDownloader:
    """
    Robust YouTube flow with rotating proxies (1081–1088) and cookie fallback.
    - Async-friendly: blocking yt-dlp calls are run in threads.
    - Logs attempts to ./logs/youtube_proxy_rotator.log using the shared logger.
    - Does not modify cookie pool management.
    """

    def __init__(self, cookie_file: Optional[str] = 'cookie_youtube.txt', ports: Optional[List[int]] = None):
        self.cookie_file = cookie_file
        self.ports = ports or [1081, 1082, 1083, 1084, 1085, 1086, 1087, 1088]
        self._last_cookie_id: Optional[int] = None

    async def _extract_info_with_opts(self, url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        def _do_extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        return await asyncio.to_thread(_do_extract)

    async def fetch_info(self, url: str) -> Optional[Dict[str, Any]]:
        proxies = _build_proxy_list(self.ports)
        if not proxies:
            _proxy_logger.warning("No local proxies available (1081–1088). Proceeding without proxy.")
        last_err: Optional[Exception] = None

        # base yt-dlp opts
        base_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'forcejson': True,
            'no_check_certificate': True,
            'socket_timeout': 12,
            'connect_timeout': 8,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }

        # Attach initial cookie if provided
        if self.cookie_file and os.path.isfile(self.cookie_file):
            base_opts['cookiefile'] = self.cookie_file

        # If no proxies available, try direct
        if not proxies:
            try:
                _proxy_logger.info(f"INFO-EX direct url={url}")
                info = await self._extract_info_with_opts(url, base_opts)
                return info if isinstance(info, dict) else None
            except Exception as e:
                _proxy_logger.error(f"ERR-EX direct url={url} err={str(e)}")
                last_err = e
                if _needs_cookie(e):
                    # Try rotating cookies if pool exists
                    try:
                        from .cookie_manager import get_rotated_cookie_file, mark_cookie_used
                        cookiefile, cid = get_rotated_cookie_file(self._last_cookie_id)
                        if cookiefile:
                            base_opts['cookiefile'] = cookiefile
                            self._last_cookie_id = cid
                            _proxy_logger.info(f"Cookie rotated: id={cid}")
                            info = await self._extract_info_with_opts(url, base_opts)
                            mark_cookie_used(cid, True)
                            return info if isinstance(info, dict) else None
                    except Exception:
                        pass
                return None

        # Iterate proxies sequentially
        for scheme, proxy_url in proxies:
            opts = dict(base_opts)
            opts['proxy'] = proxy_url
            try:
                _proxy_logger.info(f"TRY-EX url={url} proxy={proxy_url}")
                info = await self._extract_info_with_opts(url, opts)
                if isinstance(info, dict):
                    _proxy_logger.info(f"OK-EX url={url} proxy={proxy_url}")
                    return info
                else:
                    _proxy_logger.error(f"ERR-EX-NONE url={url} proxy={proxy_url}")
            except Exception as e:
                _proxy_logger.error(f"ERR-EX url={url} proxy={proxy_url} err={str(e)}")
                last_err = e
                if _needs_cookie(e):
                    # Attempt cookie rotation and retry on same proxy
                    try:
                        from .cookie_manager import get_rotated_cookie_file, mark_cookie_used
                        cookiefile, cid = get_rotated_cookie_file(self._last_cookie_id)
                        if cookiefile:
                            opts['cookiefile'] = cookiefile
                            self._last_cookie_id = cid
                            _proxy_logger.info(f"Cookie rotated for extract: id={cid}")
                            info = await self._extract_info_with_opts(url, opts)
                            if isinstance(info, dict):
                                mark_cookie_used(cid, True)
                                _proxy_logger.info(f"OK-EX url={url} proxy={proxy_url} cookie_id={cid}")
                                return info
                    except Exception:
                        pass
                # continue to next proxy

        if last_err:
            _proxy_logger.warning(f"SUMMARY-EX failed url={url} last_err={str(last_err)[:120]}")
        return None

    async def download(self, url: str, format_id: str) -> Optional[str]:
        proxies = _build_proxy_list(self.ports)
        last_err: Optional[Exception] = None

        # Prepare a temporary output template
        tempdir = tempfile.mkdtemp(prefix='yt_dl_')
        outtmpl = os.path.join(tempdir, '%(title)s.%(ext)s')

        base_opts: Dict[str, Any] = {
            'quiet': True,
            'noplaylist': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'socket_timeout': 12,
            'connect_timeout': 8,
            'format': format_id,
            'outtmpl': outtmpl,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
        }

        if self.cookie_file and os.path.isfile(self.cookie_file):
            base_opts['cookiefile'] = self.cookie_file

        def _do_download(u: str, opts: Dict[str, Any]) -> str:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(u)
                return ydl.prepare_filename(info)

        # Direct download if no proxies
        if not proxies:
            try:
                _proxy_logger.info(f"TRY-DL direct url={url} fmt={format_id}")
                fname = await asyncio.to_thread(_do_download, url, base_opts)
                _proxy_logger.info(f"OK-DL direct url={url} file={fname}")
                return fname
            except Exception as e:
                _proxy_logger.error(f"ERR-DL direct url={url} err={str(e)}")
                last_err = e
                if _needs_cookie(e):
                    try:
                        from .cookie_manager import get_rotated_cookie_file, mark_cookie_used
                        cookiefile, cid = get_rotated_cookie_file(self._last_cookie_id)
                        if cookiefile:
                            base_opts['cookiefile'] = cookiefile
                            self._last_cookie_id = cid
                            _proxy_logger.info(f"Cookie rotated for direct download: id={cid}")
                            fname = await asyncio.to_thread(_do_download, url, base_opts)
                            mark_cookie_used(cid, True)
                            return fname
                    except Exception:
                        pass
                return None

        # Iterate proxies sequentially
        for scheme, proxy_url in proxies:
            opts = dict(base_opts)
            opts['proxy'] = proxy_url
            try:
                _proxy_logger.info(f"TRY-DL url={url} fmt={format_id} proxy={proxy_url}")
                fname = await asyncio.to_thread(_do_download, url, opts)
                _proxy_logger.info(f"OK-DL url={url} proxy={proxy_url} file={fname}")
                return fname
            except Exception as e:
                _proxy_logger.error(f"ERR-DL url={url} proxy={proxy_url} err={str(e)}")
                last_err = e
                if _needs_cookie(e):
                    # Attempt cookie rotation and retry same proxy
                    try:
                        from .cookie_manager import get_rotated_cookie_file, mark_cookie_used
                        cookiefile, cid = get_rotated_cookie_file(self._last_cookie_id)
                        if cookiefile:
                            opts['cookiefile'] = cookiefile
                            self._last_cookie_id = cid
                            _proxy_logger.info(f"Cookie rotated for download: id={cid}")
                            fname = await asyncio.to_thread(_do_download, url, opts)
                            mark_cookie_used(cid, True)
                            _proxy_logger.info(f"OK-DL url={url} proxy={proxy_url} cookie_id={cid}")
                            return fname
                    except Exception:
                        pass
                # continue to next proxy

        if last_err:
            _proxy_logger.warning(f"SUMMARY-DL failed url={url} fmt={format_id} last_err={str(last_err)[:120]}")
        return None


async def list_video_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter and list video-capable formats from info dict."""
    if not isinstance(info, dict):
        return []
    return [f for f in (info.get('formats') or []) if f.get('vcodec', 'none') != 'none']


async def list_audio_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter and list audio-capable formats from info dict."""
    if not isinstance(info, dict):
        return []
    return [f for f in (info.get('formats') or []) if f.get('acodec', 'none') != 'none']