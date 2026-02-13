import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "year": [2019, 2020, 2021, 2019, 2020, 2021, 2019, 2020, 2021],
            "x1": [1.0, 1.5, 2.0, 2.0, 2.4, 2.8, 3.0, 3.4, 3.8],
            "x2": [10.0, 10.8, 11.6, 12.0, 12.9, 13.8, 14.2, 15.0, 15.9],
            "x3": [100.0, 101.0, 102.0, 99.5, 100.7, 101.8, 98.9, 100.1, 101.2],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-pca"}, df


def test_dimensionality_reducer_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.dimensionality_reducer(dataset_id=1, columns=["x1", "x2", "x3"], n_components=2))
    assert out["status"] == "success"
    assert out["n_components"] == 2
    assert len(out["explained_variance_ratio"]) == 2
    assert out["n_rows_used"] == 9


def test_dimensionality_reducer_requires_numeric(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.dimensionality_reducer(dataset_id=1, columns=["entity"], n_components=2))
    assert out["status"] == "error"
    assert "At least 2 numeric columns" in out["error"]
