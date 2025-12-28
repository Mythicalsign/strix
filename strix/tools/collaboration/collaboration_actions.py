"""
Multi-Agent Collaboration Protocol Actions.

This module enables efficient collaboration between multiple AI agents during
security testing, preventing duplicate effort and enabling vulnerability chaining.

Key Systems:
1. CLAIM SYSTEM - Prevent duplicate testing by claiming targets
2. FINDING SHARING - Share vulnerabilities for chaining opportunities
3. WORK QUEUE - Central queue for coordinated testing coverage
4. HELP REQUESTS - Request specialized assistance from other agents
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from strix.tools.registry import register_tool


# =============================================================================
# Data Structures
# =============================================================================

# Claims: agent_id -> list of claimed targets
_claims: dict[str, list[dict[str, Any]]] = {}

# Findings: shared vulnerability findings for chaining
_findings: dict[str, dict[str, Any]] = {}

# Work Queue: central queue of targets to test
_work_queue: list[dict[str, Any]] = []

# Help Requests: requests for specialized assistance
_help_requests: list[dict[str, Any]] = []

# Messages: broadcast messages between agents
_messages: list[dict[str, Any]] = []

# Statistics
_collaboration_stats: dict[str, Any] = {
    "total_claims": 0,
    "total_findings": 0,
    "total_work_items": 0,
    "total_help_requests": 0,
    "total_broadcasts": 0,
    "duplicate_tests_prevented": 0,
    "chaining_opportunities": 0,
    "start_time": datetime.now(UTC).isoformat(),
}


def _generate_id(prefix: str = "id") -> str:
    """Generate a unique identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _get_agent_info(agent_state: Any) -> dict[str, str]:
    """Extract agent information from state."""
    return {
        "agent_id": getattr(agent_state, "agent_id", "unknown"),
        "agent_name": getattr(agent_state, "agent_name", "Unknown Agent"),
    }


# =============================================================================
# Target Claiming System
# =============================================================================

@register_tool(sandbox_execution=False)
def claim_target(
    agent_state: Any,
    target: str,
    test_type: str,
    scope: str | None = None,
    estimated_duration: int = 30,
    priority: Literal["critical", "high", "medium", "low"] = "medium",
) -> dict[str, Any]:
    """
    Claim an endpoint or parameter for testing to prevent duplicate work.
    
    Before testing any target, claim it first to ensure no other agent
    is already testing the same thing. This prevents wasted effort and
    ensures complete coverage.
    
    Args:
        agent_state: Current agent's state
        target: The target to claim (URL, endpoint, parameter)
        test_type: Type of test (sqli, xss, ssrf, auth_bypass, idor, etc.)
        scope: Optional scope description (e.g., "login form", "api endpoint")
        estimated_duration: Estimated test duration in minutes (default: 30)
        priority: Test priority level
    
    Returns:
        Dictionary with claim status. If already claimed, returns the claiming agent's info.
    
    Example:
        # Claim /login endpoint for SQL injection testing
        claim_target(agent_state, "/login", "sqli", scope="authentication")
        
        # Claim specific parameter for XSS testing
        claim_target(agent_state, "/search?q=", "xss", scope="search parameter")
    """
    agent_info = _get_agent_info(agent_state)
    claim_key = f"{target}:{test_type}"
    
    # Check if already claimed by any agent
    for agent_id, claims in _claims.items():
        for claim in claims:
            if claim.get("claim_key") == claim_key:
                if claim.get("status") == "active":
                    # Check if claim has expired (2x estimated duration)
                    claimed_at = datetime.fromisoformat(claim["claimed_at"])
                    expiry_minutes = claim.get("estimated_duration", 30) * 2
                    if datetime.now(UTC) - claimed_at < timedelta(minutes=expiry_minutes):
                        _collaboration_stats["duplicate_tests_prevented"] += 1
                        return {
                            "success": False,
                            "status": "already_claimed",
                            "claimed_by": {
                                "agent_id": agent_id,
                                "agent_name": claim.get("agent_name"),
                            },
                            "claimed_at": claim["claimed_at"],
                            "test_type": claim["test_type"],
                            "message": f"Target already being tested by {claim.get('agent_name', agent_id)}. "
                                       f"Consider testing a different vulnerability type or target.",
                            "suggestion": f"Try a different test_type (currently claimed for: {test_type})",
                        }
                    else:
                        # Claim expired, release it
                        claim["status"] = "expired"
    
    # Create new claim
    claim_id = _generate_id("claim")
    new_claim = {
        "claim_id": claim_id,
        "claim_key": claim_key,
        "target": target,
        "test_type": test_type,
        "scope": scope,
        "agent_id": agent_info["agent_id"],
        "agent_name": agent_info["agent_name"],
        "priority": priority,
        "estimated_duration": estimated_duration,
        "status": "active",
        "claimed_at": datetime.now(UTC).isoformat(),
        "results": None,
    }
    
    if agent_info["agent_id"] not in _claims:
        _claims[agent_info["agent_id"]] = []
    
    _claims[agent_info["agent_id"]].append(new_claim)
    _collaboration_stats["total_claims"] += 1
    
    return {
        "success": True,
        "status": "claimed",
        "claim_id": claim_id,
        "target": target,
        "test_type": test_type,
        "scope": scope,
        "priority": priority,
        "estimated_duration": estimated_duration,
        "message": f"Successfully claimed {target} for {test_type} testing",
        "reminder": "Remember to call release_claim() when done, and share_finding() if you find something!",
    }


