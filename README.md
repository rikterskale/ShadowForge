# ShadowForge

ShadowForge is a scope-enforced LLM harness for **authorized penetration testing and security assessment**. Phase 1 establishes a small, testable execution core in which model output is advisory and only explicitly allowlisted tools can run.

## Phase 1 capabilities

- Engagement scope loaded from JSON and enforced before every tool run.
- Explicit `--authorized` operator acknowledgement.
- Allowlisted tool registry; model output cannot invoke arbitrary shell commands.
- Non-destructive Nmap TCP/service discovery adapter.
- Append-only JSONL evidence records.
- OpenAI-compatible model client suitable for local servers such as vLLM/Ollama-compatible gateways or other compatible endpoints.
- Python CLI, unit tests, Ruff, 99% coverage gate, and CodeQL workflow.

## Architecture

```text
                     LLM provider
                         |
                  advisory reasoning
                         |
                 +-------v--------+
                 | ShadowForge    |
                 | Harness        |
                 +---+---------+--+
                     |         |
              scope gate   evidence store
                     |
               tool registry
                     |
            +--------+--------+
            |                 |
     nmap_service_scan   future safe adapters
```

The trust boundary is intentional: LLM text is never treated as a shell command. Tools must be implemented and registered in code, and the harness validates the target against the engagement scope first.

## Quick start

Requires Python 3.11+ and Nmap.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1
python -m pip install -e .
```

Create `scope.json`:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24"]
}
```

Then run a service scan **only after confirming written authorization**:

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

Evidence is written to `artifacts/evidence.jsonl` by default.

## Safety model

Phase 1 intentionally excludes exploit execution, password spraying, credential dumping, persistence, evasion, relay/coercion, arbitrary remote commands, and automatic propagation. Later modules should preserve the same scope, capability-allowlist, evidence, dry-run, and operator-approval boundaries.

## Development

```bash
python -m pip install -e .[dev]
ruff check .
coverage run -m pytest
coverage report --fail-under=99
```

Beginner guides:

- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`
