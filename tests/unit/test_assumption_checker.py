import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A"] * 8 + ["B"] * 8,
            "year": list(range(2000, 2008)) + list(range(2000, 2008)),
            "x1": [1, 2, 3, 4, 5, 6, 7, 8, 2, 3, 4, 5, 6, 7, 8, 9],
            "x2": [2, 1, 3, 2, 4, 3, 5, 4, 1, 2, 2, 3, 3, 4, 4, 5],
        }
    )
    df["y"] = 1.5 * df["x1"] - 0.8 * df["x2"] + 0.2
    return {"id": dataset_id, "indicator_name": "mock-assumptions"}, df


def test_assumption_checker_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.assumption_checker(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
        )
    )
    assert out["status"] == "success"
    assert out["n_obs"] == 16
    assert len(out["assumptions"]) == 4


def test_assumption_checker_missing_column(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.assumption_checker(
            dataset_id=1,
            dependent="y",
            independents=["x_missing"],
        )
    )
    assert out["status"] == "error"
    assert "Columns not found" in out["error"]
