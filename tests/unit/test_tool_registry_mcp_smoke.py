import asyncio

from src import copilot_tools


def test_list_available_tools_matches_registry():
    out = asyncio.run(copilot_tools.list_available_tools(include_parameters=True))
    assert out["status"] == "success"
    assert out["total"] == len(copilot_tools.TOOL_REGISTRY)
    names = {t["name"] for t in out["tools"]}
    assert names == set(copilot_tools.TOOL_REGISTRY.keys())


def test_execute_tool_dispatch_all_registry_tools(monkeypatch):
    async def _dummy_tool(**kwargs):
        return {"status": "success", "kwargs": kwargs}

    for name in list(copilot_tools.TOOL_REGISTRY.keys()):
        monkeypatch.setitem(copilot_tools.TOOL_REGISTRY[name], "function", _dummy_tool)

    for name in list(copilot_tools.TOOL_REGISTRY.keys()):
        out = asyncio.run(copilot_tools.execute_tool(name, smoke=True))
        assert out["status"] == "success"
        assert out["kwargs"]["smoke"] is True
