#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from .consensus_api_adapter import consensus_api_surface, consensus_quick_search


mcp = FastMCP("Arxiv_Consensus_MCP")

ARXIV_API_BASE_URLS = [
    url.strip()
    for url in os.environ.get(
        "ARXIV_API_BASE_URLS",
        os.environ.get("ARXIV_API_BASE_URL", "https://export.arxiv.org/api/query,https://arxiv.org/api/query"),
    ).split(",")
    if url.strip()
]
USER_AGENT = os.environ.get("ARXIV_CONSENSUS_USER_AGENT", "ArxivConsensusMCP/0.1")
MCP_TRANSPORT = os.environ.get(
    "ARXIV_CONSENSUS_MCP_TRANSPORT",
    os.environ.get("CONSENSUS_MCP_TRANSPORT", "stdio"),
).strip().lower()
VALID_MCP_TRANSPORTS = {"stdio", "sse", "streamable-http"}
ARXIV_MAX_RESULTS_LIMIT = int(os.environ.get("ARXIV_MCP_MAX_RESULTS_LIMIT", "50"))
ARXIV_HTTP_TIMEOUT_SECONDS = int(os.environ.get("ARXIV_HTTP_TIMEOUT_SECONDS", "20"))
ARXIV_SORT_BY = {"relevance", "lastUpdatedDate", "submittedDate"}
ARXIV_SORT_ORDER = {"ascending", "descending"}
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _normalize_ws(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized or None


def _missing_fields(item: dict[str, Any], fields: list[str]) -> list[str]:
    return [field for field in fields if item.get(field) in (None, "", [], {})]


def _parse_arxiv_feed(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    items: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        entry_url = _normalize_ws(entry.findtext("atom:id", default=None, namespaces=ATOM_NS))
        title = _normalize_ws(entry.findtext("atom:title", default=None, namespaces=ATOM_NS))
        abstract = _normalize_ws(entry.findtext("atom:summary", default=None, namespaces=ATOM_NS))
        published = _normalize_ws(entry.findtext("atom:published", default=None, namespaces=ATOM_NS))
        updated = _normalize_ws(entry.findtext("atom:updated", default=None, namespaces=ATOM_NS))
        authors = []
        for author in entry.findall("atom:author", ATOM_NS):
            name = _normalize_ws(author.findtext("atom:name", default=None, namespaces=ATOM_NS))
            if name:
                authors.append(name)
        categories = [category.attrib["term"] for category in entry.findall("atom:category", ATOM_NS) if category.attrib.get("term")]
        doi = _normalize_ws(entry.findtext("arxiv:doi", default=None, namespaces=ATOM_NS))
        pdf_url = None
        for link in entry.findall("atom:link", ATOM_NS):
            href = link.attrib.get("href")
            if not href:
                continue
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = href
                break
        if not pdf_url and entry_url:
            pdf_url = entry_url.replace("/abs/", "/pdf/")
        arxiv_id = entry_url.rstrip("/").split("/")[-1] if entry_url else None
        year = int(published[:4]) if published and len(published) >= 4 and published[:4].isdigit() else None
        item = {
            "source": "arxiv",
            "item_type": "paper",
            "title": title,
            "url": entry_url,
            "arxiv_id": arxiv_id,
            "doi": doi,
            "authors": authors,
            "abstract": abstract,
            "year": year,
            "published_date": published,
            "updated_date": updated,
            "categories": categories,
            "pdf_url": pdf_url,
            "primary_metadata_source": "arxiv_atom_api",
        }
        item["missing_fields"] = _missing_fields(item, ["title", "url", "arxiv_id", "authors", "abstract", "year", "doi"])
        items.append(item)
    return items


def _build_arxiv_url(base_url: str, query: str, start: int, max_results: int, sort_by: str, sort_order: str) -> str:
    params = {
        "search_query": query,
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def _dedupe_key(item: dict[str, Any]) -> str | None:
    arxiv_id = item.get("arxiv_id")
    if arxiv_id:
        return f"arxiv:{str(arxiv_id).lower()}"
    doi = item.get("doi")
    if doi:
        return f"doi:{str(doi).lower()}"
    url = item.get("url")
    if url:
        return f"url:{str(url).lower()}"
    title = item.get("title")
    if title:
        return f"title:{re.sub(r'\\s+', ' ', str(title)).strip().lower()}"
    return None


def _normalize_consensus_paper(paper: dict[str, Any]) -> dict[str, Any]:
    item = {
        "source": "consensus",
        "item_type": "paper",
        "title": paper.get("title"),
        "url": paper.get("url"),
        "doi": paper.get("doi"),
        "authors": paper.get("authors") or [],
        "abstract": paper.get("abstract"),
        "year": paper.get("publish_year"),
        "journal": paper.get("journal_name"),
        "citation_count": paper.get("citation_count"),
        "study_type": paper.get("study_type"),
        "takeaway": paper.get("takeaway"),
        "pages": paper.get("pages"),
        "volume": paper.get("volume"),
        "primary_metadata_source": "consensus_quick_search_api",
    }
    item["missing_fields"] = _missing_fields(item, ["title", "url", "doi", "authors", "abstract", "year", "journal"])
    return item


@mcp.tool()
def arxiv_consensus_surface() -> dict[str, Any]:
    """Return the combined arXiv + Consensus MCP surface and auth boundary."""
    consensus_surface = consensus_api_surface()
    return {
        "ok": True,
        "mcp_server": "Arxiv_Consensus_MCP",
        "purpose": "Search and normalize arXiv public metadata and Consensus API metadata through one MCP surface.",
        "tools": [
            "arxiv_consensus_surface",
            "arxiv_search",
            "arxiv_consensus_search",
            "consensus_quick_search via imported Consensus API adapter",
        ],
        "arxiv": {
            "api_base_urls": ARXIV_API_BASE_URLS,
            "auth": "none",
            "supported_query_fields": ["query", "start", "max_results", "sort_by", "sort_order"],
            "sort_by_values": sorted(ARXIV_SORT_BY),
            "sort_order_values": sorted(ARXIV_SORT_ORDER),
            "max_results_limit": ARXIV_MAX_RESULTS_LIMIT,
            "timeout_seconds": ARXIV_HTTP_TIMEOUT_SECONDS,
        },
        "consensus": {
            "api_base_url": consensus_surface.get("api_base_url"),
            "auth_layers": consensus_surface.get("auth_layers"),
            "supported_query_fields": consensus_surface.get("supported_query_fields"),
        },
        "normalized_fields": [
            "source",
            "item_type",
            "title",
            "url",
            "arxiv_id",
            "doi",
            "authors",
            "abstract",
            "year",
            "journal",
            "citation_count",
            "study_type",
            "takeaway",
            "primary_metadata_source",
            "missing_fields",
        ],
        "dedupe_rule": "arxiv_id, then doi, then url, then normalized title",
        "oauth_boundary": "MCP client OAuth belongs at the gateway/resource-server layer; backend Consensus calls use server-held API key.",
        "transport": MCP_TRANSPORT,
    }


@mcp.tool()
def arxiv_search(
    query: str,
    start: int = 0,
    max_results: int = 10,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
) -> dict[str, Any]:
    """Search arXiv Atom API and return normalized paper metadata."""
    query = query.strip()
    if not query:
        return {"ok": False, "error": {"reason": "query is required"}}
    if sort_by not in ARXIV_SORT_BY:
        return {"ok": False, "error": {"reason": f"invalid sort_by: {sort_by}", "allowed": sorted(ARXIV_SORT_BY)}}
    if sort_order not in ARXIV_SORT_ORDER:
        return {"ok": False, "error": {"reason": f"invalid sort_order: {sort_order}", "allowed": sorted(ARXIV_SORT_ORDER)}}
    start = max(0, int(start))
    max_results = max(1, min(int(max_results), ARXIV_MAX_RESULTS_LIMIT))
    failures: list[dict[str, Any]] = []
    for base_url in ARXIV_API_BASE_URLS:
        url = _build_arxiv_url(base_url, query, start, max_results, sort_by, sort_order)
        request = urllib.request.Request(url, method="GET")
        request.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(request, timeout=ARXIV_HTTP_TIMEOUT_SECONDS) as response:
                body = response.read()
                items = _parse_arxiv_feed(body)
                return {
                    "ok": True,
                    "source": "arxiv",
                    "url": url,
                    "status_code": getattr(response, "status", 200),
                    "query": query,
                    "count": len(items),
                    "items": items,
                    "attempted_base_urls": ARXIV_API_BASE_URLS,
                    "failed_attempts": failures,
                }
        except urllib.error.HTTPError as exc:
            failures.append({"url": url, "error": {"status_code": exc.code, "reason": exc.reason}})
        except urllib.error.URLError as exc:
            failures.append({"url": url, "error": {"reason": str(exc.reason)}})
        except Exception as exc:  # pragma: no cover - defensive safety
            failures.append({"url": url, "error": {"reason": type(exc).__name__, "body": str(exc)}})
    return {
        "ok": False,
        "source": "arxiv",
        "query": query,
        "attempted_base_urls": ARXIV_API_BASE_URLS,
        "error": failures[-1]["error"] if failures else {"reason": "no arXiv base URLs configured"},
        "failed_attempts": failures,
    }


@mcp.tool()
def arxiv_consensus_search(
    query: str,
    consensus_query: str | None = None,
    arxiv_max_results: int = 10,
    include_consensus: bool = True,
) -> dict[str, Any]:
    """Search arXiv and, when enabled, Consensus quick_search; normalize and dedupe results."""
    arxiv_result = arxiv_search(query=query, max_results=arxiv_max_results)
    arxiv_items = arxiv_result.get("items", []) if arxiv_result.get("ok") else []
    consensus_result: dict[str, Any] | None = None
    consensus_items: list[dict[str, Any]] = []
    if include_consensus:
        try:
            consensus_result = consensus_quick_search(consensus_query or query)
            papers = consensus_result.get("normalized_response", {}).get("papers", []) if consensus_result.get("ok") else []
            consensus_items = [_normalize_consensus_paper(paper) for paper in papers if isinstance(paper, dict)]
        except Exception as exc:  # pragma: no cover - defensive safety
            consensus_result = {"ok": False, "error": {"reason": type(exc).__name__, "body": str(exc)}}

    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates: list[dict[str, Any]] = []
    for item in [*arxiv_items, *consensus_items]:
        key = _dedupe_key(item)
        if key and key in seen:
            duplicates.append({"source": item.get("source"), "title": item.get("title"), "dedupe_key": key})
            continue
        if key:
            seen.add(key)
        combined.append(item)

    return {
        "ok": bool(arxiv_result.get("ok")) or bool(consensus_result and consensus_result.get("ok")),
        "query": query,
        "consensus_query": consensus_query or query,
        "counts": {
            "arxiv": len(arxiv_items),
            "consensus": len(consensus_items),
            "combined": len(combined),
            "duplicates_excluded": len(duplicates),
        },
        "items": combined,
        "deduplication_decisions": duplicates,
        "source_results": {
            "arxiv": {key: value for key, value in arxiv_result.items() if key != "items"},
            "consensus": consensus_result,
        },
        "gaps": [
            "Consensus results require CONSENSUS_API_KEY; if absent or invalid, arXiv can still return public metadata.",
            "Remote MCP OAuth enforcement is outside this stdio-local server and belongs to gateway/resource-server deployment.",
        ],
    }


def main() -> None:
    if MCP_TRANSPORT not in VALID_MCP_TRANSPORTS:
        allowed = ", ".join(sorted(VALID_MCP_TRANSPORTS))
        raise SystemExit(f"Invalid ARXIV_CONSENSUS_MCP_TRANSPORT={MCP_TRANSPORT!r}. Allowed: {allowed}")
    mcp.run(transport=MCP_TRANSPORT)


if __name__ == "__main__":
    main()
