import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A"] * 5 + ["B"] * 5,
            "year": [2018, 2019, 2020, 2021, 2022] * 2,
            "value": [10.0, 11.0, 12.5, 14.0, 16.0, 20.0, 19.5, 19.0, 18.0, 17.5],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-trend"}, df


def test_trend_analyzer_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.trend_analyzer(dataset_id=1, value_column="value", min_points=4, top_entities=5))
    assert out["status"] == "success"
    assert out["overall_trend"]["n_years"] == 5
    assert out["overall_trend"]["direction"] in {"increasing", "decreasing", "flat"}
    assert len(out["entity_trends"]) == 2


def test_trend_analyzer_missing_value_column(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.trend_analyzer(dataset_id=1, value_column="missing_col"))
    assert out["status"] == "success"
    assert out["value_column"] == "value"
