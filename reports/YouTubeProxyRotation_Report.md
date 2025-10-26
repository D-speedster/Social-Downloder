Summary of YouTube SOCKS5 Proxy Rotation Implementation

Overview
- Implemented YouTube-only SOCKS5H proxy rotation over localhost ports `1081–1088`.
- Rotation is enabled via the `YOUTUBE_PROXY_ROTATION` environment variable (default off).
- Applies to metadata extraction and downloads handled in `plugins/youtube.py` and `plugins/youtube_helpers.py`.

Key Features
- Random proxy port selection per request; avoid previously tried ports in the same request.
- Up to 3 attempts per request; marks failed ports and retries with another random port.
- Per-attempt `socket_timeout` randomized between 8–12 seconds.
- Sends standard browser headers and rotates `User-Agent` from a small pool.
- Uses `socks5h` scheme so DNS is resolved through the proxy.
- Detailed per-request logging to `./logs/youtube_proxy_rotator.log` including timestamp, target URL, port, result, error type, and duration.
- Global cooldown: if a port fails 3 times consecutively, it is disabled for 60 seconds.
- Rudimentary rate-limit handling: detects 429/rate-limit hints and slows subsequent attempts minimally.

Toggle (venv-friendly)
- Set `YOUTUBE_PROXY_ROTATION=1` to enable on server.
- Leave unset or set to `0` to disable on local/venv as desired.

Files Updated/Added
- Added `plugins/youtube_proxy_rotator.py`: core rotation logic for extract and download.
- Updated `plugins/youtube.py`: uses rotation for initial extraction and fallback attempts.
- Updated `plugins/youtube_helpers.py`: uses rotation for download and direct URL extraction paths.
- Added `reports/YouTubeProxyRotation_Report.md`: this report.

Usage Notes
- When enabled, all YouTube requests in the bot (metadata and file download) go through the rotator.
- Cookie usage remains conditional; if errors indicate login/age restrictions, the rotator attaches a rotated cookie.
- If you observe many 429s, consider increasing delays or reducing concurrency at the application level.

How to Enable on Windows (PowerShell)
- `setx YOUTUBE_PROXY_ROTATION 1`
- Restart the process/session to ensure the environment variable is picked up.

How to Enable on Linux (bash)
- `export YOUTUBE_PROXY_ROTATION=1`
- Ensure the bot process inherits the variable (e.g., set in systemd unit or supervisor).

Logs
- `./logs/youtube_proxy_rotator.log`: Per-request attempt logs and port cooldown events.
- Existing logs like `./logs/youtube_main.log` and `youtube_performance.log` continue to capture high-level flow.

Limitations
- The rotator operates at the request level exposed by `yt-dlp`; internal sub-requests are governed by yt-dlp.
- Rate-limit handling is minimal; integrate broader backoff if hitting heavy throttling.

Next Steps
- Expand the User-Agent pool for better header diversity.
- Optional: persist port health state across process restarts.
- Consider adaptive backoff based on error types and historical failure rates.