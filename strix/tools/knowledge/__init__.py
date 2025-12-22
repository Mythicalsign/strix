"""
Knowledge Management System - Advanced knowledge and notes management.

This module provides a significantly enhanced knowledge management system with:
- Hierarchical knowledge organization
- Note linking and relationships
- Priority and importance levels
- Full-text search with relevance ranking
- Knowledge export/import
- Templates and schemas
- Version history
- Cross-agent knowledge sharing
"""

from .knowledge_actions import (
    # Core knowledge operations
    create_knowledge_entry,
    get_knowledge_entry,
    update_knowledge_entry,
    delete_knowledge_entry,
    
    # Advanced search
    search_knowledge,
    advanced_search,
    
    # Relationships and linking
    link_entries,
    unlink_entries,
    get_related_entries,
    
    # Organization
    create_knowledge_collection,
    add_to_collection,
    remove_from_collection,
    list_collections,
    
    # Export/Import
    export_knowledge,
    import_knowledge,
    
    # Templates
    create_from_template,
    list_templates,
    
    # Versioning
    get_entry_history,
    revert_entry,
    
    # Sharing
    share_with_agent,
    get_shared_knowledge,
    
    # Analytics
    get_knowledge_stats,
    get_knowledge_graph,
)

__all__ = [
    "create_knowledge_entry",
    "get_knowledge_entry",
    "update_knowledge_entry",
    "delete_knowledge_entry",
    "search_knowledge",
    "advanced_search",
    "link_entries",
    "unlink_entries",
    "get_related_entries",
    "create_knowledge_collection",
    "add_to_collection",
    "remove_from_collection",
    "list_collections",
    "export_knowledge",
    "import_knowledge",
    "create_from_template",
    "list_templates",
    "get_entry_history",
    "revert_entry",
    "share_with_agent",
    "get_shared_knowledge",
    "get_knowledge_stats",
    "get_knowledge_graph",
]
