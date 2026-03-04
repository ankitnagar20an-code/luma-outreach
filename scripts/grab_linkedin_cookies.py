"""
LinkedIn Cookie Extractor

Opens a fresh Edge window for you to log into LinkedIn.
Auto-detects when login completes and saves cookies.
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    print("=" * 50)
    print("LinkedIn Cookie Extractor")
    print("=" * 50)
    print()
    print("Opening Edge... Log into LinkedIn in the window.")
    print("The script will auto-detect when you're logged in.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="msedge",
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
        )

        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("Waiting for you to log in (up to 5 minutes)...")
        max_wait = 300
        elapsed = 0
        found = False

        while elapsed < max_wait:
            time.sleep(3)
            elapsed += 3
            cookies = context.cookies()
            cookie_names = {c["name"] for c in cookies}
            if "li_at" in cookie_names:
                found = True
                print("Login detected! Grabbing cookies...")
                time.sleep(5)
                break
            if elapsed % 30 == 0:
                print(f"  Still waiting... ({elapsed}s)")

        if not found:
            print("Timed out. Please try again.")
            browser.close()
            return

        all_cookies = context.cookies()
        needed = {"li_at", "JSESSIONID"}
        session_cookies = []
        for cookie in all_cookies:
            if cookie["name"] in needed:
                session_cookies.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                })

        browser.close()

    if len(session_cookies) < 2:
        print("Could not find required cookies.")
        return

    out_path = Path(__file__).parent.parent / "session.json"
    out_path.write_text(json.dumps(session_cookies, indent=2), encoding="utf-8")
    print(f"\nSession saved to: {out_path}")
    print("Cookies found:")
    for c in session_cookies:
        val = c["value"][:20]
        print(f"  {c['name']}: {val}...")
    print("\nDone!")


if __name__ == "__main__":
    main()
