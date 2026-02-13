import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "year": [2000, 2001, 2002, 2003, 2000, 2001, 2002, 2003],
            "x": [1, 2, 3, 4, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 3, 6, 9, 12],
            "z": [8, 7, 6, 5, 9, 8, 7, 6],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-corr"}, df


def test_correlation_analyzer_pooled(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    result = asyncio.run(
        copilot_tools.correlation_analyzer(
            dataset_id=1,
            columns=["x", "y", "z"],
            method="pooled",
            top_n=2,
        )
    )

    assert result["status"] == "success"
    assert result["method"] == "pooled"
    assert "correlation_matrix" in result
    assert len(result["top_pairs"]) > 0
    assert "interpretation" in result


def test_correlation_analyzer_rolling(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    result = asyncio.run(
        copilot_tools.correlation_analyzer(
            dataset_id=1,
            columns=["x", "y"],
            method="rolling",
            entity_column="entity",
            year_column="year",
            window=3,
            min_periods=2,
        )
    )

    assert result["status"] == "success"
    assert result["method"] == "rolling"
    assert result["observations"] > 0
    assert len(result["top_pairs"]) >= 1
