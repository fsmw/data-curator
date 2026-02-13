import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "B", "B"],
            "year": [2020, 2021, 2020, 2021],
            "value": [1.2, 1.5, 2.0, 2.3],
            "other": [10, 12, 14, 16],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-vis"}, df


def test_smart_visualizer_line(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.smart_visualizer(dataset_id=1, chart_type="line"))
    assert out["status"] == "success"
    assert out["chart_type"] == "line"
    assert out["chart_spec"]["mark"] == "line"
    assert out["fields"]["x"] == "year"


def test_smart_visualizer_heatmap(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.smart_visualizer(
            dataset_id=1,
            chart_type="heatmap",
            x="entity",
            y="year",
            color="value",
        )
    )
    assert out["status"] == "success"
    assert out["chart_spec"]["mark"] == "rect"
    assert out["fields"]["color"] == "value"


def test_smart_visualizer_invalid_type(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.smart_visualizer(dataset_id=1, chart_type="pie"))
    assert out["status"] == "error"
    assert "chart_type must be one of" in out["error"]
