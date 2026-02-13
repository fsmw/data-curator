import asyncio

from src import copilot_tools


def test_analysis_planner_with_dataset():
    out = asyncio.run(
        copilot_tools.analysis_planner(
            objective="Analyze correlation and regression trends by region",
            dataset_ids=[1],
            include_visualization=True,
            include_robustness=True,
        )
    )

    assert out["status"] == "success"
    assert out["dataset_ids"] == [1]
    tools = [s["tool"] for s in out["steps"]]
    assert "data_profiler" in tools
    assert "correlation_analyzer" in tools
    assert "regression_engine" in tools
    assert "group_classifier" in tools
    assert "smart_visualizer" in tools


def test_analysis_planner_without_dataset():
    out = asyncio.run(copilot_tools.analysis_planner(objective="Need a starting plan"))

    assert out["status"] == "success"
    assert out["dataset_ids"] == []
    assert out["steps"][0]["tool"] == "list_local_datasets"


def test_analysis_planner_empty_objective():
    out = asyncio.run(copilot_tools.analysis_planner(objective=""))
    assert out["status"] == "error"
    assert "objective cannot be empty" in out["error"]
