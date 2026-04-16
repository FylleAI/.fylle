"""
Pydantic v2 models for .fylle format validation.

These models represent the complete .fylle specification v0.1.0.
Every field has explicit types, descriptions, and validation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Enums
# ============================================================

class ModelCapability(str, Enum):
    """Capabilities that an agent's model must support."""
    TOOL_USE = "tool-use"
    LONG_CONTEXT = "long-context"
    VISION = "vision"
    CODE_EXECUTION = "code-execution"


class MemoryEntityType(str, Enum):
    """Types of memory entities an agent can declare."""
    DOCUMENT = "document"       # Static reference material
    FEED = "feed"               # Streaming/updating data
    LOG = "log"                 # Append-only history
    PROFILE = "profile"         # Evolving user/context data
    INDEX = "index"             # Searchable knowledge base


class RetentionPolicy(str, Enum):
    """How long a memory entity should be retained."""
    PERMANENT = "permanent"
    ROLLING_30_DAYS = "rolling_30_days"
    ROLLING_90_DAYS = "rolling_90_days"
    ROLLING_1_YEAR = "rolling_1_year"
    SESSION = "session"


class MaxAutonomy(str, Enum):
    """Level of autonomy the agent is allowed."""
    FULL = "full"                       # Execute without approval
    DRAFT_ONLY = "draft-only"           # Create drafts, human publishes
    HUMAN_APPROVAL = "human-approval"   # Propose, human approves each step


class GuardrailSeverity(str, Enum):
    """Severity level for guardrail rules."""
    BLOCK = "block"     # Hard stop — prevent the action
    WARN = "warn"       # Flag for review
    LOG = "log"         # Track silently


class InputType(str, Enum):
    """Types of inputs an agent can receive."""
    TEXT = "text"
    JSON = "json"
    FILE = "file"
    IMAGE = "image"


class OutputFormat(str, Enum):
    """Formats an agent can produce."""
    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"
    HTML = "html"
    STRUCTURED_REPORT = "structured_report"
    FREE = "free"


class ToolProtocol(str, Enum):
    """Protocol used to access a tool."""
    MCP = "mcp"
    FUNCTION = "function"
    API = "api"


# ============================================================
# Semver validation
# ============================================================

SEMVER_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _validate_semver(value: str) -> str:
    if not SEMVER_REGEX.match(value):
        raise ValueError(f"Invalid semver: '{value}'. Expected format: MAJOR.MINOR.PATCH")
    return value


# ============================================================
# Manifest sub-models
# ============================================================

class AgentAuthor(BaseModel):
    """Agent author information."""
    name: str = Field(..., description="Author or organization name")
    url: str | None = Field(None, description="Website URL")
    email: str | None = Field(None, description="Contact email")


class ModelSettings(BaseModel):
    """Default model configuration settings."""
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4000, gt=0, description="Max tokens per response")


class ModelRequirements(BaseModel):
    """Model requirements for the agent."""
    preferred: str = Field(..., description="Preferred model ID (e.g. 'claude-sonnet-4-5')")
    minimum_capability: list[ModelCapability] = Field(
        default_factory=list,
        description="Required model capabilities"
    )
    settings: ModelSettings = Field(
        default_factory=ModelSettings,
        description="Default model settings"
    )


class AgentInput(BaseModel):
    """Declaration of an input the agent expects from the runtime."""
    name: str = Field(..., description="Input identifier (snake_case)")
    type: InputType = Field(InputType.TEXT, description="Input data type")
    required: bool = Field(True, description="Whether the agent needs this to function")
    description: str = Field("", description="Human-readable description")


class AgentOutput(BaseModel):
    """Declaration of the agent's output format."""
    format: OutputFormat = Field(OutputFormat.MARKDOWN, description="Output format")


class ToolDeclaration(BaseModel):
    """Declaration of an external tool the agent needs."""
    name: str = Field(..., description="Tool identifier (e.g. 'web_search')")
    protocol: ToolProtocol = Field(ToolProtocol.MCP, description="Access protocol")
    description: str = Field("", description="Why this tool is needed")
    server: str | None = Field(None, description="Specific server identifier")


