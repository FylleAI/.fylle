"""Tests for the CrewAI adapter."""

import yaml
import pytest

from fylle_bridge.adapters.crewai_adapter import crewai_to_fylle, fylle_to_crewai


SAMPLE_CREWAI = {
    "research_analyst": {
        "role": "Senior Research Analyst",
        "goal": "Find and synthesize comprehensive information on emerging technology trends",
        "backstory": (
            "You are a seasoned research analyst with over 10 years of experience "
            "in technology analysis."
        ),
        "tools": ["search_tool", "scrape_tool"],
        "llm": "claude-sonnet-4-5",
        "max_iter": 25,
        "verbose": True,
        "allow_delegation": False,
    }
}

MINIMAL_CREWAI = {
    "simple_bot": {
        "role": "Helper",
        "goal": "Help users with questions",
        "backstory": "You are a helpful assistant.",
    }
}


class TestCrewAIToFylle:
    def test_basic_conversion(self):
        """CrewAI YAML -> FylleAgent preserves role, goal, backstory."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        assert agent.manifest.agent.name == "Research Analyst"
        assert agent.manifest.agent.role == "Senior Research Analyst"
        assert agent.manifest.agent.description.startswith("Find and synthesize")
        assert "seasoned research analyst" in agent.personality

    def test_tools_mapped(self):
        """CrewAI tools list -> .fylle ToolDeclaration objects."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        tool_names = [t.name for t in agent.manifest.agent.tools.required]
        assert "search_tool" in tool_names
        assert "scrape_tool" in tool_names
        assert len(tool_names) == 2

    def test_model_mapped(self):
        """CrewAI llm field -> .fylle model.preferred."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        assert agent.manifest.agent.model.preferred == "claude-sonnet-4-5"

    def test_max_iter_mapped(self):
        """CrewAI max_iter -> .fylle guardrails.limits.max_iterations."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        assert agent.manifest.agent.guardrails.limits.max_iterations == 25

    def test_unknown_fields_in_extensions(self):
        """CrewAI-specific fields -> extensions.crewai."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        ext = agent.manifest.agent.extensions.get("crewai", {})
        assert ext.get("allow_delegation") is False
        assert ext.get("verbose") is True

    def test_specific_agent_key(self):
        """Can select a specific agent from multi-agent config."""
        multi = {
            "agent_a": {"role": "A", "goal": "Goal A", "backstory": "Story A"},
            "agent_b": {"role": "B", "goal": "Goal B", "backstory": "Story B"},
        }
        agent = crewai_to_fylle(multi, agent_key="agent_b")
        assert agent.manifest.agent.role == "B"

    def test_minimal_agent(self):
        """Minimal CrewAI config converts successfully."""
        agent = crewai_to_fylle(MINIMAL_CREWAI)
        assert agent.manifest.agent.name == "Simple Bot"
        assert agent.manifest.agent.role == "Helper"
        assert len(agent.manifest.agent.tools.required) == 0

    def test_yaml_string_input(self):
        """Can accept a YAML string instead of a dict."""
        yaml_str = yaml.dump(SAMPLE_CREWAI)
        agent = crewai_to_fylle(yaml_str)
        assert agent.manifest.agent.name == "Research Analyst"

    def test_manifest_is_valid(self):
        """Resulting FylleAgent has valid manifest structure."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        assert agent.manifest.fylle_format == "0.1.0"
        assert agent.manifest.agent.version == "1.0.0"
        assert agent.manifest.agent.author.name == "Unknown"
        assert agent.manifest.agent.license == "MIT"

    def test_custom_author(self):
        """Author info is correctly set."""
        agent = crewai_to_fylle(
            SAMPLE_CREWAI,
            author_name="Test Author",
            author_url="https://test.com",
            version="2.0.0",
            license_id="Apache-2.0",
        )
        assert agent.manifest.agent.author.name == "Test Author"
        assert agent.manifest.agent.author.url == "https://test.com"
        assert agent.manifest.agent.version == "2.0.0"
        assert agent.manifest.agent.license == "Apache-2.0"


class TestFylleToCrewAI:
    def test_basic_conversion(self):
        """FylleAgent -> CrewAI YAML dict has expected structure."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        crewai = fylle_to_crewai(agent)

        assert "research_analyst" in crewai
        data = crewai["research_analyst"]
        assert data["role"] == "Senior Research Analyst"
        assert "seasoned research analyst" in data["backstory"]
        assert data["llm"] == "claude-sonnet-4-5"

    def test_tools_roundtrip(self):
        """Tools preserved in roundtrip."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        crewai = fylle_to_crewai(agent)
        data = crewai["research_analyst"]
        assert "search_tool" in data["tools"]
        assert "scrape_tool" in data["tools"]

    def test_extensions_restored(self):
        """CrewAI extensions restored from .fylle."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        crewai = fylle_to_crewai(agent)
        data = crewai["research_analyst"]
        assert data.get("allow_delegation") is False
        assert data.get("verbose") is True

    def test_roundtrip_preserves_core(self):
        """CrewAI -> .fylle -> CrewAI preserves role, goal, backstory."""
        agent = crewai_to_fylle(SAMPLE_CREWAI)
        crewai = fylle_to_crewai(agent)
        data = crewai["research_analyst"]

        original = SAMPLE_CREWAI["research_analyst"]
        assert data["role"] == original["role"]
        assert data["goal"] == original["goal"]
        assert data["backstory"] == original["backstory"]
