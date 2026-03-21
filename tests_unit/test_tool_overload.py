"""Tests for the tool-overload test plugin."""

import random

from tests.tool_overload.prompts import load_prompts
from tests.tool_overload.runner import (
    _get_tools_by_service,
    _is_cross_service_error,
    _pick_disclosed_subset,
    _pick_noisy_subset,
    _pick_tool_subset,
    _select_tools_for_run,
)
from tests.tool_overload.tools import load_all_tools


def test_load_tools():
    tools = load_all_tools()
    assert len(tools) > 0
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "service" in t
        assert "parameters" in t


def test_load_prompts():
    prompts = load_prompts()
    assert len(prompts) > 0
    for p in prompts:
        assert "id" in p
        assert "prompt" in p
        assert "expected_tool" in p
        assert "category" in p


def test_tools_by_service():
    tools = load_all_tools()
    by_svc = _get_tools_by_service(tools)
    assert "github" in by_svc
    assert "gitlab" in by_svc
    assert "k8s" in by_svc
    total = sum(len(v) for v in by_svc.values())
    assert total == len(tools)


def test_pick_tool_subset_includes_expected():
    tools = load_all_tools()
    rng = random.Random(42)
    for _ in range(10):
        subset = _pick_tool_subset(tools, "github_list_issues", 10, rng)
        assert len(subset) == 10
        names = [t["name"] for t in subset]
        assert "github_list_issues" in names


def test_pick_tool_subset_includes_confusors():
    tools = load_all_tools()
    rng = random.Random(42)
    subset = _pick_tool_subset(tools, "github_list_issues", 10, rng)
    names = [t["name"] for t in subset]
    # Should include at least one other github_ tool
    github_tools = [n for n in names if n.startswith("github_") and n != "github_list_issues"]
    assert len(github_tools) >= 1


def test_disclosed_subset_single_service():
    tools = load_all_tools()
    rng = random.Random(42)
    subset = _pick_disclosed_subset(tools, "github_list_issues", rng)
    services = set(t["service"] for t in subset)
    assert services == {"github"}
    assert any(t["name"] == "github_list_issues" for t in subset)


def test_noisy_subset_two_services():
    tools = load_all_tools()
    rng = random.Random(42)
    subset = _pick_noisy_subset(tools, "github_list_issues", rng)
    services = set(t["service"] for t in subset)
    assert "github" in services
    assert len(services) == 2


def test_select_tools_all_mode():
    tools = load_all_tools()
    rng = random.Random(42)
    subset = _select_tools_for_run("all", tools, "github_list_issues", 0, rng)
    assert len(subset) == len(tools)


def test_select_tools_random_mode():
    tools = load_all_tools()
    rng = random.Random(42)
    subset = _select_tools_for_run("random", tools, "github_list_issues", 15, rng)
    assert len(subset) == 15


def test_cross_service_error_same_service():
    tools = [
        {"name": "github_list_issues", "service": "github"},
        {"name": "github_create_issue", "service": "github"},
    ]
    assert not _is_cross_service_error("github_create_issue", "github_list_issues", tools)


def test_cross_service_error_different_service():
    tools = [
        {"name": "github_list_issues", "service": "github"},
        {"name": "gitlab_list_issues", "service": "gitlab"},
    ]
    assert _is_cross_service_error("gitlab_list_issues", "github_list_issues", tools)


def test_cross_service_error_none_actual():
    tools = [{"name": "github_list_issues", "service": "github"}]
    assert not _is_cross_service_error(None, "github_list_issues", tools)


def test_cross_service_error_correct():
    tools = [{"name": "github_list_issues", "service": "github"}]
    assert not _is_cross_service_error("github_list_issues", "github_list_issues", tools)


def test_all_prompts_reference_valid_tools():
    """Every prompt's expected_tool should exist in the tool definitions."""
    tools = load_all_tools()
    tool_names = {t["name"] for t in tools}
    prompts = load_prompts()
    for p in prompts:
        assert p["expected_tool"] in tool_names, f"Prompt {p['id']} references unknown tool {p['expected_tool']}"
