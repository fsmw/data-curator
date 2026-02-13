"""
Exploration Agent.

Suggests follow-up analyses and exploration paths for economic data.
Helps users discover insights by proposing relevant questions.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentResponse, TableContext
from .prompts import EXPLORATION_AGENT_SYSTEM_PROMPT_ES, EXPLORATION_AGENT_SYSTEM_PROMPT_EN
from .utils import generate_data_summary, extract_json_objects
from .client import MisesLLMClient

logger = logging.getLogger(__name__)


class ExplorationAgent(BaseAgent):
    """
    Agent specialized in suggesting exploration paths for economic data.
    
    Analyzes current data context and history to propose relevant
    follow-up questions and analyses.
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es",
        **kwargs
    ):
        """
        Initialize the exploration agent.
        
        Args:
            client: LLM client
            language: 'es' or 'en'
        """
        super().__init__(
            client=client,
            name="ExplorationAgent",
            language=language,
            **kwargs
        )

    def _get_system_prompt(self) -> str:
        """Get the appropriate prompt based on language."""
        if self.language == "es":
            return EXPLORATION_AGENT_SYSTEM_PROMPT_ES
        return EXPLORATION_AGENT_SYSTEM_PROMPT_EN

    def suggest(
        self,
        tables: List[TableContext],
        history: Optional[List[Dict]] = None,
        current_focus: Optional[str] = None
    ) -> AgentResponse:
        """
        Generate exploration suggestions based on data and history.
        
        Args:
            tables: Current data tables
            history: Previous questions/analyses
            current_focus: Current area of focus (optional)
            
        Returns:
            AgentResponse with suggestions
        """
        # Build history text
        history_text = ""
        if history:
            recent = history[-5:]  # Last 5 interactions
            if self.language == "es":
                history_text = "\n## Historial Reciente\n"
            else:
                history_text = "\n## Recent History\n"
            
            for h in recent:
                role = h.get("role", "user")
                content = h.get("content", "")[:200]  # Truncate long content
                history_text += f"- {role}: {content}\n"

        # Build focus text
        focus_text = ""
        if current_focus:
            if self.language == "es":
                focus_text = f"\n## Enfoque Actual\n{current_focus}\n"
            else:
                focus_text = f"\n## Current Focus\n{current_focus}\n"

        # Build goal
        if self.language == "es":
            goal = f"""Analiza los datos proporcionados y sugiere 3-5 análisis o preguntas interesantes para explorar.
{history_text}{focus_text}

Responde con un JSON estructurado con tus sugerencias."""
        else:
            goal = f"""Analyze the provided data and suggest 3-5 interesting analyses or questions to explore.
{history_text}{focus_text}

Respond with a structured JSON with your suggestions."""

        return self.run(goal, tables, execute_code=False)

    def get_suggestions_list(
        self,
        tables: List[TableContext],
        history: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Get suggestions as a simple list.
        
        Args:
            tables: Current data tables
            history: Previous questions/analyses
            
        Returns:
            List of suggestion dictionaries
        """
        response = self.suggest(tables, history)
        
        if response.status != "ok":
            return []
        
        # Try to extract suggestions from content
        if isinstance(response.content, dict):
            # Look for suggestions key
            suggestions = response.content.get(
                "sugerencias", 
                response.content.get("suggestions", [])
            )
            if isinstance(suggestions, list):
                return suggestions
        
        if isinstance(response.content, list):
            return response.content
        
        return []


class DataQualityAgent(BaseAgent):
    """
    Agent specialized in analyzing data quality for economic datasets.
    
    Identifies issues like missing values, outliers, inconsistencies,
    and proposes cleaning strategies.
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es",
        **kwargs
    ):
        super().__init__(
            client=client,
            name="DataQualityAgent",
            language=language,
            **kwargs
        )

    def _get_system_prompt(self) -> str:
        from .prompts import DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES, DATA_CLEAN_AGENT_SYSTEM_PROMPT_EN
        if self.language == "es":
            return DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES
        return DATA_CLEAN_AGENT_SYSTEM_PROMPT_EN

    def analyze(
        self,
        tables: List[TableContext],
        fix_issues: bool = False
    ) -> AgentResponse:
        """
        Analyze data quality and optionally generate fixing code.
        
        Args:
            tables: Data tables to analyze
            fix_issues: Whether to generate cleaning code
            
        Returns:
            AgentResponse with quality analysis
        """
        if self.language == "es":
            goal = """Analiza la calidad de los datos:
1. Identifica valores nulos y patrones de datos faltantes
2. Detecta posibles duplicados
3. Identifica inconsistencias en nombres o formatos
4. Señala posibles outliers o valores atípicos
5. Propón estrategias de limpieza"""
        else:
            goal = """Analyze data quality:
1. Identify null values and missing data patterns
2. Detect possible duplicates
3. Identify inconsistencies in names or formats
4. Flag possible outliers
5. Propose cleaning strategies"""

        return self.run(goal, tables, execute_code=fix_issues)
