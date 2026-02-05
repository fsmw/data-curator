#!/usr/bin/env python3
"""
Demo script to test the thinking process visualization.
Simulates a response with tool usage and thinking steps.
"""

import asyncio
import json
from aiohttp import web
import time

async def simulate_thinking_stream(request):
    """Simulate a streaming response with thinking process."""
    
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    
    await response.prepare(request)
    
    # Simulate thinking steps
    steps = [
        {
            'status': 'success',
            'thinking': {
                'type': 'thought',
                'content': 'Analyzing the user question about GDP data...'
            }
        },
        {
            'status': 'success',
            'thinking': {
                'type': 'reasoning',
                'content': 'I need to search the database for GDP datasets'
            }
        },
        {
            'status': 'success',
            'tool_use': {
                'name': 'search_datasets',
                'input': {'query': 'GDP', 'limit': 10}
            }
        },
        {
            'status': 'success',
            'tool_result': 'Found 5 datasets: OWID GDP, World Bank GDP, IMF GDP, UN GDP, OECD GDP'
        },
        {
            'status': 'success',
            'thinking': {
                'type': 'analysis',
                'content': 'OWID GDP dataset appears most comprehensive with data from 1990-2024'
            }
        },
        {
            'status': 'success',
            'text': 'I found several GDP datasets. '
        },
        {
            'status': 'success',
            'text': 'The most comprehensive is the OWID GDP dataset, '
        },
        {
            'status': 'success',
            'text': 'which covers 186 countries from 1990 to 2024. '
        },
        {
            'status': 'success',
            'text': 'It includes both nominal and real GDP data.'
        },
        {
            'status': 'success',
            'done': True
        }
    ]
    
    for step in steps:
        await asyncio.sleep(0.5)  # Simulate processing time
        data = f"data: {json.dumps(step)}\n\n"
        await response.write(data.encode('utf-8'))
    
    return response

async def init_app():
    """Initialize the demo server."""
    app = web.Application()
    app.router.add_post('/api/copilot/stream', simulate_thinking_stream)
    return app

if __name__ == '__main__':
    print("="*60)
    print("🧪 Thinking Process Demo Server")
    print("="*60)
    print("\nStarting demo server on http://127.0.0.1:8888")
    print("\nTo test:")
    print("1. Change frontend URL to: http://127.0.0.1:8888")
    print("2. Send any message in the chat")
    print("3. Watch the thinking process unfold!")
    print("\nPress Ctrl+C to stop\n")
    
    web.run_app(init_app(), host='127.0.0.1', port=8888)
