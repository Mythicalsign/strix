"""
CVE/Exploit Database Integration Module.

This module provides tools for querying vulnerability databases and exploit repositories
to help AI agents find and use known vulnerabilities for identified technologies.

Features:
- Query NVD (National Vulnerability Database) for CVEs by technology/version
- Search Exploit-DB for PoCs and exploits
- Search GitHub Security Advisories
- Search PacketStorm for exploits and tools
- Aggregate vulnerability data from multiple sources
- Cache results for performance
"""

from .cve_database_actions import (
    get_cve_details,
    get_technology_vulnerabilities,
    query_cve_database,
    search_exploitdb,
    search_github_advisories,
    search_packetstorm,
)


__all__ = [
    "query_cve_database",
    "search_exploitdb",
    "get_cve_details",
    "search_github_advisories",
    "get_technology_vulnerabilities",
    "search_packetstorm",
]
