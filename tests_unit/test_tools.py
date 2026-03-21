"""Tests for shared tool schema converters."""

from bench.tools import to_anthropic_schema, to_gemini_schema, to_openai_schema

SAMPLE_TOOL = {
    "name": "github_list_issues",
    "description": "List issues in a GitHub repository",
    "service": "github",
    "parameters": {
        "owner": {"type": "string", "required": True, "description": "Repository owner"},
        "name": {"type": "string", "required": True, "description": "Repository name"},
        "state": {"type": "string", "required": False, "description": "Filter by state"},
    },
}


def test_openai_schema():
    schema = to_openai_schema(SAMPLE_TOOL)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "github_list_issues"
    assert "owner" in schema["function"]["parameters"]["properties"]
    assert "owner" in schema["function"]["parameters"]["required"]
    assert "name" in schema["function"]["parameters"]["required"]
    assert "state" not in schema["function"]["parameters"]["required"]


def test_anthropic_schema():
    schema = to_anthropic_schema(SAMPLE_TOOL)
    assert schema["name"] == "github_list_issues"
    assert "input_schema" in schema
    assert "owner" in schema["input_schema"]["properties"]
    assert "owner" in schema["input_schema"]["required"]


def test_gemini_schema():
    schema = to_gemini_schema(SAMPLE_TOOL)
    assert schema["name"] == "github_list_issues"
    assert schema["parameters"]["type"] == "OBJECT"
    assert schema["parameters"]["properties"]["owner"]["type"] == "STRING"
    assert "owner" in schema["parameters"]["required"]


def test_tool_with_no_required_params():
    tool = {
        "name": "k8s_list_namespaces",
        "description": "List namespaces",
        "service": "k8s",
        "parameters": {},
    }
    openai = to_openai_schema(tool)
    assert openai["function"]["parameters"]["required"] == []

    anthropic = to_anthropic_schema(tool)
    assert anthropic["input_schema"]["required"] == []

    gemini = to_gemini_schema(tool)
    assert "required" not in gemini["parameters"]
