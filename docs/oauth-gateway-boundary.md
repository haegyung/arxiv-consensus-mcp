# Consensus API MCP OAuth Gateway Boundary

## Goal

Custom MCP가 Consensus HTTP API 전체 표면을 직접 호출하되, Consensus API 인증과 MCP client 인증을 섞지 않는다.

## 결정

- Consensus API 호출부는 backend secret 기반이다: `CONSENSUS_API_KEY` + `CONSENSUS_AUTH_MODE`.
- MCP client 보호는 MCP 노출부에 둔다: OAuth/Bearer 검증은 gateway, reverse proxy, 또는 FastMCP HTTP resource-server/token-verifier가 맡는다.
- Consensus 사용자 OAuth token을 Consensus API로 forward하지 않는다.
- local 개발 기본값은 `stdio`다. `stdio` adapter 자체는 OAuth resource server가 아니다.

## Target Architecture

```text
MCP client
  -> OAuth authorization flow / bearer token
  -> protected MCP gateway or FastMCP streamable-http resource server
  -> consensus_api_adapter.py
  -> Consensus HTTP API
```

## Layer Contract

| Layer | Owner | Auth material | Enforcement |
|---|---|---|---|
| MCP client boundary | MCP gateway/resource server | OAuth access token or bearer token | Validate issuer, audience/resource, expiry, scopes |
| Custom MCP adapter | `mcp/consensus_api_adapter.py` | none from end user | Expose tools, normalize requests, never leak backend key |
| Consensus HTTP API | Consensus API | `CONSENSUS_API_KEY` | Send `Authorization: Bearer`, `x-api-key`, or both based on `CONSENSUS_AUTH_MODE` |

## Adapter Environment

| Variable | Default | Meaning |
|---|---:|---|
| `CONSENSUS_API_BASE_URL` | `https://api.consensus.app` | Consensus API origin |
| `CONSENSUS_API_KEY` | empty | Backend API secret |
| `CONSENSUS_AUTH_MODE` | `auto` | `auto`, `x-api-key`, `bearer`, or `both` |
| `CONSENSUS_ALLOW_UNDOCUMENTED` | `0` | Allows non-catalogued paths when set to `1` |
| `CONSENSUS_MCP_TRANSPORT` | `stdio` | FastMCP transport, including `streamable-http` for HTTP exposure |
| `CONSENSUS_MCP_EXPOSURE_MODE` | `stdio-local` | Descriptive boundary marker, e.g. `remote-oauth-gateway` |
| `CONSENSUS_MCP_RESOURCE_URL` | empty | Remote MCP resource URL metadata |
| `CONSENSUS_MCP_ISSUER_URL` | empty | OAuth issuer metadata |
| `CONSENSUS_MCP_REQUIRED_SCOPES` | empty | Comma-separated required MCP scopes metadata |

## Local Mode

Use a local virtual environment and run the package module over stdio.

```bash
CONSENSUS_API_KEY=... \
CONSENSUS_AUTH_MODE=x-api-key \
python -m arxiv_consensus_mcp.consensus_api_adapter
```

This mode is local process-to-process MCP. It does not provide OAuth by itself.

## Remote Protected Mode

Use one of these enforcement points:

1. Put the adapter behind an OAuth-aware MCP gateway or reverse proxy.
2. Run FastMCP over `streamable-http` and attach a token verifier/resource-server layer.

Recommended metadata for this mode:

```bash
CONSENSUS_MCP_TRANSPORT=streamable-http
CONSENSUS_MCP_EXPOSURE_MODE=remote-oauth-gateway
CONSENSUS_MCP_RESOURCE_URL=https://example.internal/mcp/consensus
CONSENSUS_MCP_ISSUER_URL=https://issuer.example/
CONSENSUS_MCP_REQUIRED_SCOPES=consensus.search,consensus.read
```

Do not expose `streamable-http` directly on an untrusted network unless the gateway/token-verifier layer is active.

## Verification Checklist

- `consensus_api_surface()` reports `consensus_backend_api.oauth_supported_here=false`.
- `consensus_api_surface()` reports the configured MCP exposure metadata.
- A missing `CONSENSUS_API_KEY` fails at Consensus API with `401` or `403`, not inside OAuth.
- Remote OAuth tests validate rejection before the adapter receives a tool call.
