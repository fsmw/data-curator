#!/usr/bin/env python3
"""Test language switching with Playwright - bidirectional test"""

import asyncio
import sys
from playwright.async_api import async_playwright


async def test_language_switching():
    results = []
    
    async def change_language(page, target_lang, expected_label):
        print(f"\n--- Testing switch to {target_lang} ---")
        
        # Go to profile
        await page.goto("http://localhost:5000/auth/profile")
        await page.wait_for_load_state("networkidle")
        
        # Change language
        page.once('dialog', lambda dialog: dialog.accept())
        await page.locator('select[name="language"]').select_option(target_lang)
        await page.locator('button[type="submit"]').click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)
        
        # Check for success message
        success = page.locator('.alert-success')
        error = page.locator('.alert-danger')
        
        if await success.count() > 0:
            msg = await success.inner_text()
            print(f"  Success message: {msg}")
        elif await error.count() > 0:
            msg = await error.inner_text()
            print(f"  ERROR: {msg}")
            return False
        
        # Refresh and verify
        await page.reload()
        await page.wait_for_load_state("networkidle")
        
        current = await page.locator('select[name="language"]').input_value()
        print(f"  Selected: {current}, Expected: {target_lang}")
        
        # Check if UI is translated
        email_label = await page.locator('label[for="email"]').inner_text()
        print(f"  Email label text: {email_label}")
        
        if current == target_lang:
            print(f"  ✅ Language is {expected_label}")
            return True
        else:
            print(f"  ❌ Language is NOT {expected_label}")
            return False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login
            print("Login as fernando/fernando123")
            await page.goto("http://localhost:5000/auth/login")
            await page.wait_for_load_state("networkidle")
            await page.locator('input[name="username"]').fill("fernando")
            await page.locator('input[name="password"]').fill("fernando123")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
            
            # Test 1: Spanish
            results.append(("es_CL", await change_language(page, "es_CL", "Spanish (Chile)")))
            
            # Test 2: English
            results.append(("en_US", await change_language(page, "en_US", "English (United States)")))
            
            # Test 3: Spanish again
            results.append(("es_CL", await change_language(page, "es_CL", "Spanish (Chile)")))
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    print("\n=== SUMMARY ===")
    for lang, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{lang}: {status}")

    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_language_switching())
    sys.exit(0 if result else 1)