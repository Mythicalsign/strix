"""
Comprehensive test suite for Multi-Agent Collaboration Protocol module.

Tests cover:
- Target claiming system
- Finding sharing for chaining
- Work queue management
- Help request system
- Collaboration status dashboard
- Broadcast messaging
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

# Import the module under test
from strix.tools.collaboration.collaboration_actions import (
    claim_target,
    release_claim,
    list_claims,
    share_finding,
    list_findings,
    get_finding_details,
    add_to_work_queue,
    get_next_work_item,
    request_help,
    get_collaboration_status,
    broadcast_message,
    _claims,
    _findings,
    _work_queue,
    _help_requests,
    _messages,
    _collaboration_stats,
    _generate_id,
    _get_agent_info,
    _generate_chain_tips,
    _generate_help_tips,
)


# Test fixtures
@pytest.fixture
def mock_agent_state():
    """Create a mock agent state for testing."""
    state = MagicMock()
    state.agent_id = "test_agent_001"
    state.agent_name = "Test Agent"
    return state


@pytest.fixture
def mock_agent_state_2():
    """Create a second mock agent state for multi-agent tests."""
    state = MagicMock()
    state.agent_id = "test_agent_002"
    state.agent_name = "Test Agent 2"
    return state


@pytest.fixture(autouse=True)
def clear_state():
    """Clear all collaboration state before each test."""
    _claims.clear()
    _findings.clear()
    _work_queue.clear()
    _help_requests.clear()
    _messages.clear()
    
    # Reset stats
    _collaboration_stats["total_claims"] = 0
    _collaboration_stats["total_findings"] = 0
    _collaboration_stats["total_work_items"] = 0
    _collaboration_stats["total_help_requests"] = 0
    _collaboration_stats["total_broadcasts"] = 0
    _collaboration_stats["duplicate_tests_prevented"] = 0
    _collaboration_stats["chaining_opportunities"] = 0
    
    yield


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_generate_id_unique(self):
        """Test that generated IDs are unique."""
        ids = [_generate_id("test") for _ in range(100)]
        assert len(set(ids)) == 100
    
    def test_generate_id_prefix(self):
        """Test that generated IDs have correct prefix."""
        id1 = _generate_id("claim")
        id2 = _generate_id("finding")
        
        assert id1.startswith("claim_")
        assert id2.startswith("finding_")
    
    def test_get_agent_info(self, mock_agent_state):
        """Test agent info extraction."""
        info = _get_agent_info(mock_agent_state)
        
        assert info["agent_id"] == "test_agent_001"
        assert info["agent_name"] == "Test Agent"
    
    def test_generate_chain_tips_ssrf(self):
        """Test chain tips for SSRF vulnerabilities."""
        tips = _generate_chain_tips("ssrf", None)
        
        assert len(tips) > 0
        assert any("internal" in tip.lower() or "cloud" in tip.lower() for tip in tips)
    
    def test_generate_chain_tips_with_suggestions(self):
        """Test chain tips with explicit suggestions."""
        tips = _generate_chain_tips("xss", ["csrf", "session_hijack"])
        
        assert any("csrf" in tip.lower() for tip in tips)
    
    def test_generate_help_tips_decode(self):
        """Test help tips for decode requests."""
        tips = _generate_help_tips("decode", "eyJhbGciOiJIUzI1NiJ9")
        
        assert len(tips) > 0
        assert any("jwt" in tip.lower() for tip in tips)


class TestClaimTarget:
    """Tests for target claiming system."""
    
    def test_claim_target_success(self, mock_agent_state):
        """Test successful target claim."""
        result = claim_target(
            mock_agent_state,
            target="/login",
            test_type="sqli",
            scope="authentication"
        )
        
        assert result["success"] is True
        assert result["status"] == "claimed"
        assert result["target"] == "/login"
        assert result["test_type"] == "sqli"
        assert "claim_id" in result
        assert _collaboration_stats["total_claims"] == 1
    
    def test_claim_target_duplicate_blocked(self, mock_agent_state, mock_agent_state_2):
        """Test that duplicate claims are blocked."""
        # First claim
        result1 = claim_target(
            mock_agent_state,
            target="/login",
            test_type="sqli"
        )
        assert result1["success"] is True
        
        # Second claim for same target/test_type should fail
        result2 = claim_target(
            mock_agent_state_2,
            target="/login",
            test_type="sqli"
        )
        
        assert result2["success"] is False
        assert result2["status"] == "already_claimed"
        assert "claimed_by" in result2
        assert _collaboration_stats["duplicate_tests_prevented"] == 1
    
    def test_claim_different_test_type_allowed(self, mock_agent_state, mock_agent_state_2):
        """Test that different test types on same target are allowed."""
        result1 = claim_target(mock_agent_state, "/login", "sqli")
        result2 = claim_target(mock_agent_state_2, "/login", "xss")
        
        assert result1["success"] is True
        assert result2["success"] is True
    
    def test_claim_with_priority(self, mock_agent_state):
        """Test claiming with priority."""
        result = claim_target(
            mock_agent_state,
            target="/admin",
            test_type="auth_bypass",
            priority="critical"
        )
        
        assert result["success"] is True
        assert result["priority"] == "critical"
    
    def test_claim_with_estimated_duration(self, mock_agent_state):
        """Test claiming with custom duration."""
        result = claim_target(
            mock_agent_state,
            target="/api",
            test_type="idor",
            estimated_duration=60
        )
        
        assert result["success"] is True
        assert result["estimated_duration"] == 60


class TestReleaseClaim:
    """Tests for releasing claims."""
    
    def test_release_claim_by_id(self, mock_agent_state):
        """Test releasing claim by claim ID."""
        claim_result = claim_target(mock_agent_state, "/test", "sqli")
        claim_id = claim_result["claim_id"]
        
        release_result = release_claim(
            mock_agent_state,
            claim_id=claim_id,
            result="No vulnerabilities found"
        )
        
        assert release_result["success"] is True
        assert release_result["status"] == "released"
    
    def test_release_claim_by_target(self, mock_agent_state):
        """Test releasing claim by target and test type."""
        claim_target(mock_agent_state, "/test", "xss")
        
        release_result = release_claim(
            mock_agent_state,
            target="/test",
            test_type="xss",
            result="Reflected XSS found"
        )
        
        assert release_result["success"] is True
    
    def test_release_with_finding_id(self, mock_agent_state):
        """Test releasing claim with linked finding."""
        claim_result = claim_target(mock_agent_state, "/test", "ssrf")
        
        # Share a finding first
        finding_result = share_finding(
            mock_agent_state,
            title="SSRF Found",
            vulnerability_type="ssrf",
            target="/test",
            description="Test finding"
        )
        
        release_result = release_claim(
            mock_agent_state,
            claim_id=claim_result["claim_id"],
            finding_id=finding_result["finding_id"]
        )
        
        assert release_result["success"] is True
        assert release_result["had_finding"] is True
    
    def test_release_nonexistent_claim(self, mock_agent_state):
        """Test releasing a non-existent claim."""
        result = release_claim(
            mock_agent_state,
            claim_id="nonexistent_id"
        )
        
        assert result["success"] is False


class TestListClaims:
    """Tests for listing claims."""
    
    def test_list_claims_empty(self, mock_agent_state):
        """Test listing claims when none exist."""
        result = list_claims(mock_agent_state)
        
        assert result["success"] is True
        assert result["total_claims"] == 0
        assert result["active_claims"] == 0
    
    def test_list_claims_with_data(self, mock_agent_state, mock_agent_state_2):
        """Test listing claims with data."""
        claim_target(mock_agent_state, "/login", "sqli")
        claim_target(mock_agent_state_2, "/api", "idor")
        
        result = list_claims(mock_agent_state)
        
        assert result["success"] is True
        assert result["total_claims"] == 2
        assert result["active_claims"] == 2
        assert len(result["claims"]) == 2
    
    def test_list_claims_filter_by_status(self, mock_agent_state):
        """Test filtering claims by status."""
        claim_result = claim_target(mock_agent_state, "/test1", "sqli")
        claim_target(mock_agent_state, "/test2", "xss")
        release_claim(mock_agent_state, claim_id=claim_result["claim_id"])
        
        active_claims = list_claims(mock_agent_state, status="active")
        completed_claims = list_claims(mock_agent_state, status="completed")
        
        assert active_claims["active_claims"] == 1
        assert len([c for c in completed_claims["claims"] if c["status"] == "completed"]) == 1
    
    def test_list_claims_includes_statistics(self, mock_agent_state):
        """Test that list includes statistics."""
        claim_target(mock_agent_state, "/test", "sqli")
        
        result = list_claims(mock_agent_state)
        
        assert "statistics" in result
        assert "by_test_type" in result["statistics"]


class TestShareFinding:
    """Tests for finding sharing."""
    
    def test_share_finding_basic(self, mock_agent_state):
        """Test basic finding sharing."""
        result = share_finding(
            mock_agent_state,
            title="SQL Injection in Login",
            vulnerability_type="sqli",
            target="/login",
            description="Authentication bypass via SQL injection"
        )
        
        assert result["success"] is True
        assert "finding_id" in result
        assert result["title"] == "SQL Injection in Login"
        assert _collaboration_stats["total_findings"] == 1
    
    def test_share_finding_with_poc(self, mock_agent_state):
        """Test sharing finding with PoC."""
        result = share_finding(
            mock_agent_state,
            title="SSRF",
            vulnerability_type="ssrf",
            target="/api/fetch",
            description="Server-side request forgery",
            severity="high",
            poc="GET /api/fetch?url=http://169.254.169.254/"
        )
        
        assert result["success"] is True
        assert result["severity"] == "high"
    
    def test_share_chainable_finding(self, mock_agent_state):
        """Test sharing chainable finding."""
        result = share_finding(
            mock_agent_state,
            title="XSS in Search",
            vulnerability_type="xss",
            target="/search",
            description="Reflected XSS",
            chainable=True,
            chain_suggestions=["csrf", "session_hijack"]
        )
        
        assert result["success"] is True
        assert result["chainable"] is True
        assert _collaboration_stats["chaining_opportunities"] == 1
    
    def test_share_finding_creates_message(self, mock_agent_state):
        """Test that sharing creates a broadcast message."""
        share_finding(
            mock_agent_state,
            title="Test Finding",
            vulnerability_type="test",
            target="/test",
            description="Test"
        )
        
        # Should have created a message
        assert len(_messages) > 0
        assert _messages[-1]["type"] == "finding_notification"


class TestListFindings:
    """Tests for listing findings."""
    
    def test_list_findings_empty(self, mock_agent_state):
        """Test listing findings when none exist."""
        result = list_findings(mock_agent_state)
        
        assert result["success"] is True
        assert result["total_findings"] == 0
    
    def test_list_findings_with_data(self, mock_agent_state):
        """Test listing findings with data."""
        share_finding(mock_agent_state, "Finding 1", "sqli", "/t1", "D1", severity="critical")
        share_finding(mock_agent_state, "Finding 2", "xss", "/t2", "D2", severity="high")
        
        result = list_findings(mock_agent_state)
        
        assert result["success"] is True
        assert result["total_findings"] == 2
        assert len(result["findings"]) == 2
    
    def test_list_findings_filter_by_severity(self, mock_agent_state):
        """Test filtering findings by severity."""
        share_finding(mock_agent_state, "Critical", "rce", "/t1", "D1", severity="critical")
        share_finding(mock_agent_state, "High", "sqli", "/t2", "D2", severity="high")
        
        result = list_findings(mock_agent_state, severity="critical")
        
        assert result["filtered_count"] == 1
    
    def test_list_findings_chainable_only(self, mock_agent_state):
        """Test filtering for chainable findings only."""
        share_finding(mock_agent_state, "Chainable", "ssrf", "/t1", "D1", chainable=True)
        share_finding(mock_agent_state, "Not Chainable", "info", "/t2", "D2", chainable=False)
        
        result = list_findings(mock_agent_state, chainable_only=True)
        
        assert result["filtered_count"] == 1
        assert all(f["chainable"] for f in result["findings"])


class TestGetFindingDetails:
    """Tests for getting finding details."""
    
    def test_get_finding_details_success(self, mock_agent_state):
        """Test getting finding details."""
        share_result = share_finding(
            mock_agent_state,
            title="Test Finding",
            vulnerability_type="test",
            target="/test",
            description="Detailed description",
            poc="curl http://...",
            evidence="Response contained..."
        )
        
        result = get_finding_details(mock_agent_state, share_result["finding_id"])
        
        assert result["success"] is True
        assert "finding" in result
        assert result["finding"]["title"] == "Test Finding"
        assert result["finding"]["poc"] == "curl http://..."
    
    def test_get_finding_details_not_found(self, mock_agent_state):
        """Test getting non-existent finding."""
        result = get_finding_details(mock_agent_state, "nonexistent_id")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestWorkQueue:
    """Tests for work queue management."""
    
    def test_add_to_work_queue(self, mock_agent_state):
        """Test adding item to work queue."""
        result = add_to_work_queue(
            mock_agent_state,
            target="/api/v2/users",
            description="New endpoint found",
            test_types=["idor", "auth_bypass"],
            priority="high"
        )
        
        assert result["success"] is True
        assert "work_id" in result
        assert result["priority"] == "high"
        assert result["queue_position"] == 1
        assert _collaboration_stats["total_work_items"] == 1
    
    def test_work_queue_priority_sorting(self, mock_agent_state):
        """Test that queue is sorted by priority."""
        add_to_work_queue(mock_agent_state, "/low", "Low priority", priority="low")
        add_to_work_queue(mock_agent_state, "/critical", "Critical priority", priority="critical")
        add_to_work_queue(mock_agent_state, "/high", "High priority", priority="high")
        
        # Get next item should return critical first
        result = get_next_work_item(mock_agent_state)
        
        assert result["work_item"]["target"] == "/critical"
    
    def test_get_next_work_item_empty_queue(self, mock_agent_state):
        """Test getting from empty queue."""
        result = get_next_work_item(mock_agent_state)
        
        assert result["success"] is True
        assert result["work_item"] is None
    
    def test_get_next_work_item_assigns_to_agent(self, mock_agent_state):
        """Test that getting work item assigns it."""
        add_to_work_queue(mock_agent_state, "/test", "Test item")
        
        result = get_next_work_item(mock_agent_state)
        
        assert result["success"] is True
        assert result["work_item"] is not None
        
        # Second call should return empty (item was assigned)
        result2 = get_next_work_item(mock_agent_state)
        assert result2["work_item"] is None
    
    def test_get_next_work_item_with_preferences(self, mock_agent_state):
        """Test getting work item with test type preferences."""
        add_to_work_queue(mock_agent_state, "/t1", "D1", test_types=["xss"])
        add_to_work_queue(mock_agent_state, "/t2", "D2", test_types=["sqli"])
        
        result = get_next_work_item(
            mock_agent_state,
            preferred_test_types=["sqli"]
        )
        
        assert result["work_item"]["target"] == "/t2"


class TestHelpRequest:
    """Tests for help request system."""
    
    def test_request_help_basic(self, mock_agent_state):
        """Test basic help request."""
        result = request_help(
            mock_agent_state,
            help_type="decode",
            description="Can't decode this token"
        )
        
        assert result["success"] is True
        assert "request_id" in result
        assert result["help_type"] == "decode"
        assert _collaboration_stats["total_help_requests"] == 1
    
    def test_request_help_with_data(self, mock_agent_state):
        """Test help request with data."""
        result = request_help(
            mock_agent_state,
            help_type="analyze",
            description="Strange response pattern",
            data="<response>...</response>",
            context="Found on /api/debug"
        )
        
        assert result["success"] is True
    
    def test_request_help_urgency(self, mock_agent_state):
        """Test help request with urgency."""
        result = request_help(
            mock_agent_state,
            help_type="exploit",
            description="Need help with RCE",
            urgency="critical"
        )
        
        assert result["success"] is True
        assert result["urgency"] == "critical"
    
    def test_request_help_creates_broadcast(self, mock_agent_state):
        """Test that help request creates broadcast message."""
        request_help(mock_agent_state, "bypass", "Help with WAF bypass")
        
        assert len(_messages) > 0
        assert _messages[-1]["type"] == "help_request"


class TestCollaborationStatus:
    """Tests for collaboration status dashboard."""
    
    def test_get_collaboration_status_empty(self, mock_agent_state):
        """Test status with no activity."""
        result = get_collaboration_status(mock_agent_state)
        
        assert result["success"] is True
        assert "my_status" in result
        assert "collaboration_overview" in result
        assert result["my_status"]["active_claims"] == 0
    
    def test_get_collaboration_status_with_activity(self, mock_agent_state):
        """Test status with various activities."""
        claim_target(mock_agent_state, "/test", "sqli")
        share_finding(mock_agent_state, "Test", "test", "/t", "D")
        add_to_work_queue(mock_agent_state, "/q", "Q")
        request_help(mock_agent_state, "decode", "Help")
        
        result = get_collaboration_status(mock_agent_state)
        
        assert result["success"] is True
        assert result["my_status"]["active_claims"] == 1
        assert result["collaboration_overview"]["total_findings"] == 1
        assert result["collaboration_overview"]["pending_work_items"] == 1
        assert result["collaboration_overview"]["open_help_requests"] == 1
    
    def test_status_includes_recommendations(self, mock_agent_state):
        """Test that status includes recommendations."""
        result = get_collaboration_status(mock_agent_state)
        
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)


class TestBroadcastMessage:
    """Tests for broadcast messaging."""
    
    def test_broadcast_message_basic(self, mock_agent_state):
        """Test basic message broadcast."""
        result = broadcast_message(
            mock_agent_state,
            message="Found WAF - use encoded payloads"
        )
        
        assert result["success"] is True
        assert "message_id" in result
        assert _collaboration_stats["total_broadcasts"] == 1
    
    def test_broadcast_message_with_type(self, mock_agent_state):
        """Test broadcast with message type."""
        result = broadcast_message(
            mock_agent_state,
            message="Focus on auth endpoints",
            message_type="coordination"
        )
        
        assert result["success"] is True
        assert result["message_type"] == "coordination"
    
    def test_broadcast_message_with_priority(self, mock_agent_state):
        """Test broadcast with priority."""
        result = broadcast_message(
            mock_agent_state,
            message="Critical vuln found!",
            priority="urgent"
        )
        
        assert result["success"] is True
        assert result["priority"] == "urgent"


class TestMultiAgentScenarios:
    """Tests for multi-agent collaboration scenarios."""
    
    def test_agent_coordination_workflow(self, mock_agent_state, mock_agent_state_2):
        """Test full coordination workflow between agents."""
        # Agent 1 claims and finds vulnerability
        claim_target(mock_agent_state, "/login", "sqli")
        finding = share_finding(
            mock_agent_state,
            title="SQLi in Login",
            vulnerability_type="sqli",
            target="/login",
            description="Auth bypass",
            chainable=True,
            chain_suggestions=["auth_bypass"]
        )
        release_claim(
            mock_agent_state,
            target="/login",
            test_type="sqli",
            finding_id=finding["finding_id"]
        )
        
        # Agent 2 sees the finding and tries to chain
        findings = list_findings(mock_agent_state_2)
        assert findings["total_findings"] == 1
        
        # Agent 2 claims same target for different test
        result = claim_target(mock_agent_state_2, "/login", "auth_bypass")
        assert result["success"] is True
    
    def test_work_distribution(self, mock_agent_state, mock_agent_state_2):
        """Test work distribution between agents."""
        # Add multiple work items
        add_to_work_queue(mock_agent_state, "/api/v1", "API endpoint 1", test_types=["sqli"])
        add_to_work_queue(mock_agent_state, "/api/v2", "API endpoint 2", test_types=["xss"])
        
        # Different agents pick up different work
        work1 = get_next_work_item(mock_agent_state, preferred_test_types=["sqli"])
        work2 = get_next_work_item(mock_agent_state_2, preferred_test_types=["xss"])
        
        assert work1["work_item"]["target"] == "/api/v1"
        assert work2["work_item"]["target"] == "/api/v2"


class TestStatisticsTracking:
    """Tests for statistics tracking."""
    
    def test_claim_statistics(self, mock_agent_state):
        """Test claim statistics are tracked."""
        initial = _collaboration_stats["total_claims"]
        
        claim_target(mock_agent_state, "/t1", "sqli")
        claim_target(mock_agent_state, "/t2", "xss")
        
        assert _collaboration_stats["total_claims"] == initial + 2
    
    def test_duplicate_prevention_statistics(self, mock_agent_state, mock_agent_state_2):
        """Test duplicate prevention is tracked."""
        claim_target(mock_agent_state, "/test", "sqli")
        claim_target(mock_agent_state_2, "/test", "sqli")  # Should be blocked
        
        assert _collaboration_stats["duplicate_tests_prevented"] == 1
    
    def test_chaining_opportunity_statistics(self, mock_agent_state):
        """Test chaining opportunities are tracked."""
        share_finding(mock_agent_state, "T1", "ssrf", "/t", "D", chainable=True)
        share_finding(mock_agent_state, "T2", "info", "/t", "D", chainable=False)
        
        assert _collaboration_stats["chaining_opportunities"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
