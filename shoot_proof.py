#!/usr/bin/env python3
"""Screenshot the Day->Night proof at 0/25/50/75/100% scroll (desktop + one mobile)."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
CHROME = "/home/hatch/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
target = sys.argv[1] if len(sys.argv) > 1 else (HERE / "index.html").as_uri()
outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "shots"
outdir.mkdir(parents=True, exist_ok=True)
prefix = sys.argv[3] if len(sys.argv) > 3 else "local"

ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--js-flags=--max-old-space-size=512"]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, args=ARGS)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(target)
    pg.wait_for_function("window.__proof && window.__proof.loaded >= window.__proof.total", timeout=60000)
    print("frames loaded:", pg.evaluate("window.__proof.loaded"), "/", pg.evaluate("window.__proof.total"))
    total = pg.evaluate("document.getElementById('space').offsetHeight - window.innerHeight")
    for pct in (0, 25, 50, 75, 100):
        pg.evaluate(f"window.scrollTo(0, {total * pct / 100})")
        pg.wait_for_timeout(1400)  # let the lerp settle on the target frame
        cur = pg.evaluate("window.__proof.current")
        pg.screenshot(path=str(outdir / f"{prefix}-{pct:03d}.png"))
        print(f"{pct}% -> frame {cur:.1f}")
    # mobile spot-check at 50% (fresh browser; the VM is small)
    b.close()
    b = p.chromium.launch(executable_path=CHROME, args=ARGS)
    mp = b.new_page(viewport={"width": 390, "height": 844})
    mp.goto(target)
    mp.wait_for_function("window.__proof && window.__proof.loaded >= window.__proof.total", timeout=60000)
    mtotal = mp.evaluate("document.getElementById('space').offsetHeight - window.innerHeight")
    mp.evaluate(f"window.scrollTo(0, {mtotal * 0.5})")
    mp.wait_for_timeout(1400)
    mp.screenshot(path=str(outdir / f"{prefix}-mobile-050.png"))
    print("mobile 50% -> frame", mp.evaluate("window.__proof.current"))
    print("console errors:", errors if errors else "none")
    b.close()
