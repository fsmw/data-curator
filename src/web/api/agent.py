"""
Agent API endpoints.
Exposes the specialized agent capabilities (Transformation, Exploration).
"""

from flask import request, jsonify
from . import api_bp
from src.agents.flow import get_flow
# We reuse the global copilot agent provider to initialize the flow
from .copilot import create_copilot_agent

@api_bp.route('/agent/transform', methods=['POST'])
def agent_transform():
    """
    Generate data transformation code based on natural language query.
    Expected JSON: { "query": "STR", "data_summary": "STR" }
    """
    try:
        data = request.get_json()
        query = data.get('query')
        data_summary = data.get('data_summary')
        
        if not query or not data_summary:
            return jsonify({"status": "error", "message": "Missing query or data_summary"}), 400

        copilot_agent = create_copilot_agent()
        if not copilot_agent:
             return jsonify({"status": "error", "message": "Copilot backend unavailable"}), 503

        flow = get_flow(copilot_agent)
        
        # Async execution in sync flask
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(flow.run_data_transformation(query, data_summary))
        finally:
            loop.close()
            
        return jsonify({"status": "success", "result": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/agent/suggest', methods=['POST'])
def agent_suggest():
    """
    Get exploration suggestions.
    Expected JSON: { "context": "STR", "history": [List of Dict] }
    """
    try:
        data = request.get_json()
        context = data.get('context', '')
        history = data.get('history', [])
        
        copilot_agent = create_copilot_agent()
        if not copilot_agent:
             return jsonify({"status": "error", "message": "Copilot backend unavailable"}), 503

        flow = get_flow(copilot_agent)
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(flow.get_suggestions(context, history))
        finally:
            loop.close()
            
        return jsonify({"status": "success", "suggestions": result})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
