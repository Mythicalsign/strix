"""
Custom Agents Module - Advanced sub-agent creation with root terminal access.

This module provides:
- Custom sub-agent creation with configurable capabilities
- Root terminal access for sub-agents
- Advanced agent configuration options
- Agent capability management
"""

from .custom_agent_actions import (
    create_custom_agent,
    create_root_enabled_agent,
    get_agent_capabilities,
    update_agent_capabilities,
    list_custom_agents,
    terminate_custom_agent,
    grant_root_access,
    revoke_root_access,
)

__all__ = [
    "create_custom_agent",
    "create_root_enabled_agent",
    "get_agent_capabilities",
    "update_agent_capabilities",
    "list_custom_agents",
    "terminate_custom_agent",
    "grant_root_access",
    "revoke_root_access",
]
