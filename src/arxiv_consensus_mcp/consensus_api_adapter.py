#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Consensus_API_Adapter")

API_BASE_URL = os.environ.get("CONSENSUS_API_BASE_URL", "https://api.consensus.app").rstrip("/")
API_KEY = os.environ.get("CONSENSUS_API_KEY", "").strip()
AUTH_MODE = os.environ.get("CONSENSUS_AUTH_MODE", "auto").strip().lower()
ALLOW_UNDOCUMENTED = os.environ.get("CONSENSUS_ALLOW_UNDOCUMENTED", "0").strip() in {"1", "true", "yes"}
USER_AGENT = os.environ.get("CONSENSUS_USER_AGENT", "ConsensusMCPAdapter/0.1")
MCP_TRANSPORT = os.environ.get("CONSENSUS_MCP_TRANSPORT", "stdio").strip().lower()
MCP_EXPOSURE_MODE = os.environ.get("CONSENSUS_MCP_EXPOSURE_MODE", "stdio-local").strip().lower()
MCP_RESOURCE_URL = os.environ.get("CONSENSUS_MCP_RESOURCE_URL", "").strip()
MCP_ISSUER_URL = os.environ.get("CONSENSUS_MCP_ISSUER_URL", "").strip()
MCP_REQUIRED_SCOPES = [
    scope.strip()
    for scope in os.environ.get("CONSENSUS_MCP_REQUIRED_SCOPES", "").split(",")
    if scope.strip()
]
VALID_MCP_TRANSPORTS = {"stdio", "sse", "streamable-http"}

DOCUMENTED_ENDPOINTS: dict[str, dict[str, Any]] = {
    "/v1/quick_search": {
        "method": "GET",
        "summary": "Query for relevant papers.",
        "description": "Search peer-reviewed papers using the documented Consensus API quick_search endpoint.",
    }
}

STUDY_TYPE_ENUM = {
    "case report",
    "literature review",
    "meta-analysis",
    "non-rct experimental",
    "non-rct in vitro",
    "non-rct observational study",
    "rct",
    "systematic review",
    "animal",
}


class ConsensusAPIError(RuntimeError):
    pass


def _clean_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _clean_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    raise ConsensusAPIError(f"Invalid boolean value: {value!r}")


def _normalize_study_types(study_types: list[str] | None) -> list[str] | None:
    if study_types is None:
        return None
    normalized = []
    invalid = []
    for item in study_types:
        value = item.strip().lower()
        if value not in STUDY_TYPE_ENUM:
            invalid.append(item)
        else:
            normalized.append(value)
    if invalid:
        allowed = ", ".join(sorted(STUDY_TYPE_ENUM))
        raise ConsensusAPIError(f"Invalid study_types values: {invalid!r}. Allowed: {allowed}")
    return normalized


def _build_query_params(**kwargs: Any) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                params.append((key, str(item)))
        else:
            params.append((key, str(value)))
    return params


def _auth_header_variants(auth_mode: str) -> list[dict[str, str]]:
    if not API_KEY:
        return [{}]

    modes = []
    if auth_mode in {"auto", "bearer", "both"}:
        modes.append("bearer")
    if auth_mode in {"auto", "x-api-key", "both"}:
        modes.append("x-api-key")

    variants: list[dict[str, str]] = []
    for mode in modes:
        if mode == "bearer":
            variants.append({"Authorization": f"Bearer {API_KEY}"})
        elif mode == "x-api-key":
            variants.append({"x-api-key": API_KEY})

    if auth_mode == "both":
        variants.append({"Authorization": f"Bearer {API_KEY}", "x-api-key": API_KEY})

    deduped: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for headers in variants:
        fingerprint = tuple(sorted(headers.items()))
        if fingerprint not in seen:
            seen.add(fingerprint)
            deduped.append(headers)
    return deduped or [{}]


