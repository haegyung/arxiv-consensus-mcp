# Configuration

Configuration is done through environment variables.

## Local arXiv Defaults

| Variable | Default | Meaning |
|---|---:|---|
| `ARXIV_API_BASE_URLS` | `https://export.arxiv.org/api/query,https://arxiv.org/api/query` | Comma-separated arXiv Atom endpoints. |
| `ARXIV_CONSENSUS_USER_AGENT` | `ArxivConsensusMCP/0.1` | User-Agent for arXiv requests. |
| `ARXIV_MCP_MAX_RESULTS_LIMIT` | `50` | Maximum accepted `arxiv_search.max_results`. |
| `ARXIV_HTTP_TIMEOUT_SECONDS` | `20` | arXiv HTTP timeout. |

arXiv does not require an API key.

## Consensus API

| Variable | Default | Meaning |
|---|---:|---|
| `CONSENSUS_API_BASE_URL` | `https://api.consensus.app` | Consensus API origin. |
| `CONSENSUS_API_KEY` | empty | Backend API key held by the MCP server process. |
| `CONSENSUS_AUTH_MODE` | `auto` | Header strategy: `auto`, `x-api-key`, `bearer`, or `both`. |
| `CONSENSUS_USER_AGENT` | `ConsensusMCPAdapter/0.1` | User-Agent for Consensus requests. |
| `CONSENSUS_ALLOW_UNDOCUMENTED` | `0` | Allows non-catalogued Consensus paths when set to `1`, `true`, or `yes`. |

`CONSENSUS_AUTH_MODE=auto` tries bearer and `x-api-key` variants. If the API account requires a specific header, set the mode explicitly.

## MCP Transport

| Variable | Default | Meaning |
|---|---:|---|
| `ARXIV_CONSENSUS_MCP_TRANSPORT` | `stdio` | Transport for the combined server. |
| `CONSENSUS_MCP_TRANSPORT` | `stdio` | Transport for the standalone Consensus adapter. |

Allowed values:

- `stdio`
- `sse`
- `streamable-http`

Local development should normally use `stdio`.

## Remote Exposure Metadata

These variables do not enforce OAuth by themselves. They let the server report how it is expected to be protected in a remote deployment.

| Variable | Default | Meaning |
|---|---:|---|
| `CONSENSUS_MCP_EXPOSURE_MODE` | `stdio-local` | Descriptive marker such as `remote-oauth-gateway`. |
| `CONSENSUS_MCP_RESOURCE_URL` | empty | Protected MCP resource URL metadata. |
| `CONSENSUS_MCP_ISSUER_URL` | empty | OAuth issuer metadata. |
| `CONSENSUS_MCP_REQUIRED_SCOPES` | empty | Comma-separated required MCP scopes metadata. |

For remote deployments, enforce OAuth or bearer-token validation before traffic reaches the MCP adapter.

## Example: Local arXiv-Only

```bash
python -m arxiv_consensus_mcp.server
```

## Example: Local arXiv Plus Consensus

```bash
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=x-api-key \
python -m arxiv_consensus_mcp.server
```

## Example: Remote Metadata Behind A Gateway

```bash
ARXIV_CONSENSUS_MCP_TRANSPORT=streamable-http \
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=x-api-key \
CONSENSUS_MCP_EXPOSURE_MODE=remote-oauth-gateway \
CONSENSUS_MCP_RESOURCE_URL=https://mcp.example.com/arxiv-consensus \
CONSENSUS_MCP_ISSUER_URL=https://issuer.example.com/ \
CONSENSUS_MCP_REQUIRED_SCOPES=research.search,research.read \
python -m arxiv_consensus_mcp.server
```

Do not expose `streamable-http` directly on an untrusted network without a gateway or resource-server token verifier.
