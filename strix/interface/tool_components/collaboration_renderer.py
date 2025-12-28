"""
TUI Renderer for Multi-Agent Collaboration Tools.

Provides rich terminal output for collaboration status, claims, findings, and coordination.
"""

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .base_renderer import BaseToolRenderer


class CollaborationRenderer(BaseToolRenderer):
    """Renderer for collaboration tool outputs."""

    PRIORITY_COLORS = {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "green",
    }

    PRIORITY_EMOJI = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }

    STATUS_COLORS = {
        "active": "green",
        "claimed": "green",
        "completed": "blue",
        "expired": "dim",
        "pending": "yellow",
        "assigned": "cyan",
        "open": "yellow",
    }

    def render(self, name: str, arguments: dict[str, Any], result: Any) -> Any:
        """Render collaboration tool results."""
        if name == "claim_target":
            return self._render_claim_target(result)
        elif name == "release_claim":
            return self._render_release_claim(result)
        elif name == "list_claims":
            return self._render_list_claims(result)
        elif name == "share_finding":
            return self._render_share_finding(result)
        elif name == "list_findings":
            return self._render_list_findings(result)
        elif name == "get_finding_details":
            return self._render_finding_details(result)
        elif name == "add_to_work_queue":
            return self._render_add_to_queue(result)
        elif name == "get_next_work_item":
            return self._render_next_work_item(result)
        elif name == "request_help":
            return self._render_help_request(result)
        elif name == "get_collaboration_status":
            return self._render_collaboration_status(result)
        elif name == "broadcast_message":
            return self._render_broadcast(result)
        else:
            return self._render_generic(name, result)

    def _render_claim_target(self, result: dict[str, Any]) -> Panel:
        """Render claim target result."""
        if not result.get("success"):
            content = []
            content.append(Text("❌ Claim Failed", style="red bold"))
            content.append(Text())

            if result.get("status") == "already_claimed":
                claimed_by = result.get("claimed_by", {})
                content.append(Text(f"Already claimed by: {claimed_by.get('agent_name', claimed_by.get('agent_id', 'Unknown'))}", style="yellow"))
                content.append(Text(f"Test type: {result.get('test_type', 'Unknown')}", style="dim"))
                content.append(Text(f"Claimed at: {result.get('claimed_at', 'Unknown')}", style="dim"))
                content.append(Text())
                content.append(Text(f"💡 {result.get('suggestion', 'Try a different test type')}", style="cyan"))
            else:
                content.append(Text(result.get("message", "Unknown error"), style="red"))

            return Panel(
                Group(*content),
                title="🔒 Target Already Claimed",
                border_style="red",
            )

        content = []
        content.append(Text("✅ Target Claimed Successfully", style="green bold"))
        content.append(Text())
        content.append(Text(f"Target: {result.get('target', 'Unknown')}", style="cyan"))
        content.append(Text(f"Test Type: {result.get('test_type', 'Unknown')}"))
        
        if result.get("scope"):
            content.append(Text(f"Scope: {result.get('scope')}"))
        
        priority = result.get("priority", "medium")
        content.append(Text(f"Priority: {self.PRIORITY_EMOJI.get(priority, '⚪')} {priority.upper()}", style=self.PRIORITY_COLORS.get(priority, "white")))
        content.append(Text(f"Estimated Duration: {result.get('estimated_duration', 30)} minutes", style="dim"))
        content.append(Text())
        content.append(Text(f"Claim ID: {result.get('claim_id', 'Unknown')}", style="dim"))
        
        if result.get("reminder"):
            content.append(Text())
            content.append(Text(f"💡 {result.get('reminder')}", style="cyan"))

        return Panel(
            Group(*content),
            title="🎯 Target Claimed",
            border_style="green",
        )

    def _render_release_claim(self, result: dict[str, Any]) -> Panel:
        """Render release claim result."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Release Failed",
                border_style="red",
            )

        content = []
        content.append(Text("✅ Claim Released", style="green bold"))
        content.append(Text())
        content.append(Text(f"Target: {result.get('target', 'Unknown')}", style="cyan"))
        content.append(Text(f"Test Type: {result.get('test_type', 'Unknown')}"))
        content.append(Text(f"Duration: {result.get('duration_minutes', 0)} minutes", style="dim"))
        
        if result.get("had_finding"):
            content.append(Text("📋 Finding was linked", style="green"))

        return Panel(
            Group(*content),
            title="🔓 Claim Released",
            border_style="blue",
        )

    def _render_list_claims(self, result: dict[str, Any]) -> Panel:
        """Render list of claims."""
        content = []

        # Header stats
        header = Text()
        header.append(f"Total Claims: {result.get('total_claims', 0)}", style="bold")
        header.append(f" | Active: {result.get('active_claims', 0)}", style="green")
        content.append(header)

        # Statistics
        stats = result.get("statistics", {})
        if stats.get("duplicate_tests_prevented", 0) > 0:
            content.append(Text(f"🛡️ Duplicate tests prevented: {stats['duplicate_tests_prevented']}", style="cyan"))
        content.append(Text())

        # Claims table
        claims = result.get("claims", [])
        if claims:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Target", width=30)
            table.add_column("Test", width=15)
            table.add_column("Agent", width=20)
            table.add_column("Status", width=12)
            table.add_column("Priority", width=10)

            for claim in claims[:15]:
                status = claim.get("status", "unknown")
                priority = claim.get("priority", "medium")
                table.add_row(
                    claim.get("target", "Unknown")[:30],
                    claim.get("test_type", "Unknown"),
                    claim.get("agent_name", claim.get("agent_id", "Unknown"))[:20],
                    Text(status.upper(), style=self.STATUS_COLORS.get(status, "white")),
                    Text(f"{self.PRIORITY_EMOJI.get(priority, '⚪')} {priority}", style=self.PRIORITY_COLORS.get(priority, "white")),
                )

            content.append(table)
        else:
            content.append(Text("No claims found", style="dim"))

        # Suggestions
        suggestions = result.get("unclaimed_suggestions", [])
        if suggestions:
            content.append(Text())
            for suggestion in suggestions:
                content.append(Text(f"💡 {suggestion}", style="cyan"))

        return Panel(
            Group(*content),
            title="📋 Active Claims",
            border_style="cyan",
        )

    def _render_share_finding(self, result: dict[str, Any]) -> Panel:
        """Render share finding result."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Share Finding Failed",
                border_style="red",
            )

        content = []
        content.append(Text("🎉 Finding Shared Successfully!", style="green bold"))
        content.append(Text())
        content.append(Text(f"Title: {result.get('title', 'Unknown')}", style="cyan"))
        
        severity = result.get("severity", "medium")
        content.append(Text(f"Severity: {self.PRIORITY_EMOJI.get(severity, '⚪')} {severity.upper()}", style=self.PRIORITY_COLORS.get(severity, "white")))
        
        if result.get("chainable"):
            content.append(Text("🔗 Marked as chainable - other agents notified!", style="yellow"))
        
        content.append(Text(f"Finding ID: {result.get('finding_id', 'Unknown')}", style="dim"))
        content.append(Text())

        # Chain tips
        chain_tips = result.get("chain_tips", [])
        if chain_tips:
            content.append(Text("Chaining Opportunities:", style="bold"))
            for tip in chain_tips[:5]:
                content.append(Text(f"  💡 {tip}", style="cyan"))

        return Panel(
            Group(*content),
            title="📢 Finding Shared",
            border_style="green",
        )

    def _render_list_findings(self, result: dict[str, Any]) -> Panel:
        """Render list of findings."""
        content = []

        # Header
        header = Text()
        header.append(f"Total Findings: {result.get('total_findings', 0)}", style="bold")
        header.append(f" | Returned: {result.get('filtered_count', 0)}")
        content.append(header)

        # Statistics
        stats = result.get("statistics", {})
        stats_text = Text()
        by_severity = stats.get("by_severity", {})
        if by_severity:
            stats_text.append("By Severity: ")
            for sev, count in by_severity.items():
                stats_text.append(f"{self.PRIORITY_EMOJI.get(sev, '⚪')}{count} ")
        if stats.get("chainable_findings", 0) > 0:
            stats_text.append(f"| 🔗 Chainable: {stats['chainable_findings']}")
        content.append(stats_text)
        content.append(Text())

        # Findings table
        findings = result.get("findings", [])
        if findings:
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("ID", width=16)
            table.add_column("Title", width=35)
            table.add_column("Type", width=15)
            table.add_column("Severity", width=10)
            table.add_column("Chain", width=6)

            for finding in findings[:15]:
                severity = finding.get("severity", "medium")
                table.add_row(
                    finding.get("finding_id", "Unknown"),
                    finding.get("title", "Unknown")[:35],
                    finding.get("vulnerability_type", "Unknown"),
                    Text(severity.upper(), style=self.PRIORITY_COLORS.get(severity, "white")),
                    "🔗" if finding.get("chainable") else "-",
                )

            content.append(table)
        else:
            content.append(Text("No findings found", style="dim"))

        # Chaining tips
        tips = result.get("chaining_tips", [])
        if tips:
            content.append(Text())
            content.append(Text("💡 Chaining Tips:", style="bold"))
            for tip in tips[:3]:
                content.append(Text(f"   {tip}", style="cyan"))

        return Panel(
            Group(*content),
            title="🔍 Shared Findings",
            border_style="yellow",
        )

    def _render_finding_details(self, result: dict[str, Any]) -> Panel:
        """Render finding details."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Finding Not Found",
                border_style="red",
            )

        finding = result.get("finding", {})
        content = []

        # Header
        severity = finding.get("severity", "medium")
        header = Text()
        header.append(f"{finding.get('title', 'Unknown')}\n", style="bold cyan")
        header.append(f"{self.PRIORITY_EMOJI.get(severity, '⚪')} {severity.upper()}", style=self.PRIORITY_COLORS.get(severity, "white"))
        header.append(f" | Type: {finding.get('vulnerability_type', 'Unknown')}")
        content.append(header)
        content.append(Text())

        # Target
        content.append(Text(f"Target: {finding.get('target', 'Unknown')}", style="cyan"))
        content.append(Text())

        # Description
        content.append(Text("Description:", style="bold"))
        content.append(Text(finding.get("description", "No description")))
        content.append(Text())

        # PoC
        poc = finding.get("poc")
        if poc:
            content.append(Text("Proof of Concept:", style="bold"))
            content.append(Text(poc, style="green"))
            content.append(Text())

        # Evidence
        evidence = finding.get("evidence")
        if evidence:
            content.append(Text("Evidence:", style="bold"))
            content.append(Text(evidence, style="dim"))
            content.append(Text())

        # Chaining info
        if finding.get("chainable"):
            content.append(Text("🔗 This finding can be chained!", style="yellow bold"))
            chain_suggestions = finding.get("chain_suggestions", [])
            if chain_suggestions:
                content.append(Text(f"   Suggested chains: {', '.join(chain_suggestions)}"))

        # Remediation
        remediation = finding.get("remediation")
        if remediation:
            content.append(Text())
            content.append(Text("Remediation:", style="bold"))
            content.append(Text(remediation, style="cyan"))

        # Found by
        found_by = finding.get("found_by", {})
        content.append(Text())
        content.append(Text(f"Found by: {found_by.get('agent_name', 'Unknown')} at {finding.get('found_at', 'Unknown')}", style="dim"))

        return Panel(
            Group(*content),
            title=f"📋 Finding: {finding.get('finding_id', 'Unknown')}",
            border_style="yellow",
        )

    def _render_add_to_queue(self, result: dict[str, Any]) -> Panel:
        """Render add to queue result."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Add to Queue Failed",
                border_style="red",
            )

        content = []
        content.append(Text("✅ Added to Work Queue", style="green bold"))
        content.append(Text())
        content.append(Text(f"Target: {result.get('target', 'Unknown')}", style="cyan"))
        
        priority = result.get("priority", "medium")
        content.append(Text(f"Priority: {self.PRIORITY_EMOJI.get(priority, '⚪')} {priority.upper()}", style=self.PRIORITY_COLORS.get(priority, "white")))
        
        content.append(Text(f"Queue Position: #{result.get('queue_position', '?')}", style="yellow"))
        content.append(Text(f"Work ID: {result.get('work_id', 'Unknown')}", style="dim"))

        return Panel(
            Group(*content),
            title="📥 Work Queue Updated",
            border_style="green",
        )

    def _render_next_work_item(self, result: dict[str, Any]) -> Panel:
        """Render next work item result."""
        work_item = result.get("work_item")
        
        if not work_item:
            content = []
            content.append(Text("📭 No suitable work items in queue", style="yellow"))
            content.append(Text())
            
            queue_status = result.get("queue_status", {})
            content.append(Text(f"Queue Status: {queue_status.get('pending', 0)} pending, {queue_status.get('assigned', 0)} assigned", style="dim"))

            return Panel(
                Group(*content),
                title="Work Queue Empty",
                border_style="yellow",
            )

        content = []
        content.append(Text("📋 Work Item Assigned to You!", style="green bold"))
        content.append(Text())
        content.append(Text(f"Target: {work_item.get('target', 'Unknown')}", style="cyan"))
        content.append(Text(f"Description: {work_item.get('description', 'No description')}", style="white"))
        
        priority = work_item.get("priority", "medium")
        content.append(Text(f"Priority: {self.PRIORITY_EMOJI.get(priority, '⚪')} {priority.upper()}", style=self.PRIORITY_COLORS.get(priority, "white")))
        
        test_types = work_item.get("test_types", [])
        if test_types:
            content.append(Text(f"Suggested Tests: {', '.join(test_types)}"))
        
        if work_item.get("notes"):
            content.append(Text(f"Notes: {work_item.get('notes')}", style="dim"))
        
        content.append(Text())
        content.append(Text("Next Steps:", style="bold"))
        for step in result.get("next_steps", [])[:5]:
            content.append(Text(f"  {step}", style="cyan"))

        return Panel(
            Group(*content),
            title="📤 Work Item Assigned",
            border_style="green",
        )

    def _render_help_request(self, result: dict[str, Any]) -> Panel:
        """Render help request result."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Help Request Failed",
                border_style="red",
            )

        content = []
        content.append(Text("🆘 Help Request Sent!", style="yellow bold"))
        content.append(Text())
        content.append(Text(f"Type: {result.get('help_type', 'Unknown')}", style="cyan"))
        
        urgency = result.get("urgency", "normal")
        urgency_colors = {"critical": "red bold", "high": "red", "normal": "yellow", "low": "green"}
        content.append(Text(f"Urgency: {urgency.upper()}", style=urgency_colors.get(urgency, "white")))
        
        content.append(Text(f"Request ID: {result.get('request_id', 'Unknown')}", style="dim"))
        content.append(Text())

        tips = result.get("tips", [])
        if tips:
            content.append(Text("💡 While waiting:", style="bold"))
            for tip in tips[:5]:
                content.append(Text(f"   {tip}", style="cyan"))

        return Panel(
            Group(*content),
            title="🤝 Help Request Broadcast",
            border_style="yellow",
        )

    def _render_collaboration_status(self, result: dict[str, Any]) -> Panel:
        """Render collaboration status dashboard."""
        content = []

        # My status
        my_status = result.get("my_status", {})
        content.append(Text(f"👤 {my_status.get('agent_name', 'Unknown Agent')}", style="bold cyan"))
        content.append(Text(f"   Active claims: {my_status.get('active_claims', 0)}"))
        content.append(Text())

        # Overview
        overview = result.get("collaboration_overview", {})
        overview_text = Text("📊 Collaboration Overview:\n", style="bold")
        overview_text.append(f"   🎯 Active Claims: {overview.get('total_active_claims', 0)}\n")
        overview_text.append(f"   🔍 Total Findings: {overview.get('total_findings', 0)}\n")
        overview_text.append(f"   📥 Pending Work: {overview.get('pending_work_items', 0)}\n")
        overview_text.append(f"   🆘 Open Help Requests: {overview.get('open_help_requests', 0)}")
        content.append(overview_text)
        content.append(Text())

        # Recent findings
        findings = result.get("recent_findings", [])
        if findings:
            content.append(Text("🔥 Recent Findings:", style="bold"))
            for f in findings[:5]:
                severity = f.get("severity", "medium")
                chain_icon = "🔗" if f.get("chainable") else ""
                content.append(Text(f"   {self.PRIORITY_EMOJI.get(severity, '⚪')} {f.get('title', 'Unknown')[:40]} {chain_icon}", style="white"))
            content.append(Text())

        # Pending work
        work_queue = result.get("pending_work_queue", [])
        if work_queue:
            content.append(Text("📋 Pending Work Queue:", style="bold"))
            for w in work_queue[:5]:
                priority = w.get("priority", "medium")
                content.append(Text(f"   {self.PRIORITY_EMOJI.get(priority, '⚪')} {w.get('target', 'Unknown')[:40]}", style="white"))
            content.append(Text())

        # Open help requests
        help_requests = result.get("open_help_requests", [])
        if help_requests:
            content.append(Text("🆘 Open Help Requests:", style="bold"))
            for h in help_requests[:3]:
                content.append(Text(f"   [{h.get('help_type', 'unknown')}] {h.get('description', 'No description')[:40]}...", style="yellow"))
            content.append(Text())

        # Recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            content.append(Text("💡 Recommendations:", style="bold"))
            for rec in recommendations[:3]:
                content.append(Text(f"   {rec}", style="cyan"))

        # Statistics
        stats = result.get("statistics", {})
        content.append(Text())
        content.append(Text(f"📈 Stats: {stats.get('total_claims', 0)} claims | {stats.get('total_findings', 0)} findings | {stats.get('duplicate_tests_prevented', 0)} dupes prevented", style="dim"))

        return Panel(
            Group(*content),
            title="🤖 Multi-Agent Collaboration Dashboard",
            subtitle=f"Updated: {result.get('timestamp', 'Unknown')}",
            border_style="cyan",
        )

    def _render_broadcast(self, result: dict[str, Any]) -> Panel:
        """Render broadcast message result."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Broadcast Failed",
                border_style="red",
            )

        content = []
        content.append(Text("📢 Message Broadcast!", style="green bold"))
        content.append(Text())
        content.append(Text(f"Type: {result.get('message_type', 'info')}", style="cyan"))
        content.append(Text(f"Priority: {result.get('priority', 'normal')}"))
        content.append(Text(f"Delivered to: {result.get('delivered_to', 'Unknown')}", style="dim"))
        content.append(Text(f"Message ID: {result.get('message_id', 'Unknown')}", style="dim"))

        return Panel(
            Group(*content),
            title="📣 Broadcast Sent",
            border_style="green",
        )

    def _render_generic(self, name: str, result: dict[str, Any]) -> Panel:
        """Render generic tool results."""
        import json
        content = json.dumps(result, indent=2, default=str)
        return Panel(
            Text(content),
            title=f"Collaboration Tool: {name}",
            border_style="blue",
        )
