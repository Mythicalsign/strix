"""
Knowledge Actions - Significantly enhanced knowledge and notes management system.

Features:
- Hierarchical organization with collections
- Note linking and relationships (bidirectional, typed)
- Priority and importance levels (critical, high, medium, low)
- Full-text search with relevance ranking
- Advanced filtering and faceted search
- Knowledge export/import (JSON, Markdown)
- Templates for common entry types
- Version history with rollback
- Cross-agent knowledge sharing
- Analytics and visualization
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from strix.tools.registry import register_tool


# =============================================================================
# Data Structures
# =============================================================================

# Main knowledge storage
_knowledge_entries: dict[str, dict[str, Any]] = {}

# Collections (folders/categories)
_knowledge_collections: dict[str, dict[str, Any]] = {}

# Relationships between entries
_entry_relationships: list[dict[str, Any]] = []

# Version history
_entry_history: dict[str, list[dict[str, Any]]] = {}

# Shared knowledge (agent_id -> list of entry_ids)
_shared_knowledge: dict[str, list[str]] = {}

# Templates
_knowledge_templates: dict[str, dict[str, Any]] = {
    "vulnerability": {
        "name": "Vulnerability Report",
        "schema": {
            "title": "string",
            "severity": "critical|high|medium|low|info",
            "cvss_score": "float",
            "affected_component": "string",
            "description": "string",
            "poc": "string",
            "remediation": "string",
            "references": "list",
        },
        "default_category": "findings",
        "default_priority": "high",
        "default_tags": ["vulnerability", "security"],
    },
    "methodology": {
        "name": "Methodology Note",
        "schema": {
            "title": "string",
            "phase": "reconnaissance|scanning|exploitation|post-exploitation|reporting",
            "technique": "string",
            "tools_used": "list",
            "commands": "string",
            "results": "string",
            "next_steps": "string",
        },
        "default_category": "methodology",
        "default_priority": "medium",
        "default_tags": ["methodology"],
    },
    "credential": {
        "name": "Credential Entry",
        "schema": {
            "title": "string",
            "service": "string",
            "username": "string",
            "password": "string",
            "access_level": "string",
            "valid": "boolean",
            "source": "string",
        },
        "default_category": "findings",
        "default_priority": "critical",
        "default_tags": ["credential", "sensitive"],
    },
    "endpoint": {
        "name": "Endpoint Documentation",
        "schema": {
            "title": "string",
            "url": "string",
            "method": "GET|POST|PUT|DELETE|PATCH",
            "parameters": "dict",
            "headers": "dict",
            "authentication": "string",
            "response_type": "string",
            "notes": "string",
        },
        "default_category": "reconnaissance",
        "default_priority": "medium",
        "default_tags": ["endpoint", "api"],
    },
    "research": {
        "name": "Research Note",
        "schema": {
            "title": "string",
            "topic": "string",
            "summary": "string",
            "key_findings": "list",
            "sources": "list",
            "questions": "list",
            "action_items": "list",
        },
        "default_category": "questions",
        "default_priority": "medium",
        "default_tags": ["research"],
    },
}

# Valid categories
VALID_CATEGORIES = [
    "general",
    "findings",
    "methodology",
    "questions",
    "plan",
    "reconnaissance",
    "exploitation",
    "credentials",
    "research",
]

# Valid priorities
VALID_PRIORITIES = ["critical", "high", "medium", "low"]

# Valid relationship types
VALID_RELATIONSHIP_TYPES = [
    "related_to",
    "depends_on",
    "blocks",
    "references",
    "contradicts",
    "confirms",
    "supersedes",
    "extends",
]


def _generate_id() -> str:
    """Generate a unique entry ID."""
    return f"ke_{uuid.uuid4().hex[:8]}"


def _calculate_relevance(entry: dict[str, Any], query: str) -> float:
    """Calculate relevance score for search ranking."""
    score = 0.0
    query_lower = query.lower()
    words = query_lower.split()
    
    title = entry.get("title", "").lower()
    content = entry.get("content", "").lower()
    tags = [t.lower() for t in entry.get("tags", [])]
    
    # Title exact match (highest weight)
    if query_lower in title:
        score += 10.0
    
    # Title word match
    for word in words:
        if word in title:
            score += 3.0
    
    # Content match
    for word in words:
        count = content.count(word)
        score += min(count * 0.5, 5.0)  # Cap at 5 per word
    
    # Tag match
    for word in words:
        if word in tags:
            score += 2.0
    
    # Priority boost
    priority = entry.get("priority", "medium")
    priority_boost = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}
    score *= priority_boost.get(priority, 1.0)
    
    # Recency boost (entries from last 24 hours get boost)
    try:
        created = datetime.fromisoformat(entry.get("created_at", ""))
        age_hours = (datetime.now(UTC) - created).total_seconds() / 3600
        if age_hours < 24:
            score *= 1.2
    except (ValueError, TypeError):
        pass
    
    return score


def _save_history(entry_id: str, entry: dict[str, Any], action: str) -> None:
    """Save entry version to history."""
    if entry_id not in _entry_history:
        _entry_history[entry_id] = []
    
    _entry_history[entry_id].append({
        "version": len(_entry_history[entry_id]) + 1,
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "snapshot": entry.copy(),
    })


# =============================================================================
# Core Knowledge Operations
# =============================================================================

@register_tool(sandbox_execution=False)
def create_knowledge_entry(
    title: str,
    content: str,
    category: str = "general",
    priority: str = "medium",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new knowledge entry with advanced metadata and organization.
    
    Args:
        title: Title of the knowledge entry
        content: Main content (supports markdown)
        category: Category for organization (general, findings, methodology, etc.)
        priority: Importance level (critical, high, medium, low)
        tags: List of tags for categorization
        metadata: Additional structured metadata (JSON-like dict)
        collection_id: Optional collection to add entry to
    
    Returns:
        Dictionary with entry_id and creation status
    """
    try:
        if not title or not title.strip():
            return {"success": False, "error": "Title cannot be empty", "entry_id": None}
        
        if not content or not content.strip():
            return {"success": False, "error": "Content cannot be empty", "entry_id": None}
        
        if category not in VALID_CATEGORIES:
            return {
                "success": False,
                "error": f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}",
                "entry_id": None,
            }
        
        if priority not in VALID_PRIORITIES:
            return {
                "success": False,
                "error": f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}",
                "entry_id": None,
            }
        
        entry_id = _generate_id()
        timestamp = datetime.now(UTC).isoformat()
        
        entry = {
            "title": title.strip(),
            "content": content.strip(),
            "category": category,
            "priority": priority,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp,
            "version": 1,
            "views": 0,
            "linked_entries": [],
        }
        
        _knowledge_entries[entry_id] = entry
        _save_history(entry_id, entry, "created")
        
        # Add to collection if specified
        if collection_id and collection_id in _knowledge_collections:
            _knowledge_collections[collection_id]["entries"].append(entry_id)
        
    except (ValueError, TypeError) as e:
        return {"success": False, "error": f"Failed to create entry: {e}", "entry_id": None}
    else:
        return {
            "success": True,
            "entry_id": entry_id,
            "message": f"Knowledge entry '{title}' created successfully",
            "category": category,
            "priority": priority,
        }


