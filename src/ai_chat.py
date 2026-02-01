"""AI Chat Assistant for Data Curator.

Provides a conversational interface for:
- Searching datasets in local catalog and external sources
- Downloading datasets from various sources
- Analyzing and querying dataset contents
- Answering questions about available data

Uses OpenRouter with function calling for tool use.
"""

import json
from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI
from pathlib import Path
import pandas as pd

from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.searcher import IndicatorSearcher
from src.dynamic_search import DynamicSearcher
from src.ingestion import DataIngestionManager
from src.chat_history import ChatHistory
from src.cleaning import DataCleaner
from src.metadata import MetadataGenerator


class ChatAssistant:
    """AI Chat Assistant with tool calling capabilities."""
    
    def __init__(self, config: Config):
        """Initialize chat assistant with config."""
        self.config = config
        self.llm_config = config.get_llm_config()
        
        # Initialize components
        self.catalog = DatasetCatalog(config)
        self.local_searcher = IndicatorSearcher(config)
        self.dynamic_searcher = DynamicSearcher(config)
        self.ingestion = DataIngestionManager(config)
        self.cleaner = DataCleaner(config)
        self.metadata_gen = MetadataGenerator(config)
        
        # Initialize chat history
        history_dir = config.data_root / ".chat_history"
        self.history = ChatHistory(storage_dir=history_dir, max_items=100)
        
        # Initialize client depending on provider (OpenRouter by default, Ollama optional)
        provider = self.llm_config.get("provider", "openrouter")
        self.provider = provider
        
        if provider == "ollama":
            # Ollama provider - no OpenAI client needed
            import requests
            self._ollama_requests = requests
            self.ollama_host = self.llm_config.get("host", "http://localhost:11434")
            self.ollama_model = self.llm_config.get("model")
            self.client = None
        else:
            # OpenRouter/OpenAI-compatible client
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.llm_config['api_key']
            )
        
        # System prompt
        self.system_prompt = """Eres un asistente experto en datos económicos para Data Curator.

Ayudas a buscar y analizar datasets de fuentes como ILOSTAT, OECD, IMF, WorldBank, OWID (Our World in Data), ECLAC.

HERRAMIENTAS DISPONIBLES:
1. list_datasets - Lista TODOS los datasets ya descargados localmente
2. search_local_datasets - Busca en datasets YA DESCARGADOS (requiere: query)
3. search_external_sources - Busca datasets DISPONIBLES en internet para descargar (requiere: query en INGLÉS, source)
4. download_dataset - Descarga un dataset de internet (requiere: source, indicator_id)
5. analyze_dataset - Analiza un dataset descargado (requiere: dataset_id, query)

CUÁNDO USAR CADA HERRAMIENTA:
- "¿Cuántos datasets tenemos?" → list_datasets
- "¿Tenemos datos de inflación?" → search_local_datasets con query="inflacion"
- "Busca datasets sobre inflación en internet/OWID/fuentes externas" → search_external_sources con query="inflation" (EN INGLÉS) y source="owid" o "all"
- "Busca más datasets como estos" → search_external_sources con query en inglés
- "Quiero descargar..." → download_dataset

IMPORTANTE PARA search_external_sources:
- SIEMPRE traduce la query al INGLÉS (inflación → inflation, desempleo → unemployment, salarios → wages, impuestos → tax, PIB → gdp)
- SIEMPRE especifica source: "owid", "oecd", o "all"
- Ejemplo correcto: [TOOL_CALL]search_external_sources{"query":"inflation","source":"owid"}[/TOOL_CALL]
- Ejemplo incorrecto: search_external_sources sin parámetros

IMPORTANTE PARA download_dataset:
- PRIMERO busca con search_external_sources para obtener el 'slug' correcto
- Luego descarga usando ese slug: [TOOL_CALL]download_dataset{"source":"owid","indicator_id":"inflation-of-consumer-prices","topic":"inflacion"}[/TOOL_CALL]
- El dataset descargado se INDEXA AUTOMÁTICAMENTE en el catálogo local
- Después del download, el usuario puede buscarlo con search_local_datasets

FORMATO PARA LLAMAR HERRAMIENTAS:
[TOOL_CALL]nombre_herramienta{"arg1":"valor1","arg2":"valor2"}[/TOOL_CALL]

Ejemplos de workflows completos:

EJEMPLO 1: Usuario busca datasets locales
Usuario: "¿Tenemos datos de inflación?"
Tú: [TOOL_CALL]search_local_datasets{"query":"inflacion"}[/TOOL_CALL]
[Recibes resultados]
Tú: "Sí, tenemos 3 datasets de inflación: [lista datasets]"

EJEMPLO 2: Usuario busca datasets nuevos para descargar
Usuario: "Busca datasets de inflación en OWID para descargar"
Tú: [TOOL_CALL]search_external_sources{"query":"inflation","source":"owid"}[/TOOL_CALL]
[Recibes resultados con slugs]
Tú: "Encontré 15 datasets en OWID sobre inflación: 1) Inflation of consumer prices (slug: inflation-of-consumer-prices), 2) ..."

EJEMPLO 3: Usuario descarga un dataset
Usuario: "Descarga el primer dataset de inflación"
Tú: [TOOL_CALL]download_dataset{"source":"owid","indicator_id":"inflation-of-consumer-prices","topic":"inflacion"}[/TOOL_CALL]
[Recibes confirmación con dataset_id]
Tú: "✓ Dataset descargado exitosamente! ID: 20, 372 filas. Ahora está disponible en el catálogo local."

REGLAS:
- Si el usuario pide "buscar datasets similares" o "buscar más datos" → USA search_external_sources
- SIEMPRE traduce términos al inglés para search_external_sources
- Responde SIEMPRE en español (solo las queries van en inglés)
- Proporciona números específicos y detalles
- Si search_external_sources devuelve 0 resultados, sugiere al usuario reformular la búsqueda
- Cuando descargues un dataset, confirma al usuario que está disponible localmente con su ID"""

        # Define tools
        self.tools = self._define_tools()
        self.tool_functions = self._map_tool_functions()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define function calling tools for the LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_local_datasets",
                    "description": "Busca datasets en el catálogo local. Usa esto primero para ver qué datos ya están disponibles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Término de búsqueda (ej: 'salarios', 'inflación', 'Argentina')"
                            },
                            "source": {
                                "type": "string",
                                "description": "Filtrar por fuente específica (opcional): ilostat, oecd, imf, worldbank, owid, eclac"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_external_sources",
                    "description": "Busca datasets disponibles en fuentes externas (OWID, OECD). Usa esto cuando el usuario quiera datos que no están en el catálogo local.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Término de búsqueda en inglés (ej: 'inflation', 'wages', 'tax')"
                            },
                            "source": {
                                "type": "string",
                                "description": "Fuente específica a buscar: owid, oecd, o 'all' para ambas"
                            }
                        },
                        "required": ["query", "source"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "download_dataset",
                    "description": """Descarga un dataset de una fuente externa. 
                    
IMPORTANTE: Primero debes buscar el dataset con search_external_sources para obtener el 'slug' o 'id' correcto.

Parámetros:
- source: La fuente del dataset (owid, oecd, ilostat, etc.)
- indicator_id: El 'slug' del dataset (para OWID) o ID del indicador
- topic: Categoría (usa "general" si no sabes cuál) - OPCIONAL

Ejemplo de flujo correcto:
1. Usuario: "descarga el dataset de inflation de OWID"
2. Buscar con search_external_sources para obtener el slug
3. Usar download_dataset con el slug encontrado

Ejemplo: [TOOL_CALL]download_dataset{"source":"owid","indicator_id":"consumer-price-inflation","topic":"general"}[/TOOL_CALL]""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Fuente del dataset: ilostat, oecd, imf, worldbank, owid, eclac"
                            },
                            "indicator_id": {
                                "type": "string",
                                "description": "ID del indicador o slug. Para OWID usa el 'slug' del resultado de búsqueda."
                            },
                            "topic": {
                                "type": "string",
                                "description": "Categoría del dataset. Si no sabes, usa 'general'. Opciones: salarios_reales, informalidad_laboral, presion_fiscal, libertad_economica, general",
                                "default": "general"
                            },
                            "countries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Lista de países (códigos ISO3). Por defecto: países de LATAM"
                            },
                            "start_year": {
                                "type": "integer",
                                "description": "Año inicial (opcional)"
                            },
                            "end_year": {
                                "type": "integer",
                                "description": "Año final (opcional)"
                            }
                        },
                        "required": ["source", "indicator_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_dataset",
                    "description": "Analiza el contenido de un dataset local. Usa esto para responder preguntas específicas sobre los datos.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dataset_id": {
                                "type": "integer",
                                "description": "ID del dataset en el catálogo local"
                            },
                            "query": {
                                "type": "string",
                                "description": "Pregunta específica sobre el dataset (ej: '¿cuál es el valor máximo?', '¿qué países tiene?')"
                            }
                        },
                        "required": ["dataset_id", "query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_datasets",
                    "description": "Lista todos los datasets disponibles en el catálogo local con sus IDs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Filtrar por tema específico (opcional)"
                            },
                            "source": {
                                "type": "string",
                                "description": "Filtrar por fuente específica (opcional)"
                            }
                        }
                    }
                }
            }
        ]
    
    def _map_tool_functions(self) -> Dict[str, Callable]:
        """Map tool names to actual Python functions."""
        return {
            "search_local_datasets": self._search_local_datasets,
            "search_external_sources": self._search_external_sources,
            "download_dataset": self._download_dataset,
            "analyze_dataset": self._analyze_dataset,
            "list_datasets": self._list_datasets
        }
    
    def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process a chat message and return response.
        
        Args:
            message: User's message
            conversation_history: Previous messages in conversation (optional)
        
        Returns:
            Dict with 'response' (str), 'tool_calls' (list), and 'conversation_history' (list)
        """
        if conversation_history is None:
            conversation_history = []
        
        # Limit conversation history to last 10 messages to avoid context overflow
        # Keep only user and assistant messages, skip tool messages in history
        filtered_history = []
        for msg in conversation_history:
            if msg.get('role') in ['user', 'assistant']:
                # Don't include tool_calls in historical context to save tokens
                filtered_msg = {
                    "role": msg['role'],
                    "content": msg.get('content', '')
                }
                filtered_history.append(filtered_msg)
        
        # Keep only last 10 messages (5 exchanges)
        filtered_history = filtered_history[-10:]
        
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Build messages for API call
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + filtered_history + [{"role": "user", "content": message}]
        
        # Call LLM (handle both OpenRouter and Ollama)
        if self.provider == "ollama":
            # Ollama: text generation with manual tool call parsing
            import re
            
            # Build prompt from messages
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"[{role}] {content}")
            prompt = "\n\n".join(prompt_parts)
            
            # Call Ollama API
            try:
                ollama_response = self._ollama_requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60
                )
                ollama_data = ollama_response.json()
                response_text = ollama_data.get("response", "")
                
                print(f"DEBUG: Ollama response text: {response_text[:200]}")
                
                # Check if response contains tool calls - support multiple formats
                # Format 1: [TOOL_CALL]function_name{"key":"value"}[/TOOL_CALL]
                pattern1 = re.compile(r'\[TOOL_CALL\](\w+)(\{[^\]]*\})?\[/TOOL_CALL\]', re.DOTALL)
                # Format 2: minimax:tool_call function_name (optional args)
                pattern2 = re.compile(r'minimax:tool_call\s+(\w+)(?:\s+(\{[^\n]*\}))?', re.MULTILINE)
                # Format 3: <tool_call>function_name</tool_call>
                pattern3 = re.compile(r'<tool_call>(\w+)(?:\s+(\{[^\>]*\}))?</tool_call>', re.DOTALL)
                
                matches1 = pattern1.findall(response_text)
                matches2 = pattern2.findall(response_text)
                matches3 = pattern3.findall(response_text)
                
                matches = matches1 or matches2 or matches3
                
                print(f"DEBUG: Found tool calls: {matches}")
                
                if matches:
                    # Process tool calls
                    tool_calls_made = []
                    for tool_name, args_str in matches:
                        # Parse arguments
                        try:
                            if args_str and args_str.strip():
                                # Clean up args string
                                args_str = args_str.strip()
                                function_args = json.loads(args_str) if args_str != "{}" else {}
                            else:
                                function_args = {}
                        except json.JSONDecodeError as e:
                            print(f"Error parsing tool arguments: {e}")
                            function_args = {}
                        
                        # Execute tool
                        try:
                            if tool_name in self.tool_functions:
                                function_response = self.tool_functions[tool_name](**function_args)
                                tool_result = {
                                    "success": True,
                                    "data": function_response
                                }
                            else:
                                tool_result = {
                                    "success": False,
                                    "error": f"Unknown tool: {tool_name}"
                                }
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            tool_result = {
                                "success": False,
                                "error": str(e)
                            }
                        
                        tool_calls_made.append({
                            "function": tool_name,
                            "arguments": function_args,
                            "result": tool_result
                        })
                    
                    # Generate synthesis response with tool results
                    synthesis_prompt = f"""Has ejecutado las siguientes herramientas:

"""
                    for tc in tool_calls_made:
                        synthesis_prompt += f"\nHerramienta: {tc['function']}\n"
                        synthesis_prompt += f"Resultado: {json.dumps(tc['result'], ensure_ascii=False, indent=2)}\n"
                    
                    synthesis_prompt += "\n\nCon base en estos resultados, genera una respuesta clara y útil en español para el usuario. Proporciona números específicos y detalles relevantes."
                    
                    # Get synthesis response from Ollama
                    synthesis_response = self._ollama_requests.post(
                        f"{self.ollama_host}/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": synthesis_prompt,
                            "stream": False
                        },
                        timeout=60
                    )
                    synthesis_data = synthesis_response.json()
                    final_message = synthesis_data.get("response", "")
                    
                    # If synthesis is empty, create default response
                    if not final_message or final_message.strip() == "":
                        summary_parts = []
                        for tc in tool_calls_made:
                            if tc['result'].get('success'):
                                data = tc['result'].get('data', {})
                                if isinstance(data, dict):
                                    total = data.get('total', 0)
                                    summary_parts.append(f"✓ {tc['function']}: {total} resultados")
                                else:
                                    summary_parts.append(f"✓ {tc['function']}: Completado")
                            else:
                                summary_parts.append(f"✗ {tc['function']}: {tc['result'].get('error', 'Error')}")
                        
                        final_message = "He ejecutado las siguientes acciones:\n\n" + "\n".join(summary_parts)
                    
                    conversation_history.append({
                        "role": "assistant",
                        "content": final_message
                    })
                    
                    return {
                        "response": final_message,
                        "tool_calls": tool_calls_made,
                        "conversation_history": conversation_history
                    }
                else:
                    # No tool calls - return direct response
                    conversation_history.append({
                        "role": "assistant",
                        "content": response_text
                    })
                    
                    return {
                        "response": response_text,
                        "tool_calls": [],
                        "conversation_history": conversation_history
                    }
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_msg = f"Error llamando a Ollama: {str(e)}"
                conversation_history.append({
                    "role": "assistant",
                    "content": error_msg
                })
                return {
                    "response": error_msg,
                    "tool_calls": [],
                    "conversation_history": conversation_history
                }
        else:
            # OpenRouter: full function calling support
            response = self.client.chat.completions.create(
                model=self.llm_config['model'],
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=2000
            )
        
            assistant_message = response.choices[0].message
        tool_calls_made = []
        
        # Handle tool calls
        if assistant_message.tool_calls:
            # Add assistant message with tool calls to history
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                
                # Parse arguments safely
                try:
                    args_str = tool_call.function.arguments
                    if not args_str or args_str.strip() == "":
                        function_args = {}
                    else:
                        function_args = json.loads(args_str)
                except json.JSONDecodeError as e:
                    print(f"Error parsing tool arguments: {e}")
                    print(f"Arguments string: {tool_call.function.arguments}")
                    function_args = {}
                
                # Execute tool
                try:
                    function_response = self.tool_functions[function_name](**function_args)
                    tool_result = {
                        "success": True,
                        "data": function_response
                    }
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    tool_result = {
                        "success": False,
                        "error": str(e)
                    }
                
                # Add tool result to history
                conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
                
                tool_calls_made.append({
                    "function": function_name,
                    "arguments": function_args,
                    "result": tool_result
                })
            
            # Get final response with tool results
            print(f"DEBUG: Getting final response with {len(conversation_history)} messages in history")
            print(f"DEBUG: Last 3 messages: {conversation_history[-3:]}")
            
            final_response = self.client.chat.completions.create(
                model=self.llm_config['model'],
                messages=[{"role": "system", "content": self.system_prompt}] + conversation_history,
                temperature=0.3,
                max_tokens=2000
            )
            
            final_message = final_response.choices[0].message.content
            print(f"DEBUG: Final message: {final_message}")
            print(f"DEBUG: Final message length: {len(final_message) if final_message else 0}")
            
            # If final message is empty, create a default response
            if not final_message or final_message.strip() == "":
                print("WARNING: Empty final message, creating default response")
                # Summarize tool results
                summary_parts = []
                for tc in tool_calls_made:
                    func_name = tc['function']
                    result = tc['result']
                    if result.get('success'):
                        summary_parts.append(f"✓ {func_name}: Completado")
                    else:
                        summary_parts.append(f"✗ {func_name}: {result.get('error', 'Error')}")
                
                final_message = "He ejecutado las siguientes acciones:\n\n" + "\n".join(summary_parts) + "\n\n¿Necesitas más información?"
            
            conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            return {
                "response": final_message,
                "tool_calls": tool_calls_made,
                "conversation_history": conversation_history
            }
        
        # No tool calls - direct response
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message.content
        })
        
        return {
            "response": assistant_message.content,
            "tool_calls": [],
            "conversation_history": conversation_history
        }
    
    # Tool implementation methods
    
    def _search_local_datasets(self, query: str, source: Optional[str] = None) -> Dict[str, Any]:
        """Search local dataset catalog. If nothing is found, attempt to (re)index local CSVs and retry once."""
        try:
            filters = {}
            if source:
                filters['source'] = source.lower()

            results = self.catalog.search(query, filters=filters, limit=10)

            # If search yields no results, try indexing local files and retry once
            if isinstance(results, list) and len(results) == 0:
                try:
                    self.catalog.index_all(force=False)
                    results = self.catalog.search(query, filters=filters, limit=10)
                except Exception:
                    # If indexing fails, continue with empty results
                    pass

            # catalog.search returns a list, not a dict
            if not isinstance(results, list):
                return {"error": "Formato de resultados inesperado"}

            # Format results
            formatted_results = []
            for ds in results:
                formatted_results.append({
                    "id": ds.get('id'),
                    "name": ds.get('indicator_name'),
                    "source": ds.get('source'),
                    "topic": ds.get('topic'),
                    "rows": ds.get('row_count', 0),
                    "year_range": f"{ds.get('min_year', 'N/A')}-{ds.get('max_year', 'N/A')}",
                    "countries": ds.get('country_count', 0)
                })

            return {
                "total": len(formatted_results),
                "results": formatted_results
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _search_external_sources(self, query: str = None, source: str = "all") -> Dict[str, Any]:
        """Search external data sources.
        
        Args:
            query: Search term in English (required)
            source: Data source to search ('owid', 'oecd', or 'all'). Defaults to 'all'.
            
        Returns:
            Dict with 'total' and 'results' keys, or 'error' key on failure
        """
        try:
            # Validate required parameters
            if not query or not query.strip():
                return {
                    "error": "Se requiere un término de búsqueda. Por favor especifica qué datos quieres buscar.",
                    "total": 0,
                    "results": []
                }
            
            if not source:
                source = "all"
            
            # Validate source
            valid_sources = ["owid", "oecd", "ilostat", "worldbank", "imf", "eclac", "all"]
            if source.lower() not in valid_sources:
                return {
                    "error": f"Fuente inválida: '{source}'. Fuentes válidas: {', '.join(valid_sources)}",
                    "total": 0,
                    "results": []
                }
            
            print(f"DEBUG: Searching external sources with query='{query}', source='{source}'")
            
            # DynamicSearcher.search returns a dict with 'results' key
            search_result = self.dynamic_searcher.search(query, include_remote=True, max_remote=20)
            
            print(f"DEBUG: DynamicSearcher returned: {search_result}")
            
            # Get results list - try multiple possible keys
            all_results = search_result.get('remote_results') or search_result.get('results', [])
            
            print(f"DEBUG: Found {len(all_results)} total results")
            
            # Filter by source if specified and not 'all'
            if source and source.lower() != 'all':
                all_results = [r for r in all_results if r.get('source', '').lower() == source.lower()]
                print(f"DEBUG: After filtering by source '{source}': {len(all_results)} results")
            
            # Format results - limit to top 15
            formatted_results = []
            for idx, result in enumerate(all_results[:15]):
                formatted_results.append({
                    "id": result.get('id'),
                    "name": result.get('name') or result.get('title'),
                    "source": result.get('source'),
                    "description": result.get('description', '')[:300],
                    "url": result.get('url'),
                    "slug": result.get('slug')
                })
            
            return {
                "total": len(formatted_results),
                "results": formatted_results,
                "source_searched": source
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "error": f"Error buscando en fuentes externas: {str(e)}",
                "total": 0,
                "results": []
            }
    
    def _download_dataset(
        self,
        source: str,
        indicator_id: str,
        topic: str = "general",
        countries: Optional[List[str]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Download a dataset from external source.
        
        This follows the full pipeline: ingest → clean → save → index
        
        Args:
            source: Data source (owid, oecd, ilostat, etc.)
            indicator_id: Slug/code/ID for the indicator (from search_external_sources)
            topic: Topic for organization (default: "general")
            countries: List of country codes (default: LATAM countries)
            start_year: Starting year (default: 2010)
            end_year: Ending year (default: 2024)
            
        Returns:
            Dict with success, dataset_id, file_path, and message
        """
        try:
            # Prepare download parameters
            kwargs = {}
            
            # Set defaults
            if countries is None:
                countries = ["ARG", "BRA", "CHL", "COL", "MEX", "PER"]  # Default LATAM
            if start_year is None:
                start_year = 2010
            if end_year is None:
                end_year = 2024
                
            kwargs["countries"] = countries
            kwargs["start_year"] = start_year
            kwargs["end_year"] = end_year
            
            # Source-specific parameters
            source_lower = source.lower()
            if source_lower == "owid":
                kwargs["slug"] = indicator_id
            elif source_lower == "ilostat":
                kwargs["indicator"] = indicator_id
            elif source_lower == "oecd":
                kwargs["dataset"] = indicator_id
            elif source_lower == "worldbank":
                kwargs["indicator"] = indicator_id
            elif source_lower == "imf":
                kwargs["indicator"] = indicator_id
                kwargs["database"] = "IFS"  # Default database
            elif source_lower == "eclac":
                kwargs["table"] = indicator_id
            else:
                return {
                    "success": False,
                    "error": f"Fuente no soportada: {source}. Fuentes válidas: owid, oecd, ilostat, worldbank, imf, eclac"
                }
            
            # Step 1: Ingest (download raw data)
            print(f"DEBUG: Downloading from {source} with params: {kwargs}")
            raw_data = self.ingestion.ingest(source_lower, **kwargs)
            
            if raw_data is None or len(raw_data) == 0:
                return {
                    "success": False,
                    "error": "No se obtuvieron datos de la fuente. Verifica los parámetros."
                }
            
            print(f"DEBUG: Downloaded {len(raw_data)} rows")
            
            # Step 2: Clean data
            cleaned_data = self.cleaner.clean_dataset(raw_data)
            print(f"DEBUG: Cleaned data has {len(cleaned_data)} rows")
            
            # Step 3: Save to 02_Datasets_Limpios
            coverage = "latam" if len(countries) > 1 else countries[0].lower()
            file_path = self.cleaner.save_clean_dataset(
                cleaned_data, 
                topic, 
                source_lower, 
                coverage, 
                start_year, 
                end_year
            )
            print(f"DEBUG: Saved to {file_path}")
            
            # Step 4: Generate metadata
            data_summary = self.cleaner.get_data_summary(cleaned_data)
            transformations = self.cleaner.get_transformations()
            metadata_content = self.metadata_gen.generate_metadata(
                topic=topic,
                data_summary=data_summary,
                source=source_lower,
                transformations=transformations,
                original_source_url=f"https://{source_lower}.org"
            )
            metadata_path = self.metadata_gen.save_metadata(topic, metadata_content)
            print(f"DEBUG: Metadata saved to {metadata_path}")
            
            # Step 5: Index in catalog
            dataset_id = self.catalog.index_dataset(Path(file_path))
            print(f"DEBUG: Indexed as dataset_id {dataset_id}")
            
            return {
                "success": True,
                "message": f"Dataset descargado, documentado e indexado exitosamente como ID {dataset_id}",
                "dataset_id": dataset_id,
                "file_path": str(file_path),
                "metadata_path": str(metadata_path),
                "rows": len(cleaned_data),
                "source": source_lower,
                "topic": topic
            }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Error descargando dataset: {str(e)}"
            }
    
    def _analyze_dataset(self, dataset_id: int, query: str) -> Dict[str, Any]:
        """Analyze a local dataset to answer specific questions."""
        try:
            # Get dataset info
            dataset = self.catalog.get_dataset(dataset_id)
            if not dataset:
                return {"error": f"Dataset {dataset_id} no encontrado"}
            
            # Load data
            df = pd.read_csv(dataset['file_path'])
            
            # Generate analysis based on query
            analysis = {
                "dataset_name": dataset['indicator_name'],
                "source": dataset['source'],
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "columns": df.columns.tolist(),
                "year_range": f"{dataset.get('min_year', 'N/A')}-{dataset.get('max_year', 'N/A')}"
            }
            
            # Add specific insights based on query keywords
            query_lower = query.lower()
            
            if "país" in query_lower or "pais" in query_lower or "country" in query_lower:
                country_cols = [col for col in df.columns if 'country' in col.lower() or 'país' in col.lower()]
                if country_cols:
                    countries = df[country_cols[0]].unique().tolist()
                    analysis["countries"] = countries[:20]  # Limit to 20
            
            if "máx" in query_lower or "max" in query_lower or "mayor" in query_lower:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    analysis["max_values"] = {col: float(df[col].max()) for col in numeric_cols[:2]}
            
            if "mín" in query_lower or "min" in query_lower or "menor" in query_lower:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    analysis["min_values"] = {col: float(df[col].min()) for col in numeric_cols[:2]}
            
            if "promedio" in query_lower or "media" in query_lower or "average" in query_lower:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    analysis["mean_values"] = {col: float(df[col].mean()) for col in numeric_cols[:2]}
            
            # Add small preview only if requested
            if "vista" in query_lower or "preview" in query_lower or "muestra" in query_lower:
                analysis["preview"] = df.head(3).to_dict('records')
            
            return analysis
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _list_datasets(self, topic: Optional[str] = None, source: Optional[str] = None) -> Dict[str, Any]:
        """List all available datasets in catalog."""
        try:
            filters = {}
            if topic:
                filters['topic'] = topic
            if source:
                filters['source'] = source
            
            # Get all datasets - catalog.search returns a list
            results = self.catalog.search("", filters=filters, limit=100)
            
            # Format as simple list
            datasets = []
            for ds in results:  # results is already a list
                datasets.append({
                    "id": ds['id'],
                    "name": ds['indicator_name'],
                    "source": ds['source'],
                    "topic": ds['topic'],
                    "rows": ds['row_count'],
                    "year_range": f"{ds.get('min_year', 'N/A')}-{ds.get('max_year', 'N/A')}"
                })
            
            return {
                "total": len(datasets),
                "datasets": datasets
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
