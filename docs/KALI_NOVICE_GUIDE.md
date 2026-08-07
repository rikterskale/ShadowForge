# ShadowForge Kali Linux Novice Guide

This guide is specifically for Kali Linux. It assumes little command-line experience. Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.3.0 supports direct scans, Phase 2 single-action planning, and Phase 3 bounded multi-step reconnaissance.

## 1. Open Terminal and refresh packages

```bash
sudo apt update
```

A full Kali upgrade is not required just to install ShadowForge.

## 2. Install required packages

```bash
sudo apt install -y git nmap python3 python3-venv python3-pip ca-certificates
```

Verify:

```bash
git --version
nmap --version
python3 --version
```

## 3. Clone ShadowForge

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

## 4. Create a Kali-safe Python environment

Do **not** use `sudo pip` and do not use `--break-system-packages`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify:

```bash
shadowforge --help
```

## 5. Install Ollama and local models

Direct `scan` mode does not require Ollama. Model-assisted `agent` and `recon` modes do.

Required:

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

Gemma and Devstral fall back to Qwen if missing. Qwen itself is required for model-assisted commands.

## 6. Create authorized scope

```bash
nano scope.json
```

Example:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Use only targets covered by written authorization.

## 7. Direct scan

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## 8. Phase 2 agent dry-run

```bash
shadowforge --scope scope.json agent \
  "Identify common web and administration services" \
  --target 192.0.2.10
```

Dry-run validates one Qwen proposal and performs no network action.

Execute one validated Phase 2 action only after confirming written authorization:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and administration services" \
  --target 192.0.2.10 \
  --execute
```

## 9. Phase 3 recon dry-run

Phase 3 adds a hard step budget from 1 through 5. Dry-run validates only the first decision and performs no active network action:

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

Allowed Phase 3 tools are only:

- `nmap_service_scan` with a validated `ports` expression
- `http_metadata_probe` with exactly `scheme` and integer `port`

The HTTP probe requires one IP address, sends one `HEAD /`, follows no redirects, and intentionally does not record cookies or authorization headers.

## 10. Execute Phase 3 recon

Only after confirming written authorization:

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

Every active step passes through:

```text
planner decision
 -> deterministic policy validation
 -> exact-target check
 -> scope validation
 -> Harness.execute()
 -> allowlisted adapter
 -> evidence
 -> result returned as untrusted data
 -> next bounded decision or completion
```

The model cannot exceed the hard step budget or gain a generic shell/command path from tool output.

## 11. Evidence

Evidence is written to:

```text
artifacts/evidence.jsonl
```

View it with:

```bash
cat artifacts/evidence.jsonl
```

ShadowForge verifies the full existing SHA-256 hash chain before appending. Each active Phase 3 step creates its own evidence record.

## 12. Common Kali problems

### `externally-managed-environment`

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Do not use `sudo pip` or `--break-system-packages`.

### `python3: No module named venv`

```bash
sudo apt update
sudo apt install -y python3-venv
```

### `nmap: command not found`

```bash
sudo apt install -y nmap
```

### Ollama errors

```bash
ollama --version
ollama list
```

If Qwen is missing:

```bash
ollama pull qwen3.5:27b
```

### `tool is not permitted ...`

The deterministic policy blocked a model-selected capability that Phase 3 does not allow.

### `decision target must exactly match ...`

The planner attempted to change your target. ShadowForge blocked it.

### `HTTP metadata probe requires one IP address`

Use one authorized IP for HTTP probing, not a CIDR range.

### `max_steps must ...`

Choose a value from 1 through 5.

### `outside engagement scope`

Do not bypass the check. Correct scope only when your written authorization covers the target.

### `Refusing to execute`

Active model-assisted modes require `--authorized --execute`.

### `critique_error`

The active steps completed and were evidenced; only the advisory critic failed.

### `File/system error`

```bash
ls -l scope.json
ls -ld . artifacts 2>/dev/null
```

Avoid running ShadowForge with `sudo`; fix ownership or permissions instead.

## 13. Update ShadowForge

```bash
git status
git pull
source .venv/bin/activate
python -m pip install -e .
```

## 14. Leave the environment

```bash
deactivate
```

## 15. Remove ShadowForge

Only after confirming the folder is correct:

```bash
cd ..
rm -rf ShadowForge
```
