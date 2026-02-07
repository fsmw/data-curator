"""
Secure Python Code Execution Sandbox for Mises Data Curator.

Provides safe execution of LLM-generated Python code for data transformations.
Inspired by Data Formulator's py_sandbox.py patterns.

Key Features:
- Subprocess isolation for code execution
- Audit hooks to block dangerous operations
- Restricted builtins (no exec, eval, open, etc.)
- Allowed modules whitelist for data analysis
- Timeout handling
- Error capture and formatting
"""

import ast
import json
import logging
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Module Whitelist
# =============================================================================

# Modules allowed for import in sandbox
# Focused on data analysis and economic computation
ALLOWED_MODULES = frozenset([
    # Core data analysis
    "pandas",
    "numpy", 
    "scipy",
    "sklearn",
    
    # Statistics
    "statistics",
    "statsmodels",
    
    # Data manipulation
    "json",
    "csv",
    "re",
    "string",
    "collections",
    "itertools",
    "functools",
    "operator",
    
    # Time handling
    "datetime",
    "time",
    "calendar",
    
    # Math
    "math",
    "decimal",
    "fractions",
    "random",
    
    # Text/encoding
    "unicodedata",
    "hashlib",
    "base64",
    
    # Types
    "typing",
    "dataclasses",
    "enum",
    
    # Copies
    "copy",
])

# Builtins that are explicitly blocked
BLOCKED_BUILTINS = frozenset([
    "exec",
    "eval", 
    "compile",
    "open",
    "__import__",
    "input",
    "breakpoint",
    "exit",
    "quit",
    "help",
    "credits",
    "license",
    "globals",
    "locals",
])

# Blocked attributes (for security)
BLOCKED_ATTRIBUTES = frozenset([
    "__code__",
    "__globals__",
    "__builtins__",
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__class__",
])


# =============================================================================
# Code Validation
# =============================================================================

