"""
Advanced Multi-Agent Orchestration Actions.

This module provides significantly enhanced multi-agent coordination with:
- Priority-based task scheduling with dependencies
- Agent workload balancing and capacity management
- Team-based coordination
- Workflow automation
- Resource allocation
- Health monitoring and metrics
- Checkpoint synchronization
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from strix.tools.registry import register_tool


# =============================================================================
# Data Structures
# =============================================================================

# Task management
_tasks: dict[str, dict[str, Any]] = {}
_task_dependencies: list[dict[str, str]] = []
_task_assignments: dict[str, list[str]] = {}  # agent_id -> [task_ids]

# Priority queue
_priority_queue: list[str] = []

# Agent capacities and workloads
_agent_capacities: dict[str, int] = {}  # agent_id -> max concurrent tasks
_agent_workloads: dict[str, dict[str, Any]] = {}

# Teams
_teams: dict[str, dict[str, Any]] = {}

# Resources
_resources: dict[str, dict[str, Any]] = {}
_resource_allocations: dict[str, str] = {}  # resource_id -> agent_id

# Checkpoints
_checkpoints: dict[str, dict[str, Any]] = {}
_checkpoint_waiters: dict[str, list[str]] = {}

# Workflows
_workflows: dict[str, dict[str, Any]] = {}

# Metrics
_metrics: dict[str, Any] = {
    "total_tasks_created": 0,
    "total_tasks_completed": 0,
    "total_tasks_failed": 0,
    "total_messages_broadcast": 0,
    "total_coordinations": 0,
    "start_time": datetime.now(UTC).isoformat(),
}


def _get_agent_graph() -> dict[str, Any]:
    """Get the agent graph from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_graph
    return _agent_graph


def _get_agent_messages() -> dict[str, list[dict[str, Any]]]:
    """Get agent messages from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_messages
    return _agent_messages


def _generate_id(prefix: str = "id") -> str:
    """Generate a unique ID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _send_message_to_agent(
    from_agent_id: str,
    to_agent_id: str,
    content: str,
    message_type: str = "information",
    priority: str = "normal",
) -> None:
    """Send a message to an agent."""
    messages = _get_agent_messages()
    if to_agent_id not in messages:
        messages[to_agent_id] = []
    
    messages[to_agent_id].append({
        "id": _generate_id("msg"),
        "from": from_agent_id,
        "to": to_agent_id,
        "content": content,
        "message_type": message_type,
        "priority": priority,
        "timestamp": datetime.now(UTC).isoformat(),
        "delivered": True,
        "read": False,
    })


# =============================================================================
# Task Management
# =============================================================================

@register_tool(sandbox_execution=False)
def create_task(
    agent_state: Any,
    title: str,
    description: str,
    priority: Literal["critical", "high", "medium", "low"] = "medium",
    estimated_effort: str | None = None,
    deadline: str | None = None,
    tags: list[str] | None = None,
    auto_assign: bool = False,
) -> dict[str, Any]:
    """
    Create a new orchestrated task with priority and metadata.
    
    Args:
        agent_state: Current agent's state
        title: Task title
        description: Detailed description of the task
        priority: Task priority level
        estimated_effort: Estimated effort (e.g., "1h", "2d")
        deadline: ISO date deadline
        tags: Tags for categorization
        auto_assign: If True, automatically assign to least busy agent
    
    Returns:
        Dictionary with task creation status
    """
    task_id = _generate_id("task")
    
    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
        "estimated_effort": estimated_effort,
        "deadline": deadline,
        "tags": tags or [],
        "created_by": agent_state.agent_id,
        "assigned_to": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None,
    }
    
    _tasks[task_id] = task
    _metrics["total_tasks_created"] += 1
    
    # Add to priority queue
    _update_priority_queue()
    
    # Auto-assign if requested
    assigned_to = None
    if auto_assign:
        result = balance_workload(agent_state, task_ids=[task_id])
        if result.get("success") and result.get("assignments"):
            assigned_to = result["assignments"].get(task_id)
    
    return {
        "success": True,
        "task_id": task_id,
        "title": title,
        "priority": priority,
        "assigned_to": assigned_to,
        "message": f"Task '{title}' created successfully",
    }


@register_tool(sandbox_execution=False)
def assign_task(
    agent_state: Any,
    task_id: str,
    target_agent_id: str,
    notify: bool = True,
) -> dict[str, Any]:
    """
    Assign a task to a specific agent.
    
    Args:
        agent_state: Current agent's state
        task_id: Task to assign
        target_agent_id: Agent to assign the task to
        notify: Send notification to the agent
    
    Returns:
        Dictionary with assignment status
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    
    agent_graph = _get_agent_graph()
    if target_agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{target_agent_id}' not found"}
    
    task = _tasks[task_id]
    
    # Check agent capacity
    capacity = _agent_capacities.get(target_agent_id, 5)  # Default capacity of 5
    current_tasks = _task_assignments.get(target_agent_id, [])
    active_tasks = [t for t in current_tasks if _tasks.get(t, {}).get("status") in ["pending", "in_progress"]]
    
    if len(active_tasks) >= capacity:
        return {
            "success": False,
            "error": f"Agent '{target_agent_id}' is at capacity ({len(active_tasks)}/{capacity})",
        }
    
    # Assign task
    task["assigned_to"] = target_agent_id
    task["status"] = "assigned"
    task["updated_at"] = datetime.now(UTC).isoformat()
    
    # Update assignments
    if target_agent_id not in _task_assignments:
        _task_assignments[target_agent_id] = []
    _task_assignments[target_agent_id].append(task_id)
    
    # Notify agent
    if notify:
        agent_name = agent_graph["nodes"][target_agent_id].get("name", target_agent_id)
        _send_message_to_agent(
            from_agent_id=agent_state.agent_id,
            to_agent_id=target_agent_id,
            content=f"""<task_assignment>
<task_id>{task_id}</task_id>
<title>{task['title']}</title>
<description>{task['description']}</description>
<priority>{task['priority']}</priority>
<deadline>{task.get('deadline', 'None')}</deadline>
</task_assignment>""",
            message_type="instruction",
            priority="high" if task["priority"] in ["critical", "high"] else "normal",
        )
    
    return {
        "success": True,
        "task_id": task_id,
        "assigned_to": target_agent_id,
        "agent_name": agent_graph["nodes"][target_agent_id].get("name"),
        "agent_notified": notify,
    }


@register_tool(sandbox_execution=False)
def update_task_status(
    agent_state: Any,
    task_id: str,
    status: Literal["pending", "assigned", "in_progress", "completed", "failed", "blocked"],
    result: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Update the status of a task.
    
    Args:
        agent_state: Current agent's state
        task_id: Task to update
        status: New status
        result: Result description (for completed/failed)
        notes: Additional notes
    
    Returns:
        Dictionary with update status
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    
    task = _tasks[task_id]
    old_status = task["status"]
    task["status"] = status
    task["updated_at"] = datetime.now(UTC).isoformat()
    
    if status == "in_progress" and not task.get("started_at"):
        task["started_at"] = datetime.now(UTC).isoformat()
    
    if status == "completed":
        task["completed_at"] = datetime.now(UTC).isoformat()
        task["result"] = result
        _metrics["total_tasks_completed"] += 1
    
    if status == "failed":
        task["completed_at"] = datetime.now(UTC).isoformat()
        task["result"] = result
        _metrics["total_tasks_failed"] += 1
    
    if notes:
        task.setdefault("notes", []).append({
            "timestamp": datetime.now(UTC).isoformat(),
            "by": agent_state.agent_id,
            "content": notes,
        })
    
    # Notify creator if completed or failed
    if status in ["completed", "failed"] and task.get("created_by"):
        _send_message_to_agent(
            from_agent_id=agent_state.agent_id,
            to_agent_id=task["created_by"],
            content=f"""<task_status_update>
<task_id>{task_id}</task_id>
<title>{task['title']}</title>
<old_status>{old_status}</old_status>
<new_status>{status}</new_status>
<result>{result or 'N/A'}</result>
</task_status_update>""",
            message_type="information",
            priority="high" if status == "failed" else "normal",
        )
    
    # Update priority queue
    _update_priority_queue()
    
    return {
        "success": True,
        "task_id": task_id,
        "old_status": old_status,
        "new_status": status,
        "message": f"Task status updated to '{status}'",
    }


@register_tool(sandbox_execution=False)
def get_task_status(agent_state: Any, task_id: str) -> dict[str, Any]:
    """
    Get detailed status of a task.
    
    Args:
        agent_state: Current agent's state
        task_id: Task to query
    
    Returns:
        Dictionary with task details
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    
    task = _tasks[task_id].copy()
    
    # Get dependencies
    deps = get_task_dependencies(agent_state, task_id)
    task["dependencies"] = deps.get("dependencies", [])
    task["dependents"] = deps.get("dependents", [])
    
    return {
        "success": True,
        "task": task,
    }