@register_tool(sandbox_execution=False)
def release_claim(
    agent_state: Any,
    claim_id: str | None = None,
    target: str | None = None,
    test_type: str | None = None,
    result: str | None = None,
    finding_id: str | None = None,
) -> dict[str, Any]:
    """
    Release a claim on a target after completing testing.
    
    Always release claims when done testing to allow other agents
    to test the same target with different techniques.
    
    Args:
        agent_state: Current agent's state
        claim_id: The claim ID to release (preferred)
        target: Target that was claimed (alternative to claim_id)
        test_type: Test type that was claimed (used with target)
        result: Brief description of test results
        finding_id: If a vulnerability was found, link the finding ID
    
    Returns:
        Dictionary with release status.
    
    Example:
        release_claim(agent_state, claim_id="claim_abc123", result="No SQL injection found")
        release_claim(agent_state, target="/login", test_type="sqli", finding_id="finding_xyz")
    """
    agent_info = _get_agent_info(agent_state)
    agent_claims = _claims.get(agent_info["agent_id"], [])
    
    released = False
    released_claim = None
    
    for claim in agent_claims:
        should_release = False
        
        if claim_id and claim.get("claim_id") == claim_id:
            should_release = True
        elif target and test_type:
            if claim.get("target") == target and claim.get("test_type") == test_type:
                should_release = True
        
        if should_release and claim.get("status") == "active":
            claim["status"] = "completed"
            claim["released_at"] = datetime.now(UTC).isoformat()
            claim["results"] = result
            claim["finding_id"] = finding_id
            released = True
            released_claim = claim
            break
    
    if released and released_claim:
        return {
            "success": True,
            "status": "released",
            "claim_id": released_claim["claim_id"],
            "target": released_claim["target"],
            "test_type": released_claim["test_type"],
            "duration_minutes": _calculate_duration(released_claim["claimed_at"]),
            "had_finding": finding_id is not None,
            "message": "Claim released successfully",
        }
    
    return {
        "success": False,
        "error": "Claim not found or already released",
        "searched_for": {
            "claim_id": claim_id,
            "target": target,
            "test_type": test_type,
        },
    }


def _calculate_duration(start_time: str) -> int:
    """Calculate duration in minutes from start time."""
    try:
        start = datetime.fromisoformat(start_time)
        return int((datetime.now(UTC) - start).total_seconds() / 60)
    except (ValueError, TypeError):
        return 0


