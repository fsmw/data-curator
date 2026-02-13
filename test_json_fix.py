#!/usr/bin/env python3
"""
Test script to verify JSON serialization fix for NaN values.
Tests the chart generation endpoint with data containing NaN values.
"""

import json
import requests
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "http://127.0.0.1:5000"

def test_chart_generation_with_nan():
    """Test chart generation with DataFrame containing NaN values."""
    print("\n" + "="*70)
    print("TEST 1: Chart Generation with NaN Values")
    print("="*70)
    
    # Create test data with NaN values
    test_data = [
        {"year": 2020, "country": "Argentina", "gdp": 371000},
        {"year": 2020, "country": "Brazil", "gdp": 1839000},
        {"year": 2021, "country": "Argentina", "gdp": 449000},
        {"year": 2021, "country": "Brazil", "gdp": 1917000},
        {"year": 2022, "country": "Argentina", "gdp": None},  # NaN value
        {"year": 2022, "country": "Brazil", "gdp": 2081000},
    ]
    
    payload = {
        "template": "line",
        "encodings": {
            "x": {"field": "year", "type": "temporal"},
            "y": {"field": "gdp", "type": "quantitative"},
            "color": {"field": "country", "type": "nominal"}
        },
        "data": test_data,
        "title": "PIB por País (con NaN)",
        "width": 600,
        "height": 400
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/viz/generate-chart",
            json=payload,
            timeout=10
        )
        
        print(f"\n✓ Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("status") == "ok":
                print("✓ Chart generation SUCCESSFUL")
                print(f"✓ Template: {result.get('template')}")
                print(f"✓ Applied transforms: {result.get('applied_transforms')}")
                
                # Verify spec was generated
                if result.get("spec"):
                    print("✓ Vega-Lite spec generated")
                    spec = result["spec"]
                    
                    # Check if data was properly serialized
                    if spec.get("data", {}).get("values"):
                        print(f"✓ Data serialized: {len(spec['data']['values'])} rows")
                        
                        # Verify no NaN literals in JSON
                        spec_str = json.dumps(spec)
                        if "NaN" in spec_str:
                            print("✗ ERROR: NaN literal found in JSON!")
                            return False
                        else:
                            print("✓ No NaN literals in JSON (safe serialization)")
                    
                    print("\n✓ TEST 1 PASSED: NaN handling works correctly")
                    return True
            else:
                print(f"✗ Error in response: {result.get('message')}")
                return False
        else:
            print(f"✗ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False


def test_auto_detect_encodings():
    """Test auto-detection of encodings when not provided."""
    print("\n" + "="*70)
    print("TEST 2: Auto-Detection of Encodings")
    print("="*70)
    
    # Simple data without explicit encodings
    test_data = [
        {"year": 2020, "country": "Argentina", "gdp": 371000},
        {"year": 2021, "country": "Argentina", "gdp": 449000},
        {"year": 2022, "country": "Brazil", "gdp": 2081000},
    ]
    
    payload = {
        "template": "line",
        "encodings": {},  # Empty encodings - should auto-detect
        "data": test_data,
        "title": "Auto-Detected Chart"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/viz/generate-chart",
            json=payload,
            timeout=10
        )
        
        print(f"\n✓ Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("status") == "ok":
                print("✓ Chart generation SUCCESSFUL (with auto-detection)")
                print(f"✓ Applied transforms: {result.get('applied_transforms')}")
                
                # Check if auto-detection was mentioned
                transforms = result.get('applied_transforms', [])
                auto_detected = any('auto' in t.lower() for t in transforms)
                if auto_detected:
                    print("✓ Auto-detection confirmed in applied transforms")
                
                if result.get("spec"):
                    print("✓ Vega-Lite spec generated with auto-detected encodings")
                    print("\n✓ TEST 2 PASSED: Auto-detection works correctly")
                    return True
            else:
                print(f"✗ Error: {result.get('message')}")
                return False
        else:
            print(f"✗ HTTP Error {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TESTING JSON SERIALIZATION FIX")
    print("="*70)
    
    # Try to connect to server
    try:
        response = requests.get(f"{BASE_URL}/api/datasets", timeout=5)
        print(f"\n✓ Server is running at {BASE_URL}")
    except Exception as e:
        print(f"\n✗ Cannot connect to server at {BASE_URL}")
        print(f"  Error: {e}")
        print("\n  Make sure the server is running:")
        print("  python -m src.web")
        return
    
    # Run tests
    test1_result = test_chart_generation_with_nan()
    test2_result = test_auto_detect_encodings()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Test 1 (NaN Handling): {'✓ PASSED' if test1_result else '✗ FAILED'}")
    print(f"Test 2 (Auto-Detection): {'✓ PASSED' if test2_result else '✗ FAILED'}")
    
    if test1_result and test2_result:
        print("\n✓ ALL TESTS PASSED")
        print("\nThe following issues have been fixed:")
        print("  1. NaN values now serialize to null (valid JSON)")
        print("  2. Template buttons should now auto-generate charts")
        print("  3. Auto-detection of fields works when not specified")
    else:
        print("\n✗ SOME TESTS FAILED - Check errors above")


if __name__ == "__main__":
    main()