class ToolsConfig(BaseModel):
    """Tools configuration — required and optional tools."""
    required: list[ToolDeclaration] = Field(default_factory=list)
    optional: list[ToolDeclaration] = Field(default_factory=list)


class SkillRef(BaseModel):
    """Reference to a skill file."""
    ref: str = Field(..., description="Relative path to skill YAML file")


class GuardrailLimits(BaseModel):
    """Operational limits (can be inline in manifest or in guardrails.yaml)."""
    max_iterations: int = Field(50, gt=0, description="Max tool/action iterations per run")
    max_tokens_per_response: int = Field(4000, gt=0, description="Max tokens per response")


class GuardrailsRef(BaseModel):
    """Reference to guardrails configuration."""
    file: str | None = Field(None, description="Path to guardrails.yaml")
    max_autonomy: MaxAutonomy = Field(
        MaxAutonomy.DRAFT_ONLY,
        description="Agent autonomy level"
    )
    limits: GuardrailLimits = Field(
        default_factory=GuardrailLimits,
        description="Operational limits"
    )


class MemoryRef(BaseModel):
    """Reference to memory schema."""
    schema_file: str = Field("memory-schema.yaml", description="Path to memory schema")
    persistence: str = Field("host-managed", description="Always 'host-managed'")


# ============================================================
# Fylle extensions
# ============================================================

class FylleFeedbackLoop(BaseModel):
    """Fylle-specific feedback loop configuration."""
    enabled: bool = Field(True, description="Whether feedback tracking is active")
    metrics: list[str] = Field(default_factory=list, description="Metrics to track")


class FylleContextSource(BaseModel):
    """Fylle-specific context source declaration."""
    type: str = Field(..., description="Context type: 'brand', 'audience', 'compliance'")


class FylleExtensions(BaseModel):
    """Fylle platform-specific extensions."""
    original_agent_name: str | None = Field(None, description="Agent name in Fylle pack")
    original_pack_id: str | None = Field(None, description="Pack ID in Fylle platform")
    feedback_loop: FylleFeedbackLoop = Field(default_factory=FylleFeedbackLoop)
    context_sources: list[FylleContextSource] = Field(default_factory=list)


# ============================================================
# Main manifest model
# ============================================================

class AgentIdentity(BaseModel):
    """Complete agent definition from manifest.yaml."""

    # Identity (required)
    name: str = Field(..., max_length=100, description="Agent display name")
    version: str = Field(..., description="Agent version (semver)")
    description: str = Field(..., max_length=500, description="One-line description")
    role: str | None = Field(None, description="Agent role/persona")

    # Authorship (required)
    author: AgentAuthor = Field(..., description="Author information")
    license: str = Field(..., description="SPDX license identifier")

    # Model (required)
    model: ModelRequirements = Field(..., description="Model requirements")

    # System prompt (required)
    prompt_file: str = Field("agent.md", description="Path to system prompt file")
    tone: str | None = Field(None, description="Comma-separated tone descriptors")
    language: list[str] = Field(default_factory=lambda: ["en"], description="Supported languages (ISO 639-1)")

    # Inputs (optional but recommended)
    inputs: list[AgentInput] = Field(default_factory=list, description="Expected inputs from runtime")

    # Output (optional)
    output: AgentOutput = Field(default_factory=AgentOutput, description="Output format")

    # Tools (optional)
    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="Tool declarations")

    # Skills (optional)
    skills: list[SkillRef] = Field(default_factory=list, description="Skill file references")

    # Guardrails (optional)
    guardrails: GuardrailsRef = Field(default_factory=GuardrailsRef, description="Guardrails configuration")

    # Memory (optional)
    memory: MemoryRef | None = Field(None, description="Memory schema reference")

    # Metadata (optional)
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    category: str | None = Field(None, description="Primary category")
    homepage: str | None = Field(None, description="Project page URL")
    repository: str | None = Field(None, description="Source code URL")

    # Runtime extensions (optional)
    extensions: dict[str, Any] = Field(default_factory=dict, description="Runtime-specific extensions")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        return _validate_semver(v)


