# ShadowForge Linux Novice Guide

Use ShadowForge only on systems and networks you have written permission to test. This guide is for Debian/Ubuntu-style Linux. Kali users should use `docs/KALI_NOVICE_GUIDE.md`.

ShadowForge 0.4.0 supports direct scans, one-action agent mode, bounded recon, and optional persistent recon sessions.

## 1. Install prerequisites

```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip
```

Install Ollama if you want model-assisted features.

## 2. Clone and install

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

```bash
ollama pull qwen3.5:27b
ollama pull gemma4:31b       # optional
ollama pull devstral-small-2:24b  # optional
shadowforge models
```

Qwen is required. Missing Gemma or Devstral roles fall back to Qwen.

## 4. Create scope.json

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

## 6. Bounded recon dry-run

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

Dry-run performs no active network action. The hard step budget is 1 through 5.

## 7. Active bounded recon

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

Each active step is independently scope-checked and must use an allowlisted adapter.

## 8. Persistent Phase 4 session

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --max-steps 3 \
  --execute
```

State is written to:

```text
artifacts/state/assessment-01.json
```

Run the same command later with the same session ID, target, and objective to resume from prior sanitized observations.

Use another directory if needed:

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --session assessment-01 \
  --state-dir ./engagement-state
```

Dry-run may read existing state but does not create or modify it.

## 9. State safety rules

Persistent state is context only. It cannot expand scope, select new targets, add tools, change argument schemas, or increase the execution budget.

Only sanitized Nmap service observations and filtered HTTP metadata are stored. Unknown tools, cookies, authorization headers, cross-target observations, malformed step ordering, and unknown result fields are rejected or removed.

A session is capped at 100 observations. Do not run multiple writers against the same session ID at the same time.

## 10. Evidence versus state

```text
artifacts/evidence.jsonl       hash-chained execution evidence
artifacts/state/<session>.json resumable planner context
```

Session state is not a replacement for evidence.

## Troubleshooting

- `python3: command not found`: reinstall the prerequisite packages.
- `nmap: command not found`: run `sudo apt install -y nmap`.
- `required primary model ...`: run `ollama pull qwen3.5:27b`.
- `session must ...`: use a safe ID such as `assessment-01`; do not use spaces or path separators.
- `session ... is bound to target ...`: use the original target or create another session.
- `session objective does not match ...`: reuse the exact objective or create another session.
- `could not read session state`: inspect the file and permissions; malformed state is intentionally rejected.
- `max_steps must ...`: choose 1 through 5.
- `outside engagement scope`: do not bypass the check.
- `Refusing to execute`: active model-assisted execution requires `--authorized --execute`.

## Update

```bash
git status
git pull
source .venv/bin/activate
python -m pip install -e .
```

## Cleanup

```bash
deactivate
```

Remove `.venv`, session state, evidence, or the repository only when you no longer need them.