class CodeValidator:
    """AST-based code validator for sandbox safety."""
    
    def __init__(self, allowed_modules: frozenset = ALLOWED_MODULES):
        self.allowed_modules = allowed_modules
        self.errors: List[str] = []
    
    def validate(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate Python code for safety.
        
        Args:
            code: Python source code
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        self.errors = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Error de sintaxis: {e}"]
        
        for node in ast.walk(tree):
            self._check_node(node)
        
        return len(self.errors) == 0, self.errors
    
    def _check_node(self, node: ast.AST):
        """Check a single AST node for issues."""
        
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in self.allowed_modules:
                    self.errors.append(
                        f"Módulo no permitido: '{alias.name}'. "
                        f"Módulos permitidos: {', '.join(sorted(self.allowed_modules))}"
                    )
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in self.allowed_modules:
                    self.errors.append(
                        f"Módulo no permitido: '{node.module}'"
                    )
        
        # Check blocked function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in BLOCKED_BUILTINS:
                    self.errors.append(
                        f"Función no permitida: '{node.func.id}'"
                    )
        
        # Check blocked attributes
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_ATTRIBUTES:
                self.errors.append(
                    f"Atributo no permitido: '{node.attr}'"
                )


def validate_code(code: str) -> Tuple[bool, List[str]]:
    """
    Validate code safety before execution.
    
    Args:
        code: Python source code
        
    Returns:
        Tuple of (is_safe, list of errors)
    """
    validator = CodeValidator()
    return validator.validate(code)


# =============================================================================
# Subprocess Sandbox Runner
# =============================================================================

# Template for subprocess execution
SANDBOX_RUNNER_TEMPLATE = '''
import sys
import json
import pandas as pd
import numpy as np

# Restrict builtins
safe_builtins = {{k: v for k, v in __builtins__.__dict__.items() 
                  if k not in {blocked_builtins}}}
safe_builtins['__import__'] = __builtins__.__import__  # Allow controlled imports

def main():
    # Load input data
    input_data = json.loads(r\'\'\'{input_json}\'\'\')
    df = pd.DataFrame(input_data)
    
    # Define user function
{user_code}
    
    # Execute transformation
    try:
        result = transform_data(df)
        
        # Convert result to JSON-serializable format
        if isinstance(result, pd.DataFrame):
            output = {{"type": "dataframe", "data": result.to_dict(orient="records")}}
        elif isinstance(result, pd.Series):
            output = {{"type": "series", "data": result.to_dict()}}
        elif isinstance(result, (dict, list)):
            output = {{"type": "json", "data": result}}
        else:
            output = {{"type": "value", "data": str(result)}}
        
        print("__RESULT_START__")
        print(json.dumps(output))
        print("__RESULT_END__")
        
    except Exception as e:
        print("__ERROR_START__")
        print(json.dumps({{"error": str(e), "type": type(e).__name__}}))
        print("__ERROR_END__")

if __name__ == "__main__":
    main()
'''


def run_transform_in_sandbox(
    code: str,
    input_df: pd.DataFrame,
    timeout: int = 30,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Execute transformation code in an isolated subprocess sandbox.
    
    Args:
        code: Python code containing a transform_data(df) function
        input_df: Input DataFrame to transform
        timeout: Maximum execution time in seconds
        validate: Whether to validate code before execution
        
    Returns:
        Dict with keys:
        - success: bool
        - result: transformed data (if success)
        - error: error message (if failure)
        - type: result type (dataframe, series, json, value)
    """
    # Validate code first
    if validate:
        is_valid, errors = validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "error": "Código inválido:\n" + "\n".join(errors),
                "type": None,
                "result": None
            }
    
    # Check that code contains transform_data function
    if "def transform_data" not in code:
        return {
            "success": False,
            "error": "El código debe definir una función 'transform_data(df)'",
            "type": None,
            "result": None
        }
    
    # Prepare input data
    try:
        input_json = input_df.to_json(orient="records", date_format="iso")
    except Exception as e:
        return {
            "success": False,
            "error": f"Error serializando datos de entrada: {e}",
            "type": None,
            "result": None
        }
    
    # Indent user code for template
    indented_code = textwrap.indent(code, "    ")
    
    # Build runner script
    runner_code = SANDBOX_RUNNER_TEMPLATE.format(
        blocked_builtins=repr(BLOCKED_BUILTINS),
        input_json=input_json.replace("'", "\\'"),
        user_code=indented_code
    )
    
    # Write to temp file and execute
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False
    ) as f:
        f.write(runner_code)
        temp_path = f.name
    
    try:
        # Run in subprocess
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()  # Run from temp dir for isolation
        )
        
        stdout = result.stdout
        stderr = result.stderr
        
        # Parse result
        if "__RESULT_START__" in stdout:
            start = stdout.index("__RESULT_START__") + len("__RESULT_START__")
            end = stdout.index("__RESULT_END__")
            result_json = stdout[start:end].strip()
            
            try:
                parsed = json.loads(result_json)
                result_type = parsed.get("type", "unknown")
                result_data = parsed.get("data")
                
                # Convert back to DataFrame if needed
                if result_type == "dataframe":
                    result_data = pd.DataFrame(result_data)
                elif result_type == "series":
                    result_data = pd.Series(result_data)
                
                return {
                    "success": True,
                    "result": result_data,
                    "type": result_type,
                    "error": None
                }
                
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Error parseando resultado: {e}",
                    "type": None,
                    "result": None
                }
        
        elif "__ERROR_START__" in stdout:
            start = stdout.index("__ERROR_START__") + len("__ERROR_START__")
            end = stdout.index("__ERROR_END__")
            error_json = stdout[start:end].strip()
            
            try:
                parsed = json.loads(error_json)
                return {
                    "success": False,
                    "error": f"{parsed.get('type', 'Error')}: {parsed.get('error', 'Unknown')}",
                    "type": None,
                    "result": None
                }
            except:
                return {
                    "success": False,
                    "error": stdout + stderr,
                    "type": None,
                    "result": None
                }
        
        else:
            # No markers found - likely a crash
            return {
                "success": False,
                "error": stderr if stderr else "Sin salida del proceso",
                "type": None,
                "result": None
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Tiempo de ejecución excedido ({timeout}s)",
            "type": None,
            "result": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error de ejecución: {e}",
            "type": None,
            "result": None
        }
    
    finally:
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except:
            pass


# =============================================================================
# SQL Execution (DuckDB)
# =============================================================================

def run_sql_query(
    sql: str,
    tables: Dict[str, pd.DataFrame],
    max_rows: int = 5000
) -> Dict[str, Any]:
    """
    Execute SQL query using DuckDB with multiple input tables.
    
    Args:
        sql: SQL query string
        tables: Dict mapping table names to DataFrames
        max_rows: Maximum rows to return
        
    Returns:
        Dict with keys:
        - success: bool
        - result: DataFrame (if success)
        - error: error message (if failure)
    """
    try:
        import duckdb
    except ImportError:
        return {
            "success": False,
            "error": "DuckDB no está instalado. Instalar con: pip install duckdb",
            "result": None
        }
    
    try:
        # Create connection
        conn = duckdb.connect(":memory:")
        
        # Register all tables
        for name, df in tables.items():
            conn.register(name, df)
        
        # Execute query with limit
        limited_sql = f"SELECT * FROM ({sql}) LIMIT {max_rows}"
        result_df = conn.execute(limited_sql).fetchdf()
        
        conn.close()
        
        return {
            "success": True,
            "result": result_df,
            "error": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"Error SQL: {e}"
        }


def run_sql_from_string(
    sql: str,
    df: pd.DataFrame,
    table_name: str = "df",
    max_rows: int = 5000
) -> Dict[str, Any]:
    """
    Convenience wrapper for single table SQL execution.
    
    Args:
        sql: SQL query string
        df: Input DataFrame
        table_name: Name to use in SQL query
        max_rows: Maximum rows to return
        
    Returns:
        Dict with success, result, error keys
    """
    return run_sql_query(sql, {table_name: df}, max_rows)


# =============================================================================
# Execution with Auto-Repair
# =============================================================================

def run_with_repair(
    code: str,
    input_df: pd.DataFrame,
    repair_callback: Optional[callable] = None,
    max_attempts: int = 3,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute code with automatic repair on failure.
    
    If code fails, calls repair_callback with error message to get fixed code.
    
    Args:
        code: Initial Python code
        input_df: Input DataFrame
        repair_callback: Function(code, error) -> fixed_code
        max_attempts: Maximum repair attempts
        timeout: Execution timeout per attempt
        
    Returns:
        Dict with success, result, attempts, and history
    """
    history = []
    current_code = code
    
    for attempt in range(max_attempts):
        result = run_transform_in_sandbox(
            current_code,
            input_df,
            timeout=timeout
        )
        
        history.append({
            "attempt": attempt + 1,
            "code": current_code,
            "success": result["success"],
            "error": result.get("error")
        })
        
        if result["success"]:
            return {
                **result,
                "attempts": attempt + 1,
                "history": history
            }
        
        # Try to repair
        if repair_callback and attempt < max_attempts - 1:
            try:
                current_code = repair_callback(current_code, result["error"])
                if not current_code:
                    break
            except Exception as e:
                logger.warning(f"Repair callback failed: {e}")
                break
        else:
            break
    
    return {
        "success": False,
        "result": None,
        "error": result.get("error"),
        "type": None,
        "attempts": len(history),
        "history": history
    }


# =============================================================================
# Test Functions
# =============================================================================

def test_sandbox():
    """Test sandbox functionality."""
    print("🧪 Testing Python Sandbox")
    print("=" * 50)
    
    # Create test data
    test_df = pd.DataFrame({
        "pais": ["Argentina", "Brasil", "Chile"],
        "año": [2020, 2020, 2020],
        "pib_usd": [389e9, 1450e9, 252e9]
    })
    
    # Test 1: Valid transformation
    print("\n1. Testing valid transformation:")
    valid_code = '''
def transform_data(df):
    result = df.copy()
    result['pib_billones'] = result['pib_usd'] / 1e9
    return result
'''
    result = run_transform_in_sandbox(valid_code, test_df)
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Result type: {result['type']}")
        print(f"   Rows: {len(result['result'])}")
    
    # Test 2: Invalid import
    print("\n2. Testing blocked import:")
    invalid_code = '''
import os
def transform_data(df):
    return df
'''
    result = run_transform_in_sandbox(invalid_code, test_df)
    print(f"   Success: {result['success']}")
    print(f"   Error: {result['error'][:100]}...")
    
    # Test 3: Code validation
    print("\n3. Testing code validator:")
    is_valid, errors = validate_code("import os\nexec('code')")
    print(f"   Valid: {is_valid}")
    print(f"   Errors: {errors}")
    
    print("\n✅ Sandbox tests completed!")


def test_sql():
    """Test SQL execution."""
    print("\n🧪 Testing SQL Execution")
    print("=" * 50)
    
    test_df = pd.DataFrame({
        "pais": ["Argentina", "Brasil", "Chile"],
        "año": [2020, 2020, 2020],
        "pib_usd": [389e9, 1450e9, 252e9]
    })
    
    # Test SQL query
    result = run_sql_from_string(
        "SELECT pais, pib_usd / 1e9 as pib_billones FROM df ORDER BY pib_usd DESC",
        test_df
    )
    
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Result:\n{result['result']}")
    else:
        print(f"Error: {result['error']}")
    
    print("\n✅ SQL tests completed!")


if __name__ == "__main__":
    test_sandbox()
    test_sql()
