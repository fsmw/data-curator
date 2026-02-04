from playwright.sync_api import sync_playwright
import json

def test_endpoint(page, url, name):
    """Test an endpoint and report results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({url})")
    print('='*60)
    
    try:
        response = page.goto(url)
        page.wait_for_load_state('networkidle')
        
        # Get status code
        status = response.status if response else "No response"
        print(f"Status Code: {status}")
        
        # Get page title if available
        title = page.title()
        print(f"Page Title: {title}")
        
        # Get content preview
        content = page.content()
        preview = content[:500] + "..." if len(content) > 500 else content
        print(f"Content Preview:\n{preview}")
        
        # Check for errors in console
        console_logs = page.evaluate("() => { return window.consoleLogs || []; }")
        if console_logs:
            print(f"Console Messages: {len(console_logs)}")
            for log in console_logs[:5]:  # Show first 5
                print(f"  {log}")
        
        return status == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Capture console messages
    page.on("console", lambda msg: print(f"[Console] {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"[Page Error] {err}"))
    
    base_url = "http://localhost:5000"
    results = {}
    
    # Test all endpoints
    results['/'] = test_endpoint(page, f"{base_url}/", "Home")
    results['/status'] = test_endpoint(page, f"{base_url}/status", "Status")
    results['/search'] = test_endpoint(page, f"{base_url}/search", "Search")
    results['/browse/local'] = test_endpoint(page, f"{base_url}/browse/local", "Browse Local")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for endpoint, success in results.items():
        status = "✓ WORKING" if success else "✗ FAILED"
        print(f"{endpoint}: {status}")
    
    browser.close()
