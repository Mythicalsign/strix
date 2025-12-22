"""
Custom Agent Actions - Advanced sub-agent creation and management with root capabilities.

This module provides tools for creating highly customizable sub-agents that can:
- Have root terminal access
- Be configured with specific capabilities
- Have custom tool access
- Be managed and controlled by the Main AI
"""

import threading
from datetime import UTC, datetime
from typing import Any, Literal

from strix.tools.registry import register_tool


# Track custom agent configurations and capabilities
_custom_agent_configs: dict[str, dict[str, Any]] = {}
_agent_root_access: dict[str, bool] = {}


def _get_agent_graph() -> dict[str, Any]:
    """Get the agent graph from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_graph
    return _agent_graph


def _get_agent_messages() -> dict[str, list[dict[str, Any]]]:
    """Get agent messages from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_messages
    return _agent_messages


def _get_agent_instances() -> dict[str, Any]:
    """Get agent instances from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_instances
    return _agent_instances


def _get_agent_states() -> dict[str, Any]:
    """Get agent states from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _agent_states
    return _agent_states


def _get_running_agents() -> dict[str, threading.Thread]:
    """Get running agents from agents_graph_actions."""
    from strix.tools.agents_graph.agents_graph_actions import _running_agents
    return _running_agents


@register_tool(sandbox_execution=False)
def create_custom_agent(
    agent_state: Any,
    task: str,
    name: str,
    capabilities: list[str] | None = None,
    root_access: bool = False,
    inherit_context: bool = True,
    prompt_modules: str | None = None,
    max_iterations: int = 300,
    priority: Literal["low", "normal", "high", "critical"] = "normal",
    timeout: int | None = None,
    custom_instructions: str | None = None,
) -> dict[str, Any]:
    """
    Create a highly customizable sub-agent with advanced configuration options.
    
    This is an enhanced version of create_agent that allows:
    - Root terminal access for the sub-agent
    - Custom capability sets
    - Priority-based execution
    - Custom instructions injection
    - Configurable iteration limits and timeouts
    
    Args:
        agent_state: Parent agent's state
        task: The specific task for the new agent
        name: Human-readable name for the agent
        capabilities: List of capabilities to grant (e.g., ["terminal", "browser", "file_edit"])
        root_access: Whether to grant root terminal access (default: False)
        inherit_context: Whether to inherit parent's conversation history
        prompt_modules: Comma-separated list of prompt modules (max 5)
        max_iterations: Maximum iterations for the agent (default: 300)
        priority: Agent priority level (low, normal, high, critical)
        timeout: Custom timeout in seconds
        custom_instructions: Additional instructions to inject into the agent's context
    
    Returns:
        Dictionary with agent creation status and details
    """
    try:
        parent_id = agent_state.agent_id
        
        # Parse and validate prompt modules
        module_list = []
        if prompt_modules:
            module_list = [m.strip() for m in prompt_modules.split(",") if m.strip()]
        
        if len(module_list) > 5:
            return {
                "success": False,
                "error": "Cannot specify more than 5 prompt modules",
                "agent_id": None,
            }
        
        if module_list:
            from strix.prompts import get_all_module_names, validate_module_names
            
            validation = validate_module_names(module_list)
            if validation["invalid"]:
                available_modules = list(get_all_module_names())
                return {
                    "success": False,
                    "error": f"Invalid prompt modules: {validation['invalid']}. Available: {', '.join(available_modules)}",
                    "agent_id": None,
                }
        
        # Import required modules
        from strix.agents import StrixAgent
        from strix.agents.state import AgentState
        from strix.llm.config import LLMConfig
        
        # Create agent state
        state = AgentState(
            task=task,
            agent_name=name,
            parent_id=parent_id,
            max_iterations=max_iterations,
        )
        
        # Get parent agent config for inheritance
        parent_agent = _get_agent_instances().get(parent_id)
        
        parent_timeout = None
        scan_mode = "deep"
        if parent_agent and hasattr(parent_agent, "llm_config"):
            if hasattr(parent_agent.llm_config, "timeout"):
                parent_timeout = parent_agent.llm_config.timeout
            if hasattr(parent_agent.llm_config, "scan_mode"):
                scan_mode = parent_agent.llm_config.scan_mode
        
        # Use custom timeout or parent's timeout
        final_timeout = timeout or parent_timeout
        
        llm_config = LLMConfig(
            prompt_modules=module_list,
            timeout=final_timeout,
            scan_mode=scan_mode,
        )
        
        agent_config = {
            "llm_config": llm_config,
            "state": state,
        }
        if parent_agent and hasattr(parent_agent, "non_interactive"):
            agent_config["non_interactive"] = parent_agent.non_interactive
        
        agent = StrixAgent(agent_config)
        
        # Store custom configuration
        _custom_agent_configs[state.agent_id] = {
            "capabilities": capabilities or ["terminal", "browser", "file_edit", "python", "proxy"],
            "root_access": root_access,
            "priority": priority,
            "custom_instructions": custom_instructions,
            "created_at": datetime.now(UTC).isoformat(),
            "parent_id": parent_id,
        }
        
        # Grant root access if requested
        if root_access:
            _agent_root_access[state.agent_id] = True
        
        # Prepare inherited messages
        inherited_messages = []
        if inherit_context:
            inherited_messages = agent_state.get_conversation_history()
        
        # Add custom instructions to agent context
        if custom_instructions:
            custom_msg = f"""<custom_agent_instructions>
<from_parent>{agent_state.agent_name} ({parent_id})</from_parent>
<instructions>
{custom_instructions}
</instructions>
<capabilities>
- Root Terminal Access: {"ENABLED - You have full root/sudo access" if root_access else "DISABLED"}
- Available Tools: {', '.join(capabilities or ["all standard tools"])}
- Priority Level: {priority}
- Max Iterations: {max_iterations}
</capabilities>
</custom_agent_instructions>"""
            state.add_message("user", custom_msg)
        
        _get_agent_instances()[state.agent_id] = agent
        
        # Import the runner function
        from strix.tools.agents_graph.agents_graph_actions import _run_agent_in_thread
        
        # Start the agent in a thread
        thread = threading.Thread(
            target=_run_agent_in_thread,
            args=(agent, state, inherited_messages),
            daemon=True,
            name=f"CustomAgent-{name}-{state.agent_id}",
        )
        thread.start()
        _get_running_agents()[state.agent_id] = thread
        
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Failed to create custom agent: {e}",
            "agent_id": None,
        }
    else:
        return {
            "success": True,
            "agent_id": state.agent_id,
            "message": f"Custom agent '{name}' created with advanced configuration",
            "agent_info": {
                "id": state.agent_id,
                "name": name,
                "status": "running",
                "parent_id": parent_id,
                "root_access": root_access,
                "priority": priority,
                "capabilities": capabilities or ["all standard tools"],
                "max_iterations": max_iterations,
            },
        }


