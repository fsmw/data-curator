"""
Agent API endpoints.

Exposes the specialized agent capabilities:
- Data Transformation (Python/SQL)
- Data Exploration
- Data Quality Analysis
- Report Generation
- Full Workflow Orchestration
"""

from flask import request, jsonify
import pandas as pd
import io

from . import api_bp

# Import new agent system
from src.agents import (
    DataTransformAgent,
    SQLTransformAgent,
    ExplorationAgent,
    DataCleanAgent,
    ReportGenAgent,
    AgentOrchestrator,
    TableContext,
    create_table_context,
    quick_quality_check,
    quick_report,
)


def _get_orchestrator():
    """Get or create the agent orchestrator."""
    return AgentOrchestrator(language="es")


def _parse_table_from_request(data: dict) -> tuple:
    """
    Parse table data from request.
    
    Supports:
    - 'rows': List of row dicts
    - 'csv': CSV string
    
    Returns:
        Tuple of (DataFrame or None, TableContext or None, error message or None)
    """
    name = data.get('table_name', 'datos')
    description = data.get('description', '')
    
    if 'rows' in data:
        try:
            df = pd.DataFrame(data['rows'])
            ctx = create_table_context(df, name, description)
            return df, ctx, None
        except Exception as e:
            return None, None, f"Error parsing rows: {e}"
    
    if 'csv' in data:
        try:
            df = pd.read_csv(io.StringIO(data['csv']))
            ctx = create_table_context(df, name, description)
            return df, ctx, None
        except Exception as e:
            return None, None, f"Error parsing CSV: {e}"
    
    return None, None, None  # No data provided


# =============================================================================
# Transform Endpoints
# =============================================================================

@api_bp.route('/agent/transform', methods=['POST'])
def agent_transform():
    """
    Generate and execute data transformation code.
    
    Expected JSON:
    {
        "goal": "Calcular crecimiento anual del PIB",
        "rows": [{"pais": "Argentina", "año": 2020, "pib": 389e9}, ...],
        "table_name": "pib_latam",
        "mode": "python",  // or "sql"
        "execute": true
    }
    
    """
    try:
        data = request.get_json()
        
        goal = data.get('goal', '')
        mode = data.get('mode', 'python')
        execute = data.get('execute', True)
        
        if not goal:
            return jsonify({
                "status": "error", 
                "message": "Missing 'goal' parameter"
            }), 400
        
        # Parse table data
        df, table_ctx, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided. Use 'rows' or 'csv' parameter."
            }), 400
        
        # Create agent and run
        if mode == "sql":
            agent = SQLTransformAgent(language="es")
        else:
            agent = DataTransformAgent(language="es")
        
        response = agent.transform(goal, [table_ctx], execute=execute)
        
        result = {
            "status": response.status,
            "code": response.code,
            "refined_goal": response.refined_goal,
        }
        
        if response.result_data is not None:
            result["result"] = response.result_data.to_dict(orient="records")
            result["result_rows"] = len(response.result_data)
        
        if response.error:
            result["error"] = response.error
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/agent/transform/sql', methods=['POST'])
def agent_transform_sql():
    """
    SQL-specific transformation endpoint.
    
    Same as /agent/transform but forces SQL mode.
    """
    data = request.get_json() or {}
    data['mode'] = 'sql'
    # Reuse main transform endpoint
    with api_bp.test_request_context(json=data):
        return agent_transform()


# =============================================================================
# Exploration Endpoints
# =============================================================================

