"""mcp_orchestrator package init

Expose orchestrator helpers for easy imports.
"""

from .orchestrator import choose_and_call, choose_and_call as choose_and_call_sync  # re-export

__all__ = ["choose_and_call", "choose_and_call_sync"]
