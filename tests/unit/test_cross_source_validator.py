import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    if dataset_id == 1:
        df = pd.DataFrame(
            {
                "entity": ["A", "A", "B", "B"],
                "year": [2020, 2021, 2020, 2021],
                "value": [10.0, 12.0, 20.0, 22.0],
            }
        )
        return {"id": 1, "indicator_name": "x", "source": "owid"}, df
    df = pd.DataFrame(
        {
            "entity": ["A", "A", "B", "B"],
            "year": [2020, 2021, 2020, 2021],
            "value": [11.0, 13.0, 19.0, 23.0],
        }
    )
    return {"id": 2, "indicator_name": "x", "source": "worldbank"}, df


def test_cross_source_validator_success(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.cross_source_validator(dataset_ids=[1, 2], value_column="value", min_overlap=2))
    assert out["status"] == "success"
    assert len(out["pairwise"]) == 1
    assert out["pairwise"][0]["overlap_points"] == 4
    assert sorted(out["sources"]) == ["owid", "worldbank"]


def test_cross_source_validator_requires_two_datasets(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    out = asyncio.run(copilot_tools.cross_source_validator(dataset_ids=[1]))
    assert out["status"] == "error"
    assert "at least 2" in out["error"]
