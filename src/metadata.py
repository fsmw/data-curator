"""Metadata generation using GitHub Copilot SDK with template fallback."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib
import asyncio


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

        # Initialize Copilot SDK client
        self.copilot_agent = None
        if self.use_llm:
            # Import and initialize CopilotAgent lazily
            try:
                from src.copilot_agent import MisesCopilotAgent
                self.copilot_agent = MisesCopilotAgent(config)
                # Start client in sync context
                asyncio.get_event_loop().run_until_complete(self.copilot_agent.start())
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize Copilot SDK: {e}")
                print("   Falling back to template-based metadata generation")
                self.copilot_agent = None

    def generate_metadata(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str] = None,
        dataset_info: Optional[Dict[str, Any]] = None,
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
            cached = self._get_from_cache(topic, data_summary, dataset_info)
            if cached:
                print(f"✓ Using cached metadata for {topic}")
                return cached

        # Try Copilot SDK generation first
        if self.use_llm and self.copilot_agent:
            try:
                metadata = asyncio.get_event_loop().run_until_complete(
                    self._generate_with_copilot(
                        topic,
                        data_summary,
                        source,
                        transformations,
                        original_source_url,
                        dataset_info,
                    )
                )
                print(f"✓ Generated metadata using Copilot SDK for {topic}")

                # Cache the result
                if self.cache_enabled:
                    self._save_to_cache(topic, data_summary, dataset_info, metadata)

                return metadata
            except Exception as e:
                print(f"⚠ Copilot SDK generation failed: {e}")
                print("  Falling back to template...")

        # Fallback to template
        metadata = self._generate_from_template(
            topic,
            data_summary,
            source,
            transformations,
            original_source_url,
            dataset_info,
        )
        print(f"✓ Generated metadata using template for {topic}")

        return metadata

    async def _generate_with_copilot(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str],
        dataset_info: Optional[Dict[str, Any]],
    ) -> str:
        """Generate metadata using Copilot SDK."""
        # Construct prompt
        prompt = self._build_llm_prompt(
            topic,
            data_summary,
            source,
            transformations,
            original_source_url,
            dataset_info,
        )

        # Call Copilot SDK
        response = await self.copilot_agent.chat(
            message=prompt,
            stream=False
        )
        
        if response['status'] == 'success':
            return response['text']
        else:
            raise Exception(f"Copilot SDK error: {response.get('error', 'Unknown error')}")

    def _build_llm_prompt(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        source: str,
        transformations: list,
        original_source_url: Optional[str],
        dataset_info: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for LLM."""
        dataset_info = dataset_info or {}
        dataset_label = dataset_info.get("indicator_name") or dataset_info.get("file_name") or topic
        dataset_id = dataset_info.get("identifier") or dataset_info.get("indicator_id") or ""
        country_count = data_summary.get("country_count", "N/A")
        country_col = data_summary.get("country_column", "N/A")
        prompt = f"""Genera documentación metodológica en español para el siguiente dataset económico:

**Tema**: {topic}
**Dataset**: {dataset_label}
**ID**: {dataset_id or "N/A"}
**Fuente**: {source}
**URL Original**: {original_source_url or "No especificada"}

**Resumen de los datos**:
- Filas: {data_summary.get("rows", "N/A")}
- Columnas: {data_summary.get("columns", "N/A")}
- Nombres de columnas: {", ".join(data_summary.get("column_names", []))}
- Rango temporal: {data_summary.get("year_range", ["N/A", "N/A"])[0]} - {data_summary.get("year_range", ["N/A", "N/A"])[1]}
- Columna de país: {country_col}
- Países (conteo): {country_count}

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
        dataset_info: Optional[Dict[str, Any]],
    ) -> str:
        """Generate metadata using template fallback."""
        year_range = data_summary.get("year_range", ["N/A", "N/A"])
        dataset_info = dataset_info or {}
        dataset_label = dataset_info.get("indicator_name") or dataset_info.get("file_name") or topic
        dataset_id = dataset_info.get("identifier") or dataset_info.get("indicator_id") or "N/A"
        country_count = data_summary.get("country_count", "N/A")
        country_col = data_summary.get("country_column", "N/A")

        template = f"""# Metadatos: {dataset_label}

**Fecha de generación**: {datetime.now().strftime("%Y-%m-%d")}
**ID**: {dataset_id}

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

- Columna de país: {country_col}
- Países (conteo): {country_count}

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

    def save_metadata_for_dataset(self, file_path: Path, metadata_content: str) -> Path:
        """
        Save metadata using the dataset filename stem for direct lookup.

        Args:
            file_path: Path to the dataset file
            metadata_content: Markdown content

        Returns:
            Path to saved file
        """
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        stem = file_path.stem
        filepath = self.metadata_dir / f"{stem}.md"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(metadata_content)

        print(f"✓ Saved metadata to {filepath}")
        return filepath

    def get_metadata_path_for_dataset(self, file_path: Path) -> Path:
        """Get metadata path for a dataset file based on its stem."""
        return self.metadata_dir / f"{file_path.stem}.md"

    def _get_cache_key(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        dataset_info: Optional[Dict[str, Any]],
    ) -> str:
        """Generate cache key from topic and data summary."""
        dataset_info = dataset_info or {}
        cache_data = {
            "topic": topic,
            "identifier": dataset_info.get("identifier") or dataset_info.get("indicator_id") or dataset_info.get("file_name"),
            "rows": data_summary.get("rows"),
            "columns": data_summary.get("columns"),
            "column_names": data_summary.get("column_names", []),
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_from_cache(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        dataset_info: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Retrieve metadata from cache."""
        cache_key = self._get_cache_key(topic, data_summary, dataset_info)
        cache_file = self.cache_dir / f"{cache_key}.md"

        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

        return None

    def _save_to_cache(
        self,
        topic: str,
        data_summary: Dict[str, Any],
        dataset_info: Optional[Dict[str, Any]],
        metadata: str,
    ):
        """Save metadata to cache."""
        cache_key = self._get_cache_key(topic, data_summary, dataset_info)
        cache_file = self.cache_dir / f"{cache_key}.md"

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(metadata)