@api_bp.route('/agent/suggest', methods=['POST'])
def agent_suggest():
    """
    Get exploration suggestions based on current data.
    
    Expected JSON:
    {
        "rows": [...],
        "table_name": "datos",
        "history": [{"role": "user", "content": "..."}],
        "focus": "optional focus area"
    }
    
    """
    try:
        data = request.get_json()
        history = data.get('history', [])
        focus = data.get('focus')
        
        # Parse table data
        df, table_ctx, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided. Use 'rows' or 'csv' parameter."
            }), 400
        
        # Create agent and run
        agent = ExplorationAgent(language="es")
        suggestions = agent.get_suggestions_list([table_ctx], history)
        
        return jsonify({
            "status": "ok",
            "suggestions": suggestions
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Quality Analysis Endpoints
# =============================================================================

@api_bp.route('/agent/quality', methods=['POST'])
def agent_quality():
    """
    Analyze data quality and get recommendations.
    
    Expected JSON:
    {
        "rows": [...],
        "table_name": "datos",
        "generate_code": false
    }
    """
    try:
        data = request.get_json()
        
        df, table_ctx, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        name = data.get('table_name', 'datos')
        
        # Fast quality check (no LLM)
        report = quick_quality_check(df, name)
        
        return jsonify({
            "status": "ok",
            "quality_report": report
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/agent/clean', methods=['POST'])
def agent_clean():
    """
    Clean data with specified strategy.
    
    Expected JSON:
    {
        "rows": [...],
        "strategy": "auto",  // auto, drop, mean, median, mode
        "remove_duplicates": true
    }
    """
    try:
        data = request.get_json()
        
        df, _, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        strategy = data.get('strategy', 'auto')
        remove_dups = data.get('remove_duplicates', True)
        
        # Clean data
        agent = DataCleanAgent(language="es")
        
        result_df = agent.clean_nulls(df, strategy=strategy)
        if remove_dups:
            result_df = agent.remove_duplicates(result_df)
        
        return jsonify({
            "status": "ok",
            "original_rows": len(df),
            "cleaned_rows": len(result_df),
            "rows_removed": len(df) - len(result_df),
            "result": result_df.to_dict(orient="records")
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Report Generation Endpoints
# =============================================================================

@api_bp.route('/agent/report', methods=['POST'])
def agent_report():
    """
    Generate analysis report.
    
    Expected JSON:
    {
        "rows": [...],
        "table_name": "datos",
        "topic": "Análisis PIB LATAM",
        "format": "markdown"  // or "json"
    }
    """
    try:
        data = request.get_json()
        
        df, table_ctx, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        topic = data.get('topic', 'Análisis de Datos')
        output_format = data.get('format', 'json')
        name = data.get('table_name', 'datos')
        
        # Generate report
        report_md = quick_report(df, topic)
        
        if output_format == 'markdown':
            return jsonify({
                "status": "ok",
                "report": report_md,
                "format": "markdown"
            })
        else:
            # Parse markdown to structured format
            agent = ReportGenAgent(language="es")
            report_obj = agent.generate_quick_report(df, name, topic)
            
            return jsonify({
                "status": "ok",
                "report": report_obj.to_dict(),
                "format": "json"
            })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Workflow Endpoints
# =============================================================================

@api_bp.route('/agent/analyze', methods=['POST'])
def agent_analyze():
    """
    Run full analysis workflow on dataset.
    
    Expected JSON:
    {
        "rows": [...],
        "table_name": "datos",
        "description": "...",
        "clean_data": true,
        "generate_report": true
    }
    """
    try:
        data = request.get_json()
        
        df, _, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        name = data.get('table_name', 'datos')
        description = data.get('description', '')
        clean_data = data.get('clean_data', True)
        generate_report = data.get('generate_report', True)
        
        # Run workflow
        orchestrator = _get_orchestrator()
        result = orchestrator.analyze_dataset(
            df, name, description,
            clean_data=clean_data,
            generate_report=generate_report
        )
        
        response = {
            "status": "ok" if result.success else "error",
            "workflow": result.workflow_name,
            "steps": [
                {
                    "name": s.step_name,
                    "type": s.step_type.value,
                    "success": s.success,
                    "error": s.error,
                    "metadata": s.metadata
                }
                for s in result.steps
            ]
        }
        
        if result.final_report:
            response["report"] = result.final_report
        
        if result.final_data is not None:
            response["result_rows"] = len(result.final_data)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/agent/workflow', methods=['POST'])
def agent_workflow():
    """
    Run custom workflow with specified steps.
    
    Expected JSON:
    {
        "rows": [...],
        "table_name": "datos",
        "steps": [
            {"type": "clean", "config": {"strategy": "auto"}},
            {"type": "transform", "config": {"goal": "..."}},
            {"type": "report", "config": {"topic": "..."}}
        ]
    }
    """
    try:
        data = request.get_json()
        
        df, _, error = _parse_table_from_request(data)
        
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        if df is None:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        name = data.get('table_name', 'datos')
        steps = data.get('steps', [])
        
        if not steps:
            return jsonify({
                "status": "error",
                "message": "No workflow steps provided"
            }), 400
        
        # Run workflow
        orchestrator = _get_orchestrator()
        result = orchestrator.run_workflow(df, steps, name)
        
        response = {
            "status": "ok" if result.success else "error",
            "workflow": "custom",
            "steps": [
                {
                    "name": s.step_name,
                    "type": s.step_type.value,
                    "success": s.success,
                    "error": s.error,
                    "result": s.result if not isinstance(s.result, pd.DataFrame) else None,
                    "metadata": s.metadata
                }
                for s in result.steps
            ]
        }
        
        if result.final_report:
            response["report"] = result.final_report
        
        if result.final_data is not None:
            response["result"] = result.final_data.to_dict(orient="records")
            response["result_rows"] = len(result.final_data)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
