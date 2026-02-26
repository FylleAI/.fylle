"""Framework adapters for translating between .fylle and other agent formats."""

from fylle_bridge.adapters.crewai_adapter import crewai_to_fylle, fylle_to_crewai
from fylle_bridge.adapters.openai_adapter import openai_to_fylle, fylle_to_openai
from fylle_bridge.adapters.openclaw_adapter import openclaw_to_fylle, fylle_to_openclaw
from fylle_bridge.adapters.claude_code_adapter import claude_code_to_fylle, fylle_to_claude_code

__all__ = [
    "crewai_to_fylle",
    "fylle_to_crewai",
    "openai_to_fylle",
    "fylle_to_openai",
    "openclaw_to_fylle",
    "fylle_to_openclaw",
    "claude_code_to_fylle",
    "fylle_to_claude_code",
]
