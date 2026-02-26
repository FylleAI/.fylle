"""Tests for the Claude Code adapter."""

import pytest

from fylle_bridge.adapters.claude_code_adapter import (
    claude_code_to_fylle,
    fylle_to_claude_code,
)
from fylle_bridge.adapters.openclaw_adapter import openclaw_to_fylle


SAMPLE_CLAUDE_WORKSPACE = {
    "name": "My Project Agent",
    "claude_md": """# My Project

## Quick Facts
- Stack: Python, FastAPI, PostgreSQL
- Test command: pytest
- Build: docker compose up

## Code Style
- Use type hints everywhere
- Prefer dataclasses over dicts
- Write docstrings for all public functions

## Architecture
- Hexagonal architecture
- All services in app/services/
- Domain models in app/domain/
""",
    "mcp_json": {
        "mcpServers": {
            "github": {
                "type": "http",
                "url": "https://api.githubcopilot.com/mcp/",
            },
            "notion": {
                "type": "http",
                "url": "https://mcp.notion.com/mcp",
            },
        }
    },
    "settings_json": {
        "model": "claude-sonnet-4-5",
        "permissions": {
            "allow": ["Bash(pytest *)", "Read(./src/**)"],
            "deny": ["Bash(rm -rf *)"],
            "defaultMode": "acceptEdits",
        },
    },
}


SAMPLE_SOUL_MD = """# ResearchBot

## Identity
- **Name:** ResearchBot
- **Role:** Research Analyst
- **Model:** claude-sonnet-4-5
- **Tone:** Analytical

## Personality
You are a thorough research analyst who excels at finding
authoritative sources and producing structured briefs.

## Skills
- Web Search
- Data Analysis

## Rules
Always cite sources
Never fabricate statistics
Flag outdated information
"""


class TestClaudeCodeToFylle:
    def test_basic_conversion(self):
        """Claude Code workspace -> FylleAgent preserves name and content."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        assert agent.manifest.agent.name == "My Project Agent"
        assert "Hexagonal architecture" in agent.personality

    def test_model_from_settings(self):
        """Model extracted from settings.json."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        assert agent.manifest.agent.model.preferred == "claude-sonnet-4-5"

    def test_mcp_servers_as_tools(self):
        """MCP servers -> tool declarations."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        tool_names = [t.name for t in agent.manifest.agent.tools.required]
        assert "github" in tool_names
        assert "notion" in tool_names

    def test_permissions_mapped(self):
        """acceptEdits -> full autonomy."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        assert agent.manifest.agent.guardrails.max_autonomy.value == "full"

    def test_extensions_preserve_config(self):
        """MCP config and permissions preserved in extensions."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        ext = agent.manifest.agent.extensions.get("claude_code", {})
        assert "mcp_config" in ext
        assert ext["allowed_tools"] == ["Bash(pytest *)", "Read(./src/**)"]
        assert ext["denied_tools"] == ["Bash(rm -rf *)"]


class TestFylleToClaudeCode:
    def test_basic_conversion(self):
        """FylleAgent -> Claude Code workspace files."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        result = fylle_to_claude_code(agent)

        assert "claude_md" in result
        assert "mcp_json" in result
        assert "settings_json" in result
        assert "rules" in result

    def test_claude_md_has_content(self):
        """CLAUDE.md contains agent personality."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        result = fylle_to_claude_code(agent)
        assert "Hexagonal architecture" in result["claude_md"]
        assert "# My Project Agent" in result["claude_md"]

    def test_settings_has_model(self):
        """Settings JSON has correct model."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        result = fylle_to_claude_code(agent)
        assert result["settings_json"]["model"] == "claude-sonnet-4-5"

    def test_mcp_restored(self):
        """MCP config restored from extensions."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        result = fylle_to_claude_code(agent)
        assert "mcpServers" in result["mcp_json"]
        assert "github" in result["mcp_json"]["mcpServers"]

    def test_roundtrip_preserves_core(self):
        """Claude Code -> .fylle -> Claude Code preserves content."""
        agent = claude_code_to_fylle(SAMPLE_CLAUDE_WORKSPACE)
        result = fylle_to_claude_code(agent)
        assert "Hexagonal architecture" in result["claude_md"]
        assert result["settings_json"]["model"] == "claude-sonnet-4-5"


class TestOpenClawToClaudeCodeMigration:
    """THE migration test: OpenClaw SOUL.md -> .fylle -> Claude Code."""

    def test_full_migration(self):
        """OpenClaw SOUL.md -> .fylle -> Claude Code workspace."""
        # Step 1: OpenClaw -> .fylle
        fylle_agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        assert fylle_agent.manifest.agent.name == "ResearchBot"

        # Step 2: .fylle -> Claude Code
        cc_workspace = fylle_to_claude_code(fylle_agent)

        # Verify CLAUDE.md
        assert "# ResearchBot" in cc_workspace["claude_md"]
        assert "thorough research analyst" in cc_workspace["claude_md"]

        # Verify settings
        assert cc_workspace["settings_json"]["model"] == "claude-sonnet-4-5"

        # Verify rules migrated
        assert len(cc_workspace["rules"]) > 0
        rules_content = cc_workspace["rules"][0]["content"]
        assert "Always cite sources" in rules_content
        assert "Never fabricate statistics" in rules_content

    def test_migration_preserves_personality(self):
        """System prompt survives OpenClaw -> .fylle -> Claude Code."""
        fylle_agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        cc_workspace = fylle_to_claude_code(fylle_agent)
        assert "thorough research analyst" in cc_workspace["claude_md"]

    def test_migration_preserves_rules(self):
        """Rules survive OpenClaw -> .fylle -> Claude Code as .claude/rules/."""
        fylle_agent = openclaw_to_fylle(SAMPLE_SOUL_MD)
        cc_workspace = fylle_to_claude_code(fylle_agent)

        rules_file = cc_workspace["rules"][0]
        assert rules_file["filename"] == "agent-rules.md"
        assert "cite sources" in rules_file["content"]
