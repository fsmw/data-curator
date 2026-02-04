"""
Copilot API endpoints.

Handles AI chat and conversation management.
"""

from flask import request, jsonify, Response, stream_with_context
import asyncio
from typing import Dict
import json

from config import Config
from logger import get_logger

from . import api_bp

logger = get_logger(__name__)

# Import Copilot SDK agent
try:
    from copilot_agent import MisesCopilotAgent
    COPILOT_AVAILABLE = True
except ImportError:
    COPILOT_AVAILABLE = False
    logger.warning("Copilot agent not available")

def create_copilot_agent():
    """Create a new Copilot agent instance."""
    if not COPILOT_AVAILABLE:
        return None
    try:
        config = Config()
        return MisesCopilotAgent(config)
    except Exception as e:
        logger.error(f"Error initializing Copilot agent: {e}")
        return None


def run_async(coro):
    """Helper to run async functions in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@api_bp.route('/copilot/history/<session_id>', methods=["GET"])
def get_copilot_history(session_id: str) -> Response:
    """Get conversation history for a session."""
    try:
        agent = create_copilot_agent()
        if not agent:
            return jsonify({"status": "error", "message": "Copilot agent not available"}), 503

        # History is synchronous in the current implementation or simply reads a file/db
        # If get_history becomes async, use run_async
        history = agent.get_history(session_id)
        return jsonify({"status": "success", "session_id": session_id, "history": history})

    except Exception as e:
        logger.error(f"Error getting copilot history: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/chat", methods=["POST"])
def copilot_chat() -> Response:
    """Send a message to the Copilot agent."""
    try:
        agent = create_copilot_agent()
        if not agent:
            return jsonify({"status": "error", "message": "Copilot agent not available"}), 503

        data = request.get_json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)
        stream = data.get("stream", False)

        if not message:
            return jsonify({"status": "error", "message": "No message provided"}), 400

        logger.info(f"Received message: {message[:100]}...")
        logger.info(f"Session ID: {session_id}")

        if not session_id:
            from uuid import uuid4
            session_id = str(uuid4())

        try:
             # Run in a fresh event loop for this request
            response = run_async(agent.chat(message, session_id=session_id, stream=stream))
            logger.info(f"Got response status: {response.get('status')}")
            return jsonify(response), 200

        except TimeoutError as e:
            return jsonify({"status": "error", "message": "Request timeout"}), 504
        except Exception as e:
            logger.error(f"Copilot chat error: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500

    except Exception as e:
        logger.error(f"Copilot endpoint error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/stream", methods=["POST"])
def copilot_stream() -> Response:
    """Stream responses from Copilot agent."""
    try:
        # Don't create agent here, create it inside the generator to ensure thread/loop safety
        if not COPILOT_AVAILABLE:
             return jsonify({"status": "error", "message": "Copilot agent not available"}), 503

        data = request.get_json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)

        if not message:
            return jsonify({"status": "error", "message": "No message provided"}), 400

        if not session_id:
            from uuid import uuid4
            session_id = str(uuid4())

        def generate():
            # Create a NEW event loop for this streaming response
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            agent = create_copilot_agent() # Create specific instance for this stream

            try:
                async def stream_messages():
                    # We must ensure the agent uses the current loop
                    # MisesCopilotAgent.chat_stream should be robust to this
                    async for chunk in agent.chat_stream(message, session_id=session_id):
                        yield f"data: {json.dumps(chunk)}\n\n"

                # Run the async generator in the sync generator via the loop
                async_gen = stream_messages()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                    except Exception as e:
                        logger.error(f"Inner stream error: {e}")
                        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                        break
            finally:
                loop.close()


        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"Stream endpoint error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/health")
def copilot_health() -> Response:
    """Check if Copilot agent is available and healthy."""
    try:
        agent = create_copilot_agent()
        if agent:
           return jsonify({
                "status": "success",
                "available": True,
                "provider": "github_copilot_sdk"
            })
        else:
            return jsonify({
                "status": "success",
                "available": False,
                "message": "Copilot agent not initialized"
            })

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
