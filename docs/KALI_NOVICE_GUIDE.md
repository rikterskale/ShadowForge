# ShadowForge Kali Linux Novice Guide

Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.4.0 supports direct scans, one-action agent mode, bounded recon, and optional persistent recon sessions.

## 1. Install Kali prerequisites

```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip ca-certificates
```

A full Kali upgrade is not required just to install ShadowForge.

## 2. Clone and create a virtual environment

Kali uses an externally managed system Python. Do **not** use `sudo pip` and do not use `--break-system-packages`.

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
shadowforge --help
```

## 3. Install local models

Install Ollama using its supported Linux method, then:

```bash
ollama pull qwen3.5:27b
ollama pull gemma4:31b       # optional
ollama pull devstral-small-2:24b  # optional
ollama list
shadowforge models
```

Qwen is required for model-assisted features. Missing optional specialists fall back to Qwen.

## 4. Create authorized scope

Create `scope.json`:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Use only targets covered by written authorization.

## 5. Direct scan

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## 6. Phase 3 recon dry-run

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

Dry-run performs no network action. `--max-steps` must be between 1 and 5.

## 7. Active bounded recon

Only after confirming written authorization:

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

Each active step passes through scope validation, `Harness.execute()`, an allowlisted adapter, and evidence collection.

## 8. Start a persistent Phase 4 session

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --max-steps 3 \
  --execute
```

The session is stored at:

```text
artifacts/state/assessment-01.json
```

Run the same command later with the same session ID, target, and objective to resume.

## 9. Custom state directory

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --state-dir ./engagement-state
```

A dry-run may read existing state but does not create or modify a state file.

## 10. What persistent state can contain

Only sanitized results from the existing Nmap service scan and HTTP metadata probe are allowed. HTTP state excludes cookies, authorization headers, and unknown fields. Loaded files are validated and sanitized again before being shown to a model.

A session is bound to its original target and objective and is limited to 100 observations. Persistent state cannot expand scope, add tools, change arguments, or increase the hard step budget.

Do not run multiple ShadowForge processes writing to the same session ID simultaneously; cross-process file locking is not yet implemented.

## 11. Evidence versus state

```text
artifacts/evidence.jsonl       hash-chained execution evidence
artifacts/state/<session>.json resumable working memory
```

Session state is not a replacement for evidence.

## 12. Common Kali problems

### `externally-managed-environment`

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Do not use `sudo pip` or `--break-system-packages`.

### `nmap: command not found`

```bash
sudo apt install -y nmap
```

### Qwen missing

```bash
ollama pull qwen3.5:27b
```

### Session errors

- `session must ...`: use a safe ID such as `assessment-01`; do not use spaces, slashes, or path traversal.
- `session ... is bound to target ...`: use the original target or a new session ID.
- `session objective does not match ...`: use the exact original objective or a new session.
- `could not read session state`: inspect the state file and permissions; malformed files are intentionally rejected.

### Other errors

- `max_steps must ...`: choose 1 through 5.
- `outside engagement scope`: do not bypass the check.
- `Refusing to execute`: active model-assisted execution requires `--authorized --execute`.
- `File/system error`: inspect paths and permissions and avoid running ShadowForge with `sudo`.

## 13. Update ShadowForge

```bash
git status
git pull
source .venv/bin/activate
python -m pip install -e .
```

## 14. Cleanup

```bash
deactivate
```

Remove `.venv`, state files, evidence, or the repository only after confirming they are no longer needed.
