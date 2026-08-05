"""Regenerate docs/screenshot.png from the live GitHub Pages site (or a local build).

Uses Playwright (optional 'browser' extra). Ported from scripts/screenshot.mjs.
  python -m fii_dii.screenshot                              # live site
  SITE=http://localhost:5055 python -m fii_dii.screenshot   # local build
"""

from __future__ import annotations

import os
from pathlib import Path

LIVE = "https://chirag127.github.io/fii-dii-activity-api/"


def capture(out: Path, url: str) -> None:
    from playwright.sync_api import sync_playwright  # lazy — optional dep

    out.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for _ in range(3):  # launch is flaky on some machines
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
                )
                page = browser.new_page(viewport={"width": 1000, "height": 900})
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(3000)  # client-side chart render
                page.screenshot(path=str(out), full_page=True)
                browser.close()
            return
        except Exception as e:  # noqa: BLE001 — retry flaky launch
            last_err = e
    raise RuntimeError(f"screenshot failed after 3 attempts: {last_err}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    url = os.environ.get("SITE", LIVE)
    out = root / "docs" / "screenshot.png"
    capture(out, url)
    print(f"Wrote {out} from {url}")


if __name__ == "__main__":
    main()