@register_tool(sandbox_execution=False)
def list_claims(
    agent_state: Any,
    status: str | None = None,
    test_type: str | None = None,
    agent_filter: str | None = None,
) -> dict[str, Any]:
    """
    List all current claims to see what's being tested.
    
    Use this to find unclaimed targets or see what other agents
    are working on to avoid duplicate effort.
    
    Args:
        agent_state: Current agent's state
        status: Filter by status (active, completed, expired)
        test_type: Filter by test type
        agent_filter: Filter by specific agent ID
    
    Returns:
        Dictionary with all claims and statistics.
    """
    all_claims = []
    
    for agent_id, claims in _claims.items():
        for claim in claims:
            # Apply filters
            if status and claim.get("status") != status:
                continue
            if test_type and claim.get("test_type") != test_type:
                continue
            if agent_filter and agent_id != agent_filter:
                continue
            
            all_claims.append({
                "claim_id": claim["claim_id"],
                "target": claim["target"],
                "test_type": claim["test_type"],
                "scope": claim.get("scope"),
                "agent_id": agent_id,
                "agent_name": claim.get("agent_name"),
                "status": claim["status"],
                "priority": claim.get("priority", "medium"),
                "claimed_at": claim["claimed_at"],
                "finding_id": claim.get("finding_id"),
            })
    
    # Sort by priority and claim time
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_claims.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["claimed_at"]))
    
    # Calculate statistics
    active_claims = [c for c in all_claims if c["status"] == "active"]
    by_test_type: dict[str, int] = {}
    by_agent: dict[str, int] = {}
    
    for claim in active_claims:
        tt = claim["test_type"]
        by_test_type[tt] = by_test_type.get(tt, 0) + 1
        
        aid = claim["agent_id"]
        by_agent[aid] = by_agent.get(aid, 0) + 1
    
    return {
        "success": True,
        "total_claims": len(all_claims),
        "active_claims": len(active_claims),
        "claims": all_claims,
        "statistics": {
            "by_test_type": by_test_type,
            "by_agent": by_agent,
            "duplicate_tests_prevented": _collaboration_stats["duplicate_tests_prevented"],
        },
        "unclaimed_suggestions": _get_unclaimed_suggestions(all_claims),
    }


def _get_unclaimed_suggestions(current_claims: list[dict[str, Any]]) -> list[str]:
    """Generate suggestions for unclaimed test types."""
    common_tests = ["sqli", "xss", "ssrf", "idor", "auth_bypass", "path_traversal", "rce", "xxe"]
    claimed_types = {c["test_type"] for c in current_claims if c["status"] == "active"}
    unclaimed = [t for t in common_tests if t not in claimed_types]
    
    if unclaimed:
        return [f"Consider testing: {', '.join(unclaimed[:5])}"]
    return ["All common test types are currently being tested"]


# =============================================================================
# Finding Sharing System
# =============================================================================

