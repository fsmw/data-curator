"""Test Flask API endpoint."""
import requests
import json

try:
    response = requests.get("http://127.0.0.1:5001/api/search?q=tax")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"\nFound {len(data['results'])} results:")
    for r in data['results']:
        print(f"  - {r['indicator']} ({r['source'].upper()})")
except Exception as e:
    print(f"Error: {e}")
