# Getting Started

This guide walks through a local stdio setup for `arxiv-consensus-mcp`.

## Requirements

- Python 3.10 or newer.
- An MCP client that can launch a local stdio server.
- Optional: a Consensus API key if you want Consensus results in addition to arXiv.

## Install

```bash
git clone https://github.com/haegyung/arxiv-consensus-mcp.git
cd arxiv-consensus-mcp
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run The Server

Run the combined arXiv + Consensus server:

```bash
python -m arxiv_consensus_mcp.server
```

The server speaks MCP over stdio by default. It is meant to be launched by an MCP client rather than used as a long-running HTTP service in local mode.

## Register With Codex CLI

```bash
codex mcp add arxiv-consensus -- /absolute/path/to/arxiv-consensus-mcp/.venv/bin/python -m arxiv_consensus_mcp.server
```

Then ask the client to inspect the surface:

```text
Call arxiv_consensus_surface and summarize the available tools.
```

## Enable Consensus Search

arXiv calls do not need credentials. Consensus calls need a backend API key held by the server process:

```bash
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=x-api-key \
python -m arxiv_consensus_mcp.server
```

If you are not sure which header mode your key expects, start with:

```bash
CONSENSUS_AUTH_MODE=auto
```

The adapter tries bearer and `x-api-key` variants in `auto` mode.

## First Calls

Use arXiv only:

```text
Use arxiv_search with query "cat:cs.OS AND scheduler isolation", max_results 5, sort_by submittedDate, sort_order descending.
```

Use arXiv and Consensus together:

```text
Use arxiv_consensus_search with query "operating system scheduler isolation", arxiv_max_results 10, include_consensus true.
```

Inspect auth and deployment boundaries:

```text
Use arxiv_consensus_surface and explain where OAuth should be enforced.
```

## Expected Behavior Without A Consensus Key

If `CONSENSUS_API_KEY` is missing or invalid:

- `arxiv_search` can still return public arXiv metadata.
- `arxiv_consensus_search` can still return arXiv records.
- the Consensus part of the combined response reports its own API failure under `source_results.consensus`.

This lets a research workflow degrade gracefully instead of failing the whole collection run.
