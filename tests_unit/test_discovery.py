"""Tests for test plugin discovery."""

from bench.cli import discover_tests


def test_discover_tool_overload():
    plugins = discover_tests()
    assert "tool-overload" in plugins
    p = plugins["tool-overload"]
    assert p.name == "tool-overload"
    assert p.description


def test_plugin_has_register():
    plugins = discover_tests()
    p = plugins["tool-overload"]
    group = p.register()
    # Should be a click group with commands
    assert hasattr(group, "commands") or hasattr(group, "list_commands")