@register_tool(sandbox_execution=False)
def list_tasks(
    agent_state: Any,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    created_by: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    List tasks with filtering options.
    
    Args:
        agent_state: Current agent's state
        status: Filter by status
        priority: Filter by priority
        assigned_to: Filter by assignee
        created_by: Filter by creator
        limit: Maximum results
    
    Returns:
        Dictionary with tasks list
    """
    results = []
    
    for task_id, task in _tasks.items():
        if status and task["status"] != status:
            continue
        if priority and task["priority"] != priority:
            continue
        if assigned_to and task.get("assigned_to") != assigned_to:
            continue
        if created_by and task.get("created_by") != created_by:
            continue
        
        results.append({
            "task_id": task_id,
            "title": task["title"],
            "status": task["status"],
            "priority": task["priority"],
            "assigned_to": task.get("assigned_to"),
            "created_at": task["created_at"],
        })
    
    # Sort by priority and creation time
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["created_at"]))
    results = results[:limit]
    
    return {
        "success": True,
        "total_count": len(results),
        "tasks": results,
    }


@register_tool(sandbox_execution=False)
def create_task_dependency(
    agent_state: Any,
    task_id: str,
    depends_on_task_id: str,
) -> dict[str, Any]:
    """
    Create a dependency between tasks.
    
    Args:
        agent_state: Current agent's state
        task_id: Task that has the dependency
        depends_on_task_id: Task that must complete first
    
    Returns:
        Dictionary with dependency creation status
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    if depends_on_task_id not in _tasks:
        return {"success": False, "error": f"Task '{depends_on_task_id}' not found"}
    if task_id == depends_on_task_id:
        return {"success": False, "error": "Task cannot depend on itself"}
    
    # Check for circular dependency
    def has_circular(tid: str, visited: set[str]) -> bool:
        if tid in visited:
            return True
        visited.add(tid)
        for dep in _task_dependencies:
            if dep["task_id"] == tid:
                if has_circular(dep["depends_on"], visited.copy()):
                    return True
        return False
    
    if has_circular(depends_on_task_id, {task_id}):
        return {"success": False, "error": "This would create a circular dependency"}
    
    # Check if dependency already exists
    for dep in _task_dependencies:
        if dep["task_id"] == task_id and dep["depends_on"] == depends_on_task_id:
            return {"success": False, "error": "Dependency already exists"}
    
    _task_dependencies.append({
        "task_id": task_id,
        "depends_on": depends_on_task_id,
        "created_at": datetime.now(UTC).isoformat(),
    })
    
    return {
        "success": True,
        "task_id": task_id,
        "depends_on": depends_on_task_id,
        "message": f"Task '{_tasks[task_id]['title']}' now depends on '{_tasks[depends_on_task_id]['title']}'",
    }


@register_tool(sandbox_execution=False)
def get_task_dependencies(agent_state: Any, task_id: str) -> dict[str, Any]:
    """
    Get dependencies and dependents of a task.
    
    Args:
        agent_state: Current agent's state
        task_id: Task to query
    
    Returns:
        Dictionary with dependencies and dependents
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    
    dependencies = []  # Tasks this task depends on
    dependents = []    # Tasks that depend on this task
    
    for dep in _task_dependencies:
        if dep["task_id"] == task_id:
            dep_task = _tasks.get(dep["depends_on"], {})
            dependencies.append({
                "task_id": dep["depends_on"],
                "title": dep_task.get("title", "Unknown"),
                "status": dep_task.get("status", "unknown"),
            })
        if dep["depends_on"] == task_id:
            dep_task = _tasks.get(dep["task_id"], {})
            dependents.append({
                "task_id": dep["task_id"],
                "title": dep_task.get("title", "Unknown"),
                "status": dep_task.get("status", "unknown"),
            })
    
    # Check if task can start (all dependencies complete)
    can_start = all(d["status"] == "completed" for d in dependencies)
    
    return {
        "success": True,
        "task_id": task_id,
        "dependencies": dependencies,
        "dependents": dependents,
        "can_start": can_start,
        "blocking_tasks": [d for d in dependencies if d["status"] != "completed"],
    }


# =============================================================================
# Priority Queue
# =============================================================================

def _update_priority_queue() -> None:
    """Update the priority queue based on current tasks."""
    pending_tasks = [
        (tid, task) for tid, task in _tasks.items()
        if task["status"] in ["pending", "assigned"]
    ]
    
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    
    # Sort by priority, then by creation time
    pending_tasks.sort(key=lambda x: (
        priority_order.get(x[1]["priority"], 2),
        x[1]["created_at"]
    ))
    
    _priority_queue.clear()
    _priority_queue.extend([tid for tid, _ in pending_tasks])


@register_tool(sandbox_execution=False)
def get_priority_queue(agent_state: Any) -> dict[str, Any]:
    """
    Get the current priority queue of pending tasks.
    
    Returns:
        Dictionary with ordered task queue
    """
    _update_priority_queue()
    
    queue = []
    for i, task_id in enumerate(_priority_queue):
        task = _tasks.get(task_id, {})
        queue.append({
            "position": i + 1,
            "task_id": task_id,
            "title": task.get("title", "Unknown"),
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "unknown"),
            "assigned_to": task.get("assigned_to"),
        })
    
    return {
        "success": True,
        "queue_length": len(queue),
        "queue": queue,
    }


@register_tool(sandbox_execution=False)
def reorder_priority(
    agent_state: Any,
    task_id: str,
    new_priority: Literal["critical", "high", "medium", "low"],
) -> dict[str, Any]:
    """
    Change the priority of a task and reorder the queue.
    
    Args:
        agent_state: Current agent's state
        task_id: Task to reprioritize
        new_priority: New priority level
    
    Returns:
        Dictionary with reorder status
    """
    if task_id not in _tasks:
        return {"success": False, "error": f"Task '{task_id}' not found"}
    
    old_priority = _tasks[task_id]["priority"]
    _tasks[task_id]["priority"] = new_priority
    _tasks[task_id]["updated_at"] = datetime.now(UTC).isoformat()
    
    _update_priority_queue()
    
    # Find new position
    new_position = _priority_queue.index(task_id) + 1 if task_id in _priority_queue else None
    
    return {
        "success": True,
        "task_id": task_id,
        "old_priority": old_priority,
        "new_priority": new_priority,
        "new_queue_position": new_position,
    }


# =============================================================================
# Workload Management
# =============================================================================

@register_tool(sandbox_execution=False)
def get_agent_workload(
    agent_state: Any,
    target_agent_id: str | None = None,
) -> dict[str, Any]:
    """
    Get the current workload of an agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: Agent to query (default: current agent)
    
    Returns:
        Dictionary with workload information
    """
    agent_id = target_agent_id or agent_state.agent_id
    
    agent_graph = _get_agent_graph()
    if agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{agent_id}' not found"}
    
    assigned_tasks = _task_assignments.get(agent_id, [])
    capacity = _agent_capacities.get(agent_id, 5)
    
    task_breakdown = {
        "pending": 0,
        "assigned": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
        "blocked": 0,
    }
    
    active_task_details = []
    for tid in assigned_tasks:
        task = _tasks.get(tid, {})
        status = task.get("status", "unknown")
        if status in task_breakdown:
            task_breakdown[status] += 1
        
        if status in ["pending", "assigned", "in_progress", "blocked"]:
            active_task_details.append({
                "task_id": tid,
                "title": task.get("title", "Unknown"),
                "priority": task.get("priority", "medium"),
                "status": status,
            })
    
    active_count = task_breakdown["pending"] + task_breakdown["assigned"] + task_breakdown["in_progress"] + task_breakdown["blocked"]
    utilization = (active_count / capacity * 100) if capacity > 0 else 0
    
    return {
        "success": True,
        "agent_id": agent_id,
        "agent_name": agent_graph["nodes"][agent_id].get("name"),
        "capacity": capacity,
        "active_tasks": active_count,
        "utilization_percent": round(utilization, 1),
        "task_breakdown": task_breakdown,
        "active_task_details": active_task_details,
        "can_accept_tasks": active_count < capacity,
    }


@register_tool(sandbox_execution=False)
def balance_workload(
    agent_state: Any,
    task_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Balance workload by assigning unassigned tasks to least busy agents.
    
    Args:
        agent_state: Current agent's state
        task_ids: Specific tasks to assign (default: all unassigned)
    
    Returns:
        Dictionary with assignment results
    """
    agent_graph = _get_agent_graph()
    
    # Get tasks to assign
    if task_ids:
        tasks_to_assign = [tid for tid in task_ids if tid in _tasks and not _tasks[tid].get("assigned_to")]
    else:
        tasks_to_assign = [
            tid for tid, task in _tasks.items()
            if task["status"] == "pending" and not task.get("assigned_to")
        ]
    
    if not tasks_to_assign:
        return {"success": True, "message": "No tasks to assign", "assignments": {}}
    
    # Get available agents and their utilization
    agent_utilizations = []
    for agent_id, node in agent_graph["nodes"].items():
        if node.get("status") not in ["running", "waiting"]:
            continue
        
        assigned = _task_assignments.get(agent_id, [])
        active = sum(1 for tid in assigned if _tasks.get(tid, {}).get("status") in ["pending", "assigned", "in_progress"])
        capacity = _agent_capacities.get(agent_id, 5)
        
        if active < capacity:
            agent_utilizations.append({
                "agent_id": agent_id,
                "name": node.get("name"),
                "active": active,
                "capacity": capacity,
                "available": capacity - active,
            })
    
    if not agent_utilizations:
        return {"success": False, "error": "No agents available to accept tasks"}
    
    # Sort by utilization (least busy first)
    agent_utilizations.sort(key=lambda x: x["active"] / x["capacity"])
    
    # Assign tasks
    assignments = {}
    for task_id in tasks_to_assign:
        # Find agent with most availability
        for agent in agent_utilizations:
            if agent["available"] > 0:
                result = assign_task(agent_state, task_id, agent["agent_id"], notify=True)
                if result.get("success"):
                    assignments[task_id] = agent["agent_id"]
                    agent["available"] -= 1
                    agent["active"] += 1
                break
    
    return {
        "success": True,
        "total_assigned": len(assignments),
        "assignments": assignments,
        "unassigned": [tid for tid in tasks_to_assign if tid not in assignments],
    }


@register_tool(sandbox_execution=False)
def set_agent_capacity(
    agent_state: Any,
    target_agent_id: str,
    capacity: int,
) -> dict[str, Any]:
    """
    Set the maximum concurrent task capacity for an agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: Agent to configure
        capacity: Maximum concurrent tasks (1-20)
    
    Returns:
        Dictionary with configuration status
    """
    if capacity < 1 or capacity > 20:
        return {"success": False, "error": "Capacity must be between 1 and 20"}
    
    agent_graph = _get_agent_graph()
    if target_agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{target_agent_id}' not found"}
    
    old_capacity = _agent_capacities.get(target_agent_id, 5)
    _agent_capacities[target_agent_id] = capacity
    
    return {
        "success": True,
        "agent_id": target_agent_id,
        "old_capacity": old_capacity,
        "new_capacity": capacity,
    }


# =============================================================================
# Team Management
# =============================================================================

@register_tool(sandbox_execution=False)
def create_agent_team(
    agent_state: Any,
    name: str,
    description: str | None = None,
    initial_members: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a team of agents for coordinated work.
    
    Args:
        agent_state: Current agent's state
        name: Team name
        description: Team description
        initial_members: Initial member agent IDs
    
    Returns:
        Dictionary with team creation status
    """
    team_id = _generate_id("team")
    
    team = {
        "id": team_id,
        "name": name,
        "description": description,
        "leader": agent_state.agent_id,
        "members": [],
        "created_at": datetime.now(UTC).isoformat(),
        "status": "active",
    }
    
    _teams[team_id] = team
    
    # Add initial members
    if initial_members:
        for member_id in initial_members:
            add_to_team(agent_state, team_id, member_id)
    
    return {
        "success": True,
        "team_id": team_id,
        "name": name,
        "message": f"Team '{name}' created successfully",
    }


@register_tool(sandbox_execution=False)
def add_to_team(
    agent_state: Any,
    team_id: str,
    agent_id: str,
    role: str = "member",
) -> dict[str, Any]:
    """
    Add an agent to a team.
    
    Args:
        agent_state: Current agent's state
        team_id: Team to add to
        agent_id: Agent to add
        role: Role in team (member, specialist, coordinator)
    
    Returns:
        Dictionary with addition status
    """
    if team_id not in _teams:
        return {"success": False, "error": f"Team '{team_id}' not found"}
    
    agent_graph = _get_agent_graph()
    if agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{agent_id}' not found"}
    
    team = _teams[team_id]
    
    # Check if already member
    if any(m["agent_id"] == agent_id for m in team["members"]):
        return {"success": False, "error": "Agent is already a team member"}
    
    team["members"].append({
        "agent_id": agent_id,
        "name": agent_graph["nodes"][agent_id].get("name"),
        "role": role,
        "joined_at": datetime.now(UTC).isoformat(),
    })
    
    # Notify the agent
    _send_message_to_agent(
        from_agent_id=agent_state.agent_id,
        to_agent_id=agent_id,
        content=f"You have been added to team '{team['name']}' as {role}.",
        message_type="information",
        priority="normal",
    )
    
    return {
        "success": True,
        "team_id": team_id,
        "agent_id": agent_id,
        "role": role,
        "team_size": len(team["members"]),
    }


@register_tool(sandbox_execution=False)
def remove_from_team(
    agent_state: Any,
    team_id: str,
    agent_id: str,
) -> dict[str, Any]:
    """
    Remove an agent from a team.
    
    Args:
        agent_state: Current agent's state
        team_id: Team to remove from
        agent_id: Agent to remove
    
    Returns:
        Dictionary with removal status
    """
    if team_id not in _teams:
        return {"success": False, "error": f"Team '{team_id}' not found"}
    
    team = _teams[team_id]
    
    # Find and remove member
    for i, member in enumerate(team["members"]):
        if member["agent_id"] == agent_id:
            team["members"].pop(i)
            return {
                "success": True,
                "team_id": team_id,
                "agent_id": agent_id,
                "team_size": len(team["members"]),
            }
    
    return {"success": False, "error": "Agent is not a team member"}


@register_tool(sandbox_execution=False)
def dissolve_team(agent_state: Any, team_id: str) -> dict[str, Any]:
    """
    Dissolve a team.
    
    Args:
        agent_state: Current agent's state
        team_id: Team to dissolve
    
    Returns:
        Dictionary with dissolution status
    """
    if team_id not in _teams:
        return {"success": False, "error": f"Team '{team_id}' not found"}
    
    team = _teams[team_id]
    
    # Notify all members
    for member in team["members"]:
        _send_message_to_agent(
            from_agent_id=agent_state.agent_id,
            to_agent_id=member["agent_id"],
            content=f"Team '{team['name']}' has been dissolved.",
            message_type="information",
            priority="normal",
        )
    
    del _teams[team_id]
    
    return {
        "success": True,
        "team_id": team_id,
        "message": f"Team dissolved successfully",
    }


@register_tool(sandbox_execution=False)
def list_teams(agent_state: Any) -> dict[str, Any]:
    """
    List all teams.
    
    Returns:
        Dictionary with teams list
    """
    teams = []
    for team_id, team in _teams.items():
        teams.append({
            "team_id": team_id,
            "name": team["name"],
            "leader": team["leader"],
            "member_count": len(team["members"]),
            "status": team["status"],
            "created_at": team["created_at"],
        })
    
    return {
        "success": True,
        "total_teams": len(teams),
        "teams": teams,
    }


@register_tool(sandbox_execution=False)
def get_team_status(agent_state: Any, team_id: str) -> dict[str, Any]:
    """
    Get detailed status of a team.
    
    Args:
        agent_state: Current agent's state
        team_id: Team to query
    
    Returns:
        Dictionary with team details
    """
    if team_id not in _teams:
        return {"success": False, "error": f"Team '{team_id}' not found"}
    
    team = _teams[team_id]
    agent_graph = _get_agent_graph()
    
    # Get member status
    members = []
    for member in team["members"]:
        node = agent_graph["nodes"].get(member["agent_id"], {})
        workload = get_agent_workload(agent_state, member["agent_id"])
        
        members.append({
            **member,
            "agent_status": node.get("status", "unknown"),
            "active_tasks": workload.get("active_tasks", 0),
        })
    
    return {
        "success": True,
        "team": {
            "id": team_id,
            "name": team["name"],
            "description": team.get("description"),
            "leader": team["leader"],
            "status": team["status"],
            "created_at": team["created_at"],
        },
        "members": members,
    }


# =============================================================================
# Coordination
# =============================================================================

@register_tool(sandbox_execution=False)
def broadcast_message(
    agent_state: Any,
    message: str,
    target_agents: list[str] | None = None,
    team_id: str | None = None,
    priority: Literal["low", "normal", "high", "urgent"] = "normal",
) -> dict[str, Any]:
    """
    Broadcast a message to multiple agents.
    
    Args:
        agent_state: Current agent's state
        message: Message to broadcast
        target_agents: Specific agents to message (default: all)
        team_id: Send to all team members
        priority: Message priority
    
    Returns:
        Dictionary with broadcast status
    """
    recipients = []
    
    if team_id:
        if team_id not in _teams:
            return {"success": False, "error": f"Team '{team_id}' not found"}
        recipients = [m["agent_id"] for m in _teams[team_id]["members"]]
    elif target_agents:
        recipients = target_agents
    else:
        # All agents except self
        agent_graph = _get_agent_graph()
        recipients = [
            aid for aid in agent_graph["nodes"]
            if aid != agent_state.agent_id
        ]
    
    sent_to = []
    for agent_id in recipients:
        _send_message_to_agent(
            from_agent_id=agent_state.agent_id,
            to_agent_id=agent_id,
            content=f"<broadcast>\n{message}\n</broadcast>",
            message_type="information",
            priority=priority,
        )
        sent_to.append(agent_id)
    
    _metrics["total_messages_broadcast"] += 1
    
    return {
        "success": True,
        "sent_to_count": len(sent_to),
        "sent_to": sent_to,
    }


@register_tool(sandbox_execution=False)
def request_coordination(
    agent_state: Any,
    target_agent_id: str,
    coordination_type: Literal["assistance", "review", "approval", "handoff", "sync"],
    description: str,
    urgency: Literal["low", "normal", "high", "critical"] = "normal",
) -> dict[str, Any]:
    """
    Request coordination with another agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: Agent to coordinate with
        coordination_type: Type of coordination needed
        description: Description of what's needed
        urgency: How urgent the request is
    
    Returns:
        Dictionary with request status
    """
    agent_graph = _get_agent_graph()
    if target_agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{target_agent_id}' not found"}
    
    coord_id = _generate_id("coord")
    
    _send_message_to_agent(
        from_agent_id=agent_state.agent_id,
        to_agent_id=target_agent_id,
        content=f"""<coordination_request id="{coord_id}">
<type>{coordination_type}</type>
<urgency>{urgency}</urgency>
<from>{agent_state.agent_name}</from>
<description>{description}</description>
<instructions>Please respond to this coordination request.</instructions>
</coordination_request>""",
        message_type="query",
        priority="high" if urgency in ["high", "critical"] else "normal",
    )
    
    _metrics["total_coordinations"] += 1
    
    return {
        "success": True,
        "coordination_id": coord_id,
        "target_agent": target_agent_id,
        "type": coordination_type,
        "message": "Coordination request sent",
    }


@register_tool(sandbox_execution=False)
def synchronize_agents(
    agent_state: Any,
    agent_ids: list[str],
    sync_point: str,
) -> dict[str, Any]:
    """
    Create a synchronization point for multiple agents.
    
    Args:
        agent_state: Current agent's state
        agent_ids: Agents to synchronize
        sync_point: Description of the sync point
    
    Returns:
        Dictionary with sync status
    """
    checkpoint_id = _generate_id("sync")
    
    result = create_checkpoint(agent_state, checkpoint_id, sync_point)
    if not result.get("success"):
        return result
    
    # Notify all agents to reach this checkpoint
    for agent_id in agent_ids:
        _send_message_to_agent(
            from_agent_id=agent_state.agent_id,
            to_agent_id=agent_id,
            content=f"""<sync_point>
<checkpoint_id>{checkpoint_id}</checkpoint_id>
<description>{sync_point}</description>
<instruction>Please reach this sync point and call wait_for_checkpoint('{checkpoint_id}') when ready.</instruction>
</sync_point>""",
            message_type="instruction",
            priority="high",
        )
    
    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "sync_point": sync_point,
        "agents_notified": agent_ids,
    }


@register_tool(sandbox_execution=False)
def create_checkpoint(
    agent_state: Any,
    checkpoint_id: str,
    description: str,
    required_agents: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a checkpoint for agent synchronization.
    
    Args:
        agent_state: Current agent's state
        checkpoint_id: Unique checkpoint identifier
        description: Checkpoint description
        required_agents: Agents that must reach this checkpoint
    
    Returns:
        Dictionary with checkpoint creation status
    """
    if checkpoint_id in _checkpoints:
        return {"success": False, "error": f"Checkpoint '{checkpoint_id}' already exists"}
    
    _checkpoints[checkpoint_id] = {
        "id": checkpoint_id,
        "description": description,
        "created_by": agent_state.agent_id,
        "created_at": datetime.now(UTC).isoformat(),
        "required_agents": required_agents or [],
        "reached_by": [],
        "status": "active",
    }
    
    _checkpoint_waiters[checkpoint_id] = []
    
    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "description": description,
    }


@register_tool(sandbox_execution=False)
def wait_for_checkpoint(
    agent_state: Any,
    checkpoint_id: str,
) -> dict[str, Any]:
    """
    Wait at a checkpoint until all required agents arrive.
    
    Args:
        agent_state: Current agent's state
        checkpoint_id: Checkpoint to wait at
    
    Returns:
        Dictionary with checkpoint status
    """
    if checkpoint_id not in _checkpoints:
        return {"success": False, "error": f"Checkpoint '{checkpoint_id}' not found"}
    
    checkpoint = _checkpoints[checkpoint_id]
    
    # Mark this agent as reached
    if agent_state.agent_id not in checkpoint["reached_by"]:
        checkpoint["reached_by"].append(agent_state.agent_id)
    
    # Check if all required agents have reached
    all_reached = True
    if checkpoint["required_agents"]:
        all_reached = all(
            aid in checkpoint["reached_by"]
            for aid in checkpoint["required_agents"]
        )
    
    if all_reached:
        checkpoint["status"] = "complete"
        
        # Notify all waiting agents
        for waiter_id in _checkpoint_waiters.get(checkpoint_id, []):
            _send_message_to_agent(
                from_agent_id=agent_state.agent_id,
                to_agent_id=waiter_id,
                content=f"Checkpoint '{checkpoint_id}' is complete. All agents have arrived.",
                message_type="information",
                priority="high",
            )
    
    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "status": checkpoint["status"],
        "reached_by": checkpoint["reached_by"],
        "all_reached": all_reached,
        "waiting_for": [
            aid for aid in checkpoint.get("required_agents", [])
            if aid not in checkpoint["reached_by"]
        ],
    }


