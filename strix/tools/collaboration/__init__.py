"""
Multi-Agent Collaboration Protocol Module.

This module provides tools for efficient collaboration between multiple AI agents,
preventing duplicate work and enabling vulnerability chaining.

Features:
- Target claiming system to prevent duplicate testing
- Finding sharing for vulnerability chaining
- Central work queue for coordinated testing
- Help request system for specialized assistance
- Real-time collaboration status dashboard
"""

from .collaboration_actions import (
    add_to_work_queue,
    broadcast_message,
    claim_target,
    get_collaboration_status,
    get_finding_details,
    get_next_work_item,
    list_claims,
    list_findings,
    release_claim,
    request_help,
    share_finding,
)


__all__ = [
    "claim_target",
    "release_claim",
    "list_claims",
    "share_finding",
    "list_findings",
    "get_finding_details",
    "add_to_work_queue",
    "get_next_work_item",
    "request_help",
    "get_collaboration_status",
    "broadcast_message",
]
