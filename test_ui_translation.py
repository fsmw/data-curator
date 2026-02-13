#!/usr/bin/env python3
"""Test UI translation with Playwright"""

import asyncio
from playwright.async_api import async_playwright


async def test_ui_translation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login
            print("1. Login as fernando/fernando123")
            await page.goto("http://localhost:5000/auth/login")
            await page.wait_for_load_state("networkidle")
            await page.locator('input[name="username"]').fill("fernando")
            await page.locator('input[name="password"]').fill("fernando123")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Set language to Spanish
            print("2. Set language to Spanish")
            await page.goto("http://localhost:5000/auth/profile")
            await page.wait_for_load_state("networkidle")
            page.once('dialog', lambda dialog: dialog.accept())
            await page.locator('select[name="language"]').select_option("es_CL")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Check various UI elements
            print("3. Checking page title...")
            title = await page.title()
            print(f"   Page Title: {title}")

            # Check profile page
            print("4. Checking profile page...")
            email_label = await page.locator('label[for="email"]').inner_text()
            print(f"   Email label: {email_label}")

            lang_label = await page.locator('label[for="language"]').inner_text()
            print(f"   Language label: {lang_label}")

            update_btn = await page.locator('button[type="submit"]').inner_text()
            print(f"   Update button: {update_btn}")

            # Check navigation
            print("5. Checking navigation menu...")
            username_header = await page.locator('.navbar-brand, .d-inline-flex').first.inner_text()
            print(f"   Username in nav: {username_header if username_header else 'not found'}")

            # Check admin page if accessible
            print("6. Checking if admin page shows translated text...")
            await page.goto("http://localhost:5000/")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Look for common English words that should be translated
            body_text = await page.inner_text('body')
            english_words = ['Status', 'Datasets', 'Indicators']
            spanish_words = ['Estado', 'Conjuntos de datos', 'Indicadores']

            print(f"   Checking for translated content...")
            for word in english_words:
                if word.lower() in body_text.lower():
                    print(f"   - Found English word '{word}' (may not be translated)")

            for word in spanish_words:
                if word.lower() in body_text.lower():
                    print(f"   - Found Spanish word '{word}' (looks good!)")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_ui_translation())