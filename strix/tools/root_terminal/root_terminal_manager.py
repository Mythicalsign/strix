"""
Root Terminal Manager - Manages multiple root-accessed terminal sessions.

This module provides:
- Management of up to 7 temporary root terminals
- Root access capabilities for installing tools, libraries, and databases
- Full system control for the Main AI agent
"""

import atexit
import contextlib
import logging
import signal
import sys
import threading
from typing import Any

from .root_terminal_session import RootTerminalSession


logger = logging.getLogger(__name__)


class RootTerminalManager:
    """
    Manages root-accessed terminal sessions with enhanced capabilities.
    
    Features:
    - Up to 7 temporary root terminals
    - Default root terminal always available
    - Full root access for system operations
    - Package/tool installation capabilities
    - Database management
    - Service control
    """
    
    MAX_TEMPORARY_TERMINALS = 7
    DEFAULT_TERMINAL_ID = "root_default"
    
    def __init__(self) -> None:
        self.sessions: dict[str, RootTerminalSession] = {}
        self._lock = threading.Lock()
        self.default_terminal_id = self.DEFAULT_TERMINAL_ID
        self.default_timeout = 60.0  # Longer timeout for root operations
        self._temporary_terminal_ids: list[str] = []
        
        self._register_cleanup_handlers()
        
        # Create default root terminal
        self._get_or_create_session(self.default_terminal_id)
    
    def execute_command(
        self,
        command: str,
        is_input: bool = False,
        timeout: float | None = None,
        terminal_id: str | None = None,
        no_enter: bool = False,
        use_sudo: bool = True,  # Root operations use sudo by default
    ) -> dict[str, Any]:
        """Execute a command with root privileges."""
        if terminal_id is None:
            terminal_id = self.default_terminal_id
        
        # Validate terminal ID exists or create if allowed
        if terminal_id != self.default_terminal_id and terminal_id not in self.sessions:
            if terminal_id not in self._temporary_terminal_ids:
                return {
                    "error": f"Terminal '{terminal_id}' does not exist. Create it first with create_root_terminal.",
                    "command": command,
                    "terminal_id": terminal_id,
                    "content": "",
                    "status": "error",
                    "exit_code": None,
                    "working_dir": None,
                }
        
        session = self._get_or_create_session(terminal_id)
        
        # Prepend sudo for commands that need root (unless already has sudo)
        if use_sudo and not command.strip().startswith("sudo ") and not is_input:
            # Skip sudo for safe read-only commands
            safe_commands = ["ls", "cat", "pwd", "cd", "echo", "env", "which", "whoami", "id", "ps", "top", "df", "du", "find", "grep", "head", "tail", "less", "more", "file", "stat"]
            first_word = command.strip().split()[0] if command.strip() else ""
            if first_word not in safe_commands:
                command = f"sudo {command}"
        
        try:
            result = session.execute(command, is_input, timeout or self.default_timeout, no_enter)
            
            return {
                "content": result["content"],
                "command": command,
                "terminal_id": terminal_id,
                "status": result["status"],
                "exit_code": result.get("exit_code"),
                "working_dir": result.get("working_dir"),
                "is_root": True,
            }
        
        except RuntimeError as e:
            return {
                "error": str(e),
                "command": command,
                "terminal_id": terminal_id,
                "content": "",
                "status": "error",
                "exit_code": None,
                "working_dir": None,
                "is_root": True,
            }
        except OSError as e:
            return {
                "error": f"System error: {e}",
                "command": command,
                "terminal_id": terminal_id,
                "content": "",
                "status": "error",
                "exit_code": None,
                "working_dir": None,
                "is_root": True,
            }
    
    def create_temporary_terminal(self, terminal_name: str | None = None) -> dict[str, Any]:
        """Create a new temporary root terminal (up to 7)."""
        with self._lock:
            if len(self._temporary_terminal_ids) >= self.MAX_TEMPORARY_TERMINALS:
                return {
                    "success": False,
                    "error": f"Maximum number of temporary terminals ({self.MAX_TEMPORARY_TERMINALS}) reached. Close some terminals first.",
                    "active_terminals": len(self._temporary_terminal_ids),
                    "max_terminals": self.MAX_TEMPORARY_TERMINALS,
                }
            
            # Generate terminal ID
            terminal_num = len(self._temporary_terminal_ids) + 1
            terminal_id = f"root_temp_{terminal_num}" if terminal_name is None else f"root_{terminal_name}"
            
            # Ensure unique ID
            while terminal_id in self.sessions or terminal_id in self._temporary_terminal_ids:
                terminal_num += 1
                terminal_id = f"root_temp_{terminal_num}" if terminal_name is None else f"root_{terminal_name}_{terminal_num}"
            
            self._temporary_terminal_ids.append(terminal_id)
        
        # Create the session
        session = self._get_or_create_session(terminal_id)
        
        return {
            "success": True,
            "terminal_id": terminal_id,
            "message": f"Root terminal '{terminal_id}' created successfully",
            "active_terminals": len(self._temporary_terminal_ids),
            "max_terminals": self.MAX_TEMPORARY_TERMINALS,
            "remaining_slots": self.MAX_TEMPORARY_TERMINALS - len(self._temporary_terminal_ids),
            "working_dir": session.get_working_dir(),
            "is_root": True,
        }
    
    def _get_or_create_session(self, terminal_id: str) -> RootTerminalSession:
        """Get existing session or create new one."""
        with self._lock:
            if terminal_id not in self.sessions:
                self.sessions[terminal_id] = RootTerminalSession(terminal_id)
            return self.sessions[terminal_id]
    
    def close_session(self, terminal_id: str) -> dict[str, Any]:
        """Close a specific terminal session."""
        if terminal_id == self.default_terminal_id:
            return {
                "success": False,
                "error": "Cannot close the default root terminal. It is always available.",
                "terminal_id": terminal_id,
            }
        
        with self._lock:
            if terminal_id not in self.sessions:
                return {
                    "terminal_id": terminal_id,
                    "message": f"Terminal '{terminal_id}' not found",
                    "status": "not_found",
                }
            
            session = self.sessions.pop(terminal_id)
            if terminal_id in self._temporary_terminal_ids:
                self._temporary_terminal_ids.remove(terminal_id)
        
        try:
            session.close()
        except (RuntimeError, OSError) as e:
            return {
                "terminal_id": terminal_id,
                "error": f"Failed to close terminal '{terminal_id}': {e}",
                "status": "error",
            }
        else:
            return {
                "terminal_id": terminal_id,
                "message": f"Root terminal '{terminal_id}' closed successfully",
                "status": "closed",
                "remaining_terminals": len(self._temporary_terminal_ids),
            }
    
    def close_all_temporary_terminals(self) -> dict[str, Any]:
        """Close all temporary terminals (keeps default)."""
        closed = []
        errors = []
        
        with self._lock:
            terminals_to_close = list(self._temporary_terminal_ids)
        
        for terminal_id in terminals_to_close:
            result = self.close_session(terminal_id)
            if result.get("status") == "closed":
                closed.append(terminal_id)
            else:
                errors.append({"terminal_id": terminal_id, "error": result.get("error", "Unknown error")})
        
        return {
            "success": len(errors) == 0,
            "closed_terminals": closed,
            "errors": errors,
            "remaining_slots": self.MAX_TEMPORARY_TERMINALS,
            "default_terminal_active": self.default_terminal_id in self.sessions,
        }
    
    def list_sessions(self) -> dict[str, Any]:
        """List all active terminal sessions."""
        with self._lock:
            session_info: dict[str, dict[str, Any]] = {}
            for tid, session in self.sessions.items():
                session_info[tid] = {
                    "is_running": session.is_running(),
                    "working_dir": session.get_working_dir(),
                    "is_default": tid == self.default_terminal_id,
                    "is_temporary": tid in self._temporary_terminal_ids,
                    "is_root": True,
                }
        
        return {
            "sessions": session_info,
            "total_count": len(session_info),
            "temporary_count": len(self._temporary_terminal_ids),
            "max_temporary": self.MAX_TEMPORARY_TERMINALS,
            "available_slots": self.MAX_TEMPORARY_TERMINALS - len(self._temporary_terminal_ids),
        }
    
    def get_terminal_status(self, terminal_id: str | None = None) -> dict[str, Any]:
        """Get detailed status of a terminal."""
        if terminal_id is None:
            terminal_id = self.default_terminal_id
        
        with self._lock:
            if terminal_id not in self.sessions:
                return {
                    "error": f"Terminal '{terminal_id}' not found",
                    "terminal_id": terminal_id,
                }
            
            session = self.sessions[terminal_id]
            return {
                "terminal_id": terminal_id,
                "is_running": session.is_running(),
                "working_dir": session.get_working_dir(),
                "is_default": terminal_id == self.default_terminal_id,
                "is_temporary": terminal_id in self._temporary_terminal_ids,
                "is_root": True,
            }
    
    def cleanup_dead_sessions(self) -> None:
        """Clean up any dead sessions."""
        with self._lock:
            dead_sessions: list[str] = []
            for tid, session in self.sessions.items():
                if not session.is_running() and tid != self.default_terminal_id:
                    dead_sessions.append(tid)
            
            for tid in dead_sessions:
                session = self.sessions.pop(tid)
                if tid in self._temporary_terminal_ids:
                    self._temporary_terminal_ids.remove(tid)
                with contextlib.suppress(Exception):
                    session.close()
    
    def close_all_sessions(self) -> None:
        """Close all sessions including default."""
        with self._lock:
            sessions_to_close = list(self.sessions.values())
            self.sessions.clear()
            self._temporary_terminal_ids.clear()
        
        for session in sessions_to_close:
            with contextlib.suppress(Exception):
                session.close()
    
    def _register_cleanup_handlers(self) -> None:
        """Register cleanup handlers for graceful shutdown."""
        atexit.register(self.close_all_sessions)
        
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _signal_handler(self, _signum: int, _frame: Any) -> None:
        """Handle termination signals."""
        self.close_all_sessions()
        sys.exit(0)


# Global singleton instance
_root_terminal_manager: RootTerminalManager | None = None


def get_root_terminal_manager() -> RootTerminalManager:
    """Get the global root terminal manager instance."""
    global _root_terminal_manager
    if _root_terminal_manager is None:
        _root_terminal_manager = RootTerminalManager()
    return _root_terminal_manager
