"""
Data Transformation Agent.

Generates Python code to transform economic datasets.
Supports both Python (Pandas) and SQL (DuckDB) transformations.
"""

import logging
from typing import Dict, Any, Optional, List

from .base import BaseAgent, AgentResponse, TableContext
from .prompts import (
    TRANSFORM_AGENT_SYSTEM_PROMPT_ES,
    TRANSFORM_AGENT_SYSTEM_PROMPT_EN,
    SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_ES,
    SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_EN,
)
from .client import MisesLLMClient

logger = logging.getLogger(__name__)


class DataTransformAgent(BaseAgent):
    """
    Agent specialized in writing Pandas/SQL code to transform data.
    
    Can generate Python transformations using Pandas or SQL queries
    for DuckDB execution.
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es",
        mode: str = "python",
        **kwargs
    ):
        """
        Initialize the transform agent.
        
        Args:
            client: LLM client
            language: 'es' or 'en'
            mode: 'python' for Pandas, 'sql' for DuckDB
        """
        self.mode = mode
        super().__init__(
            client=client,
            name="DataTransformAgent",
            language=language,
            **kwargs
        )

    def _get_system_prompt(self) -> str:
        """Get the appropriate prompt based on mode and language."""
        if self.mode == "sql":
            if self.language == "es":
                return SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_ES
            return SQL_TRANSFORM_AGENT_SYSTEM_PROMPT_EN
        else:
            if self.language == "es":
                return TRANSFORM_AGENT_SYSTEM_PROMPT_ES
            return TRANSFORM_AGENT_SYSTEM_PROMPT_EN

    def transform(
        self,
        goal: str,
        tables: List[TableContext],
        execute: bool = True
    ) -> AgentResponse:
        """
        Generate and optionally execute a transformation.
        
        Args:
            goal: Transformation goal in natural language
            tables: Input data tables
            execute: Whether to execute the generated code
            
        Returns:
            AgentResponse with code and results
        """
        return self.run(goal, tables, execute_code=execute)

    def set_mode(self, mode: str):
        """
        Switch between Python and SQL mode.
        
        Args:
            mode: 'python' or 'sql'
        """
        if mode in ("python", "sql"):
            self.mode = mode
            self.system_prompt = self._get_system_prompt()
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'python' or 'sql'.")


class SQLTransformAgent(DataTransformAgent):
    """
    Convenience class for SQL-only transformations.
    """
    
    def __init__(self, client: Optional[MisesLLMClient] = None, language: str = "es", **kwargs):
        super().__init__(client=client, language=language, mode="sql", **kwargs)
        self.name = "SQLTransformAgent"
