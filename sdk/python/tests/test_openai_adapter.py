"""Tests for the OpenAI Assistants adapter."""

import json
import pytest

from fylle_bridge.adapters.openai_adapter import openai_to_fylle, fylle_to_openai
from fylle.schema import ModelCapability


SAMPLE_OPENAI = {
    "model": "gpt-4o",
    "name": "Research Assistant",
    "description": "Finds and analyzes information on any topic",
    "instructions": (
        "You are a research specialist. You find authoritative sources, "
        "cross-reference claims, and produce structured briefs with "
        "executive summaries, key findings, and recommendations."
    ),
    "tools": [
        {"type": "code_interpreter"},
        {"type": "file_search"},
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for current information",
            },
        },
    ],
    "temperature": 0.7,
    "top_p": 0.95,
    "metadata": {"team": "research", "version": "2"},
}

MINIMAL_OPENAI = {
    "model": "gpt-4o-mini",
    "name": "Simple Bot",
    "instructions": "You are a helpful assistant.",
}


class TestOpenAIToFylle:
    def test_basic_conversion(self):
        """OpenAI Assistant JSON -> FylleAgent preserves name, instructions."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        assert agent.manifest.agent.name == "Research Assistant"
        assert "research specialist" in agent.personality

    def test_model_mapped(self):
        """OpenAI model -> .fylle model.preferred (mapped to Claude)."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        # gpt-4o maps to claude-sonnet-4-5
        assert agent.manifest.agent.model.preferred == "claude-sonnet-4-5"

    def test_code_interpreter_as_capability(self):
        """code_interpreter -> model.minimum_capability: [code-execution]."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        caps = agent.manifest.agent.model.minimum_capability
        assert ModelCapability.CODE_EXECUTION in caps

    def test_function_tools_mapped(self):
        """OpenAI function tools -> .fylle tool declarations."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        tool_names = [t.name for t in agent.manifest.agent.tools.required]
        assert "search_web" in tool_names
        assert "file_search" in tool_names

    def test_openai_extensions_preserved(self):
        """top_p, metadata preserved in extensions.openai."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        ext = agent.manifest.agent.extensions.get("openai", {})
        assert ext.get("top_p") == 0.95
        assert ext.get("metadata") == {"team": "research", "version": "2"}
        assert ext.get("original_model") == "gpt-4o"

    def test_temperature_mapped(self):
        """Temperature preserved."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        assert agent.manifest.agent.model.settings.temperature == 0.7

    def test_minimal_assistant(self):
        """Minimal OpenAI config converts successfully."""
        agent = openai_to_fylle(MINIMAL_OPENAI)
        assert agent.manifest.agent.name == "Simple Bot"
        assert "helpful assistant" in agent.personality

    def test_json_string_input(self):
        """Can accept a JSON string instead of a dict."""
        json_str = json.dumps(SAMPLE_OPENAI)
        agent = openai_to_fylle(json_str)
        assert agent.manifest.agent.name == "Research Assistant"

    def test_description_used(self):
        """Description field is preserved."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        assert "Finds and analyzes" in agent.manifest.agent.description


class TestFylleToOpenAI:
    def test_basic_conversion(self):
        """FylleAgent -> OpenAI create params."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        openai_config = fylle_to_openai(agent)

        assert openai_config["name"] == "Research Assistant"
        assert "research specialist" in openai_config["instructions"]
        assert openai_config["model"] == "gpt-4o"  # original model restored

    def test_tools_exported(self):
        """Tools exported correctly."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        openai_config = fylle_to_openai(agent)

        tool_types = [t["type"] for t in openai_config["tools"]]
        assert "code_interpreter" in tool_types
        assert "file_search" in tool_types
        assert "function" in tool_types

    def test_extensions_restored(self):
        """OpenAI extensions restored."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        openai_config = fylle_to_openai(agent)

        assert openai_config.get("top_p") == 0.95
        assert openai_config.get("metadata") == {"team": "research", "version": "2"}

    def test_claude_model_mapped_to_openai(self):
        """Claude model names mapped to OpenAI equivalents."""
        from fylle_bridge.adapters.crewai_adapter import crewai_to_fylle

        crewai = {
            "bot": {
                "role": "Bot",
                "goal": "Help",
                "backstory": "You help.",
                "llm": "claude-sonnet-4-5",
            }
        }
        agent = crewai_to_fylle(crewai)
        openai_config = fylle_to_openai(agent)
        # claude-sonnet-4-5 -> gpt-4o
        assert openai_config["model"] == "gpt-4o"

    def test_roundtrip_preserves_core(self):
        """OpenAI -> .fylle -> OpenAI preserves name, instructions, model."""
        agent = openai_to_fylle(SAMPLE_OPENAI)
        result = fylle_to_openai(agent)

        assert result["name"] == SAMPLE_OPENAI["name"]
        assert result["model"] == SAMPLE_OPENAI["model"]
        assert result["temperature"] == SAMPLE_OPENAI["temperature"]
