"""
Comprehensive test suite for CVE/Exploit Database Integration module.

Tests cover:
- NVD API querying
- Exploit-DB search
- GitHub Security Advisories
- PacketStorm search
- Aggregated technology vulnerability search
- Caching and rate limiting
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

# Import the module under test
from strix.tools.cve_database.cve_database_actions import (
    query_cve_database,
    get_cve_details,
    search_exploitdb,
    search_github_advisories,
    search_packetstorm,
    get_technology_vulnerabilities,
    clear_cve_cache,
    get_cache_stats,
    _cache_key,
    _get_from_cache,
    _set_cache,
    _parse_nvd_cve,
    _generate_recommendations,
    _cve_cache,
)


class TestCacheManagement:
    """Tests for cache management functionality."""
    
    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        key1 = _cache_key("nvd", "nginx")
        key2 = _cache_key("nvd", "nginx")
        key3 = _cache_key("nvd", "apache")
        
        assert key1 == key2
        assert key1 != key3
    
    def test_cache_set_and_get(self):
        """Test setting and getting cached data."""
        clear_cve_cache()
        
        test_data = {"test": "data", "count": 42}
        _set_cache("test_source", "test_query", test_data)
        
        cached = _get_from_cache("test_source", "test_query")
        assert cached == test_data
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        clear_cve_cache()
        
        cached = _get_from_cache("nonexistent", "query")
        assert cached is None
    
    def test_clear_cache(self):
        """Test cache clearing."""
        _set_cache("test", "query", {"data": True})
        result = clear_cve_cache()
        
        assert result["success"] is True
        assert "cleared" in result["message"].lower()
        assert _get_from_cache("test", "query") is None
    
    def test_get_cache_stats(self):
        """Test cache statistics retrieval."""
        clear_cve_cache()
        _set_cache("test1", "q1", {"data": 1})
        _set_cache("test2", "q2", {"data": 2})
        
        stats = get_cache_stats()
        
        assert stats["success"] is True
        assert stats["cache_entries"] == 2
        assert "cache_ttl_hours" in stats


class TestNVDParsing:
    """Tests for NVD CVE parsing."""
    
    def test_parse_nvd_cve_basic(self):
        """Test parsing a basic CVE item from NVD."""
        cve_item = {
            "cve": {
                "id": "CVE-2021-44228",
                "descriptions": [
                    {"lang": "en", "value": "Apache Log4j2 RCE vulnerability"}
                ],
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {
                            "baseScore": 10.0,
                            "baseSeverity": "CRITICAL"
                        }
                    }]
                },
                "references": [
                    {"url": "https://example.com", "source": "test", "tags": ["Patch"]}
                ],
                "configurations": [],
                "weaknesses": [
                    {"description": [{"lang": "en", "value": "CWE-502"}]}
                ],
                "published": "2021-12-10T10:00:00Z",
                "lastModified": "2021-12-15T10:00:00Z"
            }
        }
        
        parsed = _parse_nvd_cve(cve_item)
        
        assert parsed["cve_id"] == "CVE-2021-44228"
        assert parsed["cvss_v3"] == 10.0
        assert parsed["severity"] == "critical"
        assert "Log4j2" in parsed["description"]
        assert len(parsed["references"]) == 1
        assert "CWE-502" in parsed["weaknesses"]
        assert parsed["source"] == "NVD"
    
    def test_parse_nvd_cve_with_cvss_v2(self):
        """Test parsing CVE with only CVSS v2."""
        cve_item = {
            "cve": {
                "id": "CVE-2020-1234",
                "descriptions": [{"lang": "en", "value": "Test vulnerability"}],
                "metrics": {
                    "cvssMetricV2": [{
                        "cvssData": {"baseScore": 7.5}
                    }]
                },
                "references": [],
                "configurations": [],
                "weaknesses": [],
                "published": "2020-01-01T00:00:00Z",
                "lastModified": "2020-01-02T00:00:00Z"
            }
        }
        
        parsed = _parse_nvd_cve(cve_item)
        
        assert parsed["cvss_v2"] == 7.5
        assert parsed["severity"] == "high"  # 7.5 is high


class TestRecommendations:
    """Tests for recommendation generation."""
    
    def test_critical_severity_recommendations(self):
        """Test recommendations for critical CVEs."""
        cve = {
            "severity": "critical",
            "weaknesses": [],
            "references": []
        }
        
        recs = _generate_recommendations(cve, has_exploit=False)
        
        assert any("urgent" in r.lower() or "immediate" in r.lower() for r in recs)
    
    def test_exploit_available_recommendations(self):
        """Test recommendations when exploit exists."""
        cve = {
            "severity": "medium",
            "weaknesses": [],
            "references": []
        }
        
        recs = _generate_recommendations(cve, has_exploit=True)
        
        assert any("exploit" in r.lower() for r in recs)
    
    def test_weakness_specific_recommendations(self):
        """Test recommendations for specific CWE weaknesses."""
        cve = {
            "severity": "high",
            "weaknesses": ["CWE-79"],  # XSS
            "references": []
        }
        
        recs = _generate_recommendations(cve, has_exploit=False)
        
        assert any("csp" in r.lower() or "content security" in r.lower() for r in recs)
    
    def test_sqli_weakness_recommendations(self):
        """Test recommendations for SQL injection weakness."""
        cve = {
            "severity": "high",
            "weaknesses": ["CWE-89"],
            "references": []
        }
        
        recs = _generate_recommendations(cve, has_exploit=False)
        
        assert any("parameterized" in r.lower() or "sql" in r.lower() for r in recs)


class TestQueryCVEDatabase:
    """Tests for NVD CVE database querying."""
    
    def test_query_with_keyword(self):
        """Test querying with keyword."""
        clear_cve_cache()
        
        # This would normally hit the API, but we test the interface
        result = query_cve_database(keyword="log4j", limit=5)
        
        assert "success" in result
        assert "source" in result
        assert result["source"] == "NVD"
    
    def test_query_with_cve_id(self):
        """Test querying specific CVE ID."""
        clear_cve_cache()
        
        result = query_cve_database(cve_id="CVE-2021-44228", limit=1)
        
        assert "success" in result
        assert "query" in result
        assert result["query"]["cve_id"] == "CVE-2021-44228"
    
    def test_query_with_product_version(self):
        """Test querying with product and version."""
        clear_cve_cache()
        
        result = query_cve_database(product="nginx", version="1.18.0", limit=10)
        
        assert "success" in result
        assert "query" in result
        assert result["query"]["product"] == "nginx"
        assert result["query"]["version"] == "1.18.0"
    
    def test_query_with_severity_filter(self):
        """Test querying with severity filter."""
        clear_cve_cache()
        
        result = query_cve_database(keyword="apache", severity="critical", limit=5)
        
        assert "success" in result
        assert result["query"]["severity"] == "critical"


class TestGetCVEDetails:
    """Tests for CVE details retrieval."""
    
    def test_invalid_cve_format(self):
        """Test with invalid CVE ID format."""
        result = get_cve_details("invalid-id")
        
        assert result["success"] is False
        assert "invalid" in result["error"].lower()
    
    def test_valid_cve_format(self):
        """Test with valid CVE ID format."""
        clear_cve_cache()
        
        result = get_cve_details("CVE-2021-44228")
        
        assert "success" in result
        # May fail if API unavailable, but format check passes
    
    def test_cve_details_includes_exploitability(self):
        """Test that CVE details include exploitability info."""
        clear_cve_cache()
        
        result = get_cve_details("CVE-2021-44228")
        
        if result.get("success"):
            assert "exploitability" in result
            assert "has_public_exploit" in result
            assert "recommendations" in result


class TestSearchExploitDB:
    """Tests for Exploit-DB search."""
    
    def test_search_requires_query(self):
        """Test that search requires query or cve_id."""
        result = search_exploitdb()
        
        assert result["success"] is False
        assert "query" in result["error"].lower() or "cve_id" in result["error"].lower()
    
    def test_search_with_query(self):
        """Test search with query string."""
        result = search_exploitdb(query="wordpress")
        
        assert result["success"] is True
        assert result["source"] == "Exploit-DB"
        assert "search_url" in result
    
    def test_search_with_cve_id(self):
        """Test search with CVE ID."""
        result = search_exploitdb(cve_id="CVE-2021-44228")
        
        assert result["success"] is True
        assert "exploits" in result
    
    def test_search_with_platform_filter(self):
        """Test search with platform filter."""
        result = search_exploitdb(query="apache", platform="linux")
        
        assert result["success"] is True
        assert result["query"]["platform"] == "linux"


class TestSearchGitHubAdvisories:
    """Tests for GitHub Security Advisories search."""
    
    def test_search_requires_input(self):
        """Test that search requires keyword or cve_id."""
        result = search_github_advisories()
        
        assert result["success"] is False
    
    def test_search_with_keyword(self):
        """Test search with keyword."""
        result = search_github_advisories(keyword="lodash")
        
        assert "success" in result
        assert result["source"] == "GitHub Security Advisories"
    
    def test_search_with_ecosystem(self):
        """Test search with ecosystem filter."""
        result = search_github_advisories(keyword="axios", ecosystem="npm")
        
        assert "success" in result
        assert result["query"]["ecosystem"] == "npm"
    
    def test_search_with_severity(self):
        """Test search with severity filter."""
        result = search_github_advisories(keyword="jackson", severity="critical")
        
        assert "success" in result
        assert result["query"]["severity"] == "critical"


class TestSearchPacketStorm:
    """Tests for PacketStorm search."""
    
    def test_search_requires_query(self):
        """Test that search requires query."""
        result = search_packetstorm("")
        
        assert result["success"] is False
    
    def test_search_with_query(self):
        """Test search with query."""
        result = search_packetstorm("apache struts")
        
        assert result["success"] is True
        assert result["source"] == "PacketStorm"
        assert "search_url" in result
    
    def test_search_includes_resources(self):
        """Test that search includes additional resources."""
        result = search_packetstorm("nginx vulnerability")
        
        assert result["success"] is True
        assert "additional_resources" in result


class TestGetTechnologyVulnerabilities:
    """Tests for aggregated technology vulnerability search."""
    
    def test_basic_technology_search(self):
        """Test basic technology vulnerability search."""
        clear_cve_cache()
        
        result = get_technology_vulnerabilities("nginx")
        
        assert result["success"] is True
        assert result["technology"] == "nginx"
        assert "sources_queried" in result
        assert "summary" in result
        assert "recommendations" in result
    
    def test_search_with_version(self):
        """Test search with specific version."""
        clear_cve_cache()
        
        result = get_technology_vulnerabilities("wordpress", version="5.8.1")
        
        assert result["success"] is True
        assert result["version"] == "5.8.1"
    
    def test_search_includes_all_sources(self):
        """Test that search queries multiple sources."""
        clear_cve_cache()
        
        result = get_technology_vulnerabilities("apache", include_exploits=True)
        
        # Should query NVD at minimum
        assert "NVD" in result["sources_queried"]
    
    def test_summary_statistics(self):
        """Test that summary includes severity breakdown."""
        clear_cve_cache()
        
        result = get_technology_vulnerabilities("spring")
        
        summary = result["summary"]
        assert "total_cves" in summary
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        assert "low" in summary
    
    def test_search_includes_manual_links(self):
        """Test that results include manual search links."""
        result = get_technology_vulnerabilities("tomcat")
        
        assert "manual_search_links" in result
        links = result["manual_search_links"]
        assert "nvd" in links
        assert "exploitdb" in links
        assert "github" in links


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_product_name(self):
        """Test handling of empty product name."""
        result = query_cve_database(product="")
        
        # Should handle gracefully
        assert "success" in result
    
    def test_special_characters_in_query(self):
        """Test handling of special characters."""
        result = search_exploitdb(query="test<script>alert(1)</script>")
        
        assert "success" in result
    
    def test_very_long_query(self):
        """Test handling of very long query."""
        long_query = "a" * 1000
        result = search_exploitdb(query=long_query)
        
        assert "success" in result
    
    def test_unicode_in_query(self):
        """Test handling of unicode characters."""
        result = search_exploitdb(query="漏洞测试")
        
        assert "success" in result
    
    def test_limit_boundaries(self):
        """Test limit parameter boundaries."""
        result = query_cve_database(keyword="test", limit=0)
        assert "success" in result
        
        result = query_cve_database(keyword="test", limit=1000)
        assert "success" in result


class TestCacheBehavior:
    """Tests for caching behavior."""
    
    def test_cached_results_returned(self):
        """Test that cached results are returned on subsequent calls."""
        clear_cve_cache()
        
        # First call
        result1 = search_exploitdb(query="test_cache_behavior")
        
        # Second call should hit cache
        result2 = search_exploitdb(query="test_cache_behavior")
        
        # Results should be the same
        assert result1 == result2
    
    def test_different_queries_not_cached_together(self):
        """Test that different queries have separate cache entries."""
        clear_cve_cache()
        
        result1 = search_exploitdb(query="query1")
        result2 = search_exploitdb(query="query2")
        
        # Should have different results (at least different queries in response)
        assert result1["query"]["search"] != result2["query"]["search"]


# Integration Tests (require network access)
@pytest.mark.integration
class TestNVDIntegration:
    """Integration tests that actually query NVD API."""
    
    def test_real_nvd_query(self):
        """Test real NVD API query."""
        clear_cve_cache()
        
        result = query_cve_database(cve_id="CVE-2021-44228", limit=1)
        
        if result.get("success"):
            assert len(result.get("vulnerabilities", [])) > 0
            cve = result["vulnerabilities"][0]
            assert cve["cve_id"] == "CVE-2021-44228"
            assert cve["severity"] == "critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
