"""HTTP fetch helpers. Number parsing lives in schema.py (to_number)."""

from __future__ import annotations

import logging
import sys

import httpx

log = logging.getLogger("fii_dii")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def fetch_text(url: str, *, accept: str = "text/html", timeout: float = 25.0, cookie: str = "") -> str:
    """GET a URL as text. Raises httpx.HTTPError on non-2xx (caller falls over)."""
    headers = {
        "User-Agent": _UA,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if cookie:
        headers["Cookie"] = cookie
        headers["Referer"] = "https://www.nseindia.com/"
    with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text
