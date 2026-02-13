#!/usr/bin/env python3
"""Test profile update with Playwright"""

import asyncio
from playwright.async_api import async_playwright


async def test_login_and_language_change():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("1. Navigating to login page...")
        await page.goto("http://localhost:5000/auth/login")
        await page.wait_for_load_state("networkidle")

        print("2. Logging in as fernando/fernando123")
        await page.locator('input[name="username"]').click()
        await page.locator('input[name="username"]').fill("fernando")
        await page.locator('input[name="password"]').fill("fernando123")
        await page.locator('button[type="submit"]').click()
        await page.wait_for_load_state("networkidle")

        # Wait to be redirected
        await asyncio.sleep(1)

        print("3. Current URL:", page.url)
        print("4. Page title:", await page.title())

        # Go to profile page
        print("5. Navigating to profile page...")
        await page.goto("http://localhost:5000/auth/profile")
        await page.wait_for_load_state("networkidle")

        # Get current language
        print("6. Current language selection...")
        language_select = page.locator('select[name="language"]')
        current_language = await language_select.input_value()
        print(f"   Current: {current_language}")

        # Change to Spanish (Chile)
        print("7. Changing language to Spanish (Chile)...")
        page.once('dialog', lambda dialog: dialog.accept())
        await language_select.select_option("es_CL")

        # Click update button
        print("8. Clicking Update Profile button...")
        await page.locator('button[type="submit"]').click()

        # Wait and check for success message
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)

        # Check for flash messages
        success_messages = page.locator('.alert-success')
        error_messages = page.locator('.alert-danger')

        if await success_messages.count() > 0:
            print("9. SUCCESS: Success message found:", await success_messages.inner_text())
        if await error_messages.count() > 0:
            print("9. ERROR: Error message found:", await error_messages.inner_text())

        # Refresh and check if language persisted
        print("10. Refreshing page to check if language persisted...")
        await page.reload()
        await page.wait_for_load_state("networkidle")

        language_select = page.locator('select[name="language"]')
        current_language = await language_select.input_value()
        print(f"   Language after refresh: {current_language}")

        if current_language == "es_CL":
            print("✅ Language successfully saved to Spanish (Chile)!")
        else:
            print("❌ Language was NOT saved to Spanish (Chile)")

        # Wait for user to see
        print("\nPress Enter in this terminal to close browser...")
        input()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_login_and_language_change())