"""
Root Terminal Tools - Enhanced terminal functionality with root access capabilities.

This module provides:
- Root-accessed terminal sessions for the Main AI
- Multiple temporary root terminals (up to 7)
- Full system access for installing tools, libraries, databases, and scripts
"""

from .root_terminal_actions import (
    root_execute,
    create_root_terminal,
    list_root_terminals,
    close_root_terminal,
    close_all_root_terminals,
    get_root_terminal_status,
    install_package,
    install_pip_package,
    install_npm_package,
    run_script,
    create_database,
    manage_service,
)

__all__ = [
    "root_execute",
    "create_root_terminal",
    "list_root_terminals",
    "close_root_terminal",
    "close_all_root_terminals",
    "get_root_terminal_status",
    "install_package",
    "install_pip_package",
    "install_npm_package",
    "run_script",
    "create_database",
    "manage_service",
]
