"""
Mises Agent Architecture.

This package contains the agentic architecture inspired by Data Formulator 
and Data Anvil, implementing specialized agents for data curation, 
transformation, and exploration.

Components:
- client: Unified LLM client (LiteLLM-based)
- utils: Data summary and response parsing utilities
- sandbox: Safe code execution environment
- base: Base agent class and response types
- prompts: System prompts for all agents
- transform: Data transformation agents
- exploration: Data exploration agents
- clean: Data quality and cleaning agents
- report: Report generation agents
- orchestrator: Multi-agent workflow coordination
"""

# Core components
from .client import (
    MisesLLMClient,
    ModelConfig,
    get_default_client,
)

from .utils import (
    generate_data_summary,
    extract_code_from_response,
    extract_json_objects,
    get_field_summary,
    detect_economic_columns,
)

from .sandbox import (
    run_transform_in_sandbox,
    run_sql_from_string,
    run_sql_query,
    validate_code,
    ALLOWED_MODULES,
)

from .base import (
    BaseAgent,
    AgentResponse,
    TableContext,
    create_table_context,
)

from .prompts import (
    get_prompt,
    TRANSFORM_AGENT_SYSTEM_PROMPT_ES,
    SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_ES,
    EXPLORATION_AGENT_SYSTEM_PROMPT_ES,
    DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES,
    REPORT_GEN_AGENT_SYSTEM_PROMPT_ES,
)

# Agent implementations
from .transform import DataTransformAgent, SQLTransformAgent
from .exploration import ExplorationAgent, DataQualityAgent
from .clean import DataCleanAgent, QualityReport, quick_quality_check
from .report import ReportGenAgent, EconomicReport, quick_report

# Orchestration
from .orchestrator import (
    AgentOrchestrator,
    WorkflowResult,
    StepResult,
    WorkflowStep,
    analyze,
    transform,
)

__all__ = [
    # Client
    "MisesLLMClient",
    "ModelConfig",
    "get_default_client",
    # Utils
    "generate_data_summary",
    "extract_code_from_response",
    "extract_json_objects",
    "get_field_summary",
    "detect_economic_columns",
    # Sandbox
    "run_transform_in_sandbox",
    "run_sql_from_string",
    "run_sql_query",
    "validate_code",
    "ALLOWED_MODULES",
    # Base
    "BaseAgent",
    "AgentResponse",
    "TableContext",
    "create_table_context",
    # Prompts
    "get_prompt",
    "TRANSFORM_AGENT_SYSTEM_PROMPT_ES",
    "SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_ES",
    "EXPLORATION_AGENT_SYSTEM_PROMPT_ES",
    "DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES",
    "REPORT_GEN_AGENT_SYSTEM_PROMPT_ES",
    # Transform Agents
    "DataTransformAgent",
    "SQLTransformAgent",
    # Exploration Agents
    "ExplorationAgent",
    "DataQualityAgent",
    # Clean Agents
    "DataCleanAgent",
    "QualityReport",
    "quick_quality_check",
    # Report Agents
    "ReportGenAgent",
    "EconomicReport",
    "quick_report",
    # Orchestration
    "AgentOrchestrator",
    "WorkflowResult",
    "StepResult",
    "WorkflowStep",
    "analyze",
    "transform",
]
