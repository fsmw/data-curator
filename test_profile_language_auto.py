#!/usr/bin/env python3
"""Test profile update with Playwright - auto close version"""

import asyncio
import sys
from playwright.async_api import async_playwright


async def test_login_and_language_change():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print("1. Navigating to login page...")
            await page.goto("http://localhost:5000/auth/login")
            await page.wait_for_load_state("networkidle")

            print("2. Logging in as fernando/fernando123")
            await page.locator('input[name="username"]').click()
            await page.locator('input[name="username"]').fill("fernando")
            await page.locator('input[name="password"]').fill("fernando123")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")

            await asyncio.sleep(1)
            print("3. Current URL:", page.url)

            print("4. Navigating to profile page...")
            await page.goto("http://localhost:5000/auth/profile")
            await page.wait_for_load_state("networkidle")

            language_select = page.locator('select[name="language"]')
            current_language = await language_select.input_value()
            print(f"5. Current language: {current_language}")

            print("6. Changing language to Spanish (Chile)...")
            page.once('dialog', lambda dialog: dialog.accept())
            await language_select.select_option("es_CL")

            print("7. Clicking Update Profile button...")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            # Check for messages
            success_messages = page.locator('.alert-success')
            error_messages = page.locator('.alert-danger')

            if await success_messages.count() > 0:
                success_text = await success_messages.inner_text()
                print(f"8. SUCCESS: {success_text}")
                results.append(("success_message", success_text))
            if await error_messages.count() > 0:
                error_text = await error_messages.inner_text()
                print(f"8. ERROR: {error_text}")
                results.append(("error_message", error_text))

            # Refresh and check persistence
            print("9. Refreshing to check if language persisted...")
            await page.reload()
            await page.wait_for_load_state("networkidle")

            language_select = page.locator('select[name="language"]')
            current_language = await language_select.input_value()
            print(f"10. Language after refresh: {current_language}")
            results.append(("final_language", current_language))

            if current_language == "es_CL":
                print("✅ SUCCESS: Language saved to Spanish (Chile)!")
                results.append(("test_result", "PASS"))
            else:
                print("❌ FAILED: Language NOT saved to Spanish (Chile)")
                results.append(("test_result", "FAIL"))

        except Exception as e:
            print(f"ERROR: {e}")
            results.append(("error", str(e)))
        finally:
            await browser.close()

    print("\n=== RESULTS ===")
    for name, value in results:
        print(f"{name}: {value}")

    return results


if __name__ == "__main__":
    result = asyncio.run(test_login_and_language_change())
    sys.exit(0 if any(r[1] == "PASS" and r[0] == "test_result" for r in result) else 1)