"""Cross-framework bridge roundtrip tests.

THE critical test: CrewAI -> .fylle -> OpenAI preserves agent semantics.
"""

import tempfile
from pathlib import Path

import yaml
import pytest

from fylle_format import build_fylle_package, parse_fylle_package, validate
from fylle_bridge.adapters.crewai_adapter import crewai_to_fylle, fylle_to_crewai
from fylle_bridge.adapters.openai_adapter import fylle_to_openai, openai_to_fylle


SAMPLE_CREWAI = {
    "content_researcher": {
        "role": "Content Research Specialist",
        "goal": "Find trending topics and authoritative sources for content creation",
        "backstory": (
            "You are an expert content researcher who excels at identifying "
            "emerging trends, finding credible sources, and synthesizing "
            "complex information into actionable insights for content teams."
        ),
        "tools": ["web_search", "rss_reader"],
        "llm": "claude-sonnet-4-5",
        "max_iter": 20,
        "verbose": False,
        "allow_delegation": True,
    }
}


class TestCrewAIToFylleToOpenAI:
    """The killer test: CrewAI YAML -> .fylle -> OpenAI Assistant JSON."""

    def test_full_bridge(self):
        """Core semantics preserved across CrewAI -> .fylle -> OpenAI."""
        # Step 1: CrewAI -> .fylle
        fylle_agent = crewai_to_fylle(SAMPLE_CREWAI, author_name="Bridge Test")

        # Step 2: Validate
        result = validate(fylle_agent)
        assert result.valid, f"Validation errors: {result.errors}"

        # Step 3: .fylle -> OpenAI
        openai_config = fylle_to_openai(fylle_agent)

        # Verify core semantics
        assert openai_config["name"] == "Content Researcher"
        assert "content researcher" in openai_config["instructions"].lower()
        assert openai_config["model"] == "gpt-4o"  # claude-sonnet-4-5 -> gpt-4o
        assert len(openai_config["tools"]) == 2

        # Tool names preserved
        func_tools = [
            t["function"]["name"]
            for t in openai_config["tools"]
            if t["type"] == "function"
        ]
        assert "web_search" in func_tools
        assert "rss_reader" in func_tools

    def test_bridge_with_package_roundtrip(self):
        """CrewAI -> .fylle -> build ZIP -> parse ZIP -> OpenAI."""
        # Step 1: CrewAI -> FylleAgent
        fylle_agent = crewai_to_fylle(SAMPLE_CREWAI, author_name="Roundtrip Test")

        # Step 2: Build .fylle package
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_path = Path(tmpdir) / "test-agent.fylle"
            build_fylle_package(fylle_agent, pkg_path)

            # Step 3: Parse it back
            parsed = parse_fylle_package(str(pkg_path))

        # Step 4: Export to OpenAI
        openai_config = fylle_to_openai(parsed)

        # Core semantics still intact
        assert openai_config["name"] == "Content Researcher"
        assert "content researcher" in openai_config["instructions"].lower()
        assert len(openai_config["tools"]) == 2

    def test_bridge_preserves_personality(self):
        """System prompt / backstory preserved through the full bridge."""
        fylle_agent = crewai_to_fylle(SAMPLE_CREWAI)
        openai_config = fylle_to_openai(fylle_agent)

        original_backstory = SAMPLE_CREWAI["content_researcher"]["backstory"]
        assert openai_config["instructions"] == original_backstory


class TestOpenAIToFylleToCrewAI:
    """Reverse bridge: OpenAI -> .fylle -> CrewAI."""

    def test_reverse_bridge(self):
        """OpenAI -> .fylle -> CrewAI preserves core semantics."""
        openai_config = {
            "model": "gpt-4o",
            "name": "Data Analyst",
            "description": "Analyzes data and produces reports",
            "instructions": "You are a skilled data analyst.",
            "tools": [
                {"type": "code_interpreter"},
                {
                    "type": "function",
                    "function": {
                        "name": "query_database",
                        "description": "Run SQL queries",
                    },
                },
            ],
            "temperature": 0.3,
        }

        # OpenAI -> .fylle
        fylle_agent = openai_to_fylle(openai_config)
        assert fylle_agent.manifest.agent.name == "Data Analyst"

        # .fylle -> CrewAI
        crewai = fylle_to_crewai(fylle_agent)
        key = next(iter(crewai))
        data = crewai[key]

        assert data["role"] == "Data Analyst"  # name used as role (no role in OpenAI)
        assert "data analyst" in data["backstory"].lower()
        # query_database should be in tools (code_interpreter becomes capability, not tool)
        assert "query_database" in data["tools"]


class TestExistingExampleConversion:
    """Test that existing .fylle examples can be converted to other formats."""

    def test_content_curator_to_crewai(self):
        """Convert the existing content-curator example to CrewAI format."""
        from fylle_format import parse_fylle_package, create_fylle_from_scratch

        # Create a FylleAgent matching the content-curator example
        agent = create_fylle_from_scratch(
            name="Content Curator",
            description="Finds and curates relevant content for marketing newsletters",
            personality="You are a research specialist who finds and curates content.",
            role="Research Specialist",
            model_preferred="claude-sonnet-4-5",
            author_name="Fylle",
        )

        crewai = fylle_to_crewai(agent)
        key = next(iter(crewai))
        data = crewai[key]

        assert data["role"] == "Research Specialist"
        assert "curates content" in data["backstory"]
        assert data["llm"] == "claude-sonnet-4-5"

    def test_content_curator_to_openai(self):
        """Convert the existing content-curator example to OpenAI format."""
        from fylle_format import create_fylle_from_scratch

        agent = create_fylle_from_scratch(
            name="Content Curator",
            description="Finds and curates relevant content for marketing newsletters",
            personality="You are a research specialist who finds and curates content.",
            role="Research Specialist",
            model_preferred="claude-sonnet-4-5",
            author_name="Fylle",
        )

        openai_config = fylle_to_openai(agent)
        assert openai_config["name"] == "Content Curator"
        assert openai_config["model"] == "gpt-4o"  # claude -> gpt mapping
