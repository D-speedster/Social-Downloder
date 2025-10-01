import os


def get_proxy_url() -> str | None:
    """Return proxy URL only if configured in environment.

    Priority:
    - V2RAY_PROXY
    - HTTPS_PROXY / HTTP_PROXY / ALL_PROXY
    - SOCKS_PROXY

    No built-in default is returned to avoid forcing local proxies.
    """
    return (
        os.getenv("V2RAY_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
        or os.getenv("ALL_PROXY")
        or os.getenv("SOCKS_PROXY")
        or None
    )


def get_requests_proxies() -> dict:
    """Return proxies dict suitable for requests library, if available."""
    proxy = get_proxy_url()
    if not proxy:
        return {}
    return {
        "http": proxy,
        "https": proxy,
    }