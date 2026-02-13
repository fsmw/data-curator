"""
Exploration Flow.

Orchestrates the interaction between agents and manages the Data Threads.
"""

from typing import Dict, Any, List, Optional
import logging
import asyncio

from .base import BaseAgent
from .transform import DataTransformAgent
from .exploration import ExplorationAgent

logger = logging.getLogger(__name__)

class ExplorationFlow:
    """
    Manages the data exploration process.
    """
    
    def __init__(self, copilot_agent):
        """
        Args:
            copilot_agent: The main MisesCopilotAgent instance (provides client/session)
        """
        self.copilot_agent = copilot_agent
        self.transform_agent = DataTransformAgent(copilot_agent, name="DataTransformer")
        self.exploration_agent = ExplorationAgent(copilot_agent, name="ExplorationAssistant")
        
    async def run_data_transformation(self, query: str, data_summary: str) -> Dict[str, Any]:
        """
        Run the transformation pipeline: Plan -> Code -> (Execute - handled by caller for now).
        """
        logger.info(f"Starting transformation flow for: {query}")
        result = await self.transform_agent.generate_transform(query, data_summary)
        return result

    async def get_suggestions(self, context: str, history: List[Dict]) -> List[Dict]:
        """
        Get exploration suggestions.
        """
        return await self.exploration_agent.suggest_next_steps(context, history)

# Global router instance (to be initialized)
_flow_instance = None

def get_flow(copilot_agent):
    global _flow_instance
    if _flow_instance is None:
        _flow_instance = ExplorationFlow(copilot_agent)
    return _flow_instance
