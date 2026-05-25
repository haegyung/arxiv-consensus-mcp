import unittest

from arxiv_consensus_mcp.consensus_api_adapter import consensus_api_surface
from arxiv_consensus_mcp.server import arxiv_consensus_surface


class SurfaceTests(unittest.TestCase):
    def test_combined_surface_exposes_expected_tools(self) -> None:
        surface = arxiv_consensus_surface()

        self.assertTrue(surface["ok"])
        self.assertEqual(surface["mcp_server"], "Arxiv_Consensus_MCP")
        self.assertIn("arxiv_search", surface["tools"])
        self.assertIn("arxiv_consensus_search", surface["tools"])
        self.assertEqual(surface["dedupe_rule"], "arxiv_id, then doi, then url, then normalized title")

    def test_consensus_surface_keeps_oauth_outside_adapter(self) -> None:
        surface = consensus_api_surface()
        auth_layers = surface["auth_layers"]

        self.assertTrue(surface["ok"])
        self.assertFalse(auth_layers["consensus_backend_api"]["oauth_supported_here"])
        self.assertEqual(
            auth_layers["mcp_client_boundary"]["oauth_boundary"],
            "gateway_or_fastmcp_resource_server",
        )


if __name__ == "__main__":
    unittest.main()
