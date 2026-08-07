# ShadowForge Windows Novice Guide

This guide assumes little command-line experience. Use ShadowForge only on systems you have written permission to test.

## 1. Install prerequisites
1. Install Python 3.11 or newer from python.org and select **Add Python to PATH** during setup.
2. Install Nmap for Windows from the official Nmap site using its normal installer.
3. Install Git for Windows.
4. If you want local LLM features, install Ollama for Windows.

## 2. Open PowerShell
Press the Windows key, type `PowerShell`, and open **Windows PowerShell** or **Terminal**.

## 3. Clone and enter ShadowForge
```powershell
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

To update an existing copy later:
```powershell
git pull
```

## 4. Create an isolated Python environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If activation is blocked:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 5. Verify the basic tools
```powershell
python --version
nmap --version
shadowforge --help
```

Success means each command prints version/help information without a Python traceback.

## 6. Install the local LLMs
Qwen is the only required model for model features:
```powershell
ollama pull qwen3.5:27b
```

Gemma and Devstral are optional specialists:
```powershell
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check your local models and ShadowForge routing:
```powershell
ollama list
shadowforge models
```

Expected behavior:
- Qwen installed, Gemma missing: critic role falls back to Qwen.
- Qwen installed, Devstral missing: coding role falls back to Qwen.
- Only Qwen installed: all three roles use Qwen.
- Qwen missing: model operations stop and tell you to install Qwen.

If `shadowforge models` says it cannot query Ollama, open Ollama and retry.

## 7. Define your authorized lab
Create a file named `scope.json` in the repository folder:
```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Replace the example ranges with only the IP/CIDR ranges covered by your written authorization. IPv4 and IPv6 ranges may appear together.

## 8. Run a scan
```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

You may also use an ascending range:
```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 80,443,8000-8100
```

Ports must be between 1 and 65535. Empty entries, reversed ranges, and extra Nmap options are rejected.

## 9. Review the evidence
A successful active run writes evidence to:
```text
artifacts\evidence.jsonl
```

Each line records the scope, target, tool, arguments, result, duration, ShadowForge version, execution ID, and a hash linked to the previous record. If the evidence chain is damaged, ShadowForge refuses to append another record.

## Troubleshooting
- `python is not recognized`: reinstall Python with **Add Python to PATH**, then reopen PowerShell.
- `nmap is not recognized`: reopen PowerShell after installing Nmap; reboot Windows if needed.
- `ollama is not recognized`: install Ollama, then reopen PowerShell.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `outside engagement scope`: do not bypass the check. Correct the scope only when authorization covers the target.
- `File/system error`: check the filename/path and permissions.
- `ports must ...`: use forms such as `80`, `22,80,443`, or `8000-8100`.
- `Refusing to run`: add `--authorized` only after confirming written permission.

## Phase 1 limitation
ShadowForge currently has local model discovery/routing and a scope-enforced tool harness, but models do not autonomously launch penetration-testing tools yet.

## Cleanup or uninstall
Deactivate the Python environment:
```powershell
deactivate
```

Then delete `.venv` if you no longer need the environment. Delete the cloned `ShadowForge` folder if you no longer need the project. Ollama models can be removed separately with `ollama rm <model-name>`.
