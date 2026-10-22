#!/usr/bin/env python3
"""Export the diagram SVGs from HTML at 2560×1440, without page wrappers.

Requires Playwright, Chromium, and a Korean font such as Noto Sans CJK KR.
Run after build.py when diagram content changes.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    for slug in ("deployment", "command-sequence", "model-paths", "gpu-residency"):
        source = here / f"{slug}-ko.html"
        page.goto(source.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        diagram = page.locator("svg").first
        diagram.evaluate('''svg => {
            svg.style.width = '1280px';
            svg.style.height = '720px';
            const background = svg.querySelector(':scope > rect[width="100%"][height="100%"]');
            if (background) background.setAttribute('fill', 'none');
        }''')
        output = source.with_suffix(".png")
        diagram.screenshot(path=str(output), omit_background=True)
        print(output)
    browser.close()
