"""Tests for the OpenClaw adapter."""

import pytest

from fylle_bridge.adapters.openclaw_adapter import (
    openclaw_to_fylle,
    fylle_to_openclaw,
    parse_soul_md,
)


SAMPLE_SOUL_MD = """# Bugsy

## Identity
- **Name:** Bugsy
- **Role:** QA Engineer
- **Model:** claude-sonnet-4-5
- **Tone:** Professional

## Personality
You are a meticulous QA engineer who catches every bug. You write comprehensive
test plans, identify edge cases others miss, and document reproduction steps
clearly. Think like a user who wants to break things.

## Greeting
> Hi! I'm Bugsy, your QA engineer. Let me test your code and find every bug
> before your users do.

## Skills
- Code Generation
- Research
- Data Analysis

## Rules
Always respond in English
Never share sensitive data
Ask for clarification when unsure
Keep responses concise
"""

MINIMAL_SOUL_MD = """# SimpleBot

## Personality
You are a helpful assistant.
"""


class TestParseSoulMd:
    def test_parse_sections(self):
        """SOUL.md parsed into correct sections."""
        sections = parse_soul_md(SAMPLE_SOUL_MD)
        assert sections.get("_title") == "Bugsy"
        assert "identity" in sections
        assert "personality" in sections
        assert "greeting" in sections
        assert "skills" in sections
        assert "rules" in sections

    def test_parse_minimal(self):
        """Minimal SOUL.md with just title and personality."""
        sections = parse_soul_md(MINIMAL_SOUL_MD)
        assert sections.get("_title") == "SimpleBot"
        assert "helpful assistant" in sections.get("personality", "")


class TestOpenClawToFylle:
    def test_basic_conversion(self):
        """SOUL.md -> FylleAgent preserves identity."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        assert agent.manifest.agent.name == "Bugsy"
        assert agent.manifest.agent.role == "QA Engineer"
        assert agent.manifest.agent.model.preferred == "claude-sonnet-4-5"
        assert agent.manifest.agent.tone == "Professional"

    def test_personality_preserved(self):
        """Personality section becomes agent.md content."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        assert "meticulous QA engineer" in agent.personality

    def test_rules_become_guardrails(self):
        """Rules -> guardrails rules."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        assert agent.guardrails is not None
        assert len(agent.guardrails.rules) == 4
        rule_texts = [r.description for r in agent.guardrails.rules]
        assert "Always respond in English" in rule_texts
        assert "Never share sensitive data" in rule_texts

    def test_skills_become_tools(self):
        """Skills list -> tool declarations."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        tool_names = [t.name for t in agent.manifest.agent.tools.optional]
        assert "code_generation" in tool_names
        assert "research" in tool_names
        assert "data_analysis" in tool_names

    def test_greeting_in_extensions(self):
        """Greeting preserved in extensions."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        ext = agent.manifest.agent.extensions.get("openclaw", {})
        assert "Bugsy" in ext.get("greeting", "")

    def test_dict_input_with_extra_files(self):
        """Can pass dict with soul_md + extra workspace files."""
        data = {
            "soul_md": SAMPLE_SOUL_MD,
            "user_md": "I am a Python developer who prefers pytest.",
            "tools_md": "SSH alias: dev-server → 10.0.0.1",
        }
        agent = openclaw_to_fylle(data)
        ext = agent.manifest.agent.extensions.get("openclaw", {})
        assert "Python developer" in ext.get("user_context", "")
        assert "SSH alias" in ext.get("tools_notes", "")

    def test_minimal_soul(self):
        """Minimal SOUL.md converts without errors."""
        agent = openclaw_to_fylle(MINIMAL_SOUL_MD)
        assert agent.manifest.agent.name == "SimpleBot"
        assert "helpful assistant" in agent.personality

    def test_model_with_provider_prefix(self):
        """Model string with provider/ prefix is parsed correctly."""
        soul = """# Bot
## Identity
- **Model:** anthropic/claude-sonnet-4-5
## Personality
You help.
"""
        agent = openclaw_to_fylle(soul)
        assert agent.manifest.agent.model.preferred == "claude-sonnet-4-5"

    def test_manifest_is_valid(self):
        """Resulting FylleAgent has valid manifest."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        assert agent.manifest.fylle_format == "0.1.0"
        assert agent.manifest.agent.version == "1.0.0"


class TestFylleToOpenClaw:
    def test_basic_conversion(self):
        """FylleAgent -> SOUL.md has correct structure."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        result = fylle_to_openclaw(agent)

        soul = result["soul_md"]
        assert "# Bugsy" in soul
        assert "## Identity" in soul
        assert "## Personality" in soul
        assert "**Role:** QA Engineer" in soul
        assert "**Model:** claude-sonnet-4-5" in soul

    def test_rules_exported(self):
        """Guardrails rules -> Rules section."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        result = fylle_to_openclaw(agent)
        soul = result["soul_md"]
        assert "## Rules" in soul
        assert "Always respond in English" in soul

    def test_skills_exported(self):
        """Tools -> Skills section."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        result = fylle_to_openclaw(agent)
        soul = result["soul_md"]
        assert "## Skills" in soul
        assert "Code Generation" in soul

    def test_roundtrip_preserves_core(self):
        """SOUL.md -> .fylle -> SOUL.md preserves name, role, personality."""
        agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        result = fylle_to_openclaw(agent)
        soul = result["soul_md"]

        assert "Bugsy" in soul
        assert "QA Engineer" in soul
        assert "meticulous QA engineer" in soul
