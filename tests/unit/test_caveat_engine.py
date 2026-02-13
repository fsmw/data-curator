import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    df = pd.DataFrame(
        {
            "entity": ["A"] * 8 + ["B"] * 2,
            "year": [2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023, 2020, 2021],
            "value": [1.0, None, 2.0, None, 3.0, None, 4.0, None, 1.5, None],
            "_is_imputed": [1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
        }
    )
    return {"id": dataset_id, "indicator_name": "mock-caveats"}, df


def test_caveat_engine_detects_multiple_caveats(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    out = asyncio.run(
        copilot_tools.caveat_engine(
            dataset_id=1,
            sample_threshold=15,
            missing_threshold=0.2,
            concentration_threshold=0.7,
            imputation_threshold=0.1,
        )
    )

    assert out["status"] == "success"
    codes = {c["code"] for c in out["caveats"]}
    assert "small_sample" in codes
    assert "high_missingness" in codes
    assert "high_imputation" in codes
    assert "geographic_concentration" in codes
    assert "short_time_span" in codes


def test_caveat_engine_no_major_caveats(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    out = asyncio.run(
        copilot_tools.caveat_engine(
            dataset_id=1,
            sample_threshold=5,
            missing_threshold=0.9,
            concentration_threshold=0.95,
            imputation_threshold=0.9,
        )
    )

    assert out["status"] == "success"
    assert out["caveat_count"] == 1  # short_time_span still expected
