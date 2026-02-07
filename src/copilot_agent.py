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
import asyncio
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import dataclass

# Import Copilot SDK
try:
    from copilot import CopilotClient, CopilotSession
    from copilot import Tool
    from copilot.types import SessionConfig, SystemMessageAppendConfig
    COPILOT_SDK_AVAILABLE = True
except ImportError as e:
    COPILOT_SDK_AVAILABLE = False
    print(f"⚠️  Warning: copilot SDK not installed. Run: pip install github-copilot-sdk")
    print(f"   Error: {e}")

from src.config import Config


@dataclass
class RetryConfig:
    """Configuration for retry and fallback behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 8.0   # Max delay between retries
    timeout: float = 45.0    # Timeout per attempt in seconds
    
    # Fallback model chain - try these if primary fails
    fallback_models: tuple = (
        'gpt-4.1',          # Fastest GPT
        'claude-haiku-4.5',  # Fastest Claude
    )


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


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
        self._session_tools: List[Tool] = []
        self._tool_names: List[str] = []
        self._rag_store = None
        self._rag_embedding = None

        self.logger = logging.getLogger(__name__)
        
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
            
            # Build SDK tool definitions for session registration
            self._session_tools = [
                self._build_sdk_tool(tool_name, tool_info)
                for tool_name, tool_info in TOOL_REGISTRY.items()
            ]
            self._tool_names = [tool.name for tool in self._session_tools]

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
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> CopilotSession:
        """
        Create a new chat session.
        
        Args:
            session_id: Optional session ID for persistence
            system_prompt: Optional custom system prompt
            model: Optional model ID to use (e.g., 'gpt-4o', 'claude-3.5-sonnet')
            
        Returns:
            Session instance
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call start() first.")
        
        # Optimized system prompt for data curation (reduced tokens for faster responses)
        default_prompt = """You are a data analyst for Mises Data Curator, specializing in economic datasets.

**Core Guidelines:**
- Act as an intelligent analyst, not just a tool executor
- Use tools to gather info, then synthesize findings
- Provide actionable insights in plain language
- Focus on what matters to users, not technical details

**Response Style:**
1. Search/explore data using tools, then explain findings clearly
2. Never dump raw output or technical IDs unless asked
3. Provide context: coverage, time periods, notable gaps
4. Suggest relevant next steps when appropriate

**Tools Available:**
- list_available_tools: list all available tools (use when asked "qué tools tienes")
- list_local_datasets: list what the user has locally (cataloged). Call this FIRST when they ask to "review my datasets" or "propose analyses crossing multiple datasets".
- search_datasets: find datasets by query/source/topic
- semantic_search_datasets: find datasets by semantic similarity (e.g. "like real wages")
- preview_data: preview rows and schema for a dataset (use id from list_local_datasets)
- run_sql_query: run SQL SELECT queries on sampled data (table name 'dataset')
- fork_dataset: create a fork marked as edited
- get_dataset_versions: list versions for an identifier
- get_dataset_statistics: catalog stats without loading full file
- export_preview_csv: export a preview CSV (first N rows)
- list_datasets_with_filters: list datasets by source/topic/edited/latest
- download_owid: download OWID data by slug
- get_metadata: fetch dataset metadata and schema
- analyze_data: automated analysis (summary/trends/outliers/correlations)
- recommend_datasets: find related datasets

**When the user asks to "revisar mis datasets" or "propuestas de análisis multi-dataset":**
1. Call list_local_datasets() to see what they have (cataloged + any uncataloged CSVs).
2. From the list, propose concrete analyses (e.g. "puedes cruzar dataset X con Y por país y año") and offer to run preview_data or analyze_data on specific ids. If there are uncataloged_files, suggest they run "curate index" so those appear in the catalog.

**When you suggest specific charts (e.g. in "Propuestas de Análisis Cruzado" or any "Gráfico: ..." line):**
1. **Inline button:** Wherever you describe a chart in the text (e.g. "Gráfico: Línea: Entrada vs Salida de IED en el tiempo" or "Gráfico: Mapa: Conflictos (color intensidad)..."), put the marker [GRAFICAR:N] immediately after that description. N is the 0-based index of that chart in the chart_suggestions array (so the first chart you describe is [GRAFICAR:0], the second [GRAFICAR:1], etc.). This makes a "Graficar" button appear right there in the text.
2. **Block at the end:** At the end of your message, add a single fenced code block with language `chart_suggestions` and a JSON array in the SAME order as the [GRAFICAR:0], [GRAFICAR:1], ... in the text:
```chart_suggestions
[
  {"type": "line", "title": "Entrada vs Salida IED", "dataset_ids": [121, 131], "encodings": {"x": "year", "y": "value"}},
  {"type": "scatter_compare", "title": "Correlación GDP vs HDI", "dataset_ids": [133, 117]}
]
```
- type: "scatter", "line", "bar", "area", "bubble", "scatter_compare", or "map"/"mapa".
- title: short label.
- dataset_ids: one ID for single-dataset, two for scatter_compare (eje X, eje Y).
- encodings: always include x and y when the chart type needs them. Use axes that make sense: for line/area charts use x=year (or time) and y=the numeric metric (e.g. GDP, HDI, life expectancy), never put year on the Y-axis. For scatter use x and y as two numeric metrics. Field names must match the dataset columns exactly (e.g. "GDP per capita", "year", "Human Development Index").

**Tool Philosophy:**
- Use tools to answer factual questions; never guess what datasets exist—call list_local_datasets or search_datasets first when in doubt.
- Synthesize multiple tool outputs into clear, actionable answers.

Always be helpful, insightful, and concise."""
        
        # Build SessionConfig with system message
        config = SessionConfig()
        
        if session_id:
            config['session_id'] = session_id
        
        # Set model if provided
        if model:
            config['model'] = model  # type: ignore
        
        # Append to default system prompt to preserve SDK tool guidance
        prompt_to_use = system_prompt if system_prompt else default_prompt
        config['system_message'] = SystemMessageAppendConfig(
            mode='append',
            content=prompt_to_use
        )

        # Register tools for this session if available
        if self._session_tools:
            config['tools'] = self._session_tools
            config['available_tools'] = [tool.name for tool in self._session_tools]

            config['custom_agents'] = [
                {
                    "name": "mises-data-curator",
                    "display_name": "Mises Data Curator",
                    "description": "Agent with dataset tools for economic data curation",
                    "tools": [tool.name for tool in self._session_tools],
                    "prompt": prompt_to_use,
                    "infer": True
                }
            ]

            config['hooks'] = {
                "on_pre_tool_use": self._on_pre_tool_use,
                "on_post_tool_use": self._on_post_tool_use,
                "on_error_occurred": self._on_error_occurred
            }
        
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
        stream: bool = False,
        model: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the Copilot agent with retry and fallback support.
        
        Args:
            message: User message
            session_id: Optional session ID (creates new if None)
            stream: Whether to stream the response
            model: Optional model ID to use
            retry_config: Optional retry configuration
            
        Returns:
            Response dictionary with text, metadata, and retry info
        """
        config = retry_config or DEFAULT_RETRY_CONFIG
        errors = []
        models_tried = []
        
        # Build model chain: primary model + fallbacks
        model_chain = [model] if model else [None]  # None = use session default
        model_chain.extend(config.fallback_models)
        
        for model_idx, current_model in enumerate(model_chain):
            if model_idx > 0:
                print(f"🔄 Falling back to model: {current_model}")
            
            models_tried.append(current_model or "default")
            
            # Retry loop for current model
            for attempt in range(config.max_retries):
                try:
                    # Calculate delay with exponential backoff
                    if attempt > 0:
                        delay = min(config.base_delay * (2 ** (attempt - 1)), config.max_delay)
                        print(f"⏳ Retry attempt {attempt + 1}/{config.max_retries} after {delay:.1f}s delay...")
                        await asyncio.sleep(delay)
                    
                    # Attempt the request with timeout
                    response = await self._chat_single_attempt(
                        message=message,
                        session_id=session_id,
                        stream=stream,
                        model=current_model,
                        timeout=config.timeout
                    )
                    
                    if response.get('status') == 'success':
                        # Add retry metadata
                        response['retry_info'] = {
                            'attempts': attempt + 1,
                            'model_used': current_model or "default",
                            'models_tried': models_tried,
                            'used_fallback': model_idx > 0
                        }
                        return response
                    else:
                        # Non-timeout error - still record it
                        error_msg = response.get('error', 'Unknown error')
                        errors.append(f"Attempt {attempt + 1}: {error_msg}")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {config.timeout}s"
                    errors.append(f"Attempt {attempt + 1} ({current_model or 'default'}): {error_msg}")
                    print(f"⏰ {error_msg}")
                    
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"Attempt {attempt + 1}: {error_msg}")
                    print(f"❌ Error: {error_msg}")
                    
                    # If it's a rate limit or overload, try fallback immediately
                    if 'overloaded' in error_msg.lower() or 'rate limit' in error_msg.lower():
                        print("🔄 Model overloaded, trying fallback...")
                        break  # Break retry loop, try next model
            
            # If all retries failed for this model, try next one
            print(f"❌ All retries exhausted for model: {current_model or 'default'}")
        
        # All models and retries exhausted
        return {
            'status': 'error',
            'error': 'All retry attempts and model fallbacks exhausted',
            'text': self._build_friendly_error_message(errors, models_tried),
            'retry_info': {
                'attempts': sum(1 for e in errors),
                'models_tried': models_tried,
                'errors': errors[-3:],  # Last 3 errors
                'suggestion': 'Try using a faster model or simplifying your request'
            }
        }
    
    async def _chat_single_attempt(
        self,
        message: str,
        session_id: Optional[str],
        stream: bool,
        model: Optional[str],
        timeout: float
    ) -> Dict[str, Any]:
        """Single chat attempt with timeout."""
        try:
            # Create session if needed
            if not self.session or (session_id and self.session.session_id != session_id):
                await self.create_session(session_id=session_id, model=model)

            # Lightweight tool-augmented fallback for dataset queries
            augmented_message, tool_event = await self._maybe_augment_prompt(message)
            
            # Wrap the actual call with timeout
            if stream:
                # Streaming response
                response_text = ""
                
                async def stream_with_timeout():
                    nonlocal response_text
                    async for chunk in self.session.send_streaming({'prompt': augmented_message}):
                        if isinstance(chunk, str):
                            response_text += chunk
                        elif hasattr(chunk, 'content'):
                            response_text += chunk.content
                        else:
                            response_text += str(chunk)
                    return response_text
                
                await asyncio.wait_for(stream_with_timeout(), timeout=timeout)
                
                response_payload = {
                    'status': 'success',
                    'text': response_text,
                    'response': response_text,
                    'session_id': self.session.session_id,
                    'streamed': True
                }
                if tool_event:
                    response_payload['tools_called'] = [tool_event['name']]
                    response_payload['fallback_used'] = True
                return response_payload
            else:
                # Regular response with timeout
                response = await asyncio.wait_for(
                    self.session.send_and_wait({'prompt': augmented_message}),
                    timeout=timeout
                )
                
                # Extract text from SessionEvent.data.content
                response_text = ""
                if hasattr(response, 'data') and hasattr(response.data, 'content') and response.data.content:
                    response_text = response.data.content
                else:
                    response_text = str(response)
                
                response_payload = {
                    'status': 'success',
                    'text': response_text,
                    'response': response_text,
                    'session_id': self.session.session_id,
                    'streamed': False
                }
                if tool_event:
                    response_payload['tools_called'] = [tool_event['name']]
                    response_payload['fallback_used'] = True
                return response_payload
                
        except asyncio.TimeoutError:
            raise  # Re-raise for handling in caller
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'text': f"Error: {str(e)}"
            }
    
    def _build_friendly_error_message(self, errors: List[str], models_tried: List[str]) -> str:
        """Build a user-friendly error message."""
        msg = "⚠️ **Request failed after multiple attempts**\n\n"
        msg += f"Tried {len(models_tried)} model(s): {', '.join(models_tried)}\n\n"
        msg += "**Suggestions:**\n"
        msg += "- Try a simpler question\n"
        msg += "- Select a faster model (GPT-4.1 or Claude Haiku)\n"
        msg += "- Wait a moment and try again\n\n"
        msg += f"Last error: {errors[-1] if errors else 'Unknown'}"
        return msg

    async def chat_stream(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Stream response from Copilot agent with thinking process.
        
        Args:
            message: User message
            session_id: Optional session ID
            model: Optional model ID to use
            
        Yields:
             Dict response chunks with thinking process
        """
        try:
            # Create session if needed
            if not self.session or (session_id and self.session.session_id != session_id):
                await self.create_session(session_id=session_id, model=model)

            # Lightweight tool-augmented fallback for dataset queries
            augmented_message, tool_event = await self._maybe_augment_prompt(message)
            
            # Try to use actual streaming if available
            try:
                if tool_event:
                    yield {
                        'status': 'success',
                        'session_id': self.session.session_id,
                        'done': False,
                        'fallback_used': True,
                        'tool_use': {
                            'name': tool_event['name'],
                            'input': tool_event.get('input')
                        }
                    }
                    yield {
                        'status': 'success',
                        'session_id': self.session.session_id,
                        'done': False,
                        'fallback_used': True,
                        'tool_result': tool_event.get('result')
                    }

                async for event in self.session.send_streaming({'prompt': augmented_message}):
                    # Parse the event to extract different types of content
                    chunk_data = {
                        'status': 'success',
                        'session_id': self.session.session_id,
                        'done': False
                    }
                    
                    # Check if this is a text chunk
                    if isinstance(event, str):
                        chunk_data['text'] = event
                    elif hasattr(event, 'content'):
                        chunk_data['text'] = event.content
                    elif hasattr(event, 'type'):
                        # Handle different event types
                        if event.type == 'thinking' or event.type == 'thought':
                            chunk_data['thinking'] = {
                                'type': event.type,
                                'content': getattr(event, 'content', str(event))
                            }
                        elif event.type == 'tool_use':
                            chunk_data['tool_use'] = {
                                'name': getattr(event, 'name', 'unknown'),
                                'input': getattr(event, 'input', None)
                            }
                        elif event.type == 'tool_result':
                            chunk_data['tool_result'] = getattr(event, 'content', str(event))
                        else:
                            # Default: treat as text
                            chunk_data['text'] = str(event)
                    else:
                        chunk_data['text'] = str(event)
                    
                    yield chunk_data
                
                # Send final done message
                yield {
                    'status': 'success',
                    'text': '',
                    'session_id': self.session.session_id,
                    'done': True
                }
                
            except AttributeError:
                # Fallback to non-streaming if SDK doesn't support streaming method
                response = await self.chat(message, session_id=session_id, stream=False, model=model)
                
                if response['status'] == 'success':
                    chunk = {
                        'status': 'success',
                        'text': response['text'],
                        'session_id': response['session_id'],
                        'done': False
                    }
                    # Include retry_info if present
                    if 'retry_info' in response:
                        chunk['retry_info'] = response['retry_info']
                    yield chunk
                else:
                    yield {
                        'status': 'error',
                        'error': response.get('error', 'Unknown error'),
                        'text': response.get('text', 'Error'),
                        'retry_info': response.get('retry_info'),
                        'done': True
                    }
                
                yield {
                    'status': 'success',
                    'text': '',
                    'session_id': self.session.session_id if self.session else None,
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

    def _build_sdk_tool(self, name: str, tool_info: Dict[str, Any]) -> Tool:
        """Create a Copilot SDK Tool with a handler bound to a local function."""
        async def handler(invocation):
            try:
                args = invocation.get("arguments") or {}
                result = await tool_info["function"](**args)
                return {
                    "textResultForLlm": json.dumps(result, ensure_ascii=True),
                    "resultType": "success"
                }
            except Exception as e:
                return {
                    "textResultForLlm": "Tool execution failed.",
                    "resultType": "failure",
                    "error": str(e)
                }

        return Tool(
            name=name,
            description=tool_info.get("description", ""),
            parameters=self._build_tool_schema(tool_info.get("parameters", {})),
            handler=handler
        )

    async def _get_rag_context(self, message: str) -> str:
        """Retrieve RAG context for the message. Returns empty string if RAG disabled or unavailable."""
        try:
            rag_cfg = self.config.get_rag_config()
            if not rag_cfg.get("enabled", False):
                return ""
            top_k = rag_cfg.get("top_k", 5)
            if self._rag_store is None or self._rag_embedding is None:
                from src.embeddings import get_embedding_provider
                from src.vector_store import VectorStore
                self._rag_embedding = get_embedding_provider(
                    rag_cfg.get("embedding_provider", "openai"),
                    model=rag_cfg.get("embedding_model"),
                    base_url=rag_cfg.get("embedding_base_url"),
                )
                self._rag_store = VectorStore(rag_cfg["chroma_persist_dir"])
            embedding = self._rag_embedding.embed(message)
            hits = self._rag_store.search(embedding, top_k=top_k)
            if not hits:
                return ""
            parts = [h.get("text", "").strip() for h in hits if h.get("text")]
            if not parts:
                return ""
            return "\n\n".join(parts)
        except Exception as e:
            self.logger.debug("RAG retrieval failed: %s", e)
            return ""

    async def _maybe_augment_prompt(self, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Attach RAG context and optionally search results for dataset-like queries."""
        if "[Tool result: search_datasets]" in message:
            augmented = message
        else:
            rag_context = await self._get_rag_context(message)
            if rag_context:
                augmented = f"{message}\n\n[Context]\n{rag_context}"
            else:
                augmented = message

        if not self._looks_like_dataset_query(augmented):
            return augmented, None

        try:
            from src.copilot_tools import search_datasets

            results = await search_datasets(query=message, limit=5)
            self.logger.info(
                "Tool fallback search_datasets status: %s",
                results.get("status")
            )
            tool_context = json.dumps(results, ensure_ascii=True)
            augmented = (
                f"{augmented}\n\n"
                f"[Tool result: search_datasets]\n{tool_context}\n\n"
                "Use these results to answer. If no matches, ask for clarification."
            )
            return augmented, {
                "name": "search_datasets",
                "input": {"query": message, "limit": 5},
                "result": results
            }
        except Exception as e:
            self.logger.warning(f"Tool fallback failed: {e}")
            return augmented, None

    def _looks_like_dataset_query(self, message: str) -> bool:
        """Heuristic detection for dataset search intent."""
        lowered = message.lower()
        keywords = [
            "dataset", "datasets", "dato", "datos", "indicador", "indicadores",
            "catalogo", "herramienta", "herramientas",
            "gdp", "pib", "inflacion", "inflation", "unemployment", "desempleo",
            "salarios", "wage", "income", "pobreza", "poverty"
        ]
        return any(k in lowered for k in keywords)

    def _on_pre_tool_use(self, input_data, _env):
        tool_name = input_data.get("toolName")
        print(f"[copilot] pre-tool: {tool_name}")
        self.logger.info(f"Copilot pre-tool: {tool_name}")

    def _on_post_tool_use(self, input_data, _env):
        tool_name = input_data.get("toolName")
        print(f"[copilot] post-tool: {tool_name}")
        self.logger.info(f"Copilot post-tool: {tool_name}")

    def _on_error_occurred(self, input_data, _env):
        print(f"[copilot] error: {input_data.get('error')}")
        self.logger.warning(f"Copilot error: {input_data.get('error')}")

    def _build_tool_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simple parameter metadata into a JSON schema for the SDK."""
        properties: Dict[str, Any] = {}
        required: list[str] = []

        for name, meta in parameters.items():
            param_type = meta.get("type", "string")
            description = meta.get("description", "")

            schema: Dict[str, Any] = {
                "type": param_type,
                "description": description
            }

            if param_type == "array":
                schema["items"] = {"type": "string"}

            properties[name] = schema

            if meta.get("required"):
                required.append(name)

        tool_schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties
        }

        if required:
            tool_schema["required"] = required

        return tool_schema
    
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
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available LLM models from Copilot SDK.
        
        Returns:
            List of model dictionaries with id, name, and other metadata
        """
        if not self.client:
            return self._get_fallback_models()
        
        try:
            # Ensure client is started before listing models
            try:
                await self.client.start()
            except Exception as e:
                # Client might already be started
                print(f"Client start: {e}")
            
            # Use the SDK's list_models() method
            models_raw = await self.client.list_models()
            
            # Convert ModelInfo objects to dicts
            models = []
            if models_raw:
                for model in models_raw:
                    # Extract id and name from ModelInfo object
                    model_dict = {
                        'id': getattr(model, 'id', str(model)),
                        'name': getattr(model, 'name', str(model))
                    }
                    models.append(model_dict)
            
            if models:
                print(f"✅ Loaded {len(models)} models from Copilot SDK")
                return models
            else:
                print("⚠️  No models returned from SDK, using fallback")
                return self._get_fallback_models()
                
        except Exception as e:
            print(f"❌ Error listing models: {e}")
            print("   Using fallback models")
            return self._get_fallback_models()
    
    def _get_fallback_models(self) -> List[Dict[str, Any]]:
        """Fallback models if SDK call fails."""
        return [
            {'id': 'gpt-4o', 'name': 'GPT-4o'},
            {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini'},
            {'id': 'claude-3.5-sonnet', 'name': 'Claude 3.5 Sonnet'},
            {'id': 'o1', 'name': 'OpenAI o1'},
            {'id': 'o1-mini', 'name': 'OpenAI o1 Mini'}
        ]
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available LLM models (sync version for backwards compatibility).
        
        Returns:
            List of model identifiers
        """
        if self.client:
            # This would depend on SDK implementation
            # Typically returns ['gpt-4', 'gpt-4-turbo', 'claude-3-opus', etc.]
            return ['gpt-4o', 'gpt-4o-mini', 'claude-3.5-sonnet', 'o1', 'o1-mini']
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