@register_tool(sandbox_execution=False)
def create_root_enabled_agent(
    agent_state: Any,
    task: str,
    name: str,
    inherit_context: bool = True,
    prompt_modules: str | None = None,
    custom_instructions: str | None = None,
) -> dict[str, Any]:
    """
    Create a sub-agent with root terminal access enabled by default.
    
    This is a convenience function that creates an agent with:
    - Full root/sudo terminal access
    - All standard capabilities enabled
    - High priority execution
    
    Args:
        agent_state: Parent agent's state
        task: The specific task for the new agent
        name: Human-readable name for the agent
        inherit_context: Whether to inherit parent's conversation history
        prompt_modules: Comma-separated list of prompt modules (max 5)
        custom_instructions: Additional instructions for the agent
    
    Returns:
        Dictionary with agent creation status and details
    """
    root_instructions = """You have been granted ROOT TERMINAL ACCESS.

You can:
- Use the root_execute tool for privileged commands
- Install any packages, libraries, or tools you need
- Create and manage databases
- Start/stop system services
- Execute scripts with elevated privileges
- Access and modify any files

Use this power responsibly to accomplish your assigned task efficiently."""

    combined_instructions = root_instructions
    if custom_instructions:
        combined_instructions += f"\n\nAdditional Instructions:\n{custom_instructions}"
    
    return create_custom_agent(
        agent_state=agent_state,
        task=task,
        name=name,
        capabilities=["root_terminal", "terminal", "browser", "file_edit", "python", "proxy"],
        root_access=True,
        inherit_context=inherit_context,
        prompt_modules=prompt_modules,
        max_iterations=300,
        priority="high",
        custom_instructions=combined_instructions,
    )


