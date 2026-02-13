"""
Copilot API endpoints.

Handles AI chat and conversation management.
"""

from flask import request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
import asyncio
import json
from typing import Dict, List, Optional
from sqlalchemy.exc import OperationalError

from src.config import Config
from src.logger import get_logger
from src.model_governance import ALLOWED_COPILOT_MODELS
from src.response_cache import get_cache
from src.models import CopilotThread, db

from . import api_bp

logger = get_logger(__name__)
ALLOWED_MODEL_IDS = set(ALLOWED_COPILOT_MODELS)
JSON_PARSE_ERRORS = (json.JSONDecodeError, TypeError, ValueError)
COPILOT_API_ERRORS = (
    AttributeError,
    KeyError,
    OSError,
    RuntimeError,
    TimeoutError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
    OperationalError,
)

# Import Copilot SDK agent
try:
    from src.copilot_agent import MisesCopilotAgent
    COPILOT_AVAILABLE = True
except ImportError:
    COPILOT_AVAILABLE = False
    logger.warning("Copilot agent not available")

# Initialize cache
cache = get_cache()


def _deserialize_json(value: Optional[str]) -> List[Dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except JSON_PARSE_ERRORS:
        return []
    return []


def _serialize_json(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value)


def _thread_to_dict(thread: CopilotThread) -> Dict:
    return {
        "id": thread.id,
        "user_id": thread.user_id,
        "title": thread.title,
        "session_id": thread.session_id,
        "messages": _deserialize_json(thread.messages_json),
        "charts": _deserialize_json(thread.charts_json),
        "last_message": thread.last_message,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
    }


def _ensure_copilot_threads_table() -> None:
    """Create copilot_threads table if it does not exist."""
    CopilotThread.__table__.create(bind=db.engine, checkfirst=True)

def create_copilot_agent():
    """Create a new Copilot agent instance."""
    if not COPILOT_AVAILABLE:
        return None
    try:
        config = Config()
        return MisesCopilotAgent(config)
    except COPILOT_API_ERRORS as e:
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
@login_required
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

    except COPILOT_API_ERRORS as e:
        logger.error(f"Error getting copilot history: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/chat", methods=["POST"])
@login_required
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
        model = data.get("model", None)
        if model and model not in ALLOWED_MODEL_IDS:
            return jsonify({"status": "error", "message": "Unsupported model"}), 400

        if not message:
            return jsonify({"status": "error", "message": "No message provided"}), 400

        logger.info(f"Received message: {message[:100]}...")
        logger.info(f"Session ID: {session_id}, Stream: {stream}, Model: {model}")

        # Check cache first (only for non-streaming requests without explicit session)
        # We check BEFORE generating a session ID so cache can work
        has_explicit_session = session_id is not None
        
        if not stream and not has_explicit_session:
            cached_response = cache.get(message, model)
            if cached_response:
                logger.info(f"✅ Cache hit for message: {message[:50]}...")
                # Add cache indicator and generate session for this response
                from uuid import uuid4
                cached_response['cached'] = True
                cached_response['session_id'] = str(uuid4())
                return jsonify(cached_response), 200
        
        # Generate session ID if not provided
        if not session_id:
            from uuid import uuid4
            session_id = str(uuid4())

        try:
             # Run in a fresh event loop for this request
            response = run_async(agent.chat(message, session_id=session_id, stream=stream, model=model))
            logger.info(f"Got response status: {response.get('status')}")
            
            # Cache successful responses (only for non-streaming requests without explicit session)
            if response.get('status') == 'success' and not stream and not has_explicit_session:
                cache.set(message, response, model)
                logger.info(f"💾 Cached response for: {message[:50]}...")
            
            return jsonify(response), 200

        except TimeoutError as e:
            return jsonify({"status": "error", "message": "Request timeout"}), 504
        except COPILOT_API_ERRORS as e:
            logger.error(f"Copilot chat error: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500

    except COPILOT_API_ERRORS as e:
        logger.error(f"Copilot endpoint error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/stream", methods=["POST"])
@login_required
def copilot_stream() -> Response:
    """Stream responses from Copilot agent."""
    try:
        # Don't create agent here, create it inside the generator to ensure thread/loop safety
        if not COPILOT_AVAILABLE:
             return jsonify({"status": "error", "message": "Copilot agent not available"}), 503

        data = request.get_json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)
        model = data.get("model", None)
        if model and model not in ALLOWED_MODEL_IDS:
            return jsonify({"status": "error", "message": "Unsupported model"}), 400

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
                    async for chunk in agent.chat_stream(message, session_id=session_id, model=model):
                        yield f"data: {json.dumps(chunk)}\n\n"

                # Run the async generator in the sync generator via the loop
                async_gen = stream_messages()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                    except COPILOT_API_ERRORS as e:
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

    except COPILOT_API_ERRORS as e:
        logger.error(f"Stream endpoint error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/health")
@login_required
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

    except COPILOT_API_ERRORS as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/models")
@login_required
def copilot_models() -> Response:
    """Get list of available models from Copilot SDK."""
    try:
        agent = create_copilot_agent()
        if not agent:
            return jsonify({"status": "error", "message": "Copilot agent not available"}), 503

        # Use the SDK's list_models() method
        models = run_async(agent.list_models())
        filtered_models = []
        for model in models:
            if isinstance(model, dict):
                model_id = str(model.get("id", "")).strip()
                if model_id in ALLOWED_MODEL_IDS:
                    filtered_models.append(model)
            else:
                model_id = str(model).strip()
                if model_id in ALLOWED_MODEL_IDS:
                    filtered_models.append({"id": model_id, "name": model_id})

        return jsonify({
            "status": "success",
            "models": filtered_models
        })

    except COPILOT_API_ERRORS as e:
        logger.error(f"Error fetching models: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/cache/stats")
@login_required
def copilot_cache_stats() -> Response:
    """Get cache statistics."""
    try:
        stats = cache.stats()
        return jsonify({
            "status": "success",
            "cache": stats
        })
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/cache/clear", methods=["POST"])
@login_required
def copilot_cache_clear() -> Response:
    """Clear the response cache."""
    try:
        cache.clear()
        logger.info("Response cache cleared")
        return jsonify({
            "status": "success",
            "message": "Cache cleared successfully"
        })
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/threads", methods=["GET"])
@login_required
def list_copilot_threads() -> Response:
    try:
        _ensure_copilot_threads_table()
        threads = (
            CopilotThread.query.filter_by(user_id=current_user.id)
            .order_by(CopilotThread.updated_at.desc())
            .all()
        )
        return jsonify({
            "status": "success",
            "threads": [_thread_to_dict(thread) for thread in threads],
        })
    except OperationalError as e:
        if "no such table: copilot_threads" in str(e):
            _ensure_copilot_threads_table()
            return list_copilot_threads()
        logger.error(f"Error listing copilot threads: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error listing copilot threads: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/threads", methods=["POST"])
@login_required
def create_copilot_thread() -> Response:
    try:
        _ensure_copilot_threads_table()
        thread = CopilotThread(
            user_id=current_user.id,
            title="New Analysis",
            messages_json=_serialize_json([]),
            charts_json=_serialize_json([]),
        )
        db.session.add(thread)
        db.session.commit()
        return jsonify({
            "status": "success",
            "thread": _thread_to_dict(thread),
        })
    except OperationalError as e:
        if "no such table: copilot_threads" in str(e):
            _ensure_copilot_threads_table()
            return create_copilot_thread()
        logger.error(f"Error creating copilot thread: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error creating copilot thread: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/threads/<int:thread_id>", methods=["PUT"])
@login_required
def update_copilot_thread(thread_id: int) -> Response:
    try:
        _ensure_copilot_threads_table()
        thread = CopilotThread.query.filter_by(
            id=thread_id,
            user_id=current_user.id,
        ).first()
        if not thread:
            return jsonify({"status": "error", "message": "Thread not found"}), 404

        payload = request.get_json(silent=True) or {}
        if "messages" in payload:
            messages = payload.get("messages")
            if not isinstance(messages, list):
                return jsonify({
                    "status": "error",
                    "message": "Invalid messages payload",
                }), 400
            try:
                _serialize_json(messages)
            except (TypeError, ValueError):
                return jsonify({
                    "status": "error",
                    "message": "Invalid messages payload",
                }), 400
        if "charts" in payload:
            charts = payload.get("charts")
            if not isinstance(charts, list):
                return jsonify({
                    "status": "error",
                    "message": "Invalid charts payload",
                }), 400
            try:
                _serialize_json(charts)
            except (TypeError, ValueError):
                return jsonify({
                    "status": "error",
                    "message": "Invalid charts payload",
                }), 400
        if "title" in payload:
            thread.title = payload.get("title")
        if "messages" in payload:
            thread.messages_json = _serialize_json(payload.get("messages"))
        if "charts" in payload:
            thread.charts_json = _serialize_json(payload.get("charts"))
        if "session_id" in payload:
            thread.session_id = payload.get("session_id")
        if "last_message" in payload:
            thread.last_message = payload.get("last_message")

        db.session.commit()
        return jsonify({
            "status": "success",
            "thread": _thread_to_dict(thread),
        })
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error updating copilot thread {thread_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/threads/<int:thread_id>", methods=["DELETE"])
@login_required
def delete_copilot_thread(thread_id: int) -> Response:
    try:
        _ensure_copilot_threads_table()
        thread = CopilotThread.query.filter_by(
            id=thread_id,
            user_id=current_user.id,
        ).first()
        if not thread:
            return jsonify({"status": "error", "message": "Thread not found"}), 404

        db.session.delete(thread)
        db.session.commit()
        return jsonify({"status": "success"})
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error deleting copilot thread {thread_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/copilot/threads/clear", methods=["POST"])
@login_required
def clear_copilot_threads() -> Response:
    try:
        _ensure_copilot_threads_table()
        CopilotThread.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({"status": "success"})
    except COPILOT_API_ERRORS as e:
        logger.error(f"Error clearing copilot threads: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
