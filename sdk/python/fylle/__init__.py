"""
fylle: Move AI agents between frameworks without rewriting them.

Parse, validate, bridge, and run .fylle agent packages.
"""

from fylle.schema import (
    # .fylle (single agent)
    FylleAgent,
    FylleManifest,
    AgentIdentity,
    AgentAuthor,
    ModelRequirements,
    ModelSettings,
    AgentInput,
    AgentOutput,
    ToolDeclaration,
    ToolsConfig,
    SkillRef,
    GuardrailsRef,
    MemoryRef,
    Skill,
    Guardrails,
    GuardrailRule,
    ContentPolicies,
    GuardrailLimits,
    MemorySchema,
    MemoryEntity,
    ModelCapability,
    MemoryEntityType,
    RetentionPolicy,
    MaxAutonomy,
    GuardrailSeverity,
    # .fyllepack (multi-agent workflow)
    FyllePack,
    FyllePackManifest,
    PackIdentity,
    PipelineStep,
    ExecutionConfig,
    ExecutionMode,
    ErrorHandling,
    BriefSchema,
    BriefQuestion,
)
from fylle.parser import parse_fylle_package, unpack_fylle_to_dir
from fylle.validator import validate, ValidationResult
from fylle.builder import build_fylle_package, create_fylle_from_scratch

__version__ = "0.1.0"

__all__ = [
    # .fylle (single agent)
    "FylleAgent",
    "FylleManifest",
    "AgentIdentity",
    # .fyllepack (multi-agent workflow)
    "FyllePack",
    "FyllePackManifest",
    "PackIdentity",
    "PipelineStep",
    "ExecutionConfig",
    "BriefSchema",
    # Parse
    "parse_fylle_package",
    "unpack_fylle_to_dir",
    # Validate
    "validate",
    "ValidationResult",
    # Build
    "build_fylle_package",
    "create_fylle_from_scratch",
]
