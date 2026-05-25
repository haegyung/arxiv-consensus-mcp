# arxiv-consensus-mcp

`arxiv-consensus-mcp` is a small Model Context Protocol (MCP) server for research collection workflows that need both public arXiv metadata and Consensus API search results in one normalized shape.

It is designed for agents that collect papers, compare research sources, build corpus-ingestion queues, or prepare literature-review material without mixing client OAuth concerns with backend API-key handling.

한국어 안내는 [시작하기 (한국어)](docs/getting-started.ko.md)를 참고하세요. 아래에도 빠른 설치와 인증 경계를 함께 적어 두었습니다.

## What It Does

- Searches the public arXiv Atom API without an API key.
- Searches the Consensus HTTP API when `CONSENSUS_API_KEY` is configured.
- Normalizes arXiv and Consensus records into one paper-oriented schema.
- Deduplicates merged results by arXiv ID, DOI, URL, then normalized title.
- Exposes the auth boundary clearly: MCP client authorization belongs at the gateway/resource-server layer; Consensus backend calls use a server-held API key.

## When To Use It

Use this server when you want an MCP client or agent to:

- collect candidate papers from arXiv and Consensus in the same run;
- keep arXiv available even when Consensus credentials are not configured;
- normalize metadata before later corpus ingestion or review;
- keep backend Consensus API keys out of client prompts, logs, and user sessions;
- add OAuth or bearer-token protection at a remote MCP gateway without forwarding end-user tokens to Consensus.

## Exposed MCP Tools

| Tool | Purpose |
|---|---|
| `arxiv_consensus_surface` | Returns server capabilities, supported fields, auth boundary, and normalization rules. |
| `arxiv_search` | Searches arXiv Atom metadata and returns normalized paper records. |
| `arxiv_consensus_search` | Searches arXiv plus optional Consensus, merges results, and reports deduplication decisions. |
| `consensus_api_surface` | Returns Consensus adapter capabilities, documented endpoint list, and auth notes. |
| `consensus_quick_search` | Calls the documented Consensus `/v1/quick_search` endpoint. |
| `consensus_request` | Calls a Consensus API path, guarded by documented-mode defaults unless explicitly allowed. |

## Quick Start

Install directly from GitHub:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install "git+https://github.com/haegyung/arxiv-consensus-mcp.git"
```

Or clone the repository and install in editable mode:

```bash
git clone https://github.com/haegyung/arxiv-consensus-mcp.git
cd arxiv-consensus-mcp
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Run the combined MCP server over stdio:

```bash
python -m arxiv_consensus_mcp.server
```

Register it with a local MCP client:

```bash
codex mcp add arxiv-consensus -- /absolute/path/to/.venv/bin/python -m arxiv_consensus_mcp.server
```

arXiv search works without credentials. To enable Consensus search, run the server with a backend key:

```bash
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=x-api-key \
python -m arxiv_consensus_mcp.server
```

## 한국어 빠른 안내

`arxiv-consensus-mcp`는 arXiv 공개 메타데이터와 Consensus API 검색 결과를 한 번에 가져와 같은 필드 구조로 정리해 주는 MCP 서버입니다.

- arXiv 검색은 API 키 없이 바로 사용할 수 있습니다.
- Consensus 검색은 서버 실행 환경에 `CONSENSUS_API_KEY`를 넣었을 때 함께 동작합니다.
- 사용자 OAuth 토큰은 Consensus API로 넘기지 않습니다. 원격으로 배포할 때 OAuth가 필요하면 MCP 서버 앞단의 gateway 또는 resource-server 계층에서 검사합니다.

