"""
Root Terminal Actions - Tool functions for root-accessed terminal operations.

This module provides registered tools for:
- Root command execution
- Package installation (apt, pip, npm, etc.)
- Database creation and management
- Service management
- Script execution with elevated privileges
- Multiple temporary root terminals (up to 7)
"""

from typing import Any

from strix.tools.registry import register_tool


@register_tool
def root_execute(
    command: str,
    is_input: bool = False,
    timeout: float | None = None,
    terminal_id: str | None = None,
    no_enter: bool = False,
    use_sudo: bool = True,
) -> dict[str, Any]:
    """
    Execute a command with root/sudo privileges.
    
    This is the primary command execution tool for the Main AI agent,
    providing full root access to the system.
    
    Args:
        command: The command to execute with root privileges
        is_input: Whether this is input to a running command
        timeout: Execution timeout in seconds (default: 60)
        terminal_id: Specific terminal to use (default: root_default)
        no_enter: If True, don't send Enter after command
        use_sudo: If True, automatically prepend sudo for privileged commands
    
    Returns:
        Dictionary with execution results including output, status, and exit code
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    try:
        return manager.execute_command(
            command=command,
            is_input=is_input,
            timeout=timeout,
            terminal_id=terminal_id,
            no_enter=no_enter,
            use_sudo=use_sudo,
        )
    except (ValueError, RuntimeError) as e:
        return {
            "error": str(e),
            "command": command,
            "terminal_id": terminal_id or "root_default",
            "content": "",
            "status": "error",
            "exit_code": None,
            "working_dir": None,
            "is_root": True,
        }


@register_tool(sandbox_execution=False)
def create_root_terminal(
    terminal_name: str | None = None,
) -> dict[str, Any]:
    """
    Create a new temporary root terminal (up to 7 maximum).
    
    This allows the Main AI to have multiple parallel root terminals
    for concurrent operations.
    
    Args:
        terminal_name: Optional custom name for the terminal
    
    Returns:
        Dictionary with terminal_id and creation status
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    try:
        return manager.create_temporary_terminal(terminal_name)
    except (ValueError, RuntimeError) as e:
        return {
            "success": False,
            "error": str(e),
        }


@register_tool(sandbox_execution=False)
def list_root_terminals() -> dict[str, Any]:
    """
    List all active root terminal sessions.
    
    Returns:
        Dictionary with all terminal sessions and their status
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    return manager.list_sessions()


@register_tool(sandbox_execution=False)
def close_root_terminal(terminal_id: str) -> dict[str, Any]:
    """
    Close a specific root terminal session.
    
    Note: Cannot close the default root terminal.
    
    Args:
        terminal_id: ID of the terminal to close
    
    Returns:
        Dictionary with closure status
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    return manager.close_session(terminal_id)


@register_tool(sandbox_execution=False)
def close_all_root_terminals() -> dict[str, Any]:
    """
    Close all temporary root terminals (keeps default terminal active).
    
    Returns:
        Dictionary with list of closed terminals and status
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    return manager.close_all_temporary_terminals()


@register_tool(sandbox_execution=False)
def get_root_terminal_status(terminal_id: str | None = None) -> dict[str, Any]:
    """
    Get detailed status of a root terminal.
    
    Args:
        terminal_id: Terminal ID to check (default: root_default)
    
    Returns:
        Dictionary with terminal status details
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    return manager.get_terminal_status(terminal_id)


@register_tool
def install_package(
    packages: str,
    update_first: bool = True,
    terminal_id: str | None = None,
) -> dict[str, Any]:
    """
    Install system packages using apt-get with root privileges.
    
    Args:
        packages: Space-separated list of packages to install
        update_first: Whether to run apt-get update first (default: True)
        terminal_id: Terminal to use for installation
    
    Returns:
        Dictionary with installation status and output
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    results = []
    
    # Update package lists if requested
    if update_first:
        update_result = manager.execute_command(
            command="apt-get update -y",
            timeout=120.0,
            terminal_id=terminal_id,
            use_sudo=True,
        )
        results.append({"step": "update", "result": update_result})
        
        if update_result.get("exit_code", 1) != 0:
            return {
                "success": False,
                "error": "Failed to update package lists",
                "details": results,
            }
    
    # Install packages
    install_result = manager.execute_command(
        command=f"apt-get install -y {packages}",
        timeout=300.0,  # 5 minutes for package installation
        terminal_id=terminal_id,
        use_sudo=True,
    )
    results.append({"step": "install", "result": install_result})
    
    success = install_result.get("exit_code", 1) == 0
    
    return {
        "success": success,
        "packages": packages,
        "message": f"Successfully installed: {packages}" if success else f"Failed to install: {packages}",
        "details": results,
    }


@register_tool
def install_pip_package(
    packages: str,
    python_version: str = "python3",
    terminal_id: str | None = None,
) -> dict[str, Any]:
    """
    Install Python packages using pip with root privileges.
    
    Args:
        packages: Space-separated list of packages to install
        python_version: Python interpreter to use (default: python3)
        terminal_id: Terminal to use for installation
    
    Returns:
        Dictionary with installation status and output
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    install_result = manager.execute_command(
        command=f"{python_version} -m pip install {packages}",
        timeout=300.0,
        terminal_id=terminal_id,
        use_sudo=True,
    )
    
    success = install_result.get("exit_code", 1) == 0
    
    return {
        "success": success,
        "packages": packages,
        "python_version": python_version,
        "message": f"Successfully installed: {packages}" if success else f"Failed to install: {packages}",
        "output": install_result.get("content", ""),
        "exit_code": install_result.get("exit_code"),
    }


