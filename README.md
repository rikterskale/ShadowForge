# ShadowForge

ShadowForge is a scope-enforced LLM-assisted harness for **authorized penetration testing and security assessment**. Version 0.4.0 adds optional persistent engagement state for resumable bounded reconnaissance while preserving the scope, allowlist, evidence, operator-approval, and hard step-budget boundaries.

## Supported platforms

ShadowForge is continuously validated on:

- Ubuntu Linux / Python 3.11 and 3.14
- Windows / Python 3.11 and 3.14
- Kali Linux rolling using Kali's repository-provided Python in the official `kalilinux/kali-rolling` container

Kali users should install ShadowForge inside a virtual environment. Do not use `sudo pip` or `--break-system-packages`.

## Local LLM stack

ShadowForge mirrors the ADAtlas Ollama roles:

- **Required primary — `qwen3.5:27b`**: bounded planning and reasoning.
- **Optional critic — `gemma4:31b`**: advisory post-run review; falls back to Qwen.
- **Optional coding — `devstral-small-2:24b`**: coding/tooling role; falls back to Qwen.

```bash
ollama pull qwen3.5:27b
ollama pull gemma4:31b       # optional
ollama pull devstral-small-2:24b  # optional
shadowforge models
```

## Current architecture

```text
Operator objective + exact target
              |
              +---- optional persistent session
              |        validated + target-bound
              |        treated as untrusted data
              v
        Qwen recon planner
              |
       structured decision
              |
 deterministic schema/policy
       |                |
       |                +-- http_metadata_probe
       |                    HEAD / only, no redirects
       +-- nmap_service_scan
              |
     exact-target validation
              |
       EngagementScope
              |
      hard step budget: 1..5
              |
      dry-run by default
              |
     --execute + --authorized
              |
        Harness.execute()
              |
       ToolRegistry allowlist
              |
       hash-chained evidence
              |
     sanitized session observation
              |
        atomic state save
              |
   next bounded decision / completion
              |
       Gemma/Qwen critic
       (no execution handle)
```

Tool output and persistent session state are explicitly treated as **untrusted data** when provided to a model. They never become execution authority. Every model decision must independently pass deterministic parsing, exact-target validation, scope checks, per-tool argument policy, and the hard step budget.

## Scope file

Create `scope.json` using only targets covered by written authorization:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

## Direct scan

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## Phase 2 single-action agent

Dry-run:

```bash
shadowforge --scope scope.json agent \
  "Identify common web and administration services" \
  --target 192.0.2.10
```

Execute one validated Nmap action:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and administration services" \
  --target 192.0.2.10 \
  --execute
```

## Phase 3 bounded recon

Dry-run plans only the first decision and performs no network activity:

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

Active bounded recon:

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

`--max-steps` is restricted to 1 through 5. The planner may stop earlier.

## Phase 4 persistent recon sessions

Add `--session` to let a later invocation reuse sanitized observations from earlier active runs:

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --max-steps 3 \
  --execute
```

Run the same command later with the **same session ID, exact target, and exact objective** to resume from prior state.

Session IDs are restricted to safe filename characters. A stored session cannot be rebound to another target or objective. State files default to:

```text
artifacts/state/<session>.json
```

Use another state directory when needed:

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --state-dir ./engagement-state
```

A dry-run may read an existing session but does **not** create or modify session state.

### What state stores

Persistent memory contains only sanitized results from the two currently allowlisted recon tools:

- Nmap: bounded service records only, maximum 256 services per stored result.
- HTTP metadata: scheme, port, status code, reason, filtered metadata headers, and bounded adapter errors.

Cookies, authorization headers, arbitrary unknown fields, unknown tools, cross-target observations, invalid statuses, malformed step ordering, and incompatible state versions are rejected or removed before model use.

Each session is capped at 100 observations. Session files use atomic replacement to avoid normal partial-write corruption. Phase 4 does not yet provide cross-process locking, so do not run multiple writers against the same session ID concurrently.

## Allowed active capabilities

### `nmap_service_scan`

Only the validated `ports` expression is model-controlled. Nmap NSE scripts and arbitrary flags are not available.

### `http_metadata_probe`

Requires one IP address and accepts exactly `scheme` plus integer `port`. It sends one `HEAD /`, follows no redirects, and records only allowlisted metadata headers.

## Evidence versus state

Active execution writes tamper-evident evidence to:

```text
artifacts/evidence.jsonl
```

Persistent session memory is separate:

```text
artifacts/state/<session>.json
```

Evidence is the hash-chained execution record. Session state is resumable working context and is not a substitute for evidence.

## Safety boundary

Version 0.4.0 intentionally does **not** add:

- generic shell, PowerShell, or Python execution
- model-selected targets
- Nmap NSE/script selection
- exploit execution
- password spraying or credential attacks
- credential dumping or secret retrieval
- relay/coercion
- persistence installation or defense evasion
- arbitrary remote commands
- automatic propagation
- unrestricted HTTP paths, methods, or redirects
- unbounded autonomous loops

## Common errors

- `required primary model ... is not installed`: install `qwen3.5:27b` in Ollama.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `tool is not permitted ...`: deterministic policy rejected a model decision.
- `decision target must exactly match ...`: the model attempted to change the target.
- `HTTP metadata probe requires one IP address`: use one authorized IP, not a CIDR, for HTTP probing.
- `max_steps must ...`: choose a value from 1 through 5.
- `session must ...`: use a safe 1-64 character session ID such as `assessment-01`.
- `session ... is bound to target ...`: use the original target or a different session ID.
- `session objective does not match ...`: reuse the exact original objective or create another session.
- `outside engagement scope`: correct the scope only if written authorization covers the target.
- `Refusing to execute`: use `--authorized` only after confirming written authorization.

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

CI validates Windows, Ubuntu, and Kali; CodeQL runs separately.

Beginner guides:

- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`
- `docs/KALI_NOVICE_GUIDE.md`

Architecture details:

- `docs/PHASE2_ARCHITECTURE.md`
- `docs/PHASE3_ARCHITECTURE.md`
- `docs/PHASE4_ARCHITECTURE.md`
