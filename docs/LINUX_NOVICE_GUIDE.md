# ShadowForge Linux Novice Guide

Use ShadowForge only on systems and networks you have written permission to test. This guide is for Debian/Ubuntu-style Linux systems.

> **Kali Linux users:** use `docs/KALI_NOVICE_GUIDE.md`. Kali is validated separately and has additional system-Python protections.

ShadowForge 0.2.0 supports direct scans and a bounded Phase 2 agent mode. Agent mode is a dry-run unless you explicitly request execution.

## 1. Install prerequisites

```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip
```

Install Ollama if you want model or agent features.

## 2. Clone ShadowForge

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

## 3. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 4. Verify installation

```bash
python --version
nmap --version
shadowforge --help
```

## 5. Install local models

Required for model features:

```bash
ollama pull qwen3.5:27b
```

Optional:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Verify:

```bash
ollama list
shadowforge models
```

## 6. Create an authorized scope

Create `scope.json`:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Use only IP addresses or CIDR ranges covered by written authorization.

## 7. Run a direct scan

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## 8. Phase 2 agent dry-run

Dry-run is the default:

```bash
shadowforge --scope scope.json agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10
```

Dry-run checks scope, asks Qwen for one structured proposal, validates it, and prints it. It does **not** run Nmap.

Qwen can only propose:

```text
tool: nmap_service_scan
target: exactly the target you supplied
arguments: ports only
rationale: short explanation
```

Any extra tool, different target, extra arguments, Nmap script syntax, malformed ports, or invalid JSON is rejected before network activity.

## 9. Phase 2 agent execution

After confirming written authorization:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10 \
  --execute
```

Both `--authorized` and `--execute` are required.

Execution flow:

```text
objective
 -> Qwen proposal
 -> deterministic policy validation
 -> scope validation
 -> Harness.execute()
 -> allowlisted Nmap adapter
 -> evidence
 -> advisory critic
```

The critic cannot launch follow-on actions. If it fails after the scan, the scan result remains available and ShadowForge reports `critique_error` separately.

## 10. Evidence

Active execution writes:

```text
artifacts/evidence.jsonl
```

ShadowForge verifies the full existing SHA-256 hash chain before appending a new record.

## Troubleshooting

- `python3: command not found`: install the prerequisite packages again and inspect package errors.
- `nmap: command not found`: run `sudo apt install -y nmap`.
- `ollama: command not found`: install Ollama and reopen the terminal.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `proposal must contain exactly ...`: the model response failed the fixed schema; no scan started.
- `tool is not permitted ...`: the model proposed an unsupported tool; no scan started.
- `proposal target must exactly match ...`: the model changed the operator target; no scan started.
- `outside engagement scope`: do not bypass the check.
- `Refusing to execute`: use `--authorized --execute` only after confirming written authorization.
- `ports must ...`: use valid individual ports or ascending ranges from 1 through 65535.
- `critique_error`: the active scan completed but the advisory critic failed.

## Phase 2 limitation

Phase 2 performs one bounded proposal per command. It is not a free-running autonomous penetration-testing agent and does not expose a generic shell or arbitrary-command tool to the model.

## Cleanup

```bash
deactivate
rm -rf .venv
```

Remove the repository directory only when you are sure you no longer need it.