@register_tool(sandbox_execution=False)
def get_agent_capabilities(
    agent_state: Any,
    target_agent_id: str | None = None,
) -> dict[str, Any]:
    """
    Get the capabilities and configuration of an agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: ID of agent to query (default: current agent)
    
    Returns:
        Dictionary with agent capabilities and configuration
    """
    agent_id = target_agent_id or agent_state.agent_id
    
    if agent_id not in _get_agent_graph()["nodes"]:
        return {
            "success": False,
            "error": f"Agent '{agent_id}' not found",
        }
    
    config = _custom_agent_configs.get(agent_id, {})
    has_root = _agent_root_access.get(agent_id, False)
    
    agent_node = _get_agent_graph()["nodes"][agent_id]
    
    return {
        "success": True,
        "agent_id": agent_id,
        "agent_name": agent_node.get("name", "Unknown"),
        "capabilities": config.get("capabilities", ["standard"]),
        "root_access": has_root,
        "priority": config.get("priority", "normal"),
        "custom_instructions": config.get("custom_instructions"),
        "created_at": config.get("created_at"),
        "status": agent_node.get("status", "unknown"),
        "task": agent_node.get("task", ""),
    }


@register_tool(sandbox_execution=False)
def update_agent_capabilities(
    agent_state: Any,
    target_agent_id: str,
    capabilities: list[str] | None = None,
    priority: Literal["low", "normal", "high", "critical"] | None = None,
    custom_instructions: str | None = None,
) -> dict[str, Any]:
    """
    Update the capabilities and configuration of a running agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: ID of agent to update
        capabilities: New capability list (replaces existing)
        priority: New priority level
        custom_instructions: Additional instructions to inject
    
    Returns:
        Dictionary with update status
    """
    if target_agent_id not in _get_agent_graph()["nodes"]:
        return {
            "success": False,
            "error": f"Agent '{target_agent_id}' not found",
        }
    
    # Initialize config if not exists
    if target_agent_id not in _custom_agent_configs:
        _custom_agent_configs[target_agent_id] = {
            "capabilities": ["standard"],
            "root_access": False,
            "priority": "normal",
            "custom_instructions": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
    
    config = _custom_agent_configs[target_agent_id]
    updates = []
    
    if capabilities is not None:
        config["capabilities"] = capabilities
        updates.append(f"capabilities={capabilities}")
    
    if priority is not None:
        config["priority"] = priority
        updates.append(f"priority={priority}")
    
    if custom_instructions is not None:
        config["custom_instructions"] = custom_instructions
        updates.append("custom_instructions=updated")
        
        # Send instructions to the agent via message
        if target_agent_id in _get_agent_messages():
            from uuid import uuid4
            
            _get_agent_messages()[target_agent_id].append({
                "id": f"cap_update_{uuid4().hex[:8]}",
                "from": agent_state.agent_id,
                "to": target_agent_id,
                "content": f"<capability_update>\n{custom_instructions}\n</capability_update>",
                "message_type": "instruction",
                "priority": "high",
                "timestamp": datetime.now(UTC).isoformat(),
                "delivered": True,
                "read": False,
            })
    
    return {
        "success": True,
        "agent_id": target_agent_id,
        "updates": updates,
        "current_config": config,
    }


@register_tool(sandbox_execution=False)
def list_custom_agents(agent_state: Any) -> dict[str, Any]:
    """
    List all custom agents created by the system with their configurations.
    
    Returns:
        Dictionary with list of custom agents and their details
    """
    agents = []
    agent_graph = _get_agent_graph()
    
    for agent_id, config in _custom_agent_configs.items():
        node = agent_graph["nodes"].get(agent_id, {})
        agents.append({
            "agent_id": agent_id,
            "name": node.get("name", "Unknown"),
            "status": node.get("status", "unknown"),
            "task": node.get("task", ""),
            "root_access": _agent_root_access.get(agent_id, False),
            "priority": config.get("priority", "normal"),
            "capabilities": config.get("capabilities", []),
            "created_at": config.get("created_at"),
            "parent_id": config.get("parent_id"),
        })
    
    # Sort by creation time
    agents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "success": True,
        "total_count": len(agents),
        "agents": agents,
        "root_enabled_count": sum(1 for a in agents if a.get("root_access")),
    }