# =============================================================================
# Health & Monitoring
# =============================================================================

@register_tool(sandbox_execution=False)
def get_agent_health(
    agent_state: Any,
    target_agent_id: str | None = None,
) -> dict[str, Any]:
    """
    Get health status of an agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: Agent to check (default: current)
    
    Returns:
        Dictionary with health information
    """
    agent_id = target_agent_id or agent_state.agent_id
    
    agent_graph = _get_agent_graph()
    if agent_id not in agent_graph["nodes"]:
        return {"success": False, "error": f"Agent '{agent_id}' not found"}
    
    node = agent_graph["nodes"][agent_id]
    
    # Get workload
    workload = get_agent_workload(agent_state, agent_id)
    
    # Determine health status
    status = node.get("status", "unknown")
    utilization = workload.get("utilization_percent", 0)
    
    if status in ["error", "failed", "stopped"]:
        health = "critical"
    elif status == "stopping":
        health = "degraded"
    elif utilization > 90:
        health = "overloaded"
    elif utilization > 70:
        health = "busy"
    elif status == "waiting":
        health = "idle"
    else:
        health = "healthy"
    
    return {
        "success": True,
        "agent_id": agent_id,
        "name": node.get("name"),
        "status": status,
        "health": health,
        "utilization_percent": utilization,
        "active_tasks": workload.get("active_tasks", 0),
        "capacity": workload.get("capacity", 5),
    }


