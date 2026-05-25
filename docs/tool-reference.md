# Tool Reference

`arxiv-consensus-mcp` exposes a combined server plus the imported Consensus adapter tools.

## `arxiv_consensus_surface`

Returns server metadata, supported tool names, normalized fields, deduplication rule, and auth boundary.

Inputs: none.

Use it for:

- capability discovery;
- deployment diagnostics;
- checking whether `CONSENSUS_API_KEY` is configured;
- confirming which layer owns OAuth.

## `arxiv_search`

Searches the arXiv Atom API and returns normalized paper metadata.

Inputs:

| Name | Type | Default | Notes |
|---|---|---:|---|
| `query` | string | required | arXiv search query, including field syntax such as `cat:cs.OS`. |
| `start` | integer | `0` | Result offset. |
| `max_results` | integer | `10` | Clamped to `ARXIV_MCP_MAX_RESULTS_LIMIT`, default max `50`. |
| `sort_by` | string | `submittedDate` | `submittedDate`, `lastUpdatedDate`, or `relevance`. |
| `sort_order` | string | `descending` | `ascending` or `descending`. |

Output highlights:

- `ok`: request success flag.
- `items`: normalized arXiv paper records.
- `attempted_base_urls`: configured arXiv API endpoints.
- `failed_attempts`: fallback errors if one endpoint failed before another succeeded.

## `arxiv_consensus_search`

Runs arXiv search and, when enabled, Consensus quick search. It then normalizes and deduplicates the combined result list.

Inputs:

| Name | Type | Default | Notes |
|---|---|---:|---|
| `query` | string | required | Primary query. Used for arXiv and Consensus unless `consensus_query` is set. |
| `consensus_query` | string or null | `null` | Optional Consensus-specific query wording. |
| `arxiv_max_results` | integer | `10` | Passed to `arxiv_search.max_results`. |
| `include_consensus` | boolean | `true` | Set `false` for arXiv-only merged-shape output. |

Output highlights:

- `counts`: arXiv, Consensus, combined, and duplicate-exclusion counts.
- `items`: merged normalized records.
- `deduplication_decisions`: duplicate records excluded from `items`.
- `source_results`: metadata and error details from each upstream source.
- `gaps`: known operational gaps, such as missing Consensus credentials.

## `consensus_api_surface`

Returns Consensus adapter metadata, documented endpoints, supported query fields, response fields, and auth notes.

Inputs: none.

Use it before remote deployment to confirm:

- whether `CONSENSUS_API_KEY` is configured in the server process;
- which `CONSENSUS_AUTH_MODE` is active;
- what MCP exposure metadata is being reported.

## `consensus_quick_search`

Calls the documented Consensus `/v1/quick_search` endpoint and normalizes result records.

Inputs:

| Name | Type | Default |
|---|---|---:|
| `query` | string | required |
| `year_min` | integer or null | `null` |
| `year_max` | integer or null | `null` |
| `study_types` | list of strings or null | `null` |
| `human` | boolean or null | `null` |
| `sample_size_min` | integer or null | `null` |
| `sjr_max` | integer or null | `null` |
| `duration_min` | integer or null | `null` |
| `duration_max` | integer or null | `null` |
| `exclude_preprints` | boolean or null | `null` |
| `publisher_name` | string or null | `null` |
| `medical_mode` | boolean or null | `null` |

Allowed `study_types` values:

- `animal`
- `case report`
- `literature review`
- `meta-analysis`
- `non-rct experimental`
- `non-rct in vitro`
- `non-rct observational study`
- `rct`
- `systematic review`

## `consensus_request`

Calls a Consensus API path and returns parsed JSON. By default, only documented paths are enabled.

Inputs:

| Name | Type | Default | Notes |
|---|---|---:|---|
| `path` | string | required | API path, for example `/v1/quick_search`. |
| `method` | string | `GET` | HTTP method. |
| `query` | object or null | `null` | Query parameters. List values are sent with repeated keys. |
| `body` | object or null | `null` | JSON request body. |
| `allow_undocumented` | boolean or null | `null` | Overrides `CONSENSUS_ALLOW_UNDOCUMENTED`. |
| `auth_mode` | string or null | `null` | Overrides `CONSENSUS_AUTH_MODE`. |

Safety default:

- undocumented paths are rejected unless explicitly allowed;
- backend API credentials stay in the server environment and are not accepted from tool input.

## Deduplication Rule

Combined results are deduplicated in this order:

1. `arxiv_id`
2. `doi`
3. `url`
4. normalized `title`

Duplicates are excluded from `items` and reported in `deduplication_decisions`.
