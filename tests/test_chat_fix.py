#!/usr/bin/env python3
"""Test script to verify AI Chat fixes."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), 'src'))

from config import Config
from ai_chat import ChatAssistant

def test_chat():
    """Test chat assistant with a simple query."""
    print("🔧 Testing AI Chat Assistant...")
    print("-" * 60)
    
    try:
        # Initialize
        config = Config()
        assistant = ChatAssistant(config)
        
        # Test query
        query = "cuantos datasets tenemos?"
        print(f"\n📝 User Query: {query}\n")
        
        # Get response
        response = assistant.chat(query)
        
        print("✅ Response received!")
        print("-" * 60)
        print(f"\n💬 Assistant Response:\n{response['response']}\n")
        print("-" * 60)
        
        # Show tool calls
        if response['tool_calls']:
            print(f"\n🔧 Tools Used: {len(response['tool_calls'])}")
            for tc in response['tool_calls']:
                print(f"  - {tc['function']}")
                if tc['result'].get('success'):
                    data = tc['result'].get('data', {})
                    if isinstance(data, dict) and 'total' in data:
                        print(f"    → Found: {data['total']} items")
        
        # Check if response is meaningful
        if response['response'] and len(response['response']) > 50:
            print("\n✅ Test PASSED - Response is meaningful")
            return True
        else:
            print("\n⚠️ Test WARNING - Response seems too short")
            print(f"   Response length: {len(response['response'])} chars")
            return False
            
    except Exception as e:
        print(f"\n❌ Test FAILED with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chat()
    sys.exit(0 if success else 1)