@register_tool(sandbox_execution=False)
def get_system_metrics(agent_state: Any) -> dict[str, Any]:
    """
    Get overall system orchestration metrics.
    
    Returns:
        Dictionary with system-wide metrics
    """
    agent_graph = _get_agent_graph()
    
    # Agent stats
    agent_stats = {"total": 0, "running": 0, "waiting": 0, "stopped": 0, "error": 0}
    for node in agent_graph["nodes"].values():
        agent_stats["total"] += 1
        status = node.get("status", "unknown")
        if status in agent_stats:
            agent_stats[status] += 1
    
    # Task stats
    task_stats = {"total": 0, "pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
    for task in _tasks.values():
        task_stats["total"] += 1
        status = task.get("status", "pending")
        if status in task_stats:
            task_stats[status] += 1
    
    # Calculate uptime
    start_time = datetime.fromisoformat(_metrics["start_time"])
    uptime_seconds = (datetime.now(UTC) - start_time).total_seconds()
    
    return {
        "success": True,
        "uptime_seconds": int(uptime_seconds),
        "agents": agent_stats,
        "tasks": task_stats,
        "teams": len(_teams),
        "active_checkpoints": len([c for c in _checkpoints.values() if c["status"] == "active"]),
        "metrics": {
            "total_tasks_created": _metrics["total_tasks_created"],
            "total_tasks_completed": _metrics["total_tasks_completed"],
            "total_tasks_failed": _metrics["total_tasks_failed"],
            "total_broadcasts": _metrics["total_messages_broadcast"],
            "total_coordinations": _metrics["total_coordinations"],
        },
    }


@register_tool(sandbox_execution=False)
def get_orchestration_dashboard(agent_state: Any) -> dict[str, Any]:
    """
    Get a comprehensive orchestration dashboard view.
    
    Returns:
        Dictionary with dashboard data
    """
    # Get system metrics
    metrics = get_system_metrics(agent_state)
    
    # Get priority queue
    queue = get_priority_queue(agent_state)
    
    # Get all teams
    teams = list_teams(agent_state)
    
    # Get agent health for all agents
    agent_graph = _get_agent_graph()
    agent_health = []
    for agent_id in agent_graph["nodes"]:
        health = get_agent_health(agent_state, agent_id)
        if health.get("success"):
            agent_health.append({
                "agent_id": agent_id,
                "name": health.get("name"),
                "health": health.get("health"),
                "utilization": health.get("utilization_percent"),
            })
    
    # Sort by health (critical first)
    health_order = {"critical": 0, "overloaded": 1, "degraded": 2, "busy": 3, "healthy": 4, "idle": 5}
    agent_health.sort(key=lambda x: health_order.get(x["health"], 99))
    
    return {
        "success": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "system_metrics": metrics,
        "priority_queue_top5": queue.get("queue", [])[:5],
        "teams_summary": teams.get("teams", []),
        "agent_health": agent_health,
    }


# =============================================================================
# Resource Management
# =============================================================================

@register_tool(sandbox_execution=False)
def allocate_resource(
    agent_state: Any,
    resource_name: str,
    resource_type: str,
    exclusive: bool = False,
) -> dict[str, Any]:
    """
    Allocate a resource to the current agent.
    
    Args:
        agent_state: Current agent's state
        resource_name: Name of the resource
        resource_type: Type (database, service, file, network, etc.)
        exclusive: If True, only one agent can use this resource
    
    Returns:
        Dictionary with allocation status
    """
    resource_id = f"res_{resource_name}_{resource_type}"
    
    # Check if resource exists and is exclusively allocated
    if resource_id in _resources:
        res = _resources[resource_id]
        if res.get("exclusive") and res.get("allocated_to"):
            if res["allocated_to"] != agent_state.agent_id:
                return {
                    "success": False,
                    "error": f"Resource '{resource_name}' is exclusively allocated to another agent",
                }
    
    _resources[resource_id] = {
        "id": resource_id,
        "name": resource_name,
        "type": resource_type,
        "exclusive": exclusive,
        "allocated_to": agent_state.agent_id,
        "allocated_at": datetime.now(UTC).isoformat(),
    }
    
    _resource_allocations[resource_id] = agent_state.agent_id
    
    return {
        "success": True,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "exclusive": exclusive,
    }


@register_tool(sandbox_execution=False)
def release_resource(
    agent_state: Any,
    resource_id: str,
) -> dict[str, Any]:
    """
    Release a resource allocation.
    
    Args:
        agent_state: Current agent's state
        resource_id: Resource to release
    
    Returns:
        Dictionary with release status
    """
    if resource_id not in _resources:
        return {"success": False, "error": f"Resource '{resource_id}' not found"}
    
    res = _resources[resource_id]
    if res.get("allocated_to") != agent_state.agent_id:
        return {"success": False, "error": "You are not the owner of this resource"}
    
    res["allocated_to"] = None
    res["released_at"] = datetime.now(UTC).isoformat()
    _resource_allocations.pop(resource_id, None)
    
    return {
        "success": True,
        "resource_id": resource_id,
        "message": "Resource released",
    }


@register_tool(sandbox_execution=False)
def list_resources(agent_state: Any) -> dict[str, Any]:
    """
    List all resources and their allocation status.
    
    Returns:
        Dictionary with resources list
    """
    resources = []
    for res_id, res in _resources.items():
        resources.append({
            "resource_id": res_id,
            "name": res["name"],
            "type": res["type"],
            "exclusive": res.get("exclusive", False),
            "allocated_to": res.get("allocated_to"),
            "available": res.get("allocated_to") is None or not res.get("exclusive"),
        })
    
    return {
        "success": True,
        "total_resources": len(resources),
        "resources": resources,
    }


# =============================================================================
# Workflow Management
# =============================================================================

@register_tool(sandbox_execution=False)
def create_workflow(
    agent_state: Any,
    name: str,
    description: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create a workflow with ordered steps.
    
    Args:
        agent_state: Current agent's state
        name: Workflow name
        description: Workflow description
        steps: List of steps, each with 'name', 'task_template', and optional 'depends_on'
    
    Returns:
        Dictionary with workflow creation status
    """
    workflow_id = _generate_id("wf")
    
    workflow = {
        "id": workflow_id,
        "name": name,
        "description": description,
        "steps": steps,
        "created_by": agent_state.agent_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "created",
        "executions": [],
    }
    
    _workflows[workflow_id] = workflow
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "name": name,
        "step_count": len(steps),
    }


@register_tool(sandbox_execution=False)
def execute_workflow(
    agent_state: Any,
    workflow_id: str,
) -> dict[str, Any]:
    """
    Execute a workflow, creating tasks for each step.
    
    Args:
        agent_state: Current agent's state
        workflow_id: Workflow to execute
    
    Returns:
        Dictionary with execution status
    """
    if workflow_id not in _workflows:
        return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
    
    workflow = _workflows[workflow_id]
    execution_id = _generate_id("exec")
    
    # Create tasks for each step
    created_tasks = []
    step_task_map = {}
    
    for step in workflow["steps"]:
        result = create_task(
            agent_state,
            title=f"[{workflow['name']}] {step['name']}",
            description=step.get("task_template", step["name"]),
            priority=step.get("priority", "medium"),
            tags=["workflow", workflow_id],
            auto_assign=step.get("auto_assign", False),
        )
        
        if result.get("success"):
            task_id = result["task_id"]
            created_tasks.append(task_id)
            step_task_map[step["name"]] = task_id
            
            # Create dependencies
            if "depends_on" in step:
                for dep_name in step["depends_on"]:
                    if dep_name in step_task_map:
                        create_task_dependency(agent_state, task_id, step_task_map[dep_name])
    
    # Record execution
    workflow["executions"].append({
        "execution_id": execution_id,
        "started_at": datetime.now(UTC).isoformat(),
        "tasks": created_tasks,
        "status": "running",
    })
    workflow["status"] = "running"
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "tasks_created": len(created_tasks),
        "task_ids": created_tasks,
    }


@register_tool(sandbox_execution=False)
def get_workflow_status(
    agent_state: Any,
    workflow_id: str,
) -> dict[str, Any]:
    """
    Get the status of a workflow.
    
    Args:
        agent_state: Current agent's state
        workflow_id: Workflow to query
    
    Returns:
        Dictionary with workflow status
    """
    if workflow_id not in _workflows:
        return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
    
    workflow = _workflows[workflow_id]
    
    # Get latest execution status
    executions = []
    for exec_data in workflow.get("executions", []):
        task_statuses = {}
        for task_id in exec_data.get("tasks", []):
            if task_id in _tasks:
                task_statuses[task_id] = _tasks[task_id]["status"]
        
        # Determine execution status
        if all(s == "completed" for s in task_statuses.values()):
            exec_status = "completed"
        elif any(s == "failed" for s in task_statuses.values()):
            exec_status = "failed"
        elif any(s == "in_progress" for s in task_statuses.values()):
            exec_status = "running"
        else:
            exec_status = "pending"
        
        executions.append({
            "execution_id": exec_data["execution_id"],
            "started_at": exec_data["started_at"],
            "status": exec_status,
            "task_statuses": task_statuses,
        })
    
    return {
        "success": True,
        "workflow": {
            "id": workflow_id,
            "name": workflow["name"],
            "status": workflow["status"],
            "step_count": len(workflow["steps"]),
        },
        "executions": executions,
    }


@register_tool(sandbox_execution=False)
def pause_workflow(
    agent_state: Any,
    workflow_id: str,
) -> dict[str, Any]:
    """
    Pause a running workflow.
    
    Args:
        agent_state: Current agent's state
        workflow_id: Workflow to pause
    
    Returns:
        Dictionary with pause status
    """
    if workflow_id not in _workflows:
        return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
    
    workflow = _workflows[workflow_id]
    workflow["status"] = "paused"
    
    # Mark pending tasks as blocked
    for exec_data in workflow.get("executions", []):
        for task_id in exec_data.get("tasks", []):
            if task_id in _tasks and _tasks[task_id]["status"] == "pending":
                _tasks[task_id]["status"] = "blocked"
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "status": "paused",
    }


@register_tool(sandbox_execution=False)
def resume_workflow(
    agent_state: Any,
    workflow_id: str,
) -> dict[str, Any]:
    """
    Resume a paused workflow.
    
    Args:
        agent_state: Current agent's state
        workflow_id: Workflow to resume
    
    Returns:
        Dictionary with resume status
    """
    if workflow_id not in _workflows:
        return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
    
    workflow = _workflows[workflow_id]
    workflow["status"] = "running"
    
    # Unblock tasks
    for exec_data in workflow.get("executions", []):
        for task_id in exec_data.get("tasks", []):
            if task_id in _tasks and _tasks[task_id]["status"] == "blocked":
                _tasks[task_id]["status"] = "pending"
    
    _update_priority_queue()
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "status": "running",
    }
