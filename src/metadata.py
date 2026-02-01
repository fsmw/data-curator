"""Metadata generation using LLM (OpenRouter) with template fallback."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib
from openai import OpenAI


class MetadataGenerator:
    """Generates metadata documentation using LLM with fallback templates."""

    def __init__(self, config):
        """
        Initialize metadata generator.

        Args:
            config: Config object
        """
        self.config = config
        self.metadata_dir = config.get_directory("metadata")
        self.llm_config = config.get_llm_config()
        self.use_llm = config.config["metadata"]["use_llm"]
        self.cache_enabled = config.config["metadata"]["cache_enabled"]
        self.cache_dir = Path(".metadata_cache")

        if self.cache_enabled:
            self.cache_dir.mkdir(exist_ok=True)

        # Initialize LLM client depending on provider
        self.client = None
        self.provider = self.llm_config.get("provider", "openrouter")
        if self.use_llm:
            if self.provider == "ollama":
                import requests

                self._ollama_requests = requests
                self.ollama_host = self.llm_config.get("host", "http://localhost:11434")
                self.ollama_model = self.llm_config.get("model")
            else:
                if self.llm_config.get("api_key"):
                    self.client = OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=self.llm_config["api_key"],
                    )
                else:
                    self.client = None

    def generate_metadata(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> str:
        """
        Generate metadata documentation.

        Args:
            topic: Topic name (e.g., 'salarios_reales')
            data_summary: Summary statistics from DataCleaner.get_data_summary()
            source: Data source name
            transformations: List of transformations applied
            original_source_url: URL of original data source
            force_regenerate: Force regeneration even if cached

        Returns:
            Markdown-formatted metadata string
        """
        # Check cache first
        if self.cache_enabled and not force_regenerate:
            cached = self._get_from_cache(topic, data_summary)
            if cached:
                print(f"✓ Using cached metadata for {topic}")
                return cached

        # Try LLM generation first
        if self.use_llm and self.client:
            try:
                metadata = self._generate_with_llm(
                    topic, data_summary, source, transformations, original_source_url
                )
                print(f"✓ Generated metadata using LLM for {topic}")

                # Cache the result
                if self.cache_enabled:
                    self._save_to_cache(topic, data_summary, metadata)

                return metadata
            except Exception as e:
                print(f"⚠ LLM generation failed: {e}")
                print("  Falling back to template...")

        # Fallback to template
        metadata = self._generate_from_template(
            topic, data_summary, source, transformations, original_source_url
        )
        print(f"✓ Generated metadata using template for {topic}")

        return metadata

    def _generate_with_llm(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str],
    ) -> str:
        """Generate metadata using LLM."""
        # Construct prompt
        prompt = self._build_llm_prompt(
            topic, data_summary, source, transformations, original_source_url
        )

        # Call LLM (supporting Ollama or OpenRouter)
        if self.provider == "ollama":
            # Build simple messages and call Ollama via HTTP
            messages = [
                {"role": "system", "content": self.llm_config["system_prompt"]},
                {"role": "user", "content": prompt},
            ]
            url = f"{self.ollama_host.rstrip('/')}/api/generate"
            payload = {
                "model": self.ollama_model,
                "prompt": "\n\n".join(
                    [f"[{m['role']}] {m['content']}" for m in messages]
                ),
                "max_tokens": int(self.llm_config["max_tokens"]),
                "temperature": float(self.llm_config["temperature"]),
            }
            resp = self._ollama_requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                return resp.text

            if isinstance(data, dict):
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if isinstance(choice, dict):
                        if "message" in choice and isinstance(choice["message"], dict):
                            return (
                                choice["message"].get("content")
                                or choice.get("text")
                                or json.dumps(choice)
                            )
                        return choice.get("text") or json.dumps(choice)
                if "text" in data:
                    return data["text"]
                return json.dumps(data)
            return str(data)
        else:
            response = self.client.chat.completions.create(
                model=self.llm_config["model"],
                messages=[
                    {"role": "system", "content": self.llm_config["system_prompt"]},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.llm_config["max_tokens"],
                temperature=self.llm_config["temperature"],
            )
            return response.choices[0].message.content

    def _build_llm_prompt(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str],
    ) -> str:
        """Build prompt for LLM."""
        prompt = f"""Genera documentación metodológica en español para el siguiente dataset económico:

**Tema**: {topic}
**Fuente**: {source}
**URL Original**: {original_source_url or "No especificada"}

