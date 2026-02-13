"""
Base Agent class for Mises Data Curator agents.

Provides the foundation for specialized data transformation and analysis agents.
Inspired by Data Formulator's agent architecture patterns.
"""

from typing import Optional, Dict, Any, List, Union
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

from .client import MisesLLMClient, get_default_client
from .utils import (
    generate_data_summary,
    extract_code_from_response,
    extract_json_objects,
)
from .sandbox import run_transform_in_sandbox, run_sql_from_string

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Response Types
# =============================================================================

@dataclass
class AgentResponse:
    """
    Standard response structure for all agents.
    
    Follows Data Formulator pattern with status, code, content, and dialog.
    """
    status: str  # "ok", "error", "no_action"
    code: Optional[str] = None  # Generated code (Python or SQL)
    content: Optional[Union[Dict, List, str]] = None  # Parsed response data
    refined_goal: Optional[Dict] = None  # Structured goal from LLM
    dialog: List[Dict] = field(default_factory=list)  # Message history
    error: Optional[str] = None  # Error message if status == "error"
    result_data: Optional[pd.DataFrame] = None  # Execution result if applicable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling DataFrame serialization."""
        result = {
            "status": self.status,
            "code": self.code,
            "content": self.content,
            "refined_goal": self.refined_goal,
            "dialog": self.dialog,
            "error": self.error,
        }
        if self.result_data is not None:
            if isinstance(self.result_data, pd.DataFrame):
                result["result_data"] = self.result_data.to_dict(orient="records")
            else:
                result["result_data"] = self.result_data
        return result


