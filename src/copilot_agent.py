"""
GitHub Copilot SDK Integration for Mises Data Curator.

This module provides integration with the GitHub Copilot SDK to enable
AI-powered data curation capabilities including natural language queries,
automated analysis, and intelligent dataset discovery.

Requirements:
    - GitHub Copilot CLI installed and in PATH
    - github-copilot-sdk Python package
    - OpenRouter API key (for BYOK)

Example:
    >>> from src.copilot_agent import MisesCopilotAgent
    >>> agent = MisesCopilotAgent()
    >>> response = await agent.chat("Show me GDP data for Brazil")
"""

import os
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import Copilot SDK
try:
    from copilot import CopilotClient, CopilotSession
    from copilot import Tool
    COPILOT_SDK_AVAILABLE = True
except ImportError as e:
    COPILOT_SDK_AVAILABLE = False
    print(f"⚠️  Warning: copilot SDK not installed. Run: pip install github-copilot-sdk")
    print(f"   Error: {e}")

from src.config import Config


class MisesCopilotAgent:
    """
    GitHub Copilot SDK client for Mises Data Curator.
    
    This class wraps the GitHub Copilot SDK to provide:
    - Natural language interaction with data
    - Tool calling for data operations
    - Multi-turn conversations with context
    - Streaming responses
    
    Attributes:
        client: CopilotClient instance
        config: Mises configuration
        session: Active session (if any)
        tools: Registered MCP tools
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Copilot agent.
        
        Args:
            config: Mises configuration instance. If None, creates new Config.
        """
        if not COPILOT_SDK_AVAILABLE:
            raise RuntimeError(
                "GitHub Copilot SDK not available. "
                "Install with: pip install github-copilot-sdk"
            )
        
        self.config = config or Config()
        self.client: Optional[CopilotClient] = None
        self.session: Optional[CopilotSession] = None
        self.tools: Dict[str, Any] = {}
        
        # Initialize the client
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Copilot SDK client with BYOK configuration."""
        try:
            # Get configuration
            llm_config = self.config.get_llm_config()
            
            # Check if we should use BYOK (Bring Your Own Key)
            provider = llm_config.get('provider', 'openrouter')
            
            if provider == 'openrouter':
                # Use OpenRouter API key
                api_key = os.getenv('OPENROUTER_API_KEY') or llm_config.get('api_key')
                model = os.getenv('OPENROUTER_MODEL') or llm_config.get('model', 'anthropic/claude-3.5-sonnet')
                
                if not api_key:
                    print("⚠️  Warning: No OpenRouter API key found. Set OPENROUTER_API_KEY in .env")
                    print("   Falling back to GitHub Copilot default (requires Copilot subscription)")
                    
                    # Initialize without BYOK - uses GitHub Copilot subscription
                    self.client = CopilotClient()
                else:
                    # Initialize with BYOK
                    self.client = CopilotClient(
                        api_key=api_key,
                        model=model
                    )
                    print(f"✅ Copilot client initialized with BYOK (model: {model})")
                    
            elif provider == 'ollama':
                # Ollama local deployment
                host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
                model = os.getenv('OLLAMA_MODEL', 'gpt-oss:120b-cloud')
                
                print(f"🦙 Using Ollama at {host} with model {model}")
                # Note: Copilot SDK may not support Ollama directly yet
                # This is a placeholder for future integration
                self.client = CopilotClient()
                
            else:
                # Default initialization
                self.client = CopilotClient()
                print("✅ Copilot client initialized (using GitHub Copilot subscription)")
                
        except Exception as e:
            print(f"❌ Error initializing Copilot client: {e}")
            raise
    
    async def start(self) -> None:
        """Start the Copilot client connection."""
        if self.client:
            await self.client.start()
            print("✅ Copilot client started")
    
    async def stop(self) -> None:
        """Stop the Copilot client connection."""
        if self.client:
            await self.client.stop()
            print("🛑 Copilot client stopped")
    
    async def create_session(
        self, 
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> CopilotSession:
        """
        Create a new chat session.
        
        Args:
            session_id: Optional session ID for persistence
            system_prompt: Optional custom system prompt
            
        Returns:
            Session instance
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call start() first.")
        
        # Default system prompt for data curation
        default_prompt = """You are a data curation assistant for Mises Data Curator.
You help users explore, analyze, and understand economic datasets.
You have access to tools for searching datasets, downloading data, analyzing trends,
and generating visualizations. Always be helpful, accurate, and concise."""
        
        session_config = {
            'model': 'gpt-4',  # Can be overridden
        }
        
        if session_id:
            session_config['session_id'] = session_id
            
        if system_prompt:
            session_config['system_prompt'] = system_prompt
        else:
            session_config['system_prompt'] = default_prompt
        
        self.session = await self.client.create_session(**session_config)
        return self.session
    
    async def chat(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to the Copilot agent.
        
        Args:
            message: User message
            session_id: Optional session ID (creates new if None)
            stream: Whether to stream the response
            
        Returns:
            Response dictionary with text and metadata
        """
        try:
            # Create session if needed
            if not self.session or (session_id and self.session.session_id != session_id):
                await self.create_session(session_id=session_id)
            
            # Send message
            if stream:
                # Streaming response
                response_text = ""
                async for chunk in self.session.send_streaming({'prompt': message}):
                    response_text += chunk.content
                    # Could yield chunks here for real-time updates
                
                return {
                    'status': 'success',
                    'text': response_text,
                    'session_id': self.session.session_id,
                    'streamed': True
                }
            else:
                # Regular response
                response = await self.session.send({'prompt': message})
                
                return {
                    'status': 'success',
                    'text': response.content,
                    'session_id': self.session.session_id,
                    'model': response.model if hasattr(response, 'model') else None,
                    'tools_called': response.tool_calls if hasattr(response, 'tool_calls') else [],
                    'streamed': False
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'text': f"Sorry, I encountered an error: {str(e)}"
            }
    
    def register_tool(self, name: str, function: callable, description: str) -> None:
        """
        Register a tool for the agent to use.
        
        Args:
            name: Tool name
            function: Callable function
            description: Tool description for the LLM
        """
        self.tools[name] = {
            'function': function,
            'description': description
        }
        print(f"🔧 Registered tool: {name}")
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool.
        
        Args:
            tool_name: Name of the tool
            **kwargs: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        
        tool = self.tools[tool_name]
        return await tool['function'](**kwargs)
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available LLM models.
        
        Returns:
            List of model identifiers
        """
        if self.client:
            # This would depend on SDK implementation
            # Typically returns ['gpt-4', 'gpt-4-turbo', 'claude-3-opus', etc.]
            return ['gpt-4', 'gpt-4-turbo-preview', 'claude-3-sonnet', 'claude-3-opus']
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Copilot SDK integration.
        
        Returns:
            Health status dictionary
        """
        status = {
            'sdk_available': COPILOT_SDK_AVAILABLE,
            'client_initialized': self.client is not None,
            'session_active': self.session is not None,
            'tools_registered': len(self.tools),
            'cli_available': self._check_cli_available()
        }
        
        # Overall health
        status['healthy'] = (
            status['sdk_available'] and 
            status['client_initialized'] and 
            status['cli_available']
        )
        
        return status
    
    def _check_cli_available(self) -> bool:
        """Check if GitHub Copilot CLI is available in PATH."""
        import shutil
        return shutil.which('copilot') is not None


# Convenience function for quick testing
async def test_copilot_agent():
    """Quick test function for the Copilot agent."""
    print("🧪 Testing GitHub Copilot SDK Integration")
    print("=" * 50)
    
    try:
        # Initialize agent
        agent = MisesCopilotAgent()
        
        # Health check
        health = agent.health_check()
        print(f"\n🏥 Health Check: {health}")
        
        if not health['healthy']:
            print("❌ Agent not healthy. Check configuration.")
            return
        
        # Start client
        await agent.start()
        
        # Create session and test
        print("\n💬 Testing chat...")
        response = await agent.chat(
            "Hello! Can you help me with economic data analysis?",
            stream=False
        )
        
        if response['status'] == 'success':
            print(f"✅ Success! Response: {response['text'][:100]}...")
            print(f"   Session ID: {response['session_id']}")
        else:
            print(f"❌ Error: {response.get('error', 'Unknown error')}")
        
        # Stop client
        await agent.stop()
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run test if executed directly
    import asyncio
    asyncio.run(test_copilot_agent())
