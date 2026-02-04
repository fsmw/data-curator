"""
Base Agent class for Mises Data Curator agents.
"""

from typing import Optional, Dict, Any, List, Generator, AsyncGenerator
import logging
from abc import ABC, abstractmethod

# Avoid circular imports - type checking only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.copilot_agent import MisesCopilotAgent

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents.
    
    Attributes:
        client: Reference to the main MisesCopilotAgent (or its underlying client)
        system_prompt: The specific system prompt for this agent's role
        name: Name of the agent for logging
    """

    def __init__(self, client: 'MisesCopilotAgent', name: str = "BaseAgent"):
        self.client = client
        self.name = name
        self.system_prompt = self._get_system_prompt()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Returns the system prompt for this agent."""
        pass

    async def run(self, message: str, context: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's main task.
        
        Args:
            message: The user input or instruction
            context: Additional context (dataset metadata, previous code, etc.)
            
        Returns:
            Structured response dictionary
        """
        logger.info(f"Agent {self.name} running with message: {message[:50]}...")
        
        # Construct the full prompt combining system prompt, context, and message
        # Note: In Data Formulator, this logic is specialized per agent.
        # Here we provide a default chat implementation.
        
        response = await self.client.chat(
            message=message,
            session_id=None, # Agents might manage their own sessions or be stateless
            stream=False
        )
        
        return response

    async def run_stream(self, message: str, context: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Execute the agent's main task with streaming.
        """
        logger.info(f"Agent {self.name} streaming with message: {message[:50]}...")
        
        # Since MisesCopilotAgent.chat manages the session wrapper,
        # we might need a lower-level call if we want custom system prompts per turn.
        # But MisesCopilotAgent currently sets system prompt on session creation.
        # We might need to extend MisesCopilotAgent to support ephemeral system prompts 
        # or manage separate sessions per agent.
        
        # For now, we assume we create a NEW session for this task 
        # (or reuse one if passed in kwargs) with the agent's system prompt.
        
        session_id = kwargs.get('session_id')
        
        # Ensure we have a session with the RIGHT system prompt
        # This interaction implies MisesCopilotAgent needs a method to 
        # "chat with specific system prompt" or we manually create a session using client.create_session
        
        # We will delegate to client.chat for now, but in implementation we will need 
        # to ensure the session is configured correctly.
        
        # Check if client has a way to set system prompt for a new session
        if hasattr(self.client, 'create_session'):
             # Create a specialized session for this agent interaction
             # Use a distinct session_id based on agent name if not provided
             agent_session_id = session_id or f"{self.name}-{hash(message)}"
             
             # Only if we don't have an active session or it's a new interaction
             # Ideally we keep session alive for multi-turn agent conversations
             # But for single-shot "Task Agents", new session is safer for clean context.
             await self.client.create_session(
                 session_id=agent_session_id,
                 system_prompt=self.system_prompt
             )
             session_id = agent_session_id

        # Stream response
        # Using private access to client helper if available, or just chat
        
        response_dict = await self.client.chat(
            message=message,
            session_id=session_id,
            stream=True
        )
        
        # The MisesCopilotAgent.chat returns a dict with 'text' when stream=True? 
        # Wait, checking implementation:
        # if stream: async for chunk in self.session.send_streaming...
        # Returns: {'status': 'success', 'text': full_text, ...} 
        # It ACCUMULATES text then returns. It does NOT yield chunks to the caller of chat().
        
        # We need to fix MisesCopilotAgent to support real streaming (yielding generator)
        # or access the underlying session directly.
        pass 
