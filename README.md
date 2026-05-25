
# arxiv-consensus-mcp

MCP server that searches public arXiv Atom metadata and, when configured with a server-side Consensus API key, searches the Consensus HTTP API. Results are normalized into one corpus-ingestion-friendly schema and deduplicated by arXiv ID, DOI, URL, then title.

## What It Exposes

- `arxiv_consensus_surface`: tool inventory, auth boundary, normalized field list.
- `arxiv_search`: arXiv Atom API search with normalized paper metadata.
- `arxiv_consensus_search`: combined arXiv + Consensus search, normalization, and deduplication.
- `consensus_api_surface`, `consensus_quick_search`, `consensus_request`: imported Consensus API adapter tools.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run Locally

arXiv search needs no API key:

```bash
python -m arxiv_consensus_mcp.server
```

Consensus search uses a backend secret held by the MCP server process:

```bash
CONSENSUS_API_KEY="replace-with-your-key" CONSENSUS_AUTH_MODE=x-api-key python -m arxiv_consensus_mcp.server
```

Register with a local MCP client by pointing the client command at the virtualenv Python and module:

```bash
codex mcp add arxiv-consensus -- /absolute/path/to/.venv/bin/python -m arxiv_consensus_mcp.server
```

## Auth Boundary

- arXiv metadata calls are public and unauthenticated.
- Consensus HTTP API calls use `CONSENSUS_API_KEY` with `CONSENSUS_AUTH_MODE`.
- OAuth for remote MCP clients belongs at the MCP gateway/resource-server layer, before this adapter receives tool calls.
- Do not forward end-user OAuth tokens to the Consensus API.

See `docs/oauth-gateway-boundary.md` for the deployment split.

## Environment

| Variable | Default | Meaning |
|---|---:|---|
| `ARXIV_API_BASE_URLS` | `https://export.arxiv.org/api/query,https://arxiv.org/api/query` | Comma-separated arXiv Atom endpoints |
| `ARXIV_CONSENSUS_USER_AGENT` | `ArxivConsensusMCP/0.1` | User-Agent for arXiv requests |
| `ARXIV_CONSENSUS_MCP_TRANSPORT` | `stdio` | FastMCP transport: `stdio`, `sse`, or `streamable-http` |
| `CONSENSUS_API_BASE_URL` | `https://api.consensus.app` | Consensus API origin |
| `CONSENSUS_API_KEY` | empty | Server-side Consensus API key |
| `CONSENSUS_AUTH_MODE` | `auto` | `auto`, `x-api-key`, `bearer`, or `both` |
| `CONSENSUS_ALLOW_UNDOCUMENTED` | `0` | Allows non-catalogued Consensus paths when set to `1` |

## Normalized Fields

`source`, `item_type`, `title`, `url`, `arxiv_id`, `doi`, `authors`, `abstract`, `year`, `journal`, `citation_count`, `study_type`, `takeaway`, `primary_metadata_source`, `missing_fields`.

## License

MIT. See `LICENSE`.
