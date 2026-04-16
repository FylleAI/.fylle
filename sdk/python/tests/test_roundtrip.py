"""
Tests for .fylle format: parse, validate, build, roundtrip.
"""

import tempfile
from pathlib import Path

import pytest

from fylle import (
    build_fylle_package,
    create_fylle_from_scratch,
    parse_fylle_package,
    validate,
)
from fylle.parser import FylleParseError, FylleSecurityError


class TestCreateAndParse:
    """Test creating a .fylle package and parsing it back."""

    def test_minimal_roundtrip(self, tmp_path):
        """Create a minimal agent, build it, parse it back."""
        agent = create_fylle_from_scratch(
            name="Test Agent",
            description="A test agent for roundtrip validation",
            personality="You are a test agent. Be helpful.",
            version="1.0.0",
            author_name="Test Author",
            license="MIT",
        )

        # Build
        output_file = tmp_path / "test-agent.fylle"
        result_path = build_fylle_package(agent, output_file)
        assert Path(result_path).exists()

        # Parse back
        parsed = parse_fylle_package(result_path)
        assert parsed.manifest.agent.name == "Test Agent"
        assert parsed.manifest.agent.version == "1.0.0"
        assert parsed.manifest.agent.description == "A test agent for roundtrip validation"
        assert parsed.manifest.agent.author.name == "Test Author"
        assert parsed.manifest.agent.license == "MIT"
        assert "test agent" in parsed.personality.lower()
        assert parsed.package_hash is not None

    def test_full_roundtrip_with_skills(self, tmp_path):
        """Create an agent with skills and validate roundtrip."""
        agent = create_fylle_from_scratch(
            name="Full Agent",
            description="Agent with all optional fields",
            personality="# Full Agent\n\nYou are a comprehensive test agent.",
            version="2.1.0",
            author_name="Fylle",
            author_url="https://www.fylle.ai",
            license="Apache-2.0",
            model_preferred="claude-sonnet-4-5",
            role="Test Specialist",
            tone="professional",
            language=["en", "it"],
            inputs=[
                {"name": "topic", "type": "text", "required": True, "description": "Topic to work on"},
                {"name": "context", "type": "text", "required": False, "description": "Optional context"},
            ],
            skills=[
                {
                    "name": "Research",
                    "version": "1.0.0",
                    "description": "Web research skill",
                    "triggers": ["research this", "find info"],
                    "instructions": "Search the web and synthesize findings.",
                    "tools_used": ["web_search"],
                    "output_format": "markdown",
                },
            ],
            tags=["test", "demo"],
            category="testing",
        )

        output_file = tmp_path / "full-agent.fylle"
        build_fylle_package(agent, output_file)
        parsed = parse_fylle_package(output_file)

        assert parsed.manifest.agent.name == "Full Agent"
        assert parsed.manifest.agent.role == "Test Specialist"
        assert len(parsed.manifest.agent.inputs) == 2
        assert parsed.manifest.agent.inputs[0].name == "topic"
        assert len(parsed.skills) == 1
        assert parsed.skills[0].name == "Research"


class TestValidation:
    """Test the validator."""

    def test_valid_agent(self):
        """A well-formed agent should validate cleanly."""
        agent = create_fylle_from_scratch(
            name="Valid Agent",
            description="A properly configured agent for validation testing",
            personality="You are a helpful assistant.\n\nFollow instructions carefully.",
            inputs=[{"name": "query", "type": "text", "required": True, "description": "User query"}],
        )
        result = validate(agent)
        assert result.valid
        assert len(result.errors) == 0

    def test_short_prompt_warning(self):
        """Very short prompts should produce a warning."""
        agent = create_fylle_from_scratch(
            name="Short Prompt",
            description="Agent with a too-short prompt",
            personality="Be helpful.",
        )
        result = validate(agent)
        assert result.valid  # Still valid, just warned
        assert any("short" in w.lower() for w in result.warnings)

    def test_no_inputs_warning(self):
        """Agent without inputs should produce a warning."""
        agent = create_fylle_from_scratch(
            name="No Inputs",
            description="Agent without declared inputs for testing",
            personality="You are a helpful assistant with no declared inputs.",
        )
        result = validate(agent)
        assert result.valid
        assert any("input" in w.lower() for w in result.warnings)


class TestSecurity:
    """Test security validations."""

    def test_oversized_package(self, tmp_path):
        """Packages over 10MB should be rejected."""
        # Create a file larger than 10MB
        large_file = tmp_path / "large.fylle"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))

        with pytest.raises(FylleSecurityError, match="too large"):
            parse_fylle_package(large_file)

    def test_invalid_zip(self, tmp_path):
        """Non-ZIP files should be rejected."""
        bad_file = tmp_path / "not-a-zip.fylle"
        bad_file.write_text("this is not a zip file")

        with pytest.raises(FylleParseError, match="ZIP"):
            parse_fylle_package(bad_file)

    def test_missing_manifest(self, tmp_path):
        """Packages without manifest.yaml should be rejected."""
        import zipfile

        bad_fylle = tmp_path / "no-manifest.fylle"
        with zipfile.ZipFile(bad_fylle, "w") as zf:
            zf.writestr("agent.md", "Some prompt")

        with pytest.raises(FylleParseError, match="manifest.yaml"):
            parse_fylle_package(bad_fylle)


class TestParseExamples:
    """Test parsing the example agents from the repo."""

    def _build_example(self, example_dir: Path, tmp_path: Path) -> Path:
        """Build a .fylle from an example directory."""
        import zipfile

        fylle_path = tmp_path / f"{example_dir.name}.fylle"
        with zipfile.ZipFile(fylle_path, "w") as zf:
            for file in example_dir.rglob("*"):
                if file.is_file():
                    arcname = str(file.relative_to(example_dir))
                    zf.write(file, arcname)
        return fylle_path

    def test_parse_content_curator(self, tmp_path):
        """Parse the content-curator example."""
        example_dir = Path(__file__).parent.parent.parent.parent / "examples" / "content-curator"
        if not example_dir.exists():
            pytest.skip("Example not found")

        fylle_path = self._build_example(example_dir, tmp_path)
        agent = parse_fylle_package(fylle_path)

        assert agent.manifest.agent.name == "Content Curator"
        assert agent.manifest.agent.version == "1.0.0"
        assert len(agent.skills) == 1
        assert agent.skills[0].name == "Web Research"
        assert "content curation" in agent.personality.lower()

        result = validate(agent)
        assert result.valid

    def test_parse_compliance_checker(self, tmp_path):
        """Parse the compliance-checker example."""
        example_dir = Path(__file__).parent.parent.parent.parent / "examples" / "compliance-checker"
        if not example_dir.exists():
            pytest.skip("Example not found")

        fylle_path = self._build_example(example_dir, tmp_path)
        agent = parse_fylle_package(fylle_path)

        assert agent.manifest.agent.name == "Compliance Checker"
        assert agent.guardrails is not None
        assert len(agent.guardrails.rules) > 0

        result = validate(agent)
        assert result.valid
