import os
from src.config import Config
from src.ai_chat import ChatAssistant


def test_minimax_tool_tag_parsing():
    # Ensure config loads predictably
    os.environ.pop("LLM_PROVIDER", None)

    cfg = Config()
    assistant = ChatAssistant(cfg)

    # Force Ollama code path but stub network calls by overriding _call_llm
    assistant.provider = "ollama"

    # Replace the list_datasets tool with a deterministic stub
    def fake_list_datasets(topic=None, source=None):
        return {"total": 1, "datasets": [{"id": 42, "name": "Test Dataset", "source": "owid"}]}

    assistant.tool_functions["list_datasets"] = fake_list_datasets

    # Simulate an Ollama-generated response that contains the minimax tool tag
    assistant._call_llm = lambda messages, **kwargs: "<minimax:tool_call> list_datasets </invoke> </minimax:tool_call>"

    res = assistant.chat("¿Cuántos datasets tenemos descargados?", conversation_history=[])

    # Basic assertions: tool was called and its output is embedded in the response
    assert isinstance(res, dict)
    assert "tool_calls" in res
    assert any(tc.get("function") == "list_datasets" for tc in res["tool_calls"])
    assert "Test Dataset" in res["response"] or "Test Dataset" in str(res)
