# API Performance Testing Instructions

## Purpose
This test script diagnoses performance issues with the Mises Data Curator API and Copilot integration.

## Prerequisites

1. **Start the server** (in one terminal):
```bash
python -m src.web
```

2. **Install dependencies** (if not already installed):
```bash
pip install aiohttp
```

## Running the Tests

In a **separate terminal**, run:

```bash
python test_api_performance.py
```

## What the Tests Check

### Test 1: Health Check
- Verifies the server is running
- Checks if Copilot SDK is available
- **Expected time**: < 1 second

### Test 2: List Available Models
- Fetches available AI models from GitHub Copilot
- Shows which models can be used
- **Expected time**: 1-3 seconds

### Test 3: Simple Chat (Non-Streaming)
- Sends a simple question: "What is 2+2?"
- Waits for complete response
- **Expected time**: 3-10 seconds
- **If > 30 seconds**: Problem with model/connection

### Test 4: Streaming Chat
- Sends a request and streams the response
- Measures time to first chunk (TTFC)
- **Expected TTFC**: 2-5 seconds
- **If > 15 seconds**: Model is slow to respond

### Test 5: Direct Agent Test
- Bypasses Flask API, tests agent directly
- Compares performance with/without API layer
- **If direct is much faster**: API overhead issue
- **If both slow**: Model/network issue

## Interpreting Results

### Scenario 1: Health Check Fails
**Problem**: Server is not running or crashed
**Solution**: Start the server with `python -m src.web`

### Scenario 2: Models Fetch Fails
**Problem**: GitHub Copilot SDK not configured
**Solution**: 
- Check `GITHUB_TOKEN` in environment or `.env`
- Verify SDK is installed: `pip install github-copilot-sdk`

### Scenario 3: All Tests Timeout (> 30s)
**Problem**: GitHub Copilot API is slow or not responding
**Possible causes**:
- Network issues
- Invalid GitHub token
- Copilot API rate limiting
- Copilot API downtime
**Solution**: Check GitHub Copilot status and token validity

### Scenario 4: Direct Agent Faster Than API
**Problem**: Flask API has overhead
**Possible causes**:
- Event loop issues
- Inefficient async handling
- Request parsing overhead
**Solution**: Optimize API endpoint implementation

### Scenario 5: Stream Works, Web Doesn't
**Problem**: Frontend issue (JavaScript, SSE handling)
**Solution**: Check browser console for errors

### Scenario 6: First Chunk Delay > 10s
**Problem**: Model initialization or processing is slow
**Possible causes**:
- Large context/system prompts
- Cold start on Copilot API
- Model selection (some models are slower)
**Solution**: 
- Try a faster model (e.g., gpt-5-mini)
- Reduce system prompt size
- Implement timeout handling in frontend

## Example Good Output

```
Test 3: Simple Chat (Non-Streaming)
✓ Chat response received (4.23s)
ℹ Response length: 156
ℹ Session ID: abc-123

Test 4: Streaming Chat
✓ First chunk received (2.15s)
✓ Stream completed (5.67s)
ℹ Time to first chunk: 2.15s
```

## Example Bad Output

```
Test 3: Simple Chat (Non-Streaming)
✗ Chat timeout (32.45s)
```

This indicates the model is taking too long to respond.

## Next Steps Based on Results

1. **If model is slow**: Consider switching to a faster model or implementing request timeouts
2. **If API has overhead**: Optimize the Flask endpoints
3. **If Copilot unavailable**: Check credentials and network
4. **If stream works but web doesn't**: Debug frontend JavaScript

## Troubleshooting

### Test hangs indefinitely
- Press Ctrl+C to stop
- Check if server is running: `curl http://127.0.0.1:5000/api/copilot/health`
- Check server logs for errors

### Import errors
- Make sure you're in the project root: `/home/fsmw/dev/mises/data-curator`
- Verify Python path: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

### Connection refused
- Server is not running
- Start with: `python -m src.web`
- Verify port 5000 is free: `lsof -i :5000`