@register_tool(sandbox_execution=False)
def terminate_custom_agent(
    agent_state: Any,
    target_agent_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Terminate a custom agent.
    
    Args:
        agent_state: Current agent's state
        target_agent_id: ID of agent to terminate
        force: If True, force immediate termination
    
    Returns:
        Dictionary with termination status
    """
    from strix.tools.agents_graph.agents_graph_actions import stop_agent
    
    result = stop_agent(target_agent_id)
    
    # Clean up custom config
    if result.get("success"):
        _custom_agent_configs.pop(target_agent_id, None)
        _agent_root_access.pop(target_agent_id, None)
    
    return result


@register_tool(sandbox_execution=False)
def grant_root_access(
    agent_state: Any,
    target_agent_id: str,
) -> dict[str, Any]:
    """
    Grant root terminal access to an existing agent.
    
    Args:
        agent_state: Current agent's state (must be parent or root agent)
        target_agent_id: ID of agent to grant root access to
    
    Returns:
        Dictionary with grant status
    """
    if target_agent_id not in _get_agent_graph()["nodes"]:
        return {
            "success": False,
            "error": f"Agent '{target_agent_id}' not found",
        }
    
    # Check if caller has authority (is parent or root agent)
    caller_id = agent_state.agent_id
    target_node = _get_agent_graph()["nodes"][target_agent_id]
    
    if target_node.get("parent_id") != caller_id and agent_state.parent_id is not None:
        return {
            "success": False,
            "error": "Only the parent agent or root agent can grant root access",
        }
    
    _agent_root_access[target_agent_id] = True
    
    # Update config
    if target_agent_id not in _custom_agent_configs:
        _custom_agent_configs[target_agent_id] = {
            "capabilities": ["root_terminal"],
            "root_access": True,
            "priority": "normal",
            "created_at": datetime.now(UTC).isoformat(),
        }
    else:
        _custom_agent_configs[target_agent_id]["root_access"] = True
        if "root_terminal" not in _custom_agent_configs[target_agent_id].get("capabilities", []):
            _custom_agent_configs[target_agent_id].setdefault("capabilities", []).append("root_terminal")
    
    # Notify the agent
    if target_agent_id not in _get_agent_messages():
        _get_agent_messages()[target_agent_id] = []
    
    from uuid import uuid4
    
    _get_agent_messages()[target_agent_id].append({
        "id": f"root_grant_{uuid4().hex[:8]}",
        "from": caller_id,
        "to": target_agent_id,
        "content": """<root_access_granted>
You have been granted ROOT TERMINAL ACCESS.

You can now use the root_execute tool for privileged operations:
- Install packages: root_execute with apt-get, pip, npm
- Manage services: root_execute with systemctl/service
- Create databases: use create_database tool
- Execute privileged scripts: use run_script tool
- Full file system access

Use this access responsibly.
</root_access_granted>""",
        "message_type": "instruction",
        "priority": "urgent",
        "timestamp": datetime.now(UTC).isoformat(),
        "delivered": True,
        "read": False,
    })
    
    return {
        "success": True,
        "agent_id": target_agent_id,
        "message": f"Root access granted to agent '{target_node.get('name', target_agent_id)}'",
        "agent_notified": True,
    }


@register_tool(sandbox_execution=False)
def revoke_root_access(
    agent_state: Any,
    target_agent_id: str,
) -> dict[str, Any]:
    """
    Revoke root terminal access from an agent.
    
    Args:
        agent_state: Current agent's state (must be parent or root agent)
        target_agent_id: ID of agent to revoke root access from
    
    Returns:
        Dictionary with revocation status
    """
    if target_agent_id not in _get_agent_graph()["nodes"]:
        return {
            "success": False,
            "error": f"Agent '{target_agent_id}' not found",
        }
    
    # Check if caller has authority
    caller_id = agent_state.agent_id
    target_node = _get_agent_graph()["nodes"][target_agent_id]
    
    if target_node.get("parent_id") != caller_id and agent_state.parent_id is not None:
        return {
            "success": False,
            "error": "Only the parent agent or root agent can revoke root access",
        }
    
    had_access = _agent_root_access.pop(target_agent_id, False)
    
    # Update config
    if target_agent_id in _custom_agent_configs:
        _custom_agent_configs[target_agent_id]["root_access"] = False
        caps = _custom_agent_configs[target_agent_id].get("capabilities", [])
        if "root_terminal" in caps:
            caps.remove("root_terminal")
    
    # Notify the agent
    if target_agent_id not in _get_agent_messages():
        _get_agent_messages()[target_agent_id] = []
    
    from uuid import uuid4
    
    _get_agent_messages()[target_agent_id].append({
        "id": f"root_revoke_{uuid4().hex[:8]}",
        "from": caller_id,
        "to": target_agent_id,
        "content": """<root_access_revoked>
Your ROOT TERMINAL ACCESS has been revoked.

You can no longer use the root_execute tool for privileged operations.
Use the standard terminal_execute tool for unprivileged commands.
</root_access_revoked>""",
        "message_type": "instruction",
        "priority": "urgent",
        "timestamp": datetime.now(UTC).isoformat(),
        "delivered": True,
        "read": False,
    })
    
    return {
        "success": True,
        "agent_id": target_agent_id,
        "had_access": had_access,
        "message": f"Root access revoked from agent '{target_node.get('name', target_agent_id)}'",
        "agent_notified": True,
    }
