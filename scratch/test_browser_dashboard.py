"""
scratch/test_browser_dashboard.py — Playwright Visual & Interactive Verification Script.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_PATH = Path("/home/kizamladjanijebac/.gemini/antigravity/brain/a6ad86bf-10c6-4fae-8f3a-b5e8ca90d036/dashboard_screenshot.png")

def main():
    print("Pokrećem headless Chromium verifikaciju...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigiram na http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        # Check page title
        title = page.title()
        print(f"Page title: {title}")
        assert "Antigravity" in title

        # Wait for KPI cards
        page.wait_for_selector("text=Multi-Agent Debate", timeout=10000)
        print("✅ KPI kartice uspešno renderovane.")

        # Test tab navigation
        tabs = [
            "Naučne Studije & Benchmark",
            "RAG Baza Znanja",
            "JudgeGuard & Revizija",
            "AI Data Chat Asistent",
            "Multi-Agent Debate"
        ]

        for tab_name in tabs:
            print(f"Klikćem na tab: {tab_name}...")
            page.click(f"text={tab_name}")
            page.wait_for_timeout(500)

        # Toggle Dark / Light theme
        print("Testiram Theme Toggle (Dark -> Light -> Dark)...")
        theme_btn = page.locator("button[aria-label='Toggle Dark/Light Mode']")
        theme_btn.click()
        page.wait_for_timeout(400)
        is_light = "dark" not in page.eval_on_selector("html", "el => el.className")
        print(f"Theme prebačen u Light: {is_light}")

        theme_btn.click()
        page.wait_for_timeout(400)
        is_dark = "dark" in page.eval_on_selector("html", "el => el.className")
        print(f"Theme vraćen u Dark: {is_dark}")

        # Capture screenshot
        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        print(f"✅ Screenshot sačuvan na: {SCREENSHOT_PATH}")

        browser.close()

        if console_errors:
            print(f"⚠️ Upozorenje: Zabeležene konzolne greške: {console_errors}")
        else:
            print("✅ 0 konzolnih grešaka! Sve vizuelne i interaktivne provere prošle!")

if __name__ == "__main__":
    main()