def _request_json(
    path: str,
    *,
    method: str = "GET",
    query: list[tuple[str, str]] | None = None,
    body: dict[str, Any] | None = None,
    auth_mode: str = AUTH_MODE,
    allow_undocumented: bool = ALLOW_UNDOCUMENTED,
    timeout_seconds: int = 45,
    max_retries: int = 2,
) -> dict[str, Any]:
    normalized_path = path if path.startswith("/") else f"/{path}"
    if normalized_path not in DOCUMENTED_ENDPOINTS and not allow_undocumented:
        raise ConsensusAPIError(
            f"Path not enabled in documented mode: {normalized_path}. Set CONSENSUS_ALLOW_UNDOCUMENTED=1 to allow it."
        )

    url = f"{API_BASE_URL}{normalized_path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"

    payload_bytes: bytes | None = None
    headers_base = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
        headers_base["Content-Type"] = "application/json"

    auth_variants = _auth_header_variants(auth_mode)
    attempts: list[dict[str, Any]] = []
    last_error: dict[str, Any] | None = None

    for header_variant in auth_variants:
        headers = dict(headers_base)
        headers.update(header_variant)
        for retry_index in range(max_retries + 1):
            attempt_record = {
                "auth_scheme": ",".join(sorted(header_variant.keys())) or "none",
                "retry": retry_index,
            }
            attempts.append(attempt_record)
            request = urllib.request.Request(url, data=payload_bytes, method=method.upper())
            for key, value in headers.items():
                request.add_header(key, value)
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    raw_text = response.read().decode("utf-8")
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type or raw_text.lstrip().startswith(("{", "[")):
                        parsed = json.loads(raw_text)
                    else:
                        parsed = {"text": raw_text}
                    return {
                        "ok": True,
                        "url": url,
                        "method": method.upper(),
                        "status_code": getattr(response, "status", 200),
                        "response": parsed,
                        "attempts": attempts,
                        "auth_mode": auth_mode,
                        "api_base_url": API_BASE_URL,
                    }
            except urllib.error.HTTPError as exc:
                error_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                last_error = {
                    "status_code": exc.code,
                    "reason": exc.reason,
                    "body": error_text,
                    "url": url,
                }
                if exc.code in {401, 403}:
                    break
                if exc.code == 429 or 500 <= exc.code < 600:
                    if retry_index < max_retries:
                        time.sleep(min(2 ** retry_index, 4))
                        continue
                break
            except urllib.error.URLError as exc:
                last_error = {
                    "status_code": None,
                    "reason": str(exc.reason),
                    "body": "",
                    "url": url,
                }
                if retry_index < max_retries:
                    time.sleep(min(2 ** retry_index, 4))
                    continue
                break
            except Exception as exc:  # pragma: no cover - defensive safety
                last_error = {
                    "status_code": None,
                    "reason": type(exc).__name__,
                    "body": str(exc),
                    "url": url,
                }
                break

    return {
        "ok": False,
        "url": url,
        "method": method.upper(),
        "error": last_error or {"reason": "request failed"},
        "attempts": attempts,
        "auth_mode": auth_mode,
        "api_base_url": API_BASE_URL,
        "hint": (
            "Provide CONSENSUS_API_KEY and try CONSENSUS_AUTH_MODE=bearer, x-api-key, or auto. "
            "The public docs expose /v1/quick_search; additional paths require explicit allowlisting."
        ),
    }


def _normalize_query_result(item: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "title": item.get("title"),
        "authors": item.get("authors") or [],
        "abstract": item.get("abstract"),
        "journal_name": item.get("journal_name") or item.get("journal"),
        "publish_year": item.get("publish_year") or item.get("year"),
        "citation_count": item.get("citation_count"),
        "url": item.get("url"),
        "doi": item.get("doi"),
        "study_type": item.get("study_type"),
        "takeaway": item.get("takeaway"),
        "pages": item.get("pages"),
        "volume": item.get("volume"),
    }
    missing = [key for key, value in normalized.items() if value in (None, "", [], {})]
    normalized["missing_fields"] = missing
    return normalized


