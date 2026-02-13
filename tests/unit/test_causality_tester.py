import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    rows = []
    years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]
    x_a = [1.0, 4.0, 2.0, 5.0, 3.0, 6.0, 2.5, 5.5]
    x_b = [2.0, 3.5, 1.5, 4.5, 2.5, 5.5, 3.0, 6.0]
    y_a = [0.0, 1.0, 4.0, 2.0, 5.0, 3.0, 6.0, 2.5]  # x_a shifted by 1
    y_b = [0.0, 2.0, 3.5, 1.5, 4.5, 2.5, 5.5, 3.0]  # x_b shifted by 1
    for i, year in enumerate(years):
        rows.append({"entity": "A", "year": year, "x": x_a[i], "y": y_a[i]})
        rows.append({"entity": "B", "year": year, "x": x_b[i], "y": y_b[i]})
    df = pd.DataFrame(rows)
    return {"id": dataset_id, "indicator_name": "mock-causality"}, df


def test_causality_tester_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.causality_tester(
            dataset_id=1,
            dependent="y",
            driver="x",
            max_lag=2,
            min_points=10,
        )
    )
    assert out["status"] == "success"
    assert out["signal"]["best_lag"] == 1
    assert len(out["lead_lag"]) == 3


def test_causality_tester_missing_column(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(
        copilot_tools.causality_tester(
            dataset_id=1,
            dependent="y_missing",
            driver="x",
        )
    )
    assert out["status"] == "error"
    assert "Columns not found" in out["error"]