GitHub에서 바로 설치하려면:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install "git+https://github.com/haegyung/arxiv-consensus-mcp.git"
```

로컬 MCP 클라이언트에 등록하려면:

```bash
codex mcp add arxiv-consensus -- /absolute/path/to/.venv/bin/python -m arxiv_consensus_mcp.server
```

Consensus까지 함께 쓰려면 서버를 실행할 때 backend API 키를 환경 변수로 전달합니다:

```bash
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=auto \
python -m arxiv_consensus_mcp.server
```

처음에는 MCP 클라이언트에서 다음처럼 확인하면 됩니다:

```text
Call arxiv_consensus_surface and summarize the available tools.
```

자세한 한국어 설치 절차와 문제 해결은 [docs/getting-started.ko.md](docs/getting-started.ko.md)에 있습니다.

## Example Prompts

After registering the server, ask your MCP client for tasks like:

```text
Use arxiv_consensus_search to find recent papers on persistent memory indexing.
Return normalized fields and deduplication decisions.
```

```text
Use arxiv_search for cs.OS papers about scheduler isolation.
Sort by submittedDate descending and return 10 results.
```

```text
Call arxiv_consensus_surface and explain which auth layer owns OAuth.
```

## Normalized Paper Fields

The combined tools return a corpus-ingestion-friendly record shape:

| Field | Meaning |
|---|---|
| `source` | `arxiv` or `consensus`. |
| `item_type` | Currently `paper`. |
| `title` | Paper title. |
| `url` | Source URL. |
| `arxiv_id` | arXiv identifier when available. |
| `doi` | DOI when available. |
| `authors` | Author list. |
| `abstract` | Abstract or summary text. |
| `year` | Publication year when available. |
| `journal` | Journal name when available from Consensus. |
| `citation_count` | Citation count when available from Consensus. |
| `study_type` | Study type when available from Consensus. |
| `takeaway` | Consensus takeaway when available. |
| `primary_metadata_source` | Source-specific metadata provenance. |
| `missing_fields` | Fields missing from the normalized record. |

## Documentation

- [Getting started](docs/getting-started.md): install, run, register, and make first calls.
- [시작하기 (한국어)](docs/getting-started.ko.md): 한국어 설치, 실행, 등록, 첫 호출 안내.
- [Tool reference](docs/tool-reference.md): tool inputs, outputs, and behavior.
- [Configuration](docs/configuration.md): environment variables and auth modes.
- [OAuth gateway boundary](docs/oauth-gateway-boundary.md): how to protect a remote MCP deployment.

## Security And Auth Boundary

- arXiv calls are public and unauthenticated.
- Consensus calls use `CONSENSUS_API_KEY` held by the MCP server process.
- Do not pass end-user OAuth tokens to the Consensus API.
- For remote deployments, put OAuth or bearer-token validation in front of this server through an MCP gateway, reverse proxy, or FastMCP HTTP resource-server layer.
- Keep `.env` files out of git; the included `.gitignore` excludes `.env` and `.env.*`.

## Environment

| Variable | Default | Meaning |
|---|---:|---|
| `ARXIV_API_BASE_URLS` | `https://export.arxiv.org/api/query,https://arxiv.org/api/query` | Comma-separated arXiv Atom endpoints. |
| `ARXIV_CONSENSUS_USER_AGENT` | `ArxivConsensusMCP/0.1` | User-Agent for arXiv requests. |
| `ARXIV_CONSENSUS_MCP_TRANSPORT` | `stdio` | FastMCP transport: `stdio`, `sse`, or `streamable-http`. |
| `ARXIV_MCP_MAX_RESULTS_LIMIT` | `50` | Upper bound for `arxiv_search.max_results`. |
| `ARXIV_HTTP_TIMEOUT_SECONDS` | `20` | arXiv HTTP timeout. |
| `CONSENSUS_API_BASE_URL` | `https://api.consensus.app` | Consensus API origin. |
| `CONSENSUS_API_KEY` | empty | Server-side Consensus API key. |
| `CONSENSUS_AUTH_MODE` | `auto` | `auto`, `x-api-key`, `bearer`, or `both`. |
| `CONSENSUS_ALLOW_UNDOCUMENTED` | `0` | Allows non-catalogued Consensus paths when set to `1`. |
| `CONSENSUS_MCP_TRANSPORT` | `stdio` | Transport for the standalone Consensus adapter. |
| `CONSENSUS_MCP_EXPOSURE_MODE` | `stdio-local` | Metadata marker for local or remote exposure mode. |
| `CONSENSUS_MCP_RESOURCE_URL` | empty | Optional protected MCP resource URL metadata. |
| `CONSENSUS_MCP_ISSUER_URL` | empty | Optional OAuth issuer metadata. |
| `CONSENSUS_MCP_REQUIRED_SCOPES` | empty | Optional comma-separated MCP scopes metadata. |

## Development Checks

Run a syntax check:

```bash
python -m py_compile \
  src/arxiv_consensus_mcp/server.py \
  src/arxiv_consensus_mcp/consensus_api_adapter.py
```

Run a quick import smoke:

```bash
PYTHONPATH=src python - <<'PY'
from arxiv_consensus_mcp.server import arxiv_consensus_surface
surface = arxiv_consensus_surface()
print(surface["ok"], surface["mcp_server"], surface["transport"])
PY
```

Expected output:

```text
True Arxiv_Consensus_MCP stdio
```

Run the local unit tests:

```bash
python -m unittest discover -s tests
```

## Current Limitations

- Consensus search requires a valid Consensus API key.
- Only the documented Consensus `/v1/quick_search` endpoint is enabled by default.
- `consensus_request` can call other paths only when `CONSENSUS_ALLOW_UNDOCUMENTED=1` or `allow_undocumented=true` is explicitly set.
- Remote OAuth enforcement is not implemented inside the local stdio adapter; it belongs to the deployment gateway/resource-server layer.

## Troubleshooting

- If the MCP client cannot start the server, verify that the client command points to the virtualenv Python that installed this package.
- If arXiv requests fail, retry with the default endpoint list and check local network access to `export.arxiv.org`.
- If Consensus returns `401` or `403`, check `CONSENSUS_API_KEY` and try `CONSENSUS_AUTH_MODE=auto`, `x-api-key`, or `bearer`.
- If remote clients need OAuth, put the server behind a gateway/resource-server layer instead of forwarding user OAuth tokens to Consensus.

## License

MIT. See [LICENSE](LICENSE).
