"""
StrixDB Module - Permanent GitHub-based Knowledge Repository

This module provides tools for the AI agent to store and retrieve useful artifacts
in a permanent GitHub repository (StrixDB). The agent acts as an enthusiastic collector,
automatically storing scripts, tools, exploits, methods, knowledge, and other useful
items for future reference across all engagements.

Categories supported:
- scripts: Automation scripts and tools
- exploits: Working exploits and PoCs
- knowledge: Security knowledge and notes
- libraries: Reusable code libraries
- sources: Wordlists, data sources, references
- methods: Attack methodologies
- tools: Custom security tools
- configs: Configuration files and templates

Environment Variables:
- STRIXDB_REPO: GitHub repository name (e.g., "username/StrixDB")
- STRIXDB_TOKEN: GitHub personal access token with repo permissions
- STRIXDB_BRANCH: Branch to use (default: "main")
"""

from .strixdb_actions import (
    strixdb_save,
    strixdb_search,
    strixdb_get,
    strixdb_list,
    strixdb_update,
    strixdb_delete,
    strixdb_get_categories,
    strixdb_create_directory,
    strixdb_get_stats,
    strixdb_export,
    strixdb_import_item,
    strixdb_tag_item,
    strixdb_get_recent,
    strixdb_sync,
)

__all__ = [
    "strixdb_save",
    "strixdb_search",
    "strixdb_get",
    "strixdb_list",
    "strixdb_update",
    "strixdb_delete",
    "strixdb_get_categories",
    "strixdb_create_directory",
    "strixdb_get_stats",
    "strixdb_export",
    "strixdb_import_item",
    "strixdb_tag_item",
    "strixdb_get_recent",
    "strixdb_sync",
]