@register_tool
def install_npm_package(
    packages: str,
    global_install: bool = True,
    terminal_id: str | None = None,
) -> dict[str, Any]:
    """
    Install Node.js packages using npm with root privileges.
    
    Args:
        packages: Space-separated list of packages to install
        global_install: Whether to install globally (default: True)
        terminal_id: Terminal to use for installation
    
    Returns:
        Dictionary with installation status and output
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    global_flag = "-g" if global_install else ""
    install_result = manager.execute_command(
        command=f"npm install {global_flag} {packages}",
        timeout=300.0,
        terminal_id=terminal_id,
        use_sudo=True,
    )
    
    success = install_result.get("exit_code", 1) == 0
    
    return {
        "success": success,
        "packages": packages,
        "global_install": global_install,
        "message": f"Successfully installed: {packages}" if success else f"Failed to install: {packages}",
        "output": install_result.get("content", ""),
        "exit_code": install_result.get("exit_code"),
    }


@register_tool
def run_script(
    script_path: str,
    script_args: str = "",
    interpreter: str | None = None,
    terminal_id: str | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """
    Run a script with root privileges.
    
    Args:
        script_path: Path to the script to execute
        script_args: Arguments to pass to the script
        interpreter: Interpreter to use (auto-detected if None)
        terminal_id: Terminal to use for execution
        timeout: Execution timeout in seconds
    
    Returns:
        Dictionary with execution results
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    # Auto-detect interpreter from file extension if not provided
    if interpreter is None:
        if script_path.endswith(".py"):
            interpreter = "python3"
        elif script_path.endswith(".sh"):
            interpreter = "bash"
        elif script_path.endswith(".rb"):
            interpreter = "ruby"
        elif script_path.endswith(".pl"):
            interpreter = "perl"
        elif script_path.endswith(".js"):
            interpreter = "node"
        else:
            interpreter = "bash"  # Default to bash
    
    command = f"{interpreter} {script_path} {script_args}".strip()
    
    result = manager.execute_command(
        command=command,
        timeout=timeout,
        terminal_id=terminal_id,
        use_sudo=True,
    )
    
    return {
        "success": result.get("exit_code", 1) == 0,
        "script_path": script_path,
        "interpreter": interpreter,
        "arguments": script_args,
        "output": result.get("content", ""),
        "exit_code": result.get("exit_code"),
        "status": result.get("status"),
    }


