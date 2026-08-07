# ShadowForge

ShadowForge is a scope-enforced LLM-assisted harness for **authorized penetration testing and security assessment**. Version 0.3.0 adds bounded multi-step reconnaissance while preserving the existing scope, allowlist, evidence, and operator-approval boundaries.

## Phase 3 in one sentence

The operator supplies the exact target and objective; Qwen may make up to five deterministic-policy-validated reconnaissance decisions using only non-destructive service discovery and root HTTP metadata probing, while every active step still passes through `Harness.execute()` and the engagement scope.

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

Install the required model:

```bash
ollama pull qwen3.5:27b
```

Optional specialists:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check routing:

```bash
ollama list
shadowforge models
```

## Architecture

```text
Operator objective + exact target
              |
              v
        Qwen recon planner
              |
              v
    one structured decision
              |
              v
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
      step budget: 1..5
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
       verified evidence
              |
   result returned as untrusted data
              |
        next bounded decision
              |
      Gemma/Qwen critic
       (no execution handle)
```

Tool output is explicitly labeled as **untrusted data** when fed back to the planner. Instructions found in banners, headers, or other target-controlled output do not gain execution authority. Every new model decision must independently pass the deterministic parser and policy.

## Allowed Phase 3 capabilities

### `nmap_service_scan`

The planner may choose only a validated `ports` expression. Nmap still runs through the existing constrained adapter.

```json
{
  "decision": "action",
  "tool": "nmap_service_scan",
  "target": "192.0.2.10",
  "arguments": {"ports": "22,80,443"},
  "rationale": "Identify common exposed services."
}
```

### `http_metadata_probe`

The HTTP adapter requires a single IP address and accepts only `scheme` and `port`. It sends exactly one `HEAD /` request, does not follow redirects, and stores only an allowlisted subset of response headers. Cookies are not collected.

```json
{
  "decision": "action",
  "tool": "http_metadata_probe",
  "target": "192.0.2.10",
  "arguments": {"scheme": "https", "port": 443},
  "rationale": "Collect root HTTPS metadata."
}
```

### Completion

The planner can stop before the step budget is exhausted:

```json
{
  "decision": "complete",
  "summary": "The bounded reconnaissance objective is satisfied."
}
```

## Scope file

Create `scope.json` using only targets covered by written authorization:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

The model cannot select or expand targets. Every action target must exactly match the operator-supplied target and pass scope validation.

## Direct service discovery

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

## Phase 3 recon dry-run

Dry-run asks for and validates only the first decision. It performs no network action and writes no execution evidence.

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

## Phase 3 recon execution

Active multi-step reconnaissance requires both explicit flags:

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

`--max-steps` must be from 1 through 5. The budget is a hard upper bound. The planner may stop earlier with a completion decision.

Each active step is independently scope-checked, executed through the allowlisted harness, and written to the verified hash-chained evidence store. A failed tool step is recorded and returned; it does not create a generic recovery shell path.

## Evidence

Active execution writes to `artifacts/evidence.jsonl` by default. Records include execution ID, timestamp, scope, tool, target, validated arguments, result, duration, ShadowForge version, prior-record hash, and current SHA-256 hash.

Before appending, ShadowForge verifies the full existing chain. A malformed, edited, or broken chain is rejected.

## Safety boundary

Version 0.3.0 intentionally does **not** add:

- generic shell, PowerShell, or Python execution
- model-selected targets
- Nmap NSE/script selection
- exploit execution
- password spraying or credential attacks
- credential dumping or secret retrieval
- relay/coercion
- persistence or evasion
- arbitrary remote commands
- automatic propagation
- unrestricted HTTP paths, methods, or redirects
- unbounded autonomous loops

Phase 3 is bounded reconnaissance orchestration, not a free-running autonomous penetration-testing agent.

## Common errors

- `required primary model ... is not installed`: install `qwen3.5:27b` in Ollama.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `tool is not permitted ...`: the deterministic policy rejected a model decision.
- `decision target must exactly match ...`: the model attempted to change the target.
- `HTTP metadata probe requires one IP address`: use a single authorized IP for HTTP probing, not a CIDR.
- `max_steps must ...`: choose a value from 1 through 5.
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
