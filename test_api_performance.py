#!/usr/bin/env python3
"""
Test script to diagnose API performance issues.
Tests both streaming and non-streaming endpoints with timing.
"""

import asyncio
import time
import json
import sys
from typing import Optional
import aiohttp

BASE_URL = "http://127.0.0.1:5000"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

async def test_health():
    """Test the health endpoint."""
    print_header("Test 1: Health Check")
    
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/copilot/health") as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                if response.status == 200:
                    print_success(f"Health check passed ({elapsed:.2f}s)")
                    print_info(f"Status: {data.get('status')}")
                    print_info(f"Available: {data.get('available')}")
                    print_info(f"Provider: {data.get('provider', 'N/A')}")
                    return True
                else:
                    print_error(f"Health check failed: {response.status}")
                    return False
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Health check error ({elapsed:.2f}s): {e}")
        return False

async def test_models():
    """Test the models endpoint."""
    print_header("Test 2: List Available Models")
    
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/copilot/models") as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                if response.status == 200 and data.get('status') == 'success':
                    print_success(f"Models fetched ({elapsed:.2f}s)")
                    models = data.get('models', [])
                    print_info(f"Found {len(models)} models:")
                    for model in models[:5]:  # Show first 5
                        print(f"  • {model.get('id')} - {model.get('name', 'N/A')}")
                    if len(models) > 5:
                        print(f"  ... and {len(models) - 5} more")
                    return models
                else:
                    print_error(f"Failed to fetch models: {response.status}")
                    return []
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Models fetch error ({elapsed:.2f}s): {e}")
        return []

async def test_chat_simple(model: Optional[str] = None):
    """Test simple chat endpoint (non-streaming)."""
    print_header("Test 3: Simple Chat (Non-Streaming)")
    
    test_message = "Hello! What is 2+2? Please answer in one sentence."
    print_info(f"Sending message: '{test_message}'")
    if model:
        print_info(f"Using model: {model}")
    
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": test_message,
                "stream": False
            }
            if model:
                payload["model"] = model
            
            async with session.post(
                f"{BASE_URL}/api/copilot/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                elapsed = time.time() - start_time
                data = await response.json()
                
                if response.status == 200 and data.get('status') == 'success':
                    print_success(f"Chat response received ({elapsed:.2f}s)")
                    print_info(f"Response length: {len(data.get('response', ''))}")
                    print_info(f"Session ID: {data.get('session_id', 'N/A')}")
                    print(f"\n{Colors.OKBLUE}Response:{Colors.ENDC}")
                    print(f"{data.get('response', 'No response')[:200]}...")
                    return True
                else:
                    print_error(f"Chat failed ({elapsed:.2f}s): {response.status}")
                    print_error(f"Error: {data.get('message', 'Unknown error')}")
                    return False
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print_error(f"Chat timeout ({elapsed:.2f}s)")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Chat error ({elapsed:.2f}s): {e}")
        return False

async def test_stream_chat(model: Optional[str] = None):
    """Test streaming chat endpoint."""
    print_header("Test 4: Streaming Chat")
    
    test_message = "Count from 1 to 5, one number per line."
    print_info(f"Sending message: '{test_message}'")
    if model:
        print_info(f"Using model: {model}")
    
    start_time = time.time()
    first_chunk_time = None
    chunks_received = 0
    total_content = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": test_message
            }
            if model:
                payload["model"] = model
            
            async with session.post(
                f"{BASE_URL}/api/copilot/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    elapsed = time.time() - start_time
                    print_error(f"Stream failed ({elapsed:.2f}s): {response.status}")
                    text = await response.text()
                    print_error(f"Error response: {text[:200]}")
                    return False
                
                print_info("Streaming started...")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or not line.startswith('data: '):
                        continue
                    
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                        print_success(f"First chunk received ({first_chunk_time:.2f}s)")
                    
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        chunks_received += 1
                        
                        if data.get('status') == 'success' and data.get('text'):
                            total_content += data['text']
                            # Print progress
                            print(f"  Chunk {chunks_received}: +{len(data['text'])} chars", end='\r')
                        elif data.get('status') == 'error':
                            print_error(f"\nStream error: {data.get('message')}")
                            return False
                            
                    except json.JSONDecodeError:
                        continue
                
                elapsed = time.time() - start_time
                print(f"\n")
                print_success(f"Stream completed ({elapsed:.2f}s)")
                print_info(f"Total chunks: {chunks_received}")
                print_info(f"Total content length: {len(total_content)}")
                print_info(f"Time to first chunk: {first_chunk_time:.2f}s")
                print_info(f"Average chunk time: {elapsed/chunks_received:.2f}s")
                
                print(f"\n{Colors.OKBLUE}Response:{Colors.ENDC}")
                print(total_content[:300])
                
                return True
                
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print_error(f"Stream timeout ({elapsed:.2f}s)")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Stream error ({elapsed:.2f}s): {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_agent():
    """Test the agent directly without the web API."""
    print_header("Test 5: Direct Agent Test (Bypass API)")
    
    try:
        from copilot_agent import MisesCopilotAgent
        from config import Config
        
        print_info("Initializing agent directly...")
        config = Config()
        agent = MisesCopilotAgent(config)
        
        test_message = "What is 2+2? Answer in one sentence."
        print_info(f"Sending message: '{test_message}'")
        
        start_time = time.time()
        response = await agent.chat(test_message, stream=False)
        elapsed = time.time() - start_time
        
        if response.get('status') == 'success':
            print_success(f"Direct agent response received ({elapsed:.2f}s)")
            print_info(f"Response length: {len(response.get('response', ''))}")
            print(f"\n{Colors.OKBLUE}Response:{Colors.ENDC}")
            print(f"{response.get('response', 'No response')[:200]}...")
            return True
        else:
            print_error(f"Direct agent failed ({elapsed:.2f}s)")
            print_error(f"Error: {response.get('message', 'Unknown error')}")
            return False
            
    except ImportError as e:
        print_error(f"Cannot import agent: {e}")
        print_warning("Skipping direct agent test")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"Direct agent error ({elapsed:.2f}s): {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"🔍 Mises Data Curator - API Performance Diagnostic")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    print_info(f"Testing against: {BASE_URL}")
    print_info("Make sure the server is running!")
    print()
    
    # Test 1: Health
    health_ok = await test_health()
    if not health_ok:
        print_error("\n❌ Server is not healthy. Please start the server first:")
        print_info("   python -m src.web")
        return
    
    # Test 2: Models
    models = await test_models()
    test_model = models[0]['id'] if models else None
    
    # Test 3: Simple chat
    await test_chat_simple(test_model)
    
    # Test 4: Streaming chat
    await test_stream_chat(test_model)
    
    # Test 5: Direct agent (bypass API)
    await test_direct_agent()
    
    # Summary
    print_header("Summary & Recommendations")
    print("""
If the tests show:
  • Health check fails → Server is not running
  • Models fetch fails → Copilot SDK not configured properly
  • Chat timeout → Check GitHub Copilot token/connection
  • Stream works but web doesn't → Frontend issue
  • Direct agent faster than API → API overhead issue
  • All slow → Model/network issue with GitHub Copilot
    """)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(0)
