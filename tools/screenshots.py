#!/usr/bin/env python3
"""Serve the site and capture the review screenshots with Playwright (Chromium).

Usage:
  PLAYWRIGHT_BROWSERS_PATH=<browsers dir> python3 tools/screenshots.py [--port N]

Writes PNGs into screenshots/ and prints any browser console errors or page
errors it saw, exiting nonzero if there were any.
"""
import argparse
import http.server
import os
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent
OUT = SITE / "screenshots"

# (file name, path, viewport width, colour scheme, forced data-theme)
SHOTS = [
    ("landing-desktop-dark.png", "/index.html", 1440, "dark"),
    ("landing-desktop-light.png", "/index.html", 1440, "light"),
    ("landing-mobile.png", "/index.html", 390, "dark"),
    ("features-desktop.png", "/features.html", 1440, "dark"),
    ("getting-started-desktop.png", "/docs/getting-started.html", 1440, "light"),
    ("download-desktop.png", "/download.html", 1440, "dark"),
    ("blocks-desktop.png", "/docs/blocks.html", 1440, "light"),
    ("block-page-desktop.png", "/docs/blocks/db-postgres.html", 1440, "dark"),
    ("block-page-mobile.png", "/docs/blocks/net-haproxy.html", 390, "dark"),
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep the terminal clean
        pass


def serve(port: int) -> http.server.ThreadingHTTPServer:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), lambda *a, **kw: QuietHandler(*a, directory=str(SITE), **kw))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    port = args.port or free_port()
    srv = serve(port)
    OUT.mkdir(exist_ok=True)
    problems = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, path, width, scheme in SHOTS:
                ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                page.on("console", lambda m, n=name: problems.append(f"{n}: console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e, n=name: problems.append(f"{n}: pageerror: {e}"))
                page.on("requestfailed", lambda r, n=name: problems.append(f"{n}: request failed: {r.url}"))
                page.goto(f"http://127.0.0.1:{port}{path}", wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                # Reveal every animated block so a full-page capture is not blank below the fold.
                page.evaluate("document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'))")
                page.wait_for_timeout(300)
                overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if overflow > 0:
                    problems.append(f"{name}: horizontal overflow of {overflow}px at {width}px wide")
                page.screenshot(path=str(OUT / name), full_page=True)
                print(f"wrote {OUT / name}")
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
    if problems:
        print("\nProblems:")
        for pr in problems:
            print("  " + pr)
        return 1
    print("\nNo console errors, failed requests or horizontal overflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
