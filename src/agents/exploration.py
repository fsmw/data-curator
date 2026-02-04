"""
Exploration Agent.
Responsible for suggesting follow-up analysis.
"""

import json
import logging
from typing import Dict, Any, List
from .base import BaseAgent
from .prompts import EXPLORATION_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class ExplorationAgent(BaseAgent):
    """
    Agent specialized in suggesting exploration paths.
    """

    def _get_system_prompt(self) -> str:
        return EXPLORATION_AGENT_SYSTEM_PROMPT

    async def suggest_next_steps(self, context: str, history: List[Dict]) -> List[Dict]:
        """
        Suggest next best actions.
        """
        history_text = "\n".join([f"{h['role']}: {h['content']}" for h in history[-5:]])
        
        user_message = f"""
[CURRENT CONTEXT]
{context}

[HISTORY]
{history_text}

Suggest 3-4 follow-up questions in JSON format.
"""
        response = await self.run(user_message)
        text = response.get('text', '')
        
        try:
             if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            
             result = json.loads(text)
             return result
        except Exception as e:
            logger.error(f"Error parsing exploration suggestions: {e}")
            return []
