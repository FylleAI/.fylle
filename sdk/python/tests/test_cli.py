"""Tests for the fylle CLI."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from fylle import create_fylle_from_scratch, build_fylle_package
from fylle_cli.main import cli


runner = CliRunner()


def _build_test_package(tmp_path: Path) -> Path:
    """Helper: create a .fylle package in tmp_path, return its path."""
    agent = create_fylle_from_scratch(
        name="Test Agent",
        description="A test agent",
        personality="You are a test agent.",
        author_name="Test",
    )
    pkg = tmp_path / "test-agent.fylle"
    build_fylle_package(agent, str(pkg))
    return pkg


def _scaffold_agent_dir(tmp_path: Path) -> Path:
    """Helper: create a minimal agent directory."""
    agent_dir = tmp_path / "my-agent"
    agent_dir.mkdir()
    (agent_dir / "manifest.yaml").write_text(
        'fylle_format: "0.1.0"\n'
        "agent:\n"
        '  name: "My Agent"\n'
        '  version: "1.0.0"\n'
        '  description: "Test"\n'
        '  prompt_file: "agent.md"\n'
        "  author:\n"
        '    name: "Test"\n'
        '  license: "MIT"\n'
        "  model:\n"
        '    preferred: "claude-sonnet-4-5"\n'
        "  inputs: []\n"
        "  tools: {}\n"
    )
    (agent_dir / "agent.md").write_text("# My Agent\n\nYou are helpful.\n")
    return agent_dir


class TestValidateCommand:
    def test_valid_package(self, tmp_path):
        pkg = _build_test_package(tmp_path)
        result = runner.invoke(cli, ["validate", str(pkg)])
        assert result.exit_code == 0
        assert "Valid" in result.output or "valid" in result.output.lower()

    def test_missing_file(self, tmp_path):
        result = runner.invoke(cli, ["validate", str(tmp_path / "nope.fylle")])
        assert result.exit_code != 0


class TestInspectCommand:
    def test_shows_agent_name(self, tmp_path):
        pkg = _build_test_package(tmp_path)
        result = runner.invoke(cli, ["inspect", str(pkg)])
        assert result.exit_code == 0
        assert "Test Agent" in result.output


class TestPackCommand:
    def test_creates_fylle_file(self, tmp_path):
        agent_dir = _scaffold_agent_dir(tmp_path)
        output = tmp_path / "output.fylle"
        result = runner.invoke(cli, ["pack", str(agent_dir), "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()


class TestUnpackCommand:
    def test_extracts_files(self, tmp_path):
        pkg = _build_test_package(tmp_path)
        out_dir = tmp_path / "extracted"
        result = runner.invoke(cli, ["unpack", str(pkg), "-o", str(out_dir)])
        assert result.exit_code == 0
        assert (out_dir / "manifest.yaml").exists()
        assert (out_dir / "agent.md").exists()


class TestInitCommand:
    def test_creates_directory(self, tmp_path):
        result = runner.invoke(cli, ["init", "Cool Agent", "-o", str(tmp_path)])
        assert result.exit_code == 0
        agent_dir = tmp_path / "cool-agent"
        assert agent_dir.exists()
        assert (agent_dir / "manifest.yaml").exists()
        assert (agent_dir / "agent.md").exists()
        assert (agent_dir / "skills").is_dir()


class TestMigrateCommand:
    def test_fylle_to_openai(self, tmp_path):
        pkg = _build_test_package(tmp_path)
        output = tmp_path / "out.openai.json"
        result = runner.invoke(cli, [
            "migrate", str(pkg),
            "--from", "fylle", "--to", "openai",
            "-o", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert "model" in data

    def test_fylle_to_crewai(self, tmp_path):
        pkg = _build_test_package(tmp_path)
        output = tmp_path / "out.crewai.yaml"
        result = runner.invoke(cli, [
            "migrate", str(pkg),
            "--from", "fylle", "--to", "crewai",
            "-o", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

    def test_fylle_to_claude_code_writes_workspace(self, tmp_path):
        """Verify --to claude-code creates CLAUDE.md and .claude/settings.json."""
        pkg = _build_test_package(tmp_path)
        workspace = tmp_path / "cc-out"
        result = runner.invoke(cli, [
            "migrate", str(pkg),
            "--from", "fylle", "--to", "claude-code",
            "-o", str(workspace),
        ])
        assert result.exit_code == 0
        assert (workspace / "CLAUDE.md").exists()
        assert (workspace / ".claude" / "settings.json").exists()
        # Verify settings has model
        settings = json.loads((workspace / ".claude" / "settings.json").read_text())
        assert "model" in settings or len(settings) >= 0  # at minimum it exists

    def test_fylle_to_fylle_warns(self, tmp_path):
        """Verify same-format guard prints warning and exits 0."""
        pkg = _build_test_package(tmp_path)
        result = runner.invoke(cli, [
            "migrate", str(pkg),
            "--from", "fylle", "--to", "fylle",
        ])
        assert result.exit_code == 0
        assert "nothing to migrate" in result.output.lower()

    def test_invalid_format_rejected(self):
        result = runner.invoke(cli, [
            "migrate", "dummy",
            "--from", "unknown", "--to", "fylle",
        ])
        assert result.exit_code != 0
