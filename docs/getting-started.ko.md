# 시작하기 (한국어)

이 문서는 `arxiv-consensus-mcp`를 로컬 MCP 서버로 설치하고 실행하는 절차를 한국어로 설명합니다.

## 무엇을 설치하나

`arxiv-consensus-mcp`는 arXiv 공개 메타데이터와 Consensus API 검색 결과를 한 번에 다루는 MCP 서버입니다. 결과는 나중에 코퍼스 수집, 문헌 검토, 연구 메모 정리에 쓰기 좋게 같은 필드 구조로 정리됩니다.

## 필요한 것

- Python 3.10 이상.
- 로컬 `stdio` MCP 서버를 실행할 수 있는 MCP 클라이언트.
- 선택 사항: arXiv 결과에 Consensus 결과를 더하려면 Consensus API 키.

## GitHub에서 바로 설치

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install "git+https://github.com/haegyung/arxiv-consensus-mcp.git"
```

## 저장소를 받아서 설치

```bash
git clone https://github.com/haegyung/arxiv-consensus-mcp.git
cd arxiv-consensus-mcp
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## 서버 실행

통합 arXiv + Consensus MCP 서버를 실행합니다:

```bash
python -m arxiv_consensus_mcp.server
```

기본값은 `stdio` 전송입니다. 로컬 모드에서는 보통 사용자가 터미널에서 오래 띄워 두는 HTTP 서비스가 아니라, MCP 클라이언트가 필요할 때 실행하는 서버로 씁니다.

## Codex CLI에 등록

```bash
codex mcp add arxiv-consensus -- /absolute/path/to/arxiv-consensus-mcp/.venv/bin/python -m arxiv_consensus_mcp.server
```

등록한 뒤 MCP 클라이언트에서 먼저 표면 정보를 확인합니다:

```text
Call arxiv_consensus_surface and summarize the available tools.
```

## Consensus 검색 켜기

arXiv 검색은 별도 키 없이 동작합니다. Consensus 검색은 서버 프로세스가 가진 backend API 키로 호출합니다:

```bash
CONSENSUS_API_KEY="replace-with-your-key" \
CONSENSUS_AUTH_MODE=auto \
python -m arxiv_consensus_mcp.server
```

`CONSENSUS_AUTH_MODE=auto`는 bearer 방식과 `x-api-key` 방식을 순서대로 시도합니다. 키가 어떤 헤더 방식을 요구하는지 확실하면 `x-api-key`, `bearer`, `both` 중 하나로 고정할 수 있습니다.

## 처음 호출해 보기

arXiv만 검색:

```text
Use arxiv_search with query "cat:cs.OS AND scheduler isolation", max_results 5, sort_by submittedDate, sort_order descending.
```

arXiv와 Consensus를 함께 검색:

```text
Use arxiv_consensus_search with query "operating system scheduler isolation", arxiv_max_results 10, include_consensus true.
```

인증 경계 확인:

```text
Use arxiv_consensus_surface and explain where OAuth should be enforced.
```

## Consensus 키가 없을 때

`CONSENSUS_API_KEY`가 없거나 올바르지 않아도 전체 흐름이 바로 멈추지는 않습니다.

- `arxiv_search`는 계속 arXiv 공개 메타데이터를 반환할 수 있습니다.
- `arxiv_consensus_search`는 arXiv 결과를 반환하고, Consensus 쪽 실패는 `source_results.consensus` 아래에 따로 기록합니다.
- 이 방식은 연구 수집 작업이 Consensus 인증 문제 때문에 통째로 실패하지 않도록 하기 위한 것입니다.

## 설치 확인

간단한 import smoke를 실행합니다:

```bash
python - <<'PY'
from arxiv_consensus_mcp.server import arxiv_consensus_surface
surface = arxiv_consensus_surface()
print(surface["ok"], surface["mcp_server"], surface["transport"])
PY
```

기대 출력:

```text
True Arxiv_Consensus_MCP stdio
```

저장소를 받아 설치했다면 테스트도 실행할 수 있습니다:

```bash
python -m unittest discover -s tests
```

## 문제 해결

- `ModuleNotFoundError`: 패키지를 설치한 virtualenv가 활성화되어 있는지 확인합니다.
- MCP 클라이언트 실행 실패: MCP 클라이언트 설정에서 `.venv/bin/python`의 절대 경로를 사용합니다.
- Consensus `401` 또는 `403`: `CONSENSUS_API_KEY` 값을 확인하고 `CONSENSUS_AUTH_MODE=auto`로 다시 시도합니다.
- 원격 클라이언트에 OAuth가 필요함: 사용자 OAuth 토큰을 Consensus로 넘기지 말고, MCP 서버 앞단의 gateway 또는 resource-server 계층에서 보호합니다.

## 다음 문서

- [Tool reference](tool-reference.md): 도구별 입력, 출력, 동작.
- [Configuration](configuration.md): 환경 변수와 인증 모드.
- [OAuth gateway boundary](oauth-gateway-boundary.md): 원격 MCP 배포에서 OAuth를 어디에 둘지에 대한 기준.
