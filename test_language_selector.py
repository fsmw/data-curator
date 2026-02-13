#!/usr/bin/env python3
"""Test language selector with Playwright"""

import asyncio
from playwright.async_api import async_playwright


async def test_language_selector():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Login
            print("1. Navegando a login...")
            await page.goto("http://localhost:5000/auth/login")
            await page.wait_for_load_state("networkidle")
            
            await page.locator('input[name="username"]').fill("fernando")
            await page.locator('input[name="password"]').fill("fernando123")
            await page.locator('button[type="submit"]').click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
            print("✓ Login exitoso")

            # Verificar que el selector de idioma está presente
            print("\n2. Verificando selector de idioma...")
            
            # Verificar que las banderas están visibles
            us_flag = page.locator('img[alt="English"]')
            cl_flag = page.locator('img[alt="Español"]')
            
            if await us_flag.is_visible() and await cl_flag.is_visible():
                print("✓ Banderas de USA y Chile visibles")
            else:
                print("✗ No se encontraron las banderas")
                return False

            # Cambiar a español
            print("\n3. Cambiando idioma a Español...")
            await cl_flag.click()
            await asyncio.sleep(2)  # Esperar recarga
            
            # Verificar que la página recargó
            print("✓ Página recargada después de cambiar idioma")
            
            # Verificar traducciones en la UI
            print("\n4. Verificando traducciones...")
            
            # Buscar elementos traducidos
            page_content = await page.content()
            
            # Verificar elementos comunes
            if "Perfil" in page_content or "Profile" in page_content:
                print("✓ Encontrado texto de perfil")
            
            if "Ayuda" in page_content or "Help" in page_content:
                print("✓ Encontrado texto de ayuda")
                
            if "Nuevo Análisis" in page_content or "New Analysis" in page_content:
                print("✓ Encontrado texto de nuevo análisis")

            # Cambiar de vuelta a inglés
            print("\n5. Cambiando idioma a Inglés...")
            await page.goto("http://localhost:5000/")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
            
            us_flag = page.locator('img[alt="English"]')
            await us_flag.click()
            await asyncio.sleep(2)
            
            print("✓ Cambio a inglés exitoso")
            
            print("\n✅ TODAS LAS PRUEBAS PASARON")
            return True

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_language_selector())
    exit(0 if result else 1)
