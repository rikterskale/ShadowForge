# ShadowForge Linux Novice Guide

Use ShadowForge only on systems and networks you have written permission to test. This guide is for Debian/Ubuntu-style Linux systems.

> **Kali Linux users:** use `docs/KALI_NOVICE_GUIDE.md`.

ShadowForge 0.3.0 supports direct scans, Phase 2 single-action planning, and Phase 3 bounded multi-step reconnaissance.

## 1. Install prerequisites

```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip
```

Install Ollama if you want `models`, `agent`, or `recon` features.

## 2. Clone and install

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify:

```bash
python --version
nmap --version
shadowforge --help
```

## 3. Install local models

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

## 6. Phase 2 single-action agent

Dry-run:

```bash
shadowforge --scope scope.json agent \
  "Identify common web and administration services" \
  --target 192.0.2.10
```

Execute only after confirming written authorization:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and administration services" \
  --target 192.0.2.10 \
  --execute
```

## 7. Phase 3 recon dry-run

Phase 3 uses a code-enforced step budget from 1 through 5. Dry-run validates only the first decision and performs no active network action:

```bash
shadowforge --scope scope.json recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3
```

Allowed Phase 3 tools are only:

- `nmap_service_scan` with `ports`
- `http_metadata_probe` with exactly `scheme` and integer `port`

The HTTP probe requires one IP address, sends one `HEAD /`, follows no redirects, and does not collect cookies.

## 8. Execute Phase 3 recon

```bash
shadowforge --scope scope.json --authorized recon \
  "Identify exposed services and collect safe web metadata" \
  --target 192.0.2.10 \
  --max-steps 3 \
  --execute
```

Each active step is scope-checked and executed through `Harness.execute()`. Results are written to evidence and then supplied back to the planner only as untrusted data. The model cannot change the target or exceed the hard step budget.

## 9. Evidence

Active execution writes:

```text
artifacts/evidence.jsonl
```

ShadowForge verifies the full existing SHA-256 hash chain before appending. Each active Phase 3 step gets its own record.

## Troubleshooting

- `python3: command not found`: reinstall prerequisite packages.
- `nmap: command not found`: run `sudo apt install -y nmap`.
- `ollama: command not found`: install Ollama and reopen the terminal.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `tool is not permitted ...`: deterministic policy blocked the model decision.
- `decision target must exactly match ...`: the model attempted to change the operator target.
- `HTTP metadata probe requires one IP address`: use one authorized IP, not a CIDR, for HTTP probing.
- `max_steps must ...`: choose a value from 1 through 5.
- `outside engagement scope`: do not bypass the check.
- `Refusing to execute`: use `--authorized --execute` only after confirming written authorization.
- `critique_error`: the active steps completed and were evidenced; only the advisory critic failed.

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
rm -rf .venv
```

Remove the repository directory only when you are sure you no longer need it.
