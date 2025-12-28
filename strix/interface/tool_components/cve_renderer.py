"""
TUI Renderer for CVE Database Tools.

Provides rich terminal output for vulnerability database queries and exploit searches.
"""

from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .base_renderer import BaseToolRenderer


class CVEDatabaseRenderer(BaseToolRenderer):
    """Renderer for CVE database tool outputs."""

    SEVERITY_COLORS = {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "green",
        "info": "blue",
        "unknown": "dim",
    }

    SEVERITY_EMOJI = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "🔵",
        "unknown": "⚪",
    }

    def render(self, name: str, arguments: dict[str, Any], result: Any) -> Any:
        """Render CVE database tool results."""
        console = Console()

        if name == "query_cve_database":
            return self._render_cve_query(result)
        elif name == "get_cve_details":
            return self._render_cve_details(result)
        elif name == "search_exploitdb":
            return self._render_exploitdb(result)
        elif name == "search_github_advisories":
            return self._render_github_advisories(result)
        elif name == "search_packetstorm":
            return self._render_packetstorm(result)
        elif name == "get_technology_vulnerabilities":
            return self._render_technology_vulns(result)
        else:
            return self._render_generic(name, result)

    def _render_cve_query(self, result: dict[str, Any]) -> Panel:
        """Render CVE database query results."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="CVE Query Failed",
                border_style="red",
            )

        content = []

        # Summary header
        summary = result.get("summary", {})
        header = Text()
        header.append(f"Found {result.get('total_results', 0)} CVEs", style="bold")
        header.append(f" | Returned: {result.get('returned_results', 0)}\n")

        # Severity breakdown
        severity_text = Text()
        severity_text.append(f"{self.SEVERITY_EMOJI['critical']} Critical: {summary.get('critical', 0)}  ")
        severity_text.append(f"{self.SEVERITY_EMOJI['high']} High: {summary.get('high', 0)}  ")
        severity_text.append(f"{self.SEVERITY_EMOJI['medium']} Medium: {summary.get('medium', 0)}  ")
        severity_text.append(f"{self.SEVERITY_EMOJI['low']} Low: {summary.get('low', 0)}")

        content.append(header)
        content.append(severity_text)
        content.append(Text())

        # CVE table
        if result.get("vulnerabilities"):
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("CVE ID", style="cyan", width=18)
            table.add_column("Severity", width=10)
            table.add_column("CVSS", width=6)
            table.add_column("Description", width=60)

            for cve in result["vulnerabilities"][:10]:
                severity = cve.get("severity", "unknown")
                cvss = cve.get("cvss_v3") or cve.get("cvss_v2") or "N/A"
                cvss_str = f"{cvss}" if isinstance(cvss, (int, float)) else cvss
                description = cve.get("description", "")[:80] + "..." if len(cve.get("description", "")) > 80 else cve.get("description", "")

                table.add_row(
                    cve.get("cve_id", "Unknown"),
                    Text(f"{self.SEVERITY_EMOJI.get(severity, '⚪')} {severity.upper()}", style=self.SEVERITY_COLORS.get(severity, "white")),
                    cvss_str,
                    description,
                )

            content.append(table)

        return Panel(
            Group(*content),
            title="🔍 CVE Database Query Results",
            subtitle=f"Source: {result.get('source', 'NVD')}",
            border_style="cyan",
        )

    def _render_cve_details(self, result: dict[str, Any]) -> Panel:
        """Render detailed CVE information."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="CVE Details Failed",
                border_style="red",
            )

        cve = result.get("cve", {})
        content = []

        # Header with CVE ID and severity
        severity = cve.get("severity", "unknown")
        header = Text()
        header.append(f"{cve.get('cve_id', 'Unknown')}", style="bold cyan")
        header.append(f" - {self.SEVERITY_EMOJI.get(severity, '⚪')} ", style=self.SEVERITY_COLORS.get(severity, "white"))
        header.append(f"{severity.upper()}", style=self.SEVERITY_COLORS.get(severity, "white"))

        cvss_v3 = cve.get("cvss_v3")
        cvss_v2 = cve.get("cvss_v2")
        if cvss_v3:
            header.append(f" | CVSS 3.x: {cvss_v3}", style="bold")
        if cvss_v2:
            header.append(f" | CVSS 2.0: {cvss_v2}")

        content.append(header)
        content.append(Text())

        # Description
        content.append(Text("Description:", style="bold"))
        content.append(Text(cve.get("description", "No description available")))
        content.append(Text())

        # Exploitability
        exploitability = result.get("exploitability", "none")
        exploit_colors = {
            "weaponized": "red bold",
            "poc_available": "red",
            "exploit_available": "yellow",
            "none": "green",
        }
        exploit_text = Text("Exploitability: ", style="bold")
        exploit_text.append(f"{exploitability.upper()}", style=exploit_colors.get(exploitability, "white"))
        if result.get("has_public_exploit"):
            exploit_text.append(" ⚠️ PUBLIC EXPLOIT EXISTS", style="red bold")
        content.append(exploit_text)
        content.append(Text())

        # Recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            content.append(Text("Recommendations:", style="bold"))
            for rec in recommendations[:5]:
                content.append(Text(f"  • {rec}"))
            content.append(Text())

        # Weaknesses
        weaknesses = cve.get("weaknesses", [])
        if weaknesses:
            content.append(Text(f"Weaknesses: {', '.join(weaknesses[:5])}", style="dim"))

        return Panel(
            Group(*content),
            title=f"📋 CVE Details: {cve.get('cve_id', 'Unknown')}",
            border_style="cyan",
        )

    def _render_exploitdb(self, result: dict[str, Any]) -> Panel:
        """Render Exploit-DB search results."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Exploit-DB Search Failed",
                border_style="red",
            )

        content = []
        
        query = result.get("query", {})
        content.append(Text(f"Search: {query.get('search', 'N/A')}", style="bold"))
        content.append(Text(f"Search URL: {result.get('search_url', 'N/A')}", style="dim"))
        content.append(Text())

        exploits = result.get("exploits", [])
        if exploits:
            for exploit in exploits[:10]:
                if exploit.get("type") == "guidance":
                    content.append(Text(f"📌 {exploit.get('title', 'Unknown')}", style="yellow"))
                    content.append(Text(f"   {exploit.get('description', '')}", style="dim"))
                elif exploit.get("type") == "tip":
                    content.append(Text(f"💡 {exploit.get('title', 'Unknown')}", style="cyan"))
                    content.append(Text(f"   {exploit.get('description', '')}", style="dim"))
                else:
                    content.append(Text(f"🔧 {exploit.get('title', 'Unknown')}", style="green"))
                    content.append(Text(f"   Type: {exploit.get('type', 'Unknown')} | Platform: {exploit.get('platform', 'N/A')}", style="dim"))
                content.append(Text())

        note = result.get("note", "")
        if note:
            content.append(Text(f"ℹ️ {note}", style="yellow"))

        return Panel(
            Group(*content),
            title="🗄️ Exploit-DB Search Results",
            border_style="yellow",
        )

    def _render_github_advisories(self, result: dict[str, Any]) -> Panel:
        """Render GitHub Security Advisories results."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="GitHub Advisories Search Failed",
                border_style="red",
            )

        content = []
        content.append(Text(f"Found {result.get('total_results', 0)} advisories", style="bold"))
        content.append(Text(f"Search URL: {result.get('search_url', 'N/A')}", style="dim"))
        content.append(Text())

        advisories = result.get("advisories", [])
        if advisories:
            table = Table(show_header=True, header_style="bold purple")
            table.add_column("GHSA ID", width=18)
            table.add_column("CVE", width=18)
            table.add_column("Severity", width=10)
            table.add_column("Summary", width=50)

            for advisory in advisories[:10]:
                severity = advisory.get("severity", "unknown")
                table.add_row(
                    advisory.get("ghsa_id", "N/A"),
                    advisory.get("cve_id") or "N/A",
                    Text(severity.upper(), style=self.SEVERITY_COLORS.get(severity, "white")),
                    advisory.get("summary", "")[:50],
                )

            content.append(table)
        else:
            content.append(Text("No advisories found", style="dim"))

        return Panel(
            Group(*content),
            title="🐙 GitHub Security Advisories",
            border_style="purple",
        )

    def _render_packetstorm(self, result: dict[str, Any]) -> Panel:
        """Render PacketStorm search results."""
        content = []
        content.append(Text(f"Query: {result.get('query', 'N/A')}", style="bold"))
        content.append(Text(f"Search URL: {result.get('search_url', 'N/A')}", style="dim"))
        content.append(Text())

        note = result.get("note", "")
        if note:
            content.append(Text(f"ℹ️ {note}", style="yellow"))
            content.append(Text())

        resources = result.get("additional_resources", [])
        if resources:
            content.append(Text("Additional Resources:", style="bold"))
            for res in resources:
                content.append(Text(f"  📁 {res.get('name', 'Unknown')}: {res.get('url', 'N/A')}", style="cyan"))

        return Panel(
            Group(*content),
            title="📦 PacketStorm Search",
            border_style="blue",
        )

    def _render_technology_vulns(self, result: dict[str, Any]) -> Panel:
        """Render aggregated technology vulnerability results."""
        if not result.get("success"):
            return Panel(
                Text(f"Error: {result.get('error', 'Unknown error')}", style="red"),
                title="Technology Vulnerability Search Failed",
                border_style="red",
            )

        content = []

        # Header
        header = Text()
        header.append(f"Technology: ", style="bold")
        header.append(f"{result.get('technology', 'Unknown')}", style="cyan bold")
        if result.get("version"):
            header.append(f" v{result.get('version')}")
        content.append(header)
        content.append(Text())

        # Summary stats
        summary = result.get("summary", {})
        stats_text = Text("Vulnerability Summary:\n", style="bold")
        stats_text.append(f"  Total CVEs: {summary.get('total_cves', 0)}\n")
        stats_text.append(f"  {self.SEVERITY_EMOJI['critical']} Critical: {summary.get('critical', 0)}  ")
        stats_text.append(f"{self.SEVERITY_EMOJI['high']} High: {summary.get('high', 0)}  ")
        stats_text.append(f"{self.SEVERITY_EMOJI['medium']} Medium: {summary.get('medium', 0)}  ")
        stats_text.append(f"{self.SEVERITY_EMOJI['low']} Low: {summary.get('low', 0)}\n")
        stats_text.append(f"  🔧 Public Exploits: {summary.get('exploits_available', 0)}")
        if summary.get("actively_exploited"):
            stats_text.append(" ⚠️ ACTIVELY EXPLOITED", style="red bold")
        content.append(stats_text)
        content.append(Text())

        # Recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            content.append(Text("Recommendations:", style="bold"))
            for rec in recommendations:
                if "CRITICAL" in rec:
                    content.append(Text(f"  🚨 {rec}", style="red bold"))
                elif "HIGH" in rec:
                    content.append(Text(f"  ⚠️ {rec}", style="red"))
                elif "WARNING" in rec:
                    content.append(Text(f"  ⚠️ {rec}", style="yellow"))
                else:
                    content.append(Text(f"  ℹ️ {rec}"))
            content.append(Text())

        # Sources queried
        sources = result.get("sources_queried", [])
        content.append(Text(f"Sources: {', '.join(sources)}", style="dim"))

        # Top CVEs table
        cves = result.get("cves", [])[:5]
        if cves:
            content.append(Text())
            content.append(Text("Top CVEs:", style="bold"))
            for cve in cves:
                severity = cve.get("severity", "unknown")
                cve_text = Text()
                cve_text.append(f"  {self.SEVERITY_EMOJI.get(severity, '⚪')} {cve.get('cve_id', 'Unknown')}")
                cve_text.append(f" - {cve.get('description', '')[:60]}...")
                content.append(cve_text)

        return Panel(
            Group(*content),
            title=f"🛡️ Vulnerability Assessment: {result.get('technology', 'Unknown')}",
            border_style="cyan",
        )

    def _render_generic(self, name: str, result: dict[str, Any]) -> Panel:
        """Render generic tool results."""
        import json
        content = json.dumps(result, indent=2, default=str)
        return Panel(
            Text(content),
            title=f"CVE Tool: {name}",
            border_style="blue",
        )