class FylleManifest(BaseModel):
    """Root model for manifest.yaml."""
    fylle_format: str = Field(..., description="Format specification version (semver)")
    agent: AgentIdentity = Field(..., description="Agent definition")

    @field_validator("fylle_format")
    @classmethod
    def validate_format_version(cls, v: str) -> str:
        return _validate_semver(v)


# ============================================================
# Skill model (for skills/*.yaml)
# ============================================================

class Skill(BaseModel):
    """A modular skill definition."""
    name: str = Field(..., description="Skill display name")
    version: str = Field(..., description="Skill version (semver)")
    description: str = Field(..., description="What this skill does")
    triggers: list[str] = Field(default_factory=list, description="Natural language triggers")
    instructions: str = Field(..., description="Detailed instructions for the LLM")
    tools_used: list[str] = Field(default_factory=list, description="Tools this skill needs")
    output_format: OutputFormat = Field(OutputFormat.MARKDOWN, description="Expected output")
    input_schema: dict[str, Any] | None = Field(None, description="JSON Schema for structured input")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        return _validate_semver(v)


# ============================================================
# Guardrails model (for guardrails.yaml)
# ============================================================

class GuardrailRule(BaseModel):
    """A single guardrail rule."""
    id: str = Field(..., description="Rule identifier (kebab-case)")
    description: str = Field(..., description="What this rule enforces")
    severity: GuardrailSeverity = Field(..., description="Severity level")
    condition: str = Field(..., description="Natural language condition")


class ContentPolicies(BaseModel):
    """Content policy constraints."""
    prohibited_topics: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    tone_boundaries: str | None = Field(None)


class Guardrails(BaseModel):
    """Complete guardrails definition from guardrails.yaml."""
    rules: list[GuardrailRule] = Field(default_factory=list)
    content_policies: ContentPolicies = Field(default_factory=ContentPolicies)
    limits: GuardrailLimits = Field(default_factory=GuardrailLimits)


# ============================================================
# Memory schema model (for memory-schema.yaml)
# ============================================================

class MemoryEntity(BaseModel):
    """A single memory entity declaration."""
    name: str = Field(..., description="Entity identifier (snake_case)")
    type: MemoryEntityType = Field(..., description="Entity type")
    description: str = Field("", description="Human-readable description")
    retention: RetentionPolicy = Field(RetentionPolicy.PERMANENT, description="Retention policy")


class MemorySchema(BaseModel):
    """Complete memory schema from memory-schema.yaml."""
    entities: list[MemoryEntity] = Field(default_factory=list)


# ============================================================
# Top-level parsed agent
# ============================================================

class FylleAgent(BaseModel):
    """A fully parsed .fylle agent package.

    This is the main object returned by parse_fylle_package().
    It contains the manifest, system prompt, and all optional components.
    """
    manifest: FylleManifest = Field(..., description="Parsed manifest.yaml")
    personality: str = Field(..., description="Contents of agent.md (system prompt)")
    skills: list[Skill] = Field(default_factory=list, description="Parsed skill definitions")
    guardrails: Guardrails | None = Field(None, description="Parsed guardrails.yaml")
    memory_schema: MemorySchema | None = Field(None, description="Parsed memory-schema.yaml")
    readme: str | None = Field(None, description="Contents of README.md")
    package_hash: str | None = Field(None, description="SHA-256 hash of the .fylle file")


# ============================================================
# .fyllepack — Multi-agent workflow models
# ============================================================

class ExecutionMode(str, Enum):
    """How agents in a pipeline are executed."""
    SEQUENTIAL = "sequential"     # One after another (default)
    PARALLEL = "parallel"         # Independent agents run simultaneously
    CONDITIONAL = "conditional"   # Agents run based on conditions