**Resumen de los datos**:
- Filas: {data_summary.get("rows", "N/A")}
- Columnas: {data_summary.get("columns", "N/A")}
- Nombres de columnas: {", ".join(data_summary.get("column_names", []))}
- Rango temporal: {data_summary.get("year_range", ["N/A", "N/A"])[0]} - {data_summary.get("year_range", ["N/A", "N/A"])[1]}

**Transformaciones aplicadas**:
{chr(10).join(f"- {t}" for t in transformations) if transformations else "- Ninguna"}

Genera un documento en Markdown con las siguientes secciones:

1. **Fuente Original**: Describe la fuente y su reputación
2. **Variables Utilizadas**: Explica las variables principales del dataset
3. **Cobertura Temporal y Geográfica**: Detalla el alcance de los datos
4. **Metodología y Transformaciones**: Describe las transformaciones aplicadas
5. **Advertencias y Limitaciones**: Menciona precauciones importantes para los investigadores

El documento debe ser profesional, claro y útil para economistas e investigadores."""

        return prompt

    def _generate_from_template(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str],
    ) -> str:
        """Generate metadata using template fallback."""
        year_range = data_summary.get("year_range", ["N/A", "N/A"])

        template = f"""# Metadatos: {topic}

**Fecha de generación**: {datetime.now().strftime("%Y-%m-%d")}

## 1. Fuente Original

- **Fuente**: {source}
- **URL**: {original_source_url or "No especificada"}
- **Tipo de fuente**: {"Internacional" if source.upper() in ["ILOSTAT", "OECD", "IMF"] else "Nacional"}

## 2. Variables Utilizadas

### Columnas del dataset

{chr(10).join(f"- `{col}` ({dtype})" for col, dtype in data_summary.get("dtypes", {}).items())}

### Variables numéricas principales

{chr(10).join(f"- `{col}`" for col in data_summary.get("numeric_columns", []))}

## 3. Cobertura Temporal y Geográfica

### Cobertura Temporal

- **Años disponibles**: {year_range[0]} - {year_range[1]}
- **Número total de observaciones**: {data_summary.get("rows", "N/A")}

### Cobertura Geográfica

- Ver columnas de país/región en el dataset

## 4. Metodología y Transformaciones

### Transformaciones Aplicadas

{chr(10).join(f"- {t}" for t in transformations) if transformations else "- No se aplicaron transformaciones"}

### Notas Metodológicas

- Dataset procesado con herramienta de curación automatizada
- Limpieza estándar aplicada (eliminación de filas/columnas vacías)
- Códigos de país estandarizados a ISO 3166-1 alpha-3 cuando fue posible

## 5. Advertencias y Limitaciones

⚠️ **IMPORTANTE**: Esta metadata fue generada automáticamente usando una plantilla.

### Recomendaciones de Uso

- Verificar la fuente original antes de publicar análisis
- Revisar la metodología específica de la fuente para detalles de recolección
- Considerar posibles sesgos o limitaciones de cobertura geográfica/temporal
- Consultar las notas metodológicas de la fuente original

### Valores Faltantes

{chr(10).join(f"- `{col}`: {count} valores faltantes" for col, count in data_summary.get("missing_values", {}).items() if count > 0)}

## 6. Información Adicional

- **Formato del archivo**: CSV (UTF-8)
- **Separador**: coma (,)
- **Codificación**: UTF-8

---

*Metadatos generados por Mises Data Curation Tool v0.1.0*
"""

        return template

    def save_metadata(self, topic: str, metadata_content: str) -> Path:
        """
        Save metadata to file.

        Args:
            topic: Topic name
            metadata_content: Markdown content

        Returns:
            Path to saved file
        """
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.metadata_dir / f"{topic}.md"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(metadata_content)

        print(f"✓ Saved metadata to {filepath}")
        return filepath

    def _get_cache_key(self, topic: str, data_summary: Dict[str, Any]) -> str:
        """Generate cache key from topic and data summary."""
        cache_data = {
            "topic": topic,
            "rows": data_summary.get("rows"),
            "columns": data_summary.get("columns"),
            "column_names": data_summary.get("column_names", []),
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_from_cache(
        self, topic: str, data_summary: Dict[str, Any]
    ) -> Optional[str]:
        """Retrieve metadata from cache."""
        cache_key = self._get_cache_key(topic, data_summary)
        cache_file = self.cache_dir / f"{cache_key}.md"

        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

        return None

    def _save_to_cache(self, topic: str, data_summary: Dict[str, Any], metadata: str):
        """Save metadata to cache."""
        cache_key = self._get_cache_key(topic, data_summary)
        cache_file = self.cache_dir / f"{cache_key}.md"

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(metadata)