@register_tool(sandbox_execution=False)
def get_knowledge_entry(entry_id: str) -> dict[str, Any]:
    """
    Get a knowledge entry by ID with full details.
    
    Args:
        entry_id: ID of the entry to retrieve
    
    Returns:
        Dictionary with entry data or error
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    entry = _knowledge_entries[entry_id]
    entry["views"] = entry.get("views", 0) + 1
    
    # Get related entries
    related = []
    for rel in _entry_relationships:
        if rel["source"] == entry_id:
            related.append({"entry_id": rel["target"], "relationship": rel["type"], "direction": "outgoing"})
        elif rel["target"] == entry_id:
            related.append({"entry_id": rel["source"], "relationship": rel["type"], "direction": "incoming"})
    
    return {
        "success": True,
        "entry_id": entry_id,
        "entry": entry,
        "related_entries": related,
        "history_count": len(_entry_history.get(entry_id, [])),
    }


@register_tool(sandbox_execution=False)
def update_knowledge_entry(
    entry_id: str,
    title: str | None = None,
    content: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    append_content: bool = False,
) -> dict[str, Any]:
    """
    Update an existing knowledge entry.
    
    Args:
        entry_id: ID of the entry to update
        title: New title (optional)
        content: New content (optional)
        category: New category (optional)
        priority: New priority (optional)
        tags: New tags list (optional, replaces existing unless append mode)
        metadata: New metadata (optional, merged with existing)
        append_content: If True, append content instead of replacing
    
    Returns:
        Dictionary with update status
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    entry = _knowledge_entries[entry_id]
    updates = []
    
    if title is not None:
        if not title.strip():
            return {"success": False, "error": "Title cannot be empty"}
        entry["title"] = title.strip()
        updates.append("title")
    
    if content is not None:
        if not content.strip():
            return {"success": False, "error": "Content cannot be empty"}
        if append_content:
            entry["content"] = entry["content"] + "\n\n" + content.strip()
        else:
            entry["content"] = content.strip()
        updates.append("content")
    
    if category is not None:
        if category not in VALID_CATEGORIES:
            return {"success": False, "error": f"Invalid category: {category}"}
        entry["category"] = category
        updates.append("category")
    
    if priority is not None:
        if priority not in VALID_PRIORITIES:
            return {"success": False, "error": f"Invalid priority: {priority}"}
        entry["priority"] = priority
        updates.append("priority")
    
    if tags is not None:
        entry["tags"] = tags
        updates.append("tags")
    
    if metadata is not None:
        entry["metadata"] = {**entry.get("metadata", {}), **metadata}
        updates.append("metadata")
    
    entry["updated_at"] = datetime.now(UTC).isoformat()
    entry["version"] = entry.get("version", 1) + 1
    
    _save_history(entry_id, entry, "updated")
    
    return {
        "success": True,
        "entry_id": entry_id,
        "updates": updates,
        "version": entry["version"],
        "message": f"Entry '{entry['title']}' updated successfully",
    }


