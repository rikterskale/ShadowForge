# ShadowForge

ShadowForge is a scope-enforced foundation for **authorized penetration testing and security assessment** with local LLM routing, an allowlisted tool registry, and tamper-evident evidence collection.

> **Phase 1 boundary:** model discovery/routing and penetration-testing tool execution are both implemented, but models do **not** autonomously drive tools yet. A later phase can add a structured proposal/validation loop while preserving the existing scope and allowlist boundaries.

## Supported platforms

ShadowForge Phase 1 is continuously validated on:

- Ubuntu Linux
- Windows
- Kali Linux rolling
- Python 3.11 and 3.14 on the Ubuntu/Windows matrix
- Kali's repository-provided Python inside the official `kalilinux/kali-rolling` container

Kali has its own beginner guide because Kali/Debian system Python is externally managed and ShadowForge should be installed in a virtual environment rather than with `sudo pip` or `--break-system-packages`.

## LLM stack

ShadowForge mirrors the ADAtlas Ollama model roles. The single source of truth is `DEFAULT_MODELS` in `src/shadowforge/model_router.py`:

- **Required primary — `qwen3.5:27b`**: planning and reasoning.
- **Optional critic — `gemma4:31b`**: validation and second-opinion review.
- **Optional coding — `devstral-small-2:24b`**: code/tooling assistance.

Fallback behavior is deterministic:

```text
Qwen missing      -> model operations stop with a setup error
Gemma missing     -> critic role uses Qwen
Devstral missing  -> coding role uses Qwen
Both missing      -> Qwen handles all three roles
```

ShadowForge talks to Ollama's OpenAI-compatible endpoint at `http://127.0.0.1:11434/v1`.

Install the required model:

```bash
ollama pull qwen3.5:27b
```

Optional specialist models:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check what ShadowForge will actually use:

```bash
ollama list
shadowforge models
```

## Phase 1 capabilities

- Engagement scope loaded from JSON and enforced before every active tool run.
- IPv4 and IPv6 scope entries can coexist safely.
- Explicit `--authorized` operator acknowledgement.
- Allowlisted tool registry; raw model text is never executed as a shell command.
- Qwen/Gemma/Devstral model discovery with Qwen-only fallback.
- Non-destructive Nmap TCP/service discovery adapter.
- Strict port/range validation before Nmap starts.
- JSONL evidence with execution ID, scope, arguments, duration, ShadowForge version, results, and SHA-256 hash chaining.
- Full evidence-chain verification before a new record is appended.
- Clean CLI handling for scope, file-system, evidence, model, and tool errors.
- Ruff, Windows/Ubuntu/Kali tests, a 99% branch-coverage gate, package build validation, dependency audit, and CodeQL.

## Architecture

```text
          Local model infrastructure
      Qwen / Gemma / Devstral via Ollama
                    |
          discovery + role routing
                    |
           (no autonomous loop yet)

Operator CLI -> scope gate -> Harness -> allowlisted Tool Registry -> Nmap adapter
                              |
                              +-> tamper-evident evidence JSONL
```

Future model-driven execution must use a structured proposal and validation layer and must still enter active execution through `Harness.execute()`.

## Quick start

Requires Python 3.11+ on the primary Windows/Ubuntu support matrix and Nmap. Kali rolling is validated with Kali's repository-provided Python. Ollama is required only for model features.

### Ubuntu / general Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Kali Linux

```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip ca-certificates
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Do not use `sudo pip` or `--break-system-packages` to install ShadowForge on Kali.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Create `scope.json`:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Use only ranges covered by your written authorization. Scope names and targets must be non-empty strings; numeric JSON values are rejected rather than being interpreted as addresses.

Run service discovery:

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443,8000-8100
```

Evidence is written to `artifacts/evidence.jsonl` by default.

## Evidence

Each execution record includes enough context to reproduce and review the action, and each record contains the prior record hash. Before a new record is appended, ShadowForge verifies every existing record's stored hash, recalculates each hash from the record contents, and verifies every previous-hash link. A malformed, edited, or broken chain is rejected rather than silently extended.

The hash chain is **tamper-evident**, not a substitute for access controls, signed logs, file locking, or external evidence retention.

## Safety model

Phase 1 intentionally excludes exploit execution, password spraying, credential dumping, persistence, evasion, relay/coercion, arbitrary remote commands, and automatic propagation. Later modules should preserve explicit scope validation, capability allowlisting, evidence collection, dry-run support where appropriate, and operator approval boundaries.

## Common errors

- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `could not query Ollama model inventory`: make sure Ollama is installed and running.
- `outside engagement scope`: do not bypass the check; correct the scope only if authorization covers the target.
- `File/system error`: verify the scope/evidence path and file permissions.
- `ports must ...`: use individual ports or ascending ranges between 1 and 65535.
- Kali `externally-managed-environment`: create/activate `.venv`; do not install ShadowForge into the system Python.

## Development

CI pins the direct development-tool versions in `requirements-ci.txt`; transitive dependencies are resolved by pip and audited during CI. In addition to the Windows/Ubuntu matrix, CI installs and tests ShadowForge inside the official Kali rolling container.

```bash
python -m pip install -r requirements-ci.txt
python -m pip install -e .
ruff check .
coverage run -m pytest
coverage report --fail-under=99
python -m build
python -m pip check
pip-audit -r requirements-ci.txt
```

Beginner guides:

- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`
- `docs/KALI_NOVICE_GUIDE.md`
