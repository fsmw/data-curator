import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "year": [2020, 2021, 2022, 2020, 2021, 2022, 2020, 2021, 2022],
            "x1": [1, 2, 3, 2, 3, 4, 1, 3, 5],
            "x2": [2, 1, 2, 1, 2, 1, 3, 2, 1],
        }
    )
    entity_effect = {"A": 1.0, "B": 2.0, "C": -1.0}
    time_effect = {2020: -0.5, 2021: 0.0, 2022: 0.5}
    df["y"] = (
        2.0 * df["x1"]
        - 1.0 * df["x2"]
        + df["entity"].map(entity_effect)
        + df["year"].map(time_effect)
    )
    return {"id": dataset_id, "indicator_name": "mock-robustness"}, df


def test_robustness_checker_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.robustness_checker(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
            key_variable="x1",
        )
    )
    assert out["status"] == "success"
    assert "stability" in out
    assert out["stability"]["key_variable"] == "x1"
    assert len(out["models_run"]) >= 2


def test_robustness_checker_invalid_key_variable(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.robustness_checker(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
            key_variable="x3",
        )
    )
    assert out["status"] == "error"
    assert "key_variable must be included" in out["error"]