@register_tool(sandbox_execution=False)
def share_finding(
    agent_state: Any,
    title: str,
    vulnerability_type: str,
    target: str,
    description: str,
    severity: Literal["critical", "high", "medium", "low", "info"] = "medium",
    poc: str | None = None,
    evidence: str | None = None,
    chainable: bool = True,
    chain_suggestions: list[str] | None = None,
    affected_parameters: list[str] | None = None,
    remediation: str | None = None,
) -> dict[str, Any]:
    """
    Share a vulnerability finding with all agents for potential chaining.
    
    When you find a vulnerability, share it so other agents can:
    1. Avoid testing the same thing
    2. Try to chain it with their findings
    3. Build on your discovery
    
    Args:
        agent_state: Current agent's state
        title: Brief title of the finding
        vulnerability_type: Type (sqli, xss, ssrf, idor, rce, etc.)
        target: Affected endpoint/parameter
        description: Detailed description of the vulnerability
        severity: Severity level
        poc: Proof of concept (payload, request, etc.)
        evidence: Evidence of exploitation (response, screenshot description)
        chainable: Whether this could be chained with other vulns
        chain_suggestions: Suggested vulns to chain with
        affected_parameters: List of affected parameters
        remediation: Suggested fix
    
    Returns:
        Dictionary with finding ID and sharing status.
    
    Example:
        share_finding(
            agent_state,
            title="SSRF in Image Fetcher",
            vulnerability_type="ssrf",
            target="/api/fetch?url=",
            description="Server-side request forgery allows internal network access",
            severity="high",
            poc="GET /api/fetch?url=http://169.254.169.254/",
            chainable=True,
            chain_suggestions=["idor", "auth_bypass"]
        )
    """
    agent_info = _get_agent_info(agent_state)
    finding_id = _generate_id("finding")
    
    finding = {
        "finding_id": finding_id,
        "title": title,
        "vulnerability_type": vulnerability_type,
        "target": target,
        "description": description,
        "severity": severity,
        "poc": poc,
        "evidence": evidence,
        "chainable": chainable,
        "chain_suggestions": chain_suggestions or [],
        "affected_parameters": affected_parameters or [],
        "remediation": remediation,
        "found_by": {
            "agent_id": agent_info["agent_id"],
            "agent_name": agent_info["agent_name"],
        },
        "found_at": datetime.now(UTC).isoformat(),
        "chain_attempts": [],
        "successfully_chained": False,
    }
    
    _findings[finding_id] = finding
    _collaboration_stats["total_findings"] += 1
    
    if chainable:
        _collaboration_stats["chaining_opportunities"] += 1
    
    # Notify other agents via broadcast
    _broadcast_finding_notification(agent_info, finding)
    
    return {
        "success": True,
        "finding_id": finding_id,
        "title": title,
        "severity": severity,
        "chainable": chainable,
        "message": f"Finding shared successfully! Other agents have been notified.",
        "chain_tips": _generate_chain_tips(vulnerability_type, chain_suggestions),
    }


