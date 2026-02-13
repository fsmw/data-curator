import asyncio

import pandas as pd

from src import copilot_tools


def _mock_loader(dataset_id: int):
    years = list(range(2015, 2023))
    rows = []
    for entity, base in [("A", 10.0), ("B", 14.0), ("C", 18.0), ("D", 22.0)]:
        for i, year in enumerate(years):
            x1 = base + i * 0.8
            x2 = (base / 2.0) + i * 0.3
            y = 1.2 * x1 - 0.6 * x2 + (i * 0.1)
            rows.append({"entity": entity, "year": year, "x1": x1, "x2": x2, "y": y})
    df = pd.DataFrame(rows)
    return {"id": dataset_id, "indicator_name": "mock-flow", "source": "owid"}, df


def test_analysis_flow_end_to_end(monkeypatch):
    monkeypatch.setattr(copilot_tools, "_load_catalog_dataset_frame", _mock_loader)

    planner = asyncio.run(
        copilot_tools.analysis_planner(
            objective="Analyze trend, regression robustness and dimension reduction",
            dataset_ids=[1],
            include_visualization=True,
            include_robustness=True,
        )
    )
    assert planner["status"] == "success"

    corr = asyncio.run(copilot_tools.correlation_analyzer(dataset_id=1, columns=["x1", "x2", "y"], method="pooled"))
    reg = asyncio.run(copilot_tools.regression_engine(dataset_id=1, dependent="y", independents=["x1", "x2"], model="pooled"))
    robust = asyncio.run(
        copilot_tools.robustness_checker(
            dataset_id=1,
            dependent="y",
            independents=["x1", "x2"],
            key_variable="x1",
            models=["pooled", "fe_entity"],
        )
    )
    trend = asyncio.run(copilot_tools.trend_analyzer(dataset_id=1, value_column="y", min_points=5))
    dr = asyncio.run(copilot_tools.dimensionality_reducer(dataset_id=1, columns=["x1", "x2", "y"], n_components=2))
    conv = asyncio.run(copilot_tools.convergence_analyzer(dataset_id=1, value_column="y", start_year=2015, end_year=2022))

    assert corr["status"] == "success"
    assert reg["status"] == "success"
    assert robust["status"] == "success"
    assert trend["status"] == "success"
    assert dr["status"] == "success"
    assert conv["status"] == "success"