@register_tool(sandbox_execution=False)
def delete_knowledge_entry(entry_id: str, hard_delete: bool = False) -> dict[str, Any]:
    """
    Delete a knowledge entry.
    
    Args:
        entry_id: ID of the entry to delete
        hard_delete: If True, permanently delete including history
    
    Returns:
        Dictionary with deletion status
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    entry_title = _knowledge_entries[entry_id]["title"]
    
    # Remove from collections
    for collection in _knowledge_collections.values():
        if entry_id in collection.get("entries", []):
            collection["entries"].remove(entry_id)
    
    # Remove relationships
    _entry_relationships[:] = [
        r for r in _entry_relationships
        if r["source"] != entry_id and r["target"] != entry_id
    ]
    
    # Remove from shared knowledge
    for agent_entries in _shared_knowledge.values():
        if entry_id in agent_entries:
            agent_entries.remove(entry_id)
    
    # Delete entry
    del _knowledge_entries[entry_id]
    
    # Delete history if hard delete
    if hard_delete and entry_id in _entry_history:
        del _entry_history[entry_id]
    
    return {
        "success": True,
        "entry_id": entry_id,
        "message": f"Entry '{entry_title}' deleted successfully",
        "hard_delete": hard_delete,
    }


# =============================================================================
# Advanced Search
# =============================================================================

@register_tool(sandbox_execution=False)
def search_knowledge(
    query: str,
    category: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search knowledge entries with relevance ranking.
    
    Args:
        query: Search query (searches title, content, tags)
        category: Filter by category
        priority: Filter by priority
        tags: Filter by tags (entries must have at least one matching tag)
        limit: Maximum results to return (default: 20)
    
    Returns:
        Dictionary with ranked search results
    """
    results = []
    
    for entry_id, entry in _knowledge_entries.items():
        # Apply filters
        if category and entry.get("category") != category:
            continue
        if priority and entry.get("priority") != priority:
            continue
        if tags:
            entry_tags = entry.get("tags", [])
            if not any(t in entry_tags for t in tags):
                continue
        
        # Calculate relevance
        relevance = _calculate_relevance(entry, query)
        
        if relevance > 0:
            results.append({
                "entry_id": entry_id,
                "title": entry["title"],
                "category": entry["category"],
                "priority": entry["priority"],
                "tags": entry["tags"],
                "created_at": entry["created_at"],
                "relevance_score": round(relevance, 2),
                "snippet": entry["content"][:200] + "..." if len(entry["content"]) > 200 else entry["content"],
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    results = results[:limit]
    
    return {
        "success": True,
        "query": query,
        "total_results": len(results),
        "results": results,
        "filters_applied": {
            "category": category,
            "priority": priority,
            "tags": tags,
        },
    }


@register_tool(sandbox_execution=False)
def advanced_search(
    query: str | None = None,
    category: list[str] | None = None,
    priority: list[str] | None = None,
    tags: list[str] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    has_links: bool | None = None,
    metadata_filter: dict[str, Any] | None = None,
    sort_by: str = "relevance",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Advanced search with multiple filters and sorting options.
    
    Args:
        query: Optional text query
        category: Filter by multiple categories
        priority: Filter by multiple priorities
        tags: Filter by tags (AND logic - must have all)
        created_after: ISO date string - entries after this date
        created_before: ISO date string - entries before this date
        has_links: Filter entries with/without links
        metadata_filter: Filter by metadata fields
        sort_by: Sort field (relevance, created_at, updated_at, priority, title)
        sort_order: Sort order (asc, desc)
        limit: Maximum results
        offset: Pagination offset
    
    Returns:
        Dictionary with search results and pagination info
    """
    results = []
    
    for entry_id, entry in _knowledge_entries.items():
        # Category filter
        if category and entry.get("category") not in category:
            continue
        
        # Priority filter
        if priority and entry.get("priority") not in priority:
            continue
        
        # Tags filter (AND logic)
        if tags:
            entry_tags = entry.get("tags", [])
            if not all(t in entry_tags for t in tags):
                continue
        
        # Date filters
        try:
            entry_date = datetime.fromisoformat(entry.get("created_at", ""))
            if created_after:
                if entry_date < datetime.fromisoformat(created_after):
                    continue
            if created_before:
                if entry_date > datetime.fromisoformat(created_before):
                    continue
        except (ValueError, TypeError):
            pass
        
        # Links filter
        if has_links is not None:
            entry_has_links = len(entry.get("linked_entries", [])) > 0
            if has_links != entry_has_links:
                continue
        
        # Metadata filter
        if metadata_filter:
            entry_meta = entry.get("metadata", {})
            if not all(entry_meta.get(k) == v for k, v in metadata_filter.items()):
                continue
        
        # Calculate relevance if query provided
        relevance = _calculate_relevance(entry, query) if query else 0
        
        # Include if no query or has relevance
        if not query or relevance > 0:
            results.append({
                "entry_id": entry_id,
                "entry": entry,
                "relevance_score": round(relevance, 2),
            })
    
    # Sorting
    if sort_by == "relevance":
        results.sort(key=lambda x: x["relevance_score"], reverse=(sort_order == "desc"))
    elif sort_by == "created_at":
        results.sort(key=lambda x: x["entry"].get("created_at", ""), reverse=(sort_order == "desc"))
    elif sort_by == "updated_at":
        results.sort(key=lambda x: x["entry"].get("updated_at", ""), reverse=(sort_order == "desc"))
    elif sort_by == "priority":
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        results.sort(
            key=lambda x: priority_order.get(x["entry"].get("priority", "medium"), 2),
            reverse=(sort_order == "desc")
        )
    elif sort_by == "title":
        results.sort(key=lambda x: x["entry"].get("title", "").lower(), reverse=(sort_order == "desc"))
    
    # Pagination
    total = len(results)
    results = results[offset:offset + limit]
    
    return {
        "success": True,
        "total_results": total,
        "returned_results": len(results),
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
        "results": [
            {
                "entry_id": r["entry_id"],
                "title": r["entry"]["title"],
                "category": r["entry"]["category"],
                "priority": r["entry"]["priority"],
                "tags": r["entry"]["tags"],
                "created_at": r["entry"]["created_at"],
                "relevance_score": r["relevance_score"],
            }
            for r in results
        ],
    }


# =============================================================================
# Relationships and Linking
# =============================================================================

@register_tool(sandbox_execution=False)
def link_entries(
    source_id: str,
    target_id: str,
    relationship_type: str = "related_to",
    bidirectional: bool = True,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Create a link between two knowledge entries.
    
    Args:
        source_id: ID of the source entry
        target_id: ID of the target entry
        relationship_type: Type of relationship (related_to, depends_on, blocks, references, etc.)
        bidirectional: If True, create link in both directions
        description: Optional description of the relationship
    
    Returns:
        Dictionary with link creation status
    """
    if source_id not in _knowledge_entries:
        return {"success": False, "error": f"Source entry '{source_id}' not found"}
    if target_id not in _knowledge_entries:
        return {"success": False, "error": f"Target entry '{target_id}' not found"}
    if source_id == target_id:
        return {"success": False, "error": "Cannot link entry to itself"}
    if relationship_type not in VALID_RELATIONSHIP_TYPES:
        return {
            "success": False,
            "error": f"Invalid relationship type. Must be one of: {', '.join(VALID_RELATIONSHIP_TYPES)}",
        }
    
    # Check if link already exists
    for rel in _entry_relationships:
        if rel["source"] == source_id and rel["target"] == target_id and rel["type"] == relationship_type:
            return {"success": False, "error": "Link already exists"}
    
    # Create link
    link_id = f"link_{uuid.uuid4().hex[:8]}"
    relationship = {
        "id": link_id,
        "source": source_id,
        "target": target_id,
        "type": relationship_type,
        "bidirectional": bidirectional,
        "description": description,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _entry_relationships.append(relationship)
    
    # Update entries
    _knowledge_entries[source_id].setdefault("linked_entries", []).append(target_id)
    if bidirectional:
        _knowledge_entries[target_id].setdefault("linked_entries", []).append(source_id)
    
    return {
        "success": True,
        "link_id": link_id,
        "source": _knowledge_entries[source_id]["title"],
        "target": _knowledge_entries[target_id]["title"],
        "relationship": relationship_type,
        "bidirectional": bidirectional,
    }


@register_tool(sandbox_execution=False)
def unlink_entries(source_id: str, target_id: str) -> dict[str, Any]:
    """
    Remove a link between two entries.
    
    Args:
        source_id: ID of the source entry
        target_id: ID of the target entry
    
    Returns:
        Dictionary with unlink status
    """
    removed = False
    
    # Remove relationships
    for i, rel in enumerate(_entry_relationships):
        if (rel["source"] == source_id and rel["target"] == target_id) or \
           (rel["bidirectional"] and rel["source"] == target_id and rel["target"] == source_id):
            _entry_relationships.pop(i)
            removed = True
            break
    
    if not removed:
        return {"success": False, "error": "Link not found"}
    
    # Update entries
    if source_id in _knowledge_entries:
        linked = _knowledge_entries[source_id].get("linked_entries", [])
        if target_id in linked:
            linked.remove(target_id)
    
    if target_id in _knowledge_entries:
        linked = _knowledge_entries[target_id].get("linked_entries", [])
        if source_id in linked:
            linked.remove(source_id)
    
    return {
        "success": True,
        "message": "Link removed successfully",
    }


@register_tool(sandbox_execution=False)
def get_related_entries(
    entry_id: str,
    relationship_type: str | None = None,
    depth: int = 1,
) -> dict[str, Any]:
    """
    Get all entries related to a specific entry.
    
    Args:
        entry_id: ID of the entry
        relationship_type: Filter by relationship type
        depth: How deep to traverse relationships (1-3)
    
    Returns:
        Dictionary with related entries
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    depth = min(max(depth, 1), 3)  # Clamp between 1 and 3
    
    visited = {entry_id}
    related = []
    current_level = [entry_id]
    
    for current_depth in range(depth):
        next_level = []
        
        for current_id in current_level:
            for rel in _entry_relationships:
                target = None
                direction = None
                
                if rel["source"] == current_id:
                    target = rel["target"]
                    direction = "outgoing"
                elif rel["target"] == current_id:
                    target = rel["source"]
                    direction = "incoming"
                
                if target and target not in visited:
                    if relationship_type is None or rel["type"] == relationship_type:
                        visited.add(target)
                        next_level.append(target)
                        
                        entry = _knowledge_entries.get(target, {})
                        related.append({
                            "entry_id": target,
                            "title": entry.get("title", "Unknown"),
                            "relationship": rel["type"],
                            "direction": direction,
                            "depth": current_depth + 1,
                        })
        
        current_level = next_level
    
    return {
        "success": True,
        "source_entry": _knowledge_entries[entry_id]["title"],
        "related_count": len(related),
        "max_depth": depth,
        "related": related,
    }


# =============================================================================
# Collections (Organization)
# =============================================================================

@register_tool(sandbox_execution=False)
def create_knowledge_collection(
    name: str,
    description: str | None = None,
    parent_collection_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a collection (folder) for organizing knowledge entries.
    
    Args:
        name: Name of the collection
        description: Optional description
        parent_collection_id: Parent collection for nested organization
    
    Returns:
        Dictionary with collection creation status
    """
    if not name or not name.strip():
        return {"success": False, "error": "Collection name cannot be empty"}
    
    if parent_collection_id and parent_collection_id not in _knowledge_collections:
        return {"success": False, "error": f"Parent collection '{parent_collection_id}' not found"}
    
    collection_id = f"coll_{uuid.uuid4().hex[:8]}"
    
    _knowledge_collections[collection_id] = {
        "name": name.strip(),
        "description": description,
        "parent_id": parent_collection_id,
        "entries": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
    
    return {
        "success": True,
        "collection_id": collection_id,
        "name": name,
        "message": f"Collection '{name}' created successfully",
    }


@register_tool(sandbox_execution=False)
def add_to_collection(collection_id: str, entry_ids: list[str]) -> dict[str, Any]:
    """
    Add entries to a collection.
    
    Args:
        collection_id: ID of the collection
        entry_ids: List of entry IDs to add
    
    Returns:
        Dictionary with add status
    """
    if collection_id not in _knowledge_collections:
        return {"success": False, "error": f"Collection '{collection_id}' not found"}
    
    collection = _knowledge_collections[collection_id]
    added = []
    errors = []
    
    for entry_id in entry_ids:
        if entry_id not in _knowledge_entries:
            errors.append(f"Entry '{entry_id}' not found")
        elif entry_id in collection["entries"]:
            errors.append(f"Entry '{entry_id}' already in collection")
        else:
            collection["entries"].append(entry_id)
            added.append(entry_id)
    
    return {
        "success": len(added) > 0,
        "collection_id": collection_id,
        "added_count": len(added),
        "added": added,
        "errors": errors,
    }


@register_tool(sandbox_execution=False)
def remove_from_collection(collection_id: str, entry_ids: list[str]) -> dict[str, Any]:
    """
    Remove entries from a collection.
    
    Args:
        collection_id: ID of the collection
        entry_ids: List of entry IDs to remove
    
    Returns:
        Dictionary with removal status
    """
    if collection_id not in _knowledge_collections:
        return {"success": False, "error": f"Collection '{collection_id}' not found"}
    
    collection = _knowledge_collections[collection_id]
    removed = []
    
    for entry_id in entry_ids:
        if entry_id in collection["entries"]:
            collection["entries"].remove(entry_id)
            removed.append(entry_id)
    
    return {
        "success": True,
        "collection_id": collection_id,
        "removed_count": len(removed),
        "removed": removed,
    }


@register_tool(sandbox_execution=False)
def list_collections() -> dict[str, Any]:
    """
    List all knowledge collections.
    
    Returns:
        Dictionary with all collections
    """
    collections = []
    
    for coll_id, coll in _knowledge_collections.items():
        collections.append({
            "collection_id": coll_id,
            "name": coll["name"],
            "description": coll.get("description"),
            "parent_id": coll.get("parent_id"),
            "entry_count": len(coll.get("entries", [])),
            "created_at": coll.get("created_at"),
        })
    
    return {
        "success": True,
        "total_count": len(collections),
        "collections": collections,
    }


# =============================================================================
# Export/Import
# =============================================================================

@register_tool(sandbox_execution=False)
def export_knowledge(
    format_type: str = "json",
    entry_ids: list[str] | None = None,
    collection_id: str | None = None,
    include_relationships: bool = True,
    include_history: bool = False,
) -> dict[str, Any]:
    """
    Export knowledge entries to JSON or Markdown format.
    
    Args:
        format_type: Export format (json, markdown)
        entry_ids: Specific entries to export (None = all)
        collection_id: Export entire collection
        include_relationships: Include entry relationships
        include_history: Include version history
    
    Returns:
        Dictionary with exported content
    """
    entries_to_export = {}
    
    # Determine which entries to export
    if entry_ids:
        for eid in entry_ids:
            if eid in _knowledge_entries:
                entries_to_export[eid] = _knowledge_entries[eid]
    elif collection_id:
        if collection_id not in _knowledge_collections:
            return {"success": False, "error": f"Collection '{collection_id}' not found"}
        for eid in _knowledge_collections[collection_id]["entries"]:
            if eid in _knowledge_entries:
                entries_to_export[eid] = _knowledge_entries[eid]
    else:
        entries_to_export = _knowledge_entries.copy()
    
    if format_type == "json":
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "entries": entries_to_export,
        }
        
        if include_relationships:
            relevant_rels = [
                r for r in _entry_relationships
                if r["source"] in entries_to_export or r["target"] in entries_to_export
            ]
            export_data["relationships"] = relevant_rels
        
        if include_history:
            export_data["history"] = {
                eid: _entry_history.get(eid, [])
                for eid in entries_to_export
            }
        
        content = json.dumps(export_data, indent=2)
        
    elif format_type == "markdown":
        lines = ["# Knowledge Export", f"Exported: {datetime.now(UTC).isoformat()}", ""]
        
        for eid, entry in entries_to_export.items():
            lines.extend([
                f"## {entry['title']}",
                f"**ID:** {eid}",
                f"**Category:** {entry['category']}",
                f"**Priority:** {entry['priority']}",
                f"**Tags:** {', '.join(entry.get('tags', []))}",
                "",
                entry['content'],
                "",
                "---",
                "",
            ])
        
        content = "\n".join(lines)
    else:
        return {"success": False, "error": f"Unsupported format: {format_type}"}
    
    return {
        "success": True,
        "format": format_type,
        "entry_count": len(entries_to_export),
        "content": content,
        "content_length": len(content),
    }


@register_tool(sandbox_execution=False)
def import_knowledge(
    content: str,
    format_type: str = "json",
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """
    Import knowledge entries from JSON format.
    
    Args:
        content: JSON content to import
        format_type: Import format (currently only json supported)
        overwrite_existing: If True, overwrite entries with same ID
    
    Returns:
        Dictionary with import status
    """
    if format_type != "json":
        return {"success": False, "error": "Only JSON import is currently supported"}
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}
    
    entries = data.get("entries", {})
    imported = []
    skipped = []
    errors = []
    
    for eid, entry in entries.items():
        if eid in _knowledge_entries and not overwrite_existing:
            skipped.append(eid)
            continue
        
        try:
            _knowledge_entries[eid] = entry
            imported.append(eid)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{eid}: {e}")
    
    # Import relationships if present
    relationships = data.get("relationships", [])
    rel_imported = 0
    for rel in relationships:
        _entry_relationships.append(rel)
        rel_imported += 1
    
    return {
        "success": True,
        "imported_count": len(imported),
        "skipped_count": len(skipped),
        "relationships_imported": rel_imported,
        "errors": errors,
    }


# =============================================================================
# Templates
# =============================================================================

@register_tool(sandbox_execution=False)
def create_from_template(
    template_name: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a knowledge entry from a predefined template.
    
    Args:
        template_name: Name of the template (vulnerability, methodology, credential, endpoint, research)
        data: Data to populate the template (must include required fields)
    
    Returns:
        Dictionary with created entry
    """
    if template_name not in _knowledge_templates:
        return {
            "success": False,
            "error": f"Template '{template_name}' not found. Available: {', '.join(_knowledge_templates.keys())}",
        }
    
    template = _knowledge_templates[template_name]
    
    # Validate required fields
    if "title" not in data:
        return {"success": False, "error": "Title is required"}
    
    # Build content from template schema
    content_parts = []
    for field, field_type in template["schema"].items():
        if field == "title":
            continue
        if field in data:
            content_parts.append(f"**{field.replace('_', ' ').title()}:** {data[field]}")
    
    content = "\n\n".join(content_parts) if content_parts else "No additional details provided."
    
    # Create the entry
    return create_knowledge_entry(
        title=data["title"],
        content=content,
        category=template["default_category"],
        priority=data.get("priority", template["default_priority"]),
        tags=data.get("tags", []) + template["default_tags"],
        metadata={"template": template_name, "template_data": data},
    )


@register_tool(sandbox_execution=False)
def list_templates() -> dict[str, Any]:
    """
    List all available knowledge templates.
    
    Returns:
        Dictionary with template information
    """
    templates = []
    
    for name, template in _knowledge_templates.items():
        templates.append({
            "name": name,
            "display_name": template["name"],
            "schema": template["schema"],
            "default_category": template["default_category"],
            "default_priority": template["default_priority"],
            "default_tags": template["default_tags"],
        })
    
    return {
        "success": True,
        "templates": templates,
    }


# =============================================================================
# Versioning
# =============================================================================

@register_tool(sandbox_execution=False)
def get_entry_history(entry_id: str) -> dict[str, Any]:
    """
    Get the version history of a knowledge entry.
    
    Args:
        entry_id: ID of the entry
    
    Returns:
        Dictionary with version history
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    history = _entry_history.get(entry_id, [])
    
    return {
        "success": True,
        "entry_id": entry_id,
        "current_version": _knowledge_entries[entry_id].get("version", 1),
        "history_count": len(history),
        "history": history,
    }


@register_tool(sandbox_execution=False)
def revert_entry(entry_id: str, version: int) -> dict[str, Any]:
    """
    Revert an entry to a previous version.
    
    Args:
        entry_id: ID of the entry
        version: Version number to revert to
    
    Returns:
        Dictionary with revert status
    """
    if entry_id not in _knowledge_entries:
        return {"success": False, "error": f"Entry '{entry_id}' not found"}
    
    history = _entry_history.get(entry_id, [])
    target_snapshot = None
    
    for h in history:
        if h["version"] == version:
            target_snapshot = h["snapshot"]
            break
    
    if not target_snapshot:
        return {"success": False, "error": f"Version {version} not found in history"}
    
    # Save current state to history
    _save_history(entry_id, _knowledge_entries[entry_id], "reverted")
    
    # Restore snapshot
    _knowledge_entries[entry_id] = target_snapshot.copy()
    _knowledge_entries[entry_id]["version"] = _knowledge_entries[entry_id].get("version", 1) + 1
    _knowledge_entries[entry_id]["updated_at"] = datetime.now(UTC).isoformat()
    
    return {
        "success": True,
        "entry_id": entry_id,
        "reverted_to_version": version,
        "new_version": _knowledge_entries[entry_id]["version"],
    }


# =============================================================================
# Sharing
# =============================================================================

@register_tool(sandbox_execution=False)
def share_with_agent(
    agent_state: Any,
    entry_ids: list[str],
    target_agent_id: str,
) -> dict[str, Any]:
    """
    Share knowledge entries with another agent.
    
    Args:
        agent_state: Current agent's state
        entry_ids: List of entry IDs to share
        target_agent_id: ID of agent to share with
    
    Returns:
        Dictionary with sharing status
    """
    if target_agent_id not in _shared_knowledge:
        _shared_knowledge[target_agent_id] = []
    
    shared = []
    errors = []
    
    for eid in entry_ids:
        if eid not in _knowledge_entries:
            errors.append(f"Entry '{eid}' not found")
        elif eid in _shared_knowledge[target_agent_id]:
            errors.append(f"Entry '{eid}' already shared with agent")
        else:
            _shared_knowledge[target_agent_id].append(eid)
            shared.append(eid)
    
    # Send notification to target agent
    try:
        from strix.tools.agents_graph.agents_graph_actions import _agent_messages
        
        if target_agent_id not in _agent_messages:
            _agent_messages[target_agent_id] = []
        
        entry_titles = [_knowledge_entries[eid]["title"] for eid in shared if eid in _knowledge_entries]
        
        _agent_messages[target_agent_id].append({
            "id": f"share_{uuid.uuid4().hex[:8]}",
            "from": agent_state.agent_id,
            "to": target_agent_id,
            "content": f"Knowledge shared with you: {', '.join(entry_titles)}. Use get_shared_knowledge to access these entries.",
            "message_type": "information",
            "priority": "normal",
            "timestamp": datetime.now(UTC).isoformat(),
            "delivered": True,
            "read": False,
        })
    except (ImportError, AttributeError):
        pass
    
    return {
        "success": len(shared) > 0,
        "shared_count": len(shared),
        "shared": shared,
        "errors": errors,
    }


@register_tool(sandbox_execution=False)
def get_shared_knowledge(agent_state: Any) -> dict[str, Any]:
    """
    Get knowledge entries shared with the current agent.
    
    Args:
        agent_state: Current agent's state
    
    Returns:
        Dictionary with shared entries
    """
    agent_id = agent_state.agent_id
    shared_ids = _shared_knowledge.get(agent_id, [])
    
    entries = []
    for eid in shared_ids:
        if eid in _knowledge_entries:
            entry = _knowledge_entries[eid]
            entries.append({
                "entry_id": eid,
                "title": entry["title"],
                "category": entry["category"],
                "priority": entry["priority"],
                "created_at": entry["created_at"],
            })
    
    return {
        "success": True,
        "shared_count": len(entries),
        "entries": entries,
    }


# =============================================================================
# Analytics
# =============================================================================

@register_tool(sandbox_execution=False)
def get_knowledge_stats() -> dict[str, Any]:
    """
    Get statistics about the knowledge base.
    
    Returns:
        Dictionary with knowledge base statistics
    """
    total_entries = len(_knowledge_entries)
    
    # Category distribution
    category_dist: dict[str, int] = {}
    for entry in _knowledge_entries.values():
        cat = entry.get("category", "general")
        category_dist[cat] = category_dist.get(cat, 0) + 1
    
    # Priority distribution
    priority_dist: dict[str, int] = {}
    for entry in _knowledge_entries.values():
        pri = entry.get("priority", "medium")
        priority_dist[pri] = priority_dist.get(pri, 0) + 1
    
    # Tag frequency
    tag_freq: dict[str, int] = {}
    for entry in _knowledge_entries.values():
        for tag in entry.get("tags", []):
            tag_freq[tag] = tag_freq.get(tag, 0) + 1
    
    # Sort tags by frequency
    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "success": True,
        "total_entries": total_entries,
        "total_collections": len(_knowledge_collections),
        "total_relationships": len(_entry_relationships),
        "category_distribution": category_dist,
        "priority_distribution": priority_dist,
        "top_tags": dict(top_tags),
        "entries_with_links": sum(1 for e in _knowledge_entries.values() if e.get("linked_entries")),
    }


@register_tool(sandbox_execution=False)
def get_knowledge_graph() -> dict[str, Any]:
    """
    Get the knowledge graph structure for visualization.
    
    Returns:
        Dictionary with nodes and edges for graph visualization
    """
    nodes = []
    edges = []
    
    for eid, entry in _knowledge_entries.items():
        nodes.append({
            "id": eid,
            "label": entry["title"],
            "category": entry["category"],
            "priority": entry["priority"],
        })
    
    for rel in _entry_relationships:
        edges.append({
            "source": rel["source"],
            "target": rel["target"],
            "type": rel["type"],
            "bidirectional": rel.get("bidirectional", False),
        })
    
    return {
        "success": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
