"""Abstract base class for framework adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from fylle.schema import FylleAgent


class FrameworkAdapter(ABC):
    """Base class for all framework adapters.

    Each adapter translates between a specific framework's agent format
    and the universal .fylle FylleAgent representation.
    """

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Human-readable framework name (e.g. 'CrewAI')."""
        ...

    @abstractmethod
    def to_fylle(self, source: dict) -> FylleAgent:
        """Convert framework-native config to a FylleAgent.

        Args:
            source: Framework-specific configuration as a dict
                    (parsed from YAML/JSON).

        Returns:
            A validated FylleAgent object.
        """
        ...

    @abstractmethod
    def from_fylle(self, agent: FylleAgent) -> dict:
        """Convert a FylleAgent to framework-native config.

        Args:
            agent: A parsed FylleAgent.

        Returns:
            A dict representing the framework-native configuration.
        """
        ...
