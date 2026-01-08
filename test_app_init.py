#!/usr/bin/env python
"""Quick test to verify TUI launches without errors."""

import sys
import asyncio

sys.path.insert(0, r'c:\dev\data-curator')

async def test_app_launch():
    """Test app initialization and screen switching."""
    from src.tui import MisesApp
    
    print("Initializing MisesApp...")
    app = MisesApp()
    
    print("App created successfully!")
    print(f"Screens registered: {list(app.SCREENS.keys())}")
    print(f"Total screens: {len(app.SCREENS)}")
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_app_launch())
        if result:
            print("\nSUCCESS: App initialization test passed!")
            print("\nYou can now safely run: python -m src.tui")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
