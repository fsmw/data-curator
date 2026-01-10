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

from config import Config
from dataset_catalog import DatasetCatalog
from searcher import IndicatorSearcher
from dynamic_search import DynamicSearcher
from ingestion import DataIngestionManager


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
        
        # Initialize OpenAI-compatible client for OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.llm_config['api_key']
        )
        
        # System prompt
        self.system_prompt = """Eres un asistente experto en datos económicos para Data Curator.

Ayudas a buscar y analizar datasets de fuentes como ILOSTAT, OECD, IMF, WorldBank, OWID, ECLAC.

Reglas:
- Busca primero en catálogo local antes de fuentes externas
- Responde en español
- Ofrece descargar datos si no existen localmente
- Proporciona insights específicos con números

Herramientas: search_local_datasets, search_external_sources, download_dataset, analyze_dataset, list_datasets"""

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
                    "description": "Descarga un dataset de una fuente externa. Requiere información específica del dataset a descargar.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Fuente del dataset: ilostat, oecd, imf, worldbank, owid, eclac"
                            },
                            "indicator_id": {
                                "type": "string",
                                "description": "ID del indicador o slug (para OWID)"
                            },
                            "topic": {
                                "type": "string",
                                "description": "Categoría del dataset: salarios_reales, informalidad_laboral, presion_fiscal, libertad_economica, general"
                            },
                            "countries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Lista de países (códigos ISO3 o nombres)"
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
                        "required": ["source", "indicator_id", "topic"]
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
        
        # Call LLM
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
    
    def _search_external_sources(self, query: str, source: str) -> Dict[str, Any]:
        """Search external data sources."""
        try:
            # DynamicSearcher.search returns a dict with 'results' key
            search_result = self.dynamic_searcher.search(query, include_remote=True, max_remote=10)
            
            # Get results list
            all_results = search_result.get('results', [])
            
            # Filter by source if specified and not 'all'
            if source and source.lower() != 'all':
                all_results = [r for r in all_results if r.get('source', '').lower() == source.lower()]
            
            # Format results - limit to top 10
            formatted_results = []
            for idx, result in enumerate(all_results[:10]):
                formatted_results.append({
                    "id": result.get('id'),
                    "name": result.get('name'),
                    "source": result.get('source'),
                    "description": result.get('description', '')[:200],
                    "url": result.get('url'),
                    "slug": result.get('slug')
                })
            
            return {
                "total": len(formatted_results),
                "results": formatted_results
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _download_dataset(
        self,
        source: str,
        indicator_id: str,
        topic: str,
        countries: Optional[List[str]] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Download a dataset from external source."""
        try:
            # Prepare download parameters
            params = {
                "source": source.lower(),
                "topic": topic,
                "countries": countries or ["ARG", "BRA", "CHL", "COL", "MEX", "PER"]  # Default LATAM
            }
            
            # Source-specific parameters
            if source.lower() == "owid":
                params["slug"] = indicator_id
            elif source.lower() == "ilostat":
                params["indicator"] = indicator_id
            elif source.lower() == "oecd":
                params["dataset"] = indicator_id
            elif source.lower() == "worldbank":
                params["indicator"] = indicator_id
            elif source.lower() == "imf":
                params["indicator"] = indicator_id
                params["database"] = "IFS"  # Default database
            elif source.lower() == "eclac":
                params["table"] = indicator_id
            else:
                return {"error": f"Fuente no soportada: {source}"}
            
            if start_year:
                params["start_year"] = start_year
            if end_year:
                params["end_year"] = end_year
            
            # Download using ingestion manager
            result = self.ingestion.ingest(**params)
            
            # Index in catalog
            if result.get('success'):
                file_path = Path(result['file_path'])
                dataset_id = self.catalog.index_dataset(file_path)
                
                return {
                    "success": True,
                    "message": f"Dataset descargado exitosamente",
                    "dataset_id": dataset_id,
                    "file_path": str(file_path),
                    "rows": result.get('rows', 0)
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Error desconocido')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
