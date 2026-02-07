"""
Data Cleaning Agent for Mises Data Curator.

Specialized agent for identifying and fixing data quality issues
in economic datasets. Handles missing values, duplicates, outliers,
type conversions, and inconsistencies.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from .base import BaseAgent, AgentResponse, TableContext
from .prompts import DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES, DATA_CLEAN_AGENT_SYSTEM_PROMPT_EN
from .client import MisesLLMClient
from .utils import generate_data_summary, extract_json_objects, extract_code_from_response
from .sandbox import run_transform_in_sandbox

logger = logging.getLogger(__name__)


# =============================================================================
# Quality Issue Types
# =============================================================================

@dataclass
class QualityIssue:
    """Represents a single data quality issue."""
    tipo: str  # null_values, duplicates, outliers, type_mismatch, inconsistency
    columna: Optional[str] = None
    descripcion: str = ""
    filas_afectadas: int = 0
    severidad: str = "media"  # baja, media, alta
    solucion_propuesta: str = ""


@dataclass
class QualityReport:
    """Complete data quality report."""
    tabla: str
    total_filas: int
    total_columnas: int
    calidad_general: str  # buena, media, baja
    issues: List[QualityIssue] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "tabla": self.tabla,
            "total_filas": self.total_filas,
            "total_columnas": self.total_columnas,
            "calidad_general": self.calidad_general,
            "issues": [
                {
                    "tipo": i.tipo,
                    "columna": i.columna,
                    "descripcion": i.descripcion,
                    "filas_afectadas": i.filas_afectadas,
                    "severidad": i.severidad,
                    "solucion_propuesta": i.solucion_propuesta
                }
                for i in self.issues
            ],
            "estadisticas": self.estadisticas
        }


# =============================================================================
# Data Clean Agent
# =============================================================================

class DataCleanAgent(BaseAgent):
    """
    Agent specialized in data quality analysis and cleaning.
    
    Capabilities:
    - Detect missing values and patterns
    - Identify duplicates
    - Find outliers using statistical methods
    - Detect type mismatches
    - Identify naming inconsistencies
    - Generate cleaning code
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es",
        **kwargs
    ):
        super().__init__(
            client=client,
            name="DataCleanAgent",
            language=language,
            **kwargs
        )

    def _get_system_prompt(self) -> str:
        if self.language == "es":
            return DATA_CLEAN_AGENT_SYSTEM_PROMPT_ES
        return DATA_CLEAN_AGENT_SYSTEM_PROMPT_EN

    # =========================================================================
    # Automated Quality Analysis (No LLM)
    # =========================================================================

    def analyze_quality_fast(self, df: pd.DataFrame, table_name: str = "datos") -> QualityReport:
        """
        Perform fast automated quality analysis without LLM.
        
        Args:
            df: DataFrame to analyze
            table_name: Name for the table
            
        Returns:
            QualityReport with detected issues
        """
        issues = []
        stats = {}
        
        # Basic stats
        stats["filas"] = len(df)
        stats["columnas"] = len(df.columns)
        stats["memoria_mb"] = df.memory_usage(deep=True).sum() / 1024 / 1024
        
        # 1. Missing values analysis
        null_counts = df.isnull().sum()
        null_pcts = (null_counts / len(df) * 100).round(2)
        
        for col in df.columns:
            if null_counts[col] > 0:
                pct = null_pcts[col]
                severidad = "alta" if pct > 50 else ("media" if pct > 10 else "baja")
                issues.append(QualityIssue(
                    tipo="valores_nulos",
                    columna=col,
                    descripcion=f"{null_counts[col]:,} valores nulos ({pct}%)",
                    filas_afectadas=int(null_counts[col]),
                    severidad=severidad,
                    solucion_propuesta=self._suggest_null_solution(df, col, pct)
                ))
        
        stats["nulos_totales"] = int(null_counts.sum())
        stats["nulos_por_columna"] = null_counts.to_dict()
        
        # 2. Duplicates analysis
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            issues.append(QualityIssue(
                tipo="duplicados",
                descripcion=f"{dup_count:,} filas duplicadas exactas",
                filas_afectadas=int(dup_count),
                severidad="media",
                solucion_propuesta="Eliminar con df.drop_duplicates()"
            ))
        
        stats["duplicados"] = int(dup_count)
        
        # 3. Outliers in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            outliers = self._detect_outliers_iqr(df[col])
            if outliers > 0:
                pct = (outliers / len(df) * 100)
                if pct > 1:  # Only report if significant
                    issues.append(QualityIssue(
                        tipo="outliers",
                        columna=col,
                        descripcion=f"{outliers:,} valores atípicos detectados (IQR)",
                        filas_afectadas=outliers,
                        severidad="baja" if pct < 5 else "media",
                        solucion_propuesta="Revisar valores extremos o aplicar winsorización"
                    ))
        
        # 4. Type issues
        for col in df.columns:
            if df[col].dtype == object:
                # Check if could be numeric
                numeric_ratio = self._check_numeric_ratio(df[col])
                if 0.5 < numeric_ratio < 1.0:
                    issues.append(QualityIssue(
                        tipo="tipo_incorrecto",
                        columna=col,
                        descripcion=f"Columna parece numérica ({numeric_ratio*100:.0f}% valores)",
                        filas_afectadas=int(len(df) * (1 - numeric_ratio)),
                        severidad="media",
                        solucion_propuesta="Convertir a numérico con pd.to_numeric(errors='coerce')"
                    ))
        
        # 5. Inconsistencies in categorical columns
        cat_cols = df.select_dtypes(include=[object]).columns
        for col in cat_cols:
            similar = self._find_similar_values(df[col])
            if similar:
                issues.append(QualityIssue(
                    tipo="inconsistencia",
                    columna=col,
                    descripcion=f"Posibles duplicados: {similar[:3]}",
                    filas_afectadas=0,
                    severidad="baja",
                    solucion_propuesta="Estandarizar nombres con mapeo"
                ))
        
        # Calculate overall quality
        issue_score = sum(
            3 if i.severidad == "alta" else (2 if i.severidad == "media" else 1)
            for i in issues
        )
        
        if issue_score == 0:
            calidad = "buena"
        elif issue_score <= 5:
            calidad = "media"
        else:
            calidad = "baja"
        
        return QualityReport(
            tabla=table_name,
            total_filas=len(df),
            total_columnas=len(df.columns),
            calidad_general=calidad,
            issues=issues,
            estadisticas=stats
        )

    def _suggest_null_solution(self, df: pd.DataFrame, col: str, pct: float) -> str:
        """Suggest solution for null values based on column type and pattern."""
        if pct > 80:
            return "Considerar eliminar la columna"
        
        if pd.api.types.is_numeric_dtype(df[col]):
            if pct < 5:
                return "Imputar con mediana: df[col].fillna(df[col].median())"
            else:
                return "Imputar con interpolación o modelo"
        else:
            if pct < 5:
                return "Imputar con moda: df[col].fillna(df[col].mode()[0])"
            else:
                return "Marcar como 'Desconocido' o eliminar filas"

    def _detect_outliers_iqr(self, series: pd.Series) -> int:
        """Detect outliers using IQR method."""
        clean = series.dropna()
        if len(clean) < 4:
            return 0
        
        Q1 = clean.quantile(0.25)
        Q3 = clean.quantile(0.75)
        IQR = Q3 - Q1
        
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        
        outliers = ((clean < lower) | (clean > upper)).sum()
        return int(outliers)

    def _check_numeric_ratio(self, series: pd.Series) -> float:
        """Check what proportion of values could be numeric."""
        def is_numeric(val):
            if pd.isna(val):
                return True
            try:
                float(str(val).replace(",", "").replace(" ", ""))
                return True
            except:
                return False
        
        numeric_count = series.apply(is_numeric).sum()
        return numeric_count / len(series) if len(series) > 0 else 0

    def _find_similar_values(self, series: pd.Series, threshold: float = 0.8) -> List[str]:
        """Find potentially similar categorical values."""
        unique_vals = series.dropna().unique()
        if len(unique_vals) > 100:  # Skip if too many unique values
            return []
        
        similar_pairs = []
        vals = [str(v).lower().strip() for v in unique_vals]
        
        for i, v1 in enumerate(vals):
            for v2 in vals[i+1:]:
                # Simple similarity check
                if v1 in v2 or v2 in v1:
                    if v1 != v2:
                        similar_pairs.append(f"'{unique_vals[i]}' ≈ '{unique_vals[vals.index(v2)]}'")
        
        return similar_pairs[:5]

    # =========================================================================
    # LLM-Assisted Analysis
    # =========================================================================

    def analyze_with_llm(
        self,
        tables: List[TableContext],
        generate_code: bool = True
    ) -> AgentResponse:
        """
        Perform LLM-assisted quality analysis.
        
        Args:
            tables: Tables to analyze
            generate_code: Whether to generate cleaning code
            
        Returns:
            AgentResponse with analysis and optional code
        """
        if self.language == "es":
            goal = """Analiza la calidad de los datos económicos:

1. **Valores Nulos**: Identifica patrones de datos faltantes
2. **Duplicados**: Detecta filas repetidas
3. **Tipos de Datos**: Verifica tipos correctos
4. **Outliers**: Señala valores atípicos sospechosos
5. **Inconsistencias**: Nombres diferentes para lo mismo

Para cada problema, indica:
- Severidad (alta/media/baja)
- Filas afectadas
- Solución propuesta

"""
            if generate_code:
                goal += "Genera código Python para limpiar los datos."
        else:
            goal = """Analyze economic data quality:

1. **Null Values**: Identify missing data patterns
2. **Duplicates**: Detect repeated rows
3. **Data Types**: Verify correct types
4. **Outliers**: Flag suspicious atypical values
5. **Inconsistencies**: Different names for same entity

For each issue indicate:
- Severity (high/medium/low)
- Affected rows
- Proposed solution

"""
            if generate_code:
                goal += "Generate Python code to clean the data."

        return self.run(goal, tables, execute_code=generate_code)

    # =========================================================================
    # Cleaning Operations
    # =========================================================================

    def clean_nulls(
        self,
        df: pd.DataFrame,
        strategy: str = "auto",
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Clean null values with specified strategy.
        
        Args:
            df: Input DataFrame
            strategy: 'auto', 'drop', 'mean', 'median', 'mode', 'forward', 'zero'
            columns: Columns to clean (all if None)
            
        Returns:
            Cleaned DataFrame
        """
        result = df.copy()
        cols = columns or df.columns.tolist()
        
        for col in cols:
            if col not in result.columns:
                continue
            
            if result[col].isnull().sum() == 0:
                continue
            
            if strategy == "drop":
                result = result.dropna(subset=[col])
            elif strategy == "mean" and pd.api.types.is_numeric_dtype(result[col]):
                result[col] = result[col].fillna(result[col].mean())
            elif strategy == "median" and pd.api.types.is_numeric_dtype(result[col]):
                result[col] = result[col].fillna(result[col].median())
            elif strategy == "mode":
                mode_val = result[col].mode()
                if len(mode_val) > 0:
                    result[col] = result[col].fillna(mode_val[0])
            elif strategy == "forward":
                result[col] = result[col].ffill()
            elif strategy == "zero":
                result[col] = result[col].fillna(0)
            elif strategy == "auto":
                # Auto-select based on type and null percentage
                null_pct = result[col].isnull().sum() / len(result)
                if null_pct > 0.5:
                    continue  # Skip if too many nulls
                if pd.api.types.is_numeric_dtype(result[col]):
                    result[col] = result[col].fillna(result[col].median())
                else:
                    mode_val = result[col].mode()
                    if len(mode_val) > 0:
                        result[col] = result[col].fillna(mode_val[0])
        
        return result

    def remove_duplicates(
        self,
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = "first"
    ) -> pd.DataFrame:
        """
        Remove duplicate rows.
        
        Args:
            df: Input DataFrame
            subset: Columns to consider for duplicates
            keep: 'first', 'last', or False
            
        Returns:
            DataFrame without duplicates
        """
        return df.drop_duplicates(subset=subset, keep=keep)

    def fix_types(
        self,
        df: pd.DataFrame,
        type_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Fix column data types.
        
        Args:
            df: Input DataFrame
            type_map: Dict mapping column names to types ('numeric', 'datetime', 'string')
            
        Returns:
            DataFrame with corrected types
        """
        result = df.copy()
        
        if type_map is None:
            # Auto-detect
            for col in result.columns:
                if result[col].dtype == object:
                    # Try numeric
                    try:
                        result[col] = pd.to_numeric(result[col], errors='coerce')
                        if result[col].notna().sum() > len(result) * 0.5:
                            continue  # Keep as numeric
                        else:
                            result[col] = df[col]  # Revert
                    except:
                        pass
        else:
            for col, dtype in type_map.items():
                if col not in result.columns:
                    continue
                if dtype == "numeric":
                    result[col] = pd.to_numeric(result[col], errors='coerce')
                elif dtype == "datetime":
                    result[col] = pd.to_datetime(result[col], errors='coerce')
                elif dtype == "string":
                    result[col] = result[col].astype(str)
        
        return result


# =============================================================================
# Convenience Function
# =============================================================================

def quick_quality_check(df: pd.DataFrame, name: str = "datos") -> Dict:
    """
    Perform a quick quality check without instantiating the full agent.
    
    Args:
        df: DataFrame to check
        name: Table name
        
    Returns:
        Quality report as dictionary
    """
    agent = DataCleanAgent()
    report = agent.analyze_quality_fast(df, name)
    return report.to_dict()