@mcp.tool()
def consensus_api_surface() -> dict[str, Any]:
    """Return the documented Consensus API surface, auth notes, and supported query fields."""
    return {
        "ok": True,
        "purpose": "Expose Consensus HTTP API through an MCP tool surface while keeping Consensus backend credentials server-side and enforcing user/client access at the MCP gateway or resource-server layer.",
        "api_base_url": API_BASE_URL,
        "documented_endpoints": DOCUMENTED_ENDPOINTS,
        "supported_query_fields": [
            "query",
            "year_min",
            "year_max",
            "study_types",
            "human",
            "sample_size_min",
            "sjr_max",
            "duration_min",
            "duration_max",
            "exclude_preprints",
            "publisher_name",
            "medical_mode",
        ],
        "response_fields": [
            "abstract",
            "authors",
            "doi",
            "journal_name",
            "pages",
            "publish_year",
            "title",
            "url",
            "volume",
            "citation_count",
            "study_type",
            "takeaway",
        ],
        "auth_notes": [
            "Consensus direct HTTP API auth is backend key based for this adapter: CONSENSUS_API_KEY plus CONSENSUS_AUTH_MODE.",
            "Consensus OAuth/MCP client authorization is a separate MCP exposure-layer concern, not a Consensus API user-token flow.",
            "Remote OAuth should terminate at an MCP gateway, reverse proxy, or FastMCP HTTP resource-server layer before this adapter calls Consensus.",
            "This adapter will try bearer first, then x-api-key, unless CONSENSUS_AUTH_MODE overrides it.",
            "Set CONSENSUS_ALLOW_UNDOCUMENTED=1 only when you intentionally want to call non-catalogued paths.",
        ],
        "auth_layers": {
            "consensus_backend_api": {
                "secret_env": "CONSENSUS_API_KEY",
                "auth_mode_env": "CONSENSUS_AUTH_MODE",
                "supported_header_modes": ["bearer", "x-api-key", "both", "auto"],
                "api_key_configured": bool(API_KEY),
                "oauth_supported_here": False,
            },
            "mcp_client_boundary": {
                "purpose": "Authorize MCP clients to this server or gateway before backend Consensus API calls are made.",
                "transport_env": "CONSENSUS_MCP_TRANSPORT",
                "transport": MCP_TRANSPORT,
                "exposure_mode_env": "CONSENSUS_MCP_EXPOSURE_MODE",
                "exposure_mode": MCP_EXPOSURE_MODE,
                "resource_url_env": "CONSENSUS_MCP_RESOURCE_URL",
                "resource_url": MCP_RESOURCE_URL or None,
                "issuer_url_env": "CONSENSUS_MCP_ISSUER_URL",
                "issuer_url": MCP_ISSUER_URL or None,
                "required_scopes_env": "CONSENSUS_MCP_REQUIRED_SCOPES",
                "required_scopes": MCP_REQUIRED_SCOPES,
                "oauth_boundary": "gateway_or_fastmcp_resource_server",
                "oauth_enforced_by_this_stdio_adapter": False,
            },
        },
    }


@mcp.tool()
def consensus_quick_search(
    query: str,
    year_min: int | None = None,
    year_max: int | None = None,
    study_types: list[str] | None = None,
    human: bool | None = None,
    sample_size_min: int | None = None,
    sjr_max: int | None = None,
    duration_min: int | None = None,
    duration_max: int | None = None,
    exclude_preprints: bool | None = None,
    publisher_name: str | None = None,
    medical_mode: bool | None = None,
) -> dict[str, Any]:
    """Search Consensus papers through the documented quick_search API."""
    normalized_study_types = _normalize_study_types(study_types)
    params = _build_query_params(
        query=query,
        year_min=_clean_optional_int(year_min),
        year_max=_clean_optional_int(year_max),
        study_types=normalized_study_types,
        human=_clean_optional_bool(human),
        sample_size_min=_clean_optional_int(sample_size_min),
        sjr_max=_clean_optional_int(sjr_max),
        duration_min=_clean_optional_int(duration_min),
        duration_max=_clean_optional_int(duration_max),
        exclude_preprints=_clean_optional_bool(exclude_preprints),
        publisher_name=publisher_name,
        medical_mode=_clean_optional_bool(medical_mode),
    )
    result = _request_json("/v1/quick_search", query=params)
    if not result.get("ok"):
        return result

    response = result.get("response", {})
    papers = response.get("results", []) if isinstance(response, dict) else []
    normalized_papers = [_normalize_query_result(item) for item in papers if isinstance(item, dict)]
    return {
        **result,
        "normalized_response": {
            "query": query,
            "total_results": len(papers),
            "papers": normalized_papers,
        },
    }


@mcp.tool()
def consensus_request(
    path: str,
    method: str = "GET",
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    allow_undocumented: bool | None = None,
    auth_mode: str | None = None,
) -> dict[str, Any]:
    """Call a Consensus API path and return the parsed JSON response."""
    normalized_query = []
    if query:
        for key, value in query.items():
            if isinstance(value, list):
                for item in value:
                    normalized_query.append((key, str(item)))
            elif value is not None:
                normalized_query.append((key, str(value)))
    return _request_json(
        path,
        method=method,
        query=normalized_query or None,
        body=body,
        auth_mode=(auth_mode or AUTH_MODE),
        allow_undocumented=ALLOW_UNDOCUMENTED if allow_undocumented is None else allow_undocumented,
    )


def main() -> None:
    if MCP_TRANSPORT not in VALID_MCP_TRANSPORTS:
        allowed = ", ".join(sorted(VALID_MCP_TRANSPORTS))
        raise SystemExit(f"Invalid CONSENSUS_MCP_TRANSPORT={MCP_TRANSPORT!r}. Allowed: {allowed}")
    mcp.run(transport=MCP_TRANSPORT)


if __name__ == "__main__":
    main()
