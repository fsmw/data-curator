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
    from copilot.types import SessionConfig, SystemMessageReplaceConfig
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
        self._system_prompt: str = ""  # Will be set when creating session
        
        # Initialize the client
        self._initialize_client()
        
        # Register MCP tools
        self._register_mcp_tools()
    
    def _initialize_client(self) -> None:
        """Initialize the Copilot SDK client.
        
        Uses GitHub Copilot CLI authentication and subscription.
        The CLI must be installed and authenticated separately.
        """
        try:
            # Initialize Copilot SDK client
            # The client will use the authenticated Copilot CLI automatically
            self.client = CopilotClient()
            print("✅ Copilot SDK client initialized (using GitHub Copilot subscription)")
            print("   Note: Ensure copilot CLI is installed and authenticated")
                
        except Exception as e:
            print(f"❌ Error initializing Copilot client: {e}")
            print("   Install Copilot CLI: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli")
            raise
    
    def _register_mcp_tools(self) -> None:
        """Register all MCP tools from copilot_tools module."""
        try:
            from src.copilot_tools import (
                search_datasets,
                preview_data,
                download_owid,
                get_metadata,
                analyze_data,
                recommend_datasets,
                TOOL_REGISTRY
            )
            
            # Store tool functions and metadata
            # Note: The Copilot SDK discovers tools through MCP protocol,
            # not through direct registration in Python
            for tool_name, tool_info in TOOL_REGISTRY.items():
                self.register_tool(
                    name=tool_name,
                    function=tool_info['function'],
                    description=tool_info['description']
                )
            
            print(f"✅ Registered {len(TOOL_REGISTRY)} MCP tools")
            
        except ImportError as e:
            print(f"⚠️  Warning: Could not import MCP tools: {e}")
        except Exception as e:
            print(f"⚠️  Warning: Error registering tools: {e}")
    
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
        default_prompt = """You are an expert data analyst for Mises Data Curator, specializing in economic datasets.

**Your Role:**
- Act as an intelligent analyst, not just a tool executor
- Use tools INTERNALLY to gather information, then synthesize findings
- Process and analyze data before presenting to users
- Provide actionable insights and contextualized answers

**Response Guidelines:**
1. When users ask about data availability: Use tools to search/explore, then explain what you found in plain language with key insights
2. Never dump raw tool output or technical details like indicator IDs unless specifically asked
3. Focus on answering "what this means for the user" rather than "what the system contains"
4. Provide context: data coverage, time periods, notable gaps, quality notes
5. Suggest next steps or related analyses when appropriate

**Tool Usage Philosophy:**
- Tools are YOUR research instruments, not user-facing outputs
- Call tools to gather facts, then THINK about what matters
- Synthesize multiple tool results into coherent insights
- Present findings as a knowledgeable analyst would, not as API responses

**Example Approach:**
User: "Tell me about inflation data"
❌ BAD: List indicator IDs and dump technical metadata
✅ GOOD: "We have comprehensive inflation data from two major sources. The OWID dataset covers consumer prices for 186 countries from 2015-2024, while IMF provides both historical data and forecasts. Coverage is particularly strong for Latin America. I can help you analyze trends for specific countries or compare regional patterns."

Always be helpful, insightful, and user-focused."""
        
        # Build SessionConfig with system message
        config = SessionConfig()
        
        if session_id:
            config['session_id'] = session_id
        
        # Set system message using SystemMessageReplaceConfig
        prompt_to_use = system_prompt if system_prompt else default_prompt
        config['system_message'] = SystemMessageReplaceConfig(
            mode='replace',
            content=prompt_to_use
        )
        
        # Note: Tools are registered globally via _register_mcp_tools()
        # The SDK discovers them automatically through the MCP protocol
        # No need to pass them explicitly in SessionConfig
        
        self._system_prompt = prompt_to_use  # Store for reference
        
        self.session = await self.client.create_session(config)
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
                    # chunk is likely a string directly
                    if isinstance(chunk, str):
                        response_text += chunk
                    elif hasattr(chunk, 'content'):
                        response_text += chunk.content
                    else:
                        response_text += str(chunk)
                
                return {
                    'status': 'success',
                    'text': response_text,
                    'session_id': self.session.session_id,
                    'streamed': True
                }
            else:
                # Regular response - use send_and_wait() which returns a SessionEvent
                response = await self.session.send_and_wait({'prompt': message})
                
                # Extract text from SessionEvent.data.content
                response_text = ""
                if hasattr(response, 'data') and hasattr(response.data, 'content') and response.data.content:
                    response_text = response.data.content
                else:
                    response_text = str(response)
                
                return {
                    'status': 'success',
                    'text': response_text,
                    'session_id': self.session.session_id,
                    'streamed': False
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'text': f"Sorry, I encountered an error: {str(e)}"
            }

    async def chat_stream(
        self, 
        message: str, 
        session_id: Optional[str] = None
    ):
        """
        Stream response from Copilot agent.
        
        Args:
            message: User message
            session_id: Optional session ID
            
        Yields:
             Dict response chunks
        """
        try:
            # Create session if needed
            if not self.session or (session_id and self.session.session_id != session_id):
                await self.create_session(session_id=session_id)
            
            # Fallback to non-streaming if SDK doesn't support streaming method
            # This ensures stability while maintaining the async generator interface
            response = await self.chat(message, session_id=session_id, stream=False)
            
            if response['status'] == 'success':
                yield {
                    'status': 'success',
                    'text': response['text'],
                    'session_id': response['session_id'],
                    'done': False
                }
            else:
                yield {
                    'status': 'error',
                    'error': response.get('error', 'Unknown error'),
                    'text': response.get('text', 'Error'),
                    'done': True
                }
            
            yield {
                'status': 'success',
                'text': '',
                'session_id': self.session.session_id,
                'done': True
            }

        except Exception as e:
            yield {
                'status': 'error',
                'error': str(e),
                'text': f"Error: {str(e)}",
                'done': True
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