def _broadcast_finding_notification(agent_info: dict[str, str], finding: dict[str, Any]) -> None:
    """Broadcast a finding notification to all agents."""
    message = {
        "message_id": _generate_id("msg"),
        "type": "finding_notification",
        "from": agent_info,
        "finding_id": finding["finding_id"],
        "title": finding["title"],
        "vulnerability_type": finding["vulnerability_type"],
        "severity": finding["severity"],
        "chainable": finding["chainable"],
        "chain_suggestions": finding.get("chain_suggestions", []),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _messages.append(message)


def _generate_chain_tips(vuln_type: str, suggestions: list[str] | None) -> list[str]:
    """Generate tips for chaining this vulnerability type."""
    tips = []
    
    chain_combos = {
        "ssrf": ["Cloud metadata access", "Internal service discovery", "Bypass IP restrictions"],
        "xss": ["Session hijacking", "CSRF bypass", "Keylogging"],
        "sqli": ["Data exfiltration", "Authentication bypass", "Privilege escalation"],
        "idor": ["Mass data access", "Account takeover", "Privilege escalation"],
        "auth_bypass": ["Account takeover", "Privilege escalation", "Data access"],
        "path_traversal": ["Source code disclosure", "Config file access", "Credential theft"],
        "rce": ["System compromise", "Lateral movement", "Data exfiltration"],
    }
    
    if vuln_type in chain_combos:
        tips.extend([f"Potential chain: {combo}" for combo in chain_combos[vuln_type]])
    
    if suggestions:
        tips.extend([f"Try chaining with: {s}" for s in suggestions])
    
    return tips[:5]  # Limit to 5 tips


@register_tool(sandbox_execution=False)
def list_findings(
    agent_state: Any,
    severity: str | None = None,
    vulnerability_type: str | None = None,
    chainable_only: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """
    List all shared findings for review and potential chaining.
    
    Use this to see what other agents have found and identify
    chaining opportunities.
    
    Args:
        agent_state: Current agent's state
        severity: Filter by severity
        vulnerability_type: Filter by vulnerability type
        chainable_only: Only show chainable findings
        limit: Maximum results
    
    Returns:
        Dictionary with findings list and chaining statistics.
    """
    filtered_findings = []
    
    for finding_id, finding in _findings.items():
        # Apply filters
        if severity and finding.get("severity") != severity:
            continue
        if vulnerability_type and finding.get("vulnerability_type") != vulnerability_type:
            continue
        if chainable_only and not finding.get("chainable"):
            continue
        
        filtered_findings.append({
            "finding_id": finding_id,
            "title": finding["title"],
            "vulnerability_type": finding["vulnerability_type"],
            "target": finding["target"],
            "severity": finding["severity"],
            "chainable": finding.get("chainable", False),
            "chain_suggestions": finding.get("chain_suggestions", []),
            "found_by": finding["found_by"],
            "found_at": finding["found_at"],
            "successfully_chained": finding.get("successfully_chained", False),
        })
    
    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    filtered_findings.sort(key=lambda x: severity_order.get(x["severity"], 5))
    filtered_findings = filtered_findings[:limit]
    
    # Calculate statistics
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    chainable_count = 0
    
    for f in _findings.values():
        sev = f.get("severity", "info")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        
        vt = f.get("vulnerability_type", "unknown")
        by_type[vt] = by_type.get(vt, 0) + 1
        
        if f.get("chainable"):
            chainable_count += 1
    
    return {
        "success": True,
        "total_findings": len(_findings),
        "filtered_count": len(filtered_findings),
        "findings": filtered_findings,
        "statistics": {
            "by_severity": by_severity,
            "by_type": by_type,
            "chainable_findings": chainable_count,
            "chaining_opportunities": _collaboration_stats["chaining_opportunities"],
        },
        "chaining_tips": [
            "Look for SSRF findings to chain with cloud metadata access",
            "XSS can be chained with CSRF bypass for account takeover",
            "IDOR + auth bypass often leads to privilege escalation",
        ],
    }


@register_tool(sandbox_execution=False)
def get_finding_details(agent_state: Any, finding_id: str) -> dict[str, Any]:
    """
    Get full details of a specific finding including PoC.
    
    Use this when you want to understand a finding better or
    use its PoC as a starting point for chaining.
    
    Args:
        agent_state: Current agent's state
        finding_id: The finding ID to retrieve
    
    Returns:
        Dictionary with complete finding details.
    """
    if finding_id not in _findings:
        return {
            "success": False,
            "error": f"Finding '{finding_id}' not found",
        }
    
    finding = _findings[finding_id].copy()
    
    return {
        "success": True,
        "finding": finding,
        "chaining_tips": _generate_chain_tips(
            finding.get("vulnerability_type", ""),
            finding.get("chain_suggestions", [])
        ),
    }


# =============================================================================
# Work Queue System
# =============================================================================

@register_tool(sandbox_execution=False)
def add_to_work_queue(
    agent_state: Any,
    target: str,
    description: str,
    test_types: list[str] | None = None,
    priority: Literal["critical", "high", "medium", "low"] = "medium",
    notes: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """
    Add a target to the central work queue for testing.
    
    Use this when you discover new endpoints or parameters that
    need testing but you can't handle them right now.
    
    Args:
        agent_state: Current agent's state
        target: Target URL, endpoint, or parameter to test
        description: What needs to be tested and why
        test_types: Suggested test types (sqli, xss, etc.)
        priority: Priority level
        notes: Additional notes or context
        source: How this target was discovered
    
    Returns:
        Dictionary with work item details.
    
    Example:
        add_to_work_queue(
            agent_state,
            target="/api/v2/users/{id}",
            description="New API endpoint found in JS bundle",
            test_types=["idor", "auth_bypass"],
            priority="high",
            source="JavaScript analysis"
        )
    """
    agent_info = _get_agent_info(agent_state)
    work_id = _generate_id("work")
    
    work_item = {
        "work_id": work_id,
        "target": target,
        "description": description,
        "test_types": test_types or ["general"],
        "priority": priority,
        "notes": notes,
        "source": source,
        "added_by": agent_info,
        "added_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "assigned_to": None,
        "assigned_at": None,
    }
    
    _work_queue.append(work_item)
    _collaboration_stats["total_work_items"] += 1
    
    # Sort queue by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    _work_queue.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["added_at"]))
    
    return {
        "success": True,
        "work_id": work_id,
        "target": target,
        "priority": priority,
        "queue_position": _work_queue.index(work_item) + 1,
        "message": f"Added to work queue at position {_work_queue.index(work_item) + 1}",
    }


@register_tool(sandbox_execution=False)
def get_next_work_item(
    agent_state: Any,
    preferred_test_types: list[str] | None = None,
    min_priority: str | None = None,
) -> dict[str, Any]:
    """
    Get the next work item from the queue to test.
    
    Use this when you're ready to start testing something new.
    The item will be marked as assigned to you.
    
    Args:
        agent_state: Current agent's state
        preferred_test_types: Preferred test types to match
        min_priority: Minimum priority level to accept
    
    Returns:
        Dictionary with work item details or empty if queue is empty.
    """
    agent_info = _get_agent_info(agent_state)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    
    # Find suitable work item
    for item in _work_queue:
        if item["status"] != "pending":
            continue
        
        # Check priority filter
        if min_priority:
            item_priority = priority_order.get(item["priority"], 2)
            min_pri = priority_order.get(min_priority, 2)
            if item_priority > min_pri:
                continue
        
        # Check test type preference
        if preferred_test_types:
            item_types = set(item.get("test_types", []))
            preferred = set(preferred_test_types)
            if not item_types.intersection(preferred):
                continue
        
        # Assign to this agent
        item["status"] = "assigned"
        item["assigned_to"] = agent_info
        item["assigned_at"] = datetime.now(UTC).isoformat()
        
        return {
            "success": True,
            "work_item": {
                "work_id": item["work_id"],
                "target": item["target"],
                "description": item["description"],
                "test_types": item["test_types"],
                "priority": item["priority"],
                "notes": item.get("notes"),
                "source": item.get("source"),
                "added_by": item["added_by"],
            },
            "message": "Work item assigned to you. Remember to claim specific tests!",
            "next_steps": [
                "1. Review the target and description",
                f"2. Claim specific test types: claim_target(target='{item['target']}', test_type='...')",
                "3. Perform testing",
                "4. Share any findings: share_finding(...)",
                "5. Release claims: release_claim(...)",
            ],
        }
    
    return {
        "success": True,
        "work_item": None,
        "message": "No suitable work items in queue",
        "queue_status": {
            "total_items": len(_work_queue),
            "pending": sum(1 for i in _work_queue if i["status"] == "pending"),
            "assigned": sum(1 for i in _work_queue if i["status"] == "assigned"),
        },
    }


# =============================================================================
# Help Request System
# =============================================================================

@register_tool(sandbox_execution=False)
def request_help(
    agent_state: Any,
    help_type: Literal["decode", "analyze", "exploit", "bypass", "escalate", "other"],
    description: str,
    context: str | None = None,
    data: str | None = None,
    urgency: Literal["critical", "high", "normal", "low"] = "normal",
) -> dict[str, Any]:
    """
    Request specialized help from other agents.
    
    Use this when you encounter something you can't handle alone,
    like encoded data, complex exploits, or unfamiliar technologies.
    
    Args:
        agent_state: Current agent's state
        help_type: Type of help needed
            - decode: Help decoding data (base64, JWT, encrypted)
            - analyze: Help analyzing complex data/responses
            - exploit: Help developing or executing exploit
            - bypass: Help bypassing security controls
            - escalate: Help with privilege escalation
            - other: Other specialized assistance
        description: What you need help with
        context: Where/how you encountered this
        data: Relevant data (encoded string, payload, etc.)
        urgency: How urgent the request is
    
    Returns:
        Dictionary with help request status.
    
    Example:
        request_help(
            agent_state,
            help_type="decode",
            description="Found base64-encoded parameter that seems to contain user data",
            data="eyJ1c2VyIjoiYWRtaW4iLCJyb2xlIjoiZ3Vlc3QifQ==",
            context="Cookie named 'session' on /dashboard"
        )
    """
    agent_info = _get_agent_info(agent_state)
    request_id = _generate_id("help")
    
    help_request = {
        "request_id": request_id,
        "help_type": help_type,
        "description": description,
        "context": context,
        "data": data,
        "urgency": urgency,
        "requested_by": agent_info,
        "requested_at": datetime.now(UTC).isoformat(),
        "status": "open",
        "responses": [],
    }
    
    _help_requests.append(help_request)
    _collaboration_stats["total_help_requests"] += 1
    
    # Broadcast help request
    _broadcast_help_request(agent_info, help_request)
    
    return {
        "success": True,
        "request_id": request_id,
        "help_type": help_type,
        "urgency": urgency,
        "message": "Help request broadcasted to all agents",
        "tips": _generate_help_tips(help_type, data),
    }


def _broadcast_help_request(agent_info: dict[str, str], request: dict[str, Any]) -> None:
    """Broadcast a help request to all agents."""
    message = {
        "message_id": _generate_id("msg"),
        "type": "help_request",
        "from": agent_info,
        "request_id": request["request_id"],
        "help_type": request["help_type"],
        "description": request["description"],
        "urgency": request["urgency"],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _messages.append(message)


def _generate_help_tips(help_type: str, data: str | None) -> list[str]:
    """Generate helpful tips based on help type."""
    tips = []
    
    if help_type == "decode":
        tips.append("Common encodings: Base64, URL encoding, Hex, JWT")
        if data and data.startswith("ey"):
            tips.append("This looks like a JWT token - try jwt.io to decode")
        if data and "%" in str(data):
            tips.append("Contains URL-encoded characters")
    elif help_type == "bypass":
        tips.append("Try case variations, encoding, and payload obfuscation")
        tips.append("Check for WAF fingerprints in responses")
    elif help_type == "escalate":
        tips.append("Look for IDOR vulnerabilities in user references")
        tips.append("Check role/permission parameters for manipulation")
    elif help_type == "exploit":
        tips.append("Search Exploit-DB for known PoCs")
        tips.append("Check GitHub for vulnerability-specific tools")
    
    return tips


# =============================================================================
# Collaboration Status & Communication
# =============================================================================

@register_tool(sandbox_execution=False)
def get_collaboration_status(agent_state: Any) -> dict[str, Any]:
    """
    Get comprehensive collaboration status dashboard.
    
    Use this to get an overview of all collaboration activities,
    pending items, and coordination opportunities.
    
    Args:
        agent_state: Current agent's state
    
    Returns:
        Dictionary with complete collaboration status.
    """
    agent_info = _get_agent_info(agent_state)
    
    # Active claims
    active_claims = []
    for agent_id, claims in _claims.items():
        for claim in claims:
            if claim["status"] == "active":
                active_claims.append({
                    "target": claim["target"],
                    "test_type": claim["test_type"],
                    "agent_name": claim.get("agent_name"),
                    "priority": claim.get("priority"),
                    "claimed_at": claim["claimed_at"],
                })
    
    # My claims
    my_claims = _claims.get(agent_info["agent_id"], [])
    my_active_claims = [c for c in my_claims if c["status"] == "active"]
    
    # Recent findings (last 10)
    recent_findings = sorted(
        _findings.values(),
        key=lambda x: x["found_at"],
        reverse=True
    )[:10]
    
    # Pending work items
    pending_work = [w for w in _work_queue if w["status"] == "pending"][:10]
    
    # Open help requests
    open_help = [h for h in _help_requests if h["status"] == "open"]
    
    # Recent messages
    recent_messages = sorted(
        _messages,
        key=lambda x: x["timestamp"],
        reverse=True
    )[:20]
    
    return {
        "success": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "my_status": {
            "agent_id": agent_info["agent_id"],
            "agent_name": agent_info["agent_name"],
            "active_claims": len(my_active_claims),
            "my_claims": [{
                "target": c["target"],
                "test_type": c["test_type"],
                "claimed_at": c["claimed_at"],
            } for c in my_active_claims],
        },
        "collaboration_overview": {
            "total_active_claims": len(active_claims),
            "total_findings": len(_findings),
            "pending_work_items": len(pending_work),
            "open_help_requests": len(open_help),
        },
        "active_claims": active_claims[:10],
        "recent_findings": [{
            "finding_id": f["finding_id"],
            "title": f["title"],
            "severity": f["severity"],
            "vulnerability_type": f["vulnerability_type"],
            "found_by": f["found_by"]["agent_name"],
            "chainable": f.get("chainable", False),
        } for f in recent_findings],
        "pending_work_queue": [{
            "work_id": w["work_id"],
            "target": w["target"],
            "priority": w["priority"],
            "test_types": w["test_types"],
        } for w in pending_work],
        "open_help_requests": [{
            "request_id": h["request_id"],
            "help_type": h["help_type"],
            "description": h["description"][:100],
            "urgency": h["urgency"],
            "requested_by": h["requested_by"]["agent_name"],
        } for h in open_help],
        "statistics": _collaboration_stats,
        "recommendations": _generate_collaboration_recommendations(
            my_active_claims, recent_findings, pending_work, open_help
        ),
    }


def _generate_collaboration_recommendations(
    my_claims: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    work_queue: list[dict[str, Any]],
    help_requests: list[dict[str, Any]],
) -> list[str]:
    """Generate collaboration recommendations."""
    recommendations = []
    
    if len(my_claims) >= 3:
        recommendations.append("You have many active claims. Consider completing some before claiming more.")
    
    if len(my_claims) == 0 and work_queue:
        recommendations.append("No active claims. Use get_next_work_item() to pick up work from the queue.")
    
    chainable_findings = [f for f in findings if f.get("chainable")]
    if chainable_findings:
        recommendations.append(f"{len(chainable_findings)} chainable findings available. Check for chaining opportunities!")
    
    if help_requests:
        recommendations.append(f"{len(help_requests)} open help requests. Can you assist another agent?")
    
    if not recommendations:
        recommendations.append("Collaboration running smoothly. Keep up the good work!")
    
    return recommendations


@register_tool(sandbox_execution=False)
def broadcast_message(
    agent_state: Any,
    message: str,
    message_type: Literal["info", "warning", "finding", "question", "coordination"] = "info",
    priority: Literal["low", "normal", "high", "urgent"] = "normal",
) -> dict[str, Any]:
    """
    Broadcast a message to all agents.
    
    Use this for important announcements, coordination messages,
    or questions that all agents should see.
    
    Args:
        agent_state: Current agent's state
        message: The message content
        message_type: Type of message
        priority: Message priority
    
    Returns:
        Dictionary with broadcast status.
    """
    agent_info = _get_agent_info(agent_state)
    message_id = _generate_id("msg")
    
    broadcast = {
        "message_id": message_id,
        "type": message_type,
        "from": agent_info,
        "content": message,
        "priority": priority,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    
    _messages.append(broadcast)
    _collaboration_stats["total_broadcasts"] += 1
    
    return {
        "success": True,
        "message_id": message_id,
        "delivered_to": "all_agents",
        "message_type": message_type,
        "priority": priority,
    }