class ErrorHandling(str, Enum):
    """How pipeline errors are handled."""
    STOP = "stop"       # Stop the entire pipeline on error
    SKIP = "skip"       # Skip the failing agent, continue pipeline
    RETRY = "retry"     # Retry the failing agent


class PipelineStep(BaseModel):
    """A single step in a .fyllepack pipeline."""
    name: str = Field(..., description="Step identifier (unique within pack)")
    agent: str = Field(..., description="Relative path to .fylle package")
    receives_from: list[str] = Field(
        default_factory=list,
        description="Step names this agent receives output from"
    )
    input_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Maps agent inputs to data sources (dot notation)"
    )


class ExecutionConfig(BaseModel):
    """Pipeline execution configuration."""
    mode: ExecutionMode = Field(ExecutionMode.SEQUENTIAL, description="Execution mode")
    final_output: str = Field(..., description="Which step's output is the workflow result")
    error_handling: ErrorHandling = Field(ErrorHandling.STOP, description="Error handling strategy")


class BriefSchemaRef(BaseModel):
    """Reference to brief schema file."""
    file: str = Field("brief_schema.yaml", description="Path to brief schema YAML")


class BriefQuestion(BaseModel):
    """A single brief question the user answers before workflow execution."""
    id: str = Field(..., description="Question identifier (snake_case)")
    question: str = Field(..., description="Question text shown to the user")
    type: str = Field("text", description="Input type: text, select, multiselect, number")
    required: bool = Field(True, description="Whether an answer is required")
    options: list[str] = Field(default_factory=list, description="Options for select/multiselect")
    default: str | None = Field(None, description="Default value")


class BriefSchema(BaseModel):
    """Complete brief schema from brief_schema.yaml."""
    questions: list[BriefQuestion] = Field(default_factory=list)


class PackIdentity(BaseModel):
    """Complete pack definition from .fyllepack manifest.yaml."""

    # Identity (required)
    name: str = Field(..., max_length=100, description="Workflow name")
    version: str = Field(..., description="Pack version (semver)")
    description: str = Field(..., max_length=500, description="One-line description")

    # Authorship (required)
    author: AgentAuthor = Field(..., description="Author information")
    license: str = Field(..., description="SPDX license identifier")

    # Pipeline (required)
    pipeline: list[PipelineStep] = Field(..., min_length=1, description="Ordered agent pipeline")

    # Execution (optional)
    execution: ExecutionConfig | None = Field(None, description="Execution configuration")

    # Brief schema (optional)
    brief_schema: BriefSchemaRef | None = Field(None, description="Reference to brief schema")

    # Guardrails (optional)
    guardrails: GuardrailsRef = Field(default_factory=GuardrailsRef, description="Workflow-level guardrails")

    # Metadata (optional)
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    category: str | None = Field(None, description="Primary category")

    # Runtime extensions (optional)
    extensions: dict[str, Any] = Field(default_factory=dict, description="Runtime-specific extensions")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        return _validate_semver(v)


class FyllePackManifest(BaseModel):
    """Root model for .fyllepack manifest.yaml."""
    fylle_format: str = Field(..., description="Format specification version (semver)")
    pack: PackIdentity = Field(..., description="Pack definition")

    @field_validator("fylle_format")
    @classmethod
    def validate_format_version(cls, v: str) -> str:
        return _validate_semver(v)


class FyllePack(BaseModel):
    """A fully parsed .fyllepack workflow package.

    Contains the pack manifest, all constituent agents, and optional components.
    """
    manifest: FyllePackManifest = Field(..., description="Parsed manifest.yaml")
    agents: dict[str, FylleAgent] = Field(
        default_factory=dict,
        description="Parsed agents, keyed by pipeline step name"
    )
    brief_schema: BriefSchema | None = Field(None, description="Parsed brief_schema.yaml")
    guardrails: Guardrails | None = Field(None, description="Parsed workflow-level guardrails")
    readme: str | None = Field(None, description="Contents of README.md")
    package_hash: str | None = Field(None, description="SHA-256 hash of the .fyllepack file")
