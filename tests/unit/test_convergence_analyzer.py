import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "year": [2010, 2015, 2020, 2010, 2015, 2020, 2010, 2015, 2020],
            "value": [5.0, 9.0, 12.0, 10.0, 12.0, 14.0, 20.0, 18.0, 16.0],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-convergence"}, df


def test_convergence_analyzer_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.convergence_analyzer(dataset_id=1, value_column="value", start_year=2010, end_year=2020))
    assert out["status"] == "success"
    assert out["sample"]["entities"] == 3
    assert "beta_convergence" in out
    assert "sigma_convergence" in out


def test_convergence_analyzer_invalid_period(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.convergence_analyzer(dataset_id=1, start_year=2020, end_year=2020))
    assert out["status"] == "error"
    assert "end_year must be greater" in out["error"]
