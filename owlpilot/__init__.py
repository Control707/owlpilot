"""Academic validation/extraction helpers for an It-owned OwlPilot page.

This package never runs an agent, a server, a queue, or an It command.
"""

from .core import OwlPilotError, initial_state, handle_action, complete_guide, guide_context

__all__ = ["OwlPilotError", "initial_state", "handle_action", "complete_guide", "guide_context"]