@register_tool
def create_database(
    db_type: str,
    db_name: str,
    db_user: str | None = None,
    db_password: str | None = None,
    terminal_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a database with root privileges.
    
    Supports: mysql, postgresql, sqlite, mongodb
    
    Args:
        db_type: Database type (mysql, postgresql, sqlite, mongodb)
        db_name: Name of the database to create
        db_user: Optional username for database access
        db_password: Optional password for database user
        terminal_id: Terminal to use for database creation
    
    Returns:
        Dictionary with creation status and connection details
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    results = []
    
    db_type = db_type.lower()
    
    if db_type == "sqlite":
        # SQLite just needs a file
        result = manager.execute_command(
            command=f"touch /workspace/{db_name}.db && chmod 666 /workspace/{db_name}.db",
            terminal_id=terminal_id,
            use_sudo=True,
        )
        results.append({"step": "create_db", "result": result})
        
        return {
            "success": result.get("exit_code", 1) == 0,
            "db_type": "sqlite",
            "db_name": db_name,
            "db_path": f"/workspace/{db_name}.db",
            "connection_string": f"sqlite:///workspace/{db_name}.db",
            "details": results,
        }
    
    elif db_type in ("mysql", "mariadb"):
        # Start MySQL service if not running
        start_result = manager.execute_command(
            command="service mysql start || service mariadb start",
            terminal_id=terminal_id,
            timeout=60.0,
            use_sudo=True,
        )
        results.append({"step": "start_service", "result": start_result})
        
        # Create database
        create_result = manager.execute_command(
            command=f"mysql -e 'CREATE DATABASE IF NOT EXISTS {db_name};'",
            terminal_id=terminal_id,
            use_sudo=True,
        )
        results.append({"step": "create_db", "result": create_result})
        
        # Create user if specified
        if db_user and db_password:
            user_result = manager.execute_command(
                command=f"mysql -e \"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'; GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost'; FLUSH PRIVILEGES;\"",
                terminal_id=terminal_id,
                use_sudo=True,
            )
            results.append({"step": "create_user", "result": user_result})
        
        success = create_result.get("exit_code", 1) == 0
        
        return {
            "success": success,
            "db_type": "mysql",
            "db_name": db_name,
            "db_user": db_user,
            "connection_string": f"mysql://{db_user}:{db_password}@localhost/{db_name}" if db_user else f"mysql://localhost/{db_name}",
            "details": results,
        }
    
    elif db_type in ("postgresql", "postgres", "pg"):
        # Start PostgreSQL service
        start_result = manager.execute_command(
            command="service postgresql start",
            terminal_id=terminal_id,
            timeout=60.0,
            use_sudo=True,
        )
        results.append({"step": "start_service", "result": start_result})
        
        # Create database
        create_result = manager.execute_command(
            command=f"su - postgres -c \"psql -c 'CREATE DATABASE {db_name};'\" || true",
            terminal_id=terminal_id,
            use_sudo=True,
        )
        results.append({"step": "create_db", "result": create_result})
        
        # Create user if specified
        if db_user and db_password:
            user_result = manager.execute_command(
                command=f"su - postgres -c \"psql -c \\\"CREATE USER {db_user} WITH PASSWORD '{db_password}'; GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\\\"\" || true",
                terminal_id=terminal_id,
                use_sudo=True,
            )
            results.append({"step": "create_user", "result": user_result})
        
        return {
            "success": True,  # PostgreSQL commands may show "already exists" but succeed
            "db_type": "postgresql",
            "db_name": db_name,
            "db_user": db_user,
            "connection_string": f"postgresql://{db_user}:{db_password}@localhost/{db_name}" if db_user else f"postgresql://localhost/{db_name}",
            "details": results,
        }
    
    elif db_type == "mongodb":
        # Start MongoDB service
        start_result = manager.execute_command(
            command="service mongod start || mongod --fork --logpath /var/log/mongodb.log",
            terminal_id=terminal_id,
            timeout=60.0,
            use_sudo=True,
        )
        results.append({"step": "start_service", "result": start_result})
        
        # MongoDB creates database on first use
        return {
            "success": True,
            "db_type": "mongodb",
            "db_name": db_name,
            "connection_string": f"mongodb://localhost:27017/{db_name}",
            "note": "MongoDB creates the database automatically on first write",
            "details": results,
        }
    
    else:
        return {
            "success": False,
            "error": f"Unsupported database type: {db_type}. Supported: mysql, postgresql, sqlite, mongodb",
        }


@register_tool
def manage_service(
    service_name: str,
    action: str,
    terminal_id: str | None = None,
) -> dict[str, Any]:
    """
    Manage system services with root privileges.
    
    Args:
        service_name: Name of the service to manage
        action: Action to perform (start, stop, restart, status, enable, disable)
        terminal_id: Terminal to use for service management
    
    Returns:
        Dictionary with service action result
    """
    from .root_terminal_manager import get_root_terminal_manager
    
    manager = get_root_terminal_manager()
    
    valid_actions = ["start", "stop", "restart", "status", "enable", "disable"]
    if action not in valid_actions:
        return {
            "success": False,
            "error": f"Invalid action: {action}. Valid actions: {', '.join(valid_actions)}",
        }
    
    # Try systemctl first, fall back to service command
    result = manager.execute_command(
        command=f"systemctl {action} {service_name} 2>/dev/null || service {service_name} {action}",
        terminal_id=terminal_id,
        timeout=60.0,
        use_sudo=True,
    )
    
    success = result.get("exit_code", 1) == 0 or action == "status"
    
    return {
        "success": success,
        "service_name": service_name,
        "action": action,
        "output": result.get("content", ""),
        "exit_code": result.get("exit_code"),
    }
