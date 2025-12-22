"""
Advanced Multi-Agent Orchestration System.

This module provides significantly enhanced multi-agent coordination with:
- Priority-based task scheduling
- Agent workload balancing
- Resource allocation and management
- Task dependencies and workflows
- Agent health monitoring
- Coordination protocols
- Broadcast messaging
- Team management
"""

from .orchestration_actions import (
    # Task Management
    create_task,
    assign_task,
    update_task_status,
    get_task_status,
    list_tasks,
    create_task_dependency,
    get_task_dependencies,
    
    # Priority Queue
    get_priority_queue,
    reorder_priority,
    
    # Workload Management
    get_agent_workload,
    balance_workload,
    set_agent_capacity,
    
    # Team Management
    create_agent_team,
    add_to_team,
    remove_from_team,
    dissolve_team,
    list_teams,
    get_team_status,
    
    # Coordination
    broadcast_message,
    request_coordination,
    synchronize_agents,
    create_checkpoint,
    wait_for_checkpoint,
    
    # Health & Monitoring
    get_agent_health,
    get_system_metrics,
    get_orchestration_dashboard,
    
    # Resource Management
    allocate_resource,
    release_resource,
    list_resources,
    
    # Workflow Management
    create_workflow,
    execute_workflow,
    get_workflow_status,
    pause_workflow,
    resume_workflow,
)

__all__ = [
    "create_task",
    "assign_task",
    "update_task_status",
    "get_task_status",
    "list_tasks",
    "create_task_dependency",
    "get_task_dependencies",
    "get_priority_queue",
    "reorder_priority",
    "get_agent_workload",
    "balance_workload",
    "set_agent_capacity",
    "create_agent_team",
    "add_to_team",
    "remove_from_team",
    "dissolve_team",
    "list_teams",
    "get_team_status",
    "broadcast_message",
    "request_coordination",
    "synchronize_agents",
    "create_checkpoint",
    "wait_for_checkpoint",
    "get_agent_health",
    "get_system_metrics",
    "get_orchestration_dashboard",
    "allocate_resource",
    "release_resource",
    "list_resources",
    "create_workflow",
    "execute_workflow",
    "get_workflow_status",
    "pause_workflow",
    "resume_workflow",
]
