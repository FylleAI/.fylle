"""
fylle-bridge: Universal agent translation layer for the .fylle protocol.

Import agents from CrewAI, OpenAI Assistants, and more.
Export to any supported framework. Execute live via LLM APIs.
"""

from fylle_bridge.adapters.crewai_adapter import (
    crewai_to_fylle,
    fylle_to_crewai,
    crewai_to_fylle_yaml,
    CrewAIAdapter,
)
from fylle_bridge.adapters.openai_adapter import (
    openai_to_fylle,
    fylle_to_openai,
    fylle_to_openai_json,
    OpenAIAdapter,
)
from fylle_bridge.runner.simple_runner import run_fylle_agent

__version__ = "0.1.0"

__all__ = [
    # CrewAI
    "crewai_to_fylle",
    "fylle_to_crewai",
    "crewai_to_fylle_yaml",
    "CrewAIAdapter",
    # OpenAI
    "openai_to_fylle",
    "fylle_to_openai",
    "fylle_to_openai_json",
    "OpenAIAdapter",
    # Runner
    "run_fylle_agent",
]