@dataclass
class TableContext:
    """
    Context for a single data table.
    
    Used to pass table information to agents.
    """
    name: str
    df: pd.DataFrame
    description: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format for LLM context."""
        return {
            "name": self.name,
            "rows": self.df.to_dict(orient="records"),
            "description": self.description
        }


# =============================================================================
# Base Agent Class
# =============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents.
    
    Provides common functionality for LLM interaction, code extraction,
    and result handling. Specialized agents override specific methods.
    
    Attributes:
        client: LLM client for API calls
        name: Agent name for logging
        language: Response language ("es" for Spanish, "en" for English)
        max_repair_attempts: Maximum code repair attempts on failure
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        name: str = "BaseAgent",
        language: str = "es",
        max_repair_attempts: int = 3
    ):
        """
        Initialize the agent.
        
        Args:
            client: LLM client instance (uses default if None)
            name: Agent identifier
            language: Output language
            max_repair_attempts: Max auto-repair attempts
        """
        self.client = client or get_default_client()
        self.name = name
        self.language = language
        self.max_repair_attempts = max_repair_attempts
        self.system_prompt = self._get_system_prompt()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        Returns the system prompt for this agent.
        
        Must be implemented by subclasses to define agent behavior.
        """
        pass

    def _build_user_message(
        self,
        goal: str,
        tables: List[TableContext],
        **kwargs
    ) -> str:
        """
        Build the user message for the LLM.
        
        Args:
            goal: User's transformation/analysis goal
            tables: List of input table contexts
            **kwargs: Additional context
            
        Returns:
            Formatted user message string
        """
        # Generate data summary
        table_dicts = [t.to_dict() for t in tables]
        data_summary = generate_data_summary(
            table_dicts, 
            language=self.language
        )
        
        # Build message
        if self.language == "es":
            message = f"""## Datos de Entrada

{data_summary}

## Objetivo

{goal}"""
        else:
            message = f"""## Input Data

{data_summary}

## Goal

{goal}"""
        
        return message

    def run(
        self,
        goal: str,
        tables: List[TableContext],
        execute_code: bool = True,
        **kwargs
    ) -> AgentResponse:
        """
        Execute the agent's main task synchronously.
        
        Args:
            goal: The transformation or analysis goal
            tables: List of input tables
            execute_code: Whether to execute generated code
            **kwargs: Additional parameters
            
        Returns:
            AgentResponse with results
        """
        logger.info(f"Agent {self.name} running: {goal[:50]}...")
        
        # Build messages
        user_message = self._build_user_message(goal, tables, **kwargs)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Call LLM
        try:
            response_text = self.client.get_completion(messages)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return AgentResponse(
                status="error",
                error=str(e),
                dialog=messages
            )
        
        # Parse response
        messages.append({"role": "assistant", "content": response_text})
        
        return self._process_response(
            response_text,
            tables,
            execute_code,
            messages
        )

    def _process_response(
        self,
        response_text: str,
        tables: List[TableContext],
        execute_code: bool,
        dialog: List[Dict]
    ) -> AgentResponse:
        """
        Process LLM response and optionally execute code.
        
        Args:
            response_text: Raw LLM response
            tables: Input tables for execution context
            execute_code: Whether to run extracted code
            dialog: Conversation history
            
        Returns:
            AgentResponse with parsed and executed results
        """
        # Extract JSON objects from response
        json_objects = extract_json_objects(response_text)
        refined_goal = json_objects[0] if json_objects else None
        
        # Extract code blocks
        python_code = extract_code_from_response(response_text, "python")
        sql_code = extract_code_from_response(response_text, "sql")
        
        code = None
        code_type = None
        
        if python_code:
            code = python_code[0]
            code_type = "python"
        elif sql_code:
            code = sql_code[0]
            code_type = "sql"
        
        if not code:
            # No code found - might be a planning or explanation response
            return AgentResponse(
                status="ok",
                content=refined_goal or response_text,
                refined_goal=refined_goal,
                dialog=dialog
            )
        
        # Execute code if requested
        result_data = None
        if execute_code and tables:
            primary_df = tables[0].df
            
            if code_type == "python":
                result = run_transform_in_sandbox(code, primary_df)
            else:  # SQL
                result = run_sql_from_string(code, primary_df, tables[0].name)
            
            if result["success"]:
                result_data = result["result"]
            else:
                # Attempt auto-repair
                result_data = self._attempt_repair(
                    code,
                    code_type,
                    result["error"],
                    primary_df,
                    tables[0].name if code_type == "sql" else None,
                    dialog
                )
        
        return AgentResponse(
            status="ok" if result_data is not None or not execute_code else "error",
            code=code,
            content=refined_goal,
            refined_goal=refined_goal,
            dialog=dialog,
            result_data=result_data,
            error=result.get("error") if not (result_data is not None or not execute_code) else None
        )

    def _attempt_repair(
        self,
        code: str,
        code_type: str,
        error: str,
        df: pd.DataFrame,
        table_name: Optional[str],
        dialog: List[Dict]
    ) -> Optional[pd.DataFrame]:
        """
        Attempt to repair failed code using LLM.
        
        Args:
            code: Failed code
            code_type: "python" or "sql"
            error: Error message
            df: Input DataFrame
            table_name: Table name for SQL
            dialog: Current dialog
            
        Returns:
            Result DataFrame if repair succeeds, None otherwise
        """
        for attempt in range(self.max_repair_attempts):
            logger.info(f"Repair attempt {attempt + 1}/{self.max_repair_attempts}")
            
            if self.language == "es":
                repair_prompt = f"""El código anterior falló con este error:

```
{error}
```

Por favor corrige el código y devuelve solo el código corregido en un bloque ```{code_type}."""
            else:
                repair_prompt = f"""The previous code failed with this error:

```
{error}
```

Please fix the code and return only the corrected code in a ```{code_type} block."""
            
            dialog.append({"role": "user", "content": repair_prompt})
            
            try:
                repair_response = self.client.get_completion(dialog)
            except Exception as e:
                logger.warning(f"Repair LLM call failed: {e}")
                break
            
            dialog.append({"role": "assistant", "content": repair_response})
            
            # Extract repaired code
            repaired_codes = extract_code_from_response(repair_response, code_type)
            if not repaired_codes:
                continue
            
            repaired_code = repaired_codes[0]
            
            # Try executing repaired code
            if code_type == "python":
                result = run_transform_in_sandbox(repaired_code, df)
            else:
                result = run_sql_from_string(repaired_code, df, table_name)
            
            if result["success"]:
                return result["result"]
            
            error = result["error"]
        
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# =============================================================================
# Convenience Functions
# =============================================================================

def create_table_context(
    df: pd.DataFrame,
    name: str = "datos",
    description: str = ""
) -> TableContext:
    """
    Create a TableContext from a DataFrame.
    
    Args:
        df: Input DataFrame
        name: Table name
        description: Optional description
        
    Returns:
        TableContext instance
    """
    return TableContext(name=name, df=df, description=description)
