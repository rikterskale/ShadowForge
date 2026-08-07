# ShadowForge Linux Novice Guide

Use ShadowForge only on systems you have written permission to test. This guide is for Debian/Ubuntu-style Linux systems.

> **Kali Linux users:** use `docs/KALI_NOVICE_GUIDE.md`. Kali has additional system-Python protections and is validated separately in CI using the official Kali rolling container.

## 1. Open Terminal
Open your system's Terminal application.

## 2. Install prerequisites
```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip
```

If you want local LLM features, install Ollama using its official Linux installation instructions.

## 3. Clone and enter ShadowForge
```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

To update an existing copy later:
```bash
git pull
```

## 4. Create an isolated Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 5. Verify the basic tools
```bash
python --version
nmap --version
shadowforge --help
```

Success means version/help information appears without a Python traceback.

## 6. Install the local LLMs
Qwen is the only required model for model features:
```bash
ollama pull qwen3.5:27b
```

Gemma and Devstral are optional specialists:
```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check the installed models and active routing:
```bash
ollama list
shadowforge models
```

Expected behavior:
- Qwen installed, Gemma missing: critic role falls back to Qwen.
- Qwen installed, Devstral missing: coding role falls back to Qwen.
- Only Qwen installed: all three roles use Qwen.
- Qwen missing: model operations stop and provide the Qwen install command.

If ShadowForge cannot query Ollama, make sure the Ollama service is running and retry.

## 7. Define your authorized lab
Create `scope.json`:
```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Replace the example ranges with only the IP/CIDR ranges named in your written authorization. IPv4 and IPv6 ranges can be used in the same scope file.

## 8. Run a scan
```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

Ascending ranges are also accepted:
```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 80,443,8000-8100
```

Ports must be between 1 and 65535. Empty entries, reversed ranges, and extra Nmap options are rejected.

## 9. Review the evidence
Evidence is written to:
```text
artifacts/evidence.jsonl
```

Each execution records the scope, target, tool, arguments, result, duration, ShadowForge version, execution ID, and a SHA-256 hash linked to the prior record. If the existing chain is malformed, ShadowForge refuses to append a new record.

## Troubleshooting
- `python3: command not found`: rerun the prerequisite installation and inspect package errors.
- `nmap: command not found`: run `sudo apt install -y nmap`.
- `ollama: command not found`: install Ollama and reopen the terminal.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `outside engagement scope`: do not bypass the check; correct the scope only when authorization covers the target.
- `File/system error`: verify the scope/evidence path and permissions.
- `ports must ...`: use forms such as `80`, `22,80,443`, or `8000-8100`.
- `Refusing to run`: use `--authorized` only after confirming written permission.

## Phase 1 limitation
ShadowForge currently has local model discovery/routing and a scope-enforced tool harness, but models do not autonomously launch penetration-testing tools yet.

## Cleanup or uninstall
Deactivate the environment:
```bash
deactivate
```

Delete the environment if desired:
```bash
rm -rf .venv
```

Remove the cloned repository directory if it is no longer needed. Ollama models can be removed separately with `ollama rm <model-name>`.
