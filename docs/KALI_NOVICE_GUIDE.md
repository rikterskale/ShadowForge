# ShadowForge Kali Linux Novice Guide

This guide is specifically for Kali Linux. It assumes little command-line experience. Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.2.0 adds a bounded Phase 2 agent mode. The agent can propose only one non-destructive Nmap service-discovery action for the exact target you provide. Dry-run is the default.

## 1. Open Terminal

Open the **Terminal** application from the Kali menu.

## 2. Refresh Kali's package list

```bash
sudo apt update
```

A full Kali upgrade is not required just to install ShadowForge.

## 3. Install required system packages

```bash
sudo apt install -y git nmap python3 python3-venv python3-pip ca-certificates
```

Verify:

```bash
git --version
nmap --version
python3 --version
```

## 4. Clone ShadowForge

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

If you are testing an unmerged Phase 2 pull request, switch to the branch named in that PR.

## 5. Create an isolated Python environment

Kali uses Debian's externally-managed Python protections. Do **not** use `sudo pip install` and do not use `--break-system-packages` for ShadowForge.

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

## 6. Install Ollama and local models for Phase 2

Direct `scan` mode does not require an LLM. The `models` and `agent` commands do.

After installing Ollama using its supported Linux installation method:

```bash
ollama --version
ollama list
```

Required model:

```bash
ollama pull qwen3.5:27b
```

Optional specialists:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check ShadowForge routing:

```bash
shadowforge models
```

Fallback behavior:

```text
Qwen missing      -> model operations stop
Gemma missing     -> critic role uses Qwen
Devstral missing  -> coding role uses Qwen
Both missing      -> Qwen handles all three roles
```

## 7. Create an authorized scope file

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

Replace the example networks with only authorized IPs/CIDRs.

Save in Nano with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**.

## 8. Run a direct service-discovery scan

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

A successful run prints JSON and writes execution evidence.

## 9. Use Phase 2 agent dry-run first

```bash
shadowforge --scope scope.json agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10
```

Dry-run:

1. validates the target against `scope.json`
2. asks Qwen for one JSON proposal
3. validates the proposal in Python
4. prints the proposal
5. does **not** run Nmap
6. does **not** create active execution evidence

The proposal may contain only:

```text
tool = nmap_service_scan
target = exactly your --target value
arguments = ports only
rationale = short text
```

If Qwen proposes another target, another tool, extra fields, Nmap scripts, or malformed ports, ShadowForge blocks it.

## 10. Execute a validated agent proposal

Only after confirming written authorization:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common web and remote administration services" \
  --target 192.0.2.10 \
  --execute
```

Both `--authorized` and `--execute` are required.

Execution still goes through:

```text
scope check
 -> proposal validation
 -> Harness.execute()
 -> ToolRegistry allowlist
 -> Nmap adapter
 -> evidence
 -> advisory critic
```

The critic cannot launch another action.

If the critic fails after the active scan has already completed, ShadowForge preserves the scan result and reports `critique_error` separately.

## 11. Inspect evidence

Evidence is written to:

```text
artifacts/evidence.jsonl
```

View it with:

```bash
cat artifacts/evidence.jsonl
```

Before appending a new record, ShadowForge verifies every existing record hash and every previous-hash link.

## 12. Common Kali problems

### `externally-managed-environment`

Create and activate the virtual environment:

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
sudo apt update
sudo apt install -y nmap
```

### `could not query Ollama model inventory`

```bash
ollama --version
ollama list
```

Make sure Ollama is running.

### `required primary model ... is not installed`

```bash
ollama pull qwen3.5:27b
```

### `proposal must contain exactly ...`

The planner produced data outside the Phase 2 schema. ShadowForge blocked it before network activity.

### `tool is not permitted ...`

The planner attempted to select an unsupported tool. ShadowForge blocked it.

### `proposal target must exactly match ...`

The planner changed the operator target. ShadowForge blocked it.

### `outside engagement scope`

Do not bypass the check. Correct the scope only when written authorization covers the target.

### `Refusing to execute`

Active agent mode requires both `--authorized` and `--execute`.

### `ports must ...`

Use valid ports from 1 through 65535, for example:

```text
22,80,443,8000-8100
```

### `critique_error`

The active scan completed and was evidenced, but the advisory critic model failed. Review the returned result and evidence.

### `File/system error`

Check paths and permissions:

```bash
ls -l scope.json
ls -ld . artifacts 2>/dev/null
```

Avoid running ShadowForge with `sudo`; fix ownership or permissions instead.

## 13. Phase 2 limitation

Phase 2 is not a free-running autonomous penetration-testing agent. It performs one bounded proposal per invocation and does not expose a generic shell, Python executor, Nmap NSE selector, or arbitrary-command interface to the model.

## 14. Update ShadowForge

```bash
git status
git pull
source .venv/bin/activate
python -m pip install -e .
```

## 15. Leave the virtual environment

```bash
deactivate
```

## 16. Remove ShadowForge

Only after confirming you are deleting the correct folder:

```bash
cd ..
rm -rf ShadowForge
```
