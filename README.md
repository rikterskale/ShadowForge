# ShadowForge

ShadowForge is a scope-enforced LLM-assisted harness for **authorized penetration testing and security assessment**. Version 0.2.0 adds a bounded model-driven planning path while preserving the Phase 1 scope, allowlist, evidence, and operator-approval boundaries.

## Phase 2 in one sentence

The operator supplies the exact target and objective; Qwen may propose **one** non-destructive `nmap_service_scan` action, ShadowForge validates the proposal in code, dry-run is the default, and execution still requires `--authorized --execute` and must pass through `Harness.execute()`.

## Supported platforms

ShadowForge is continuously validated on:

- Ubuntu Linux / Python 3.11 and 3.14
- Windows / Python 3.11 and 3.14
- Kali Linux rolling using Kali's repository-provided Python inside the official `kalilinux/kali-rolling` container

Kali has its own beginner guide because Kali/Debian system Python is externally managed. Use a virtual environment; do not install ShadowForge with `sudo pip` or `--break-system-packages`.

## LLM stack

ShadowForge mirrors the ADAtlas Ollama model roles:

- **Required primary — `qwen3.5:27b`**: bounded action planning and general reasoning.
- **Optional critic — `gemma4:31b`**: advisory post-execution review.
- **Optional coding — `devstral-small-2:24b`**: reserved for coding/tooling workflows as Phase 2 expands.

Fallback behavior is deterministic:

```text
Qwen missing      -> model operations stop with a setup error
Gemma missing     -> critic role uses Qwen
Devstral missing  -> coding role uses Qwen
Both missing      -> Qwen handles all three roles
```

Install the required model:

```bash
ollama pull qwen3.5:27b
```

Optional specialists:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check model routing:

```bash
ollama list
shadowforge models
```

## Phase 2 architecture

```text
Operator objective + exact target
              |
              v
       Qwen primary planner
              |
              v
       JSON ActionProposal
              |
              v
  strict schema/policy validation
       |      |       |
       |      |       +-- only {"ports": ...}
       |      +---------- target must equal operator target
       +----------------- tool must be nmap_service_scan
              |
              v
       EngagementScope.require()
              |
        dry-run by default
              |
     --execute + --authorized
              |
              v
         Harness.execute()
              |
      ToolRegistry allowlist
              |
          Nmap adapter
              |
              v
   verified hash-chained evidence
              |
              v
      Gemma/Qwen advisory critic
       (cannot launch tools)
```

The model never receives a generic shell-execution capability. Model output is data that must pass deterministic validation before any active tool can run.

## What the Phase 2 planner is allowed to propose

Exactly this shape:

```json
{
  "tool": "nmap_service_scan",
  "target": "192.0.2.10",
  "arguments": {
    "ports": "22,80,443,8000-8100"
  },
  "rationale": "Identify common remote administration and web services."
}
```

The parser rejects:

- any other tool name
- a target different from the operator-supplied target
- extra JSON fields
- extra argument fields
- non-string port values
- malformed, reversed, or out-of-range ports
- empty or oversized rationale text
- non-JSON planner output

The target is also checked against the engagement scope before planning and again after parsing the model response.

## Quick start

Requires Python 3.11+ on the primary Windows/Ubuntu matrix and Nmap. Kali rolling is validated with Kali's repository Python. Ollama is required for `models` and `agent` commands.

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

Use only targets covered by written authorization.

## Direct Phase 1 scan

The direct command remains available:

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## Phase 2 agent dry-run

Dry-run asks Qwen for a proposal, validates it, and prints it. **It does not run Nmap and does not create execution evidence.**

```bash
shadowforge --scope scope.json agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10
```

Example output shape:

```json
{
  "mode": "dry-run",
  "proposal": {
    "arguments": {"ports": "22,80,443,3389"},
    "rationale": "Identify common administration and web services.",
    "target": "192.0.2.10",
    "tool": "nmap_service_scan"
  }
}
```

## Phase 2 agent execution

Execution requires both explicit flags:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10 \
  --execute
```

The sequence is:

1. verify the target is in scope
2. ask Qwen for one structured proposal
3. strictly parse and validate the proposal
4. verify the proposal target is still in scope
5. execute only through the allowlisted harness
6. write verified hash-chained evidence
7. ask the critic model for advisory interpretation

If the critic is unavailable after execution, the evidenced tool result is preserved and returned with a separate `critique_error` field.

## Evidence

Active execution writes to `artifacts/evidence.jsonl` by default.

Each record includes:

- execution ID
- timestamp
- engagement scope name
- tool
- target
- validated arguments
- status
- duration
- ShadowForge version
- result data
- prior-record hash
- current-record SHA-256 hash

Before appending, ShadowForge verifies the full existing chain. A malformed, edited, or broken chain is rejected rather than silently extended.

The chain is tamper-evident; it is not a substitute for signed logs, external evidence retention, or cross-process file locking.

## Safety boundary

Version 0.2.0 still intentionally excludes autonomous or model-selected exploit execution, password spraying, credential dumping, persistence, evasion, relay/coercion, arbitrary remote commands, automatic propagation, and generic shell execution.

Phase 2 is **not** a free-running autonomous penetration-testing agent. It is one bounded proposal per invocation, against an operator-selected target, for the single non-destructive tool currently permitted by the policy layer.

Future capabilities must add explicit typed schemas and policy checks; they must not obtain a bypass around `Harness.execute()`.

## Common errors

- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `could not query Ollama model inventory`: make sure Ollama is installed and running.
- `proposal must ...` or `tool is not permitted ...`: the model produced output rejected by the deterministic policy layer; no active action was started.
- `proposal target must exactly match ...`: the model changed the operator target; the proposal was blocked.
- `outside engagement scope`: do not bypass the check; correct scope only if written authorization covers the target.
- `Refusing to execute`: add `--authorized` only after confirming written authorization.
- `ports must ...`: use individual ports or ascending ranges from 1 through 65535.
- Kali `externally-managed-environment`: activate `.venv`; do not use `sudo pip` or `--break-system-packages`.

## Development

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

CI validates Windows, Ubuntu, and Kali, and CodeQL runs separately.

Beginner guides:

- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`
- `docs/KALI_NOVICE_GUIDE.md`

Phase 2 design details:

- `docs/PHASE2_ARCHITECTURE.md`
