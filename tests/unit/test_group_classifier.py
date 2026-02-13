import asyncio

import pandas as pd

from src import copilot_tools


class _MockConfig:
    def get_regions(self):
        return {
            "latam": ["ARG", "BRA"],
            "oecd": ["USA", "DEU"],
        }


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["ARG", "BRA", "USA", "DEU", "XYZ"],
            "year": [2020, 2020, 2020, 2020, 2020],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
            "income_group": ["upper-middle", "upper-middle", "high", "high", None],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-groups"}, df


def _mock_loader_no_income(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["ARG", "BRA", "USA"],
            "year": [2020, 2020, 2020],
            "value": [1.0, 2.0, 3.0],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-groups-no-income"}, df


def test_group_classifier_region(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    monkeypatch.setattr(copilot_tools, "get_config", lambda: _MockConfig())

    out = asyncio.run(copilot_tools.group_classifier(dataset_id=1, group_by="region"))

    assert out["status"] == "success"
    assert out["group_by"] == "region"
    groups = {row["group"] for row in out["groups"]}
    assert "LATAM" in groups
    assert "OECD" in groups


def test_group_classifier_income_and_unknown(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)
    monkeypatch.setattr(copilot_tools, "get_config", lambda: _MockConfig())

    out = asyncio.run(copilot_tools.group_classifier(dataset_id=1, group_by="income", income_column="income_group"))

    assert out["status"] == "success"
    groups = {row["group"] for row in out["groups"]}
    assert "high" in groups
    assert "upper-middle" in groups
    assert any("unknown" in w.lower() for w in out["warnings"])


def test_group_classifier_income_missing_metadata(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader_no_income)
    monkeypatch.setattr(copilot_tools, "get_config", lambda: _MockConfig())

    out = asyncio.run(copilot_tools.group_classifier(dataset_id=1, group_by="income"))

    assert out["status"] == "error"
    assert "Income metadata not found" in out["error"]
