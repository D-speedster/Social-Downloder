import os


def get_proxy_url() -> str:
    """Return proxy URL for network calls.

    Priority:
    - V2RAY_PROXY
    - HTTPS_PROXY / HTTP_PROXY / ALL_PROXY
    - SOCKS_PROXY
    Fallback to V2Ray's default HTTP port.
    """
    return (
        os.getenv("V2RAY_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
        or os.getenv("ALL_PROXY")
        or os.getenv("SOCKS_PROXY")
        or "http://127.0.0.1:10808"
    )


def get_requests_proxies() -> dict:
    """Return proxies dict suitable for requests library."""
    proxy = get_proxy_url()
    return {
        "http": proxy,
        "https": proxy,
    }