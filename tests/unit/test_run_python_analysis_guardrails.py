import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "B", "B"],
            "year": [2020, 2021, 2020, 2021],
            "x": [1.0, 2.0, 3.0, 4.0],
            "y": [2.0, 4.1, 5.9, 8.2],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-guardrails"}, df


def test_run_python_analysis_blocks_import(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.run_python_analysis(
            dataset_ids=[1],
            python_code="import os\nresult = {'ok': True}",
        )
    )
    assert out["status"] == "error"
    assert "disallowed statements" in out["error"]


def test_run_python_analysis_blocks_unsafe_builtins(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.run_python_analysis(
            dataset_ids=[1],
            python_code="result = {'cwd': __import__('os').getcwd()}",
        )
    )
    assert out["status"] == "error"
    assert "__import__" in out["error"]
