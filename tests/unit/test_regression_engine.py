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
    # y = 2*x1 - 1*x2 + entity effect + time effect
    entity_effect = {"A": 1.0, "B": 2.0, "C": -1.0}
    time_effect = {2020: -0.5, 2021: 0.0, 2022: 0.5}
    df["y"] = (
        2.0 * df["x1"]
        - 1.0 * df["x2"]
        + df["entity"].map(entity_effect)
        + df["year"].map(time_effect)
    )
    return {"id": dataset_id, "indicator_name": "mock-regression"}, df


def test_regression_engine_pooled(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    out = asyncio.run(
        copilot_tools.regression_engine(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
            model="pooled",
        )
    )

    assert out["status"] == "success"
    assert out["model"] == "pooled"
    assert "coefficients" in out
    assert "x1" in out["coefficients"]


def test_regression_engine_fe_two_way(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    out = asyncio.run(
        copilot_tools.regression_engine(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
            model="fe_two_way",
            entity_column="entity",
            year_column="year",
        )
    )

    assert out["status"] == "success"
    assert out["model"] == "fe_two_way"
    assert out["n_obs"] == 9
    assert "x1" in out["coefficients"]
    assert "x2" in out["coefficients"]


def test_regression_engine_invalid_model(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    out = asyncio.run(
        copilot_tools.regression_engine(
            dataset_id=1,
            dependent="y",
            independents=["x1"],
            model="random_effects",
        )
    )

    assert out["status"] == "error"
    assert "model must be one of" in out["error"]
