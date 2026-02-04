"""
Data Transformation Agent.
Responsible for generating Python code to transform datasets.
"""

import json
import logging
from typing import Dict, Any, Optional
from .base import BaseAgent
from .prompts import TRANSFORM_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class DataTransformAgent(BaseAgent):
    """
    Agent specialized in writing Pandas code to transform data.
    """

    def _get_system_prompt(self) -> str:
        return TRANSFORM_AGENT_SYSTEM_PROMPT

    async def generate_transform(self, query: str, data_summary: str) -> Dict[str, Any]:
        """
        Generate a transformation plan and code.
        
        Args:
            query: User's goal (e.g. "Aggregate by year")
            data_summary: String description of the input dataframe
            
        Returns:
            Dict containing 'code', 'plan', etc.
        """
        
        user_message = f"""
[DATA SUMMARY]
{data_summary}

[GOAL]
{query}

Please generate the transformation plan and code. Response in JSON format.
"""
        # Execute LLM call
        response = await self.run(user_message)
        
        # Parse output
        text = response.get('text', '')
        try:
            # simple cleanup for code blocks if the LLM puts json inside markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[0].strip()
            
            result = json.loads(text)
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from transform agent: {text}")
            return {
                "status": "error",
                "message": "Failed to parse agent response",
                "raw_text": text
            }
        except Exception as e:
             logger.error(f"Error in transform agent: {e}")
             return {
                "status": "error",
                "message": str(e)
             }
