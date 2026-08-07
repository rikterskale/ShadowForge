# ShadowForge Kali Linux Novice Guide

This guide is specifically for Kali Linux. It assumes little command-line experience. Use ShadowForge only on systems and networks you have written permission to test.

## 1. Open Terminal
Open the **Terminal** application from the Kali menu.

## 2. Refresh Kali's package list
Run:

```bash
sudo apt update
```

A full Kali system upgrade is not required just to install ShadowForge. If you normally maintain Kali with `apt full-upgrade`, do that separately according to your normal system-maintenance process.

## 3. Install required system packages
Run:

```bash
sudo apt install -y git nmap python3 python3-venv python3-pip ca-certificates
```

Verify them:

```bash
git --version
nmap --version
python3 --version
```

Each command should print version information.

## 4. Clone ShadowForge
Choose a folder where you keep projects, then run:

```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

If you are testing the Phase 1 pull request before it is merged, use the branch named in that pull request instead of `main`.

## 5. Create an isolated Python environment
Kali uses Debian's externally-managed Python protections. Do **not** use `sudo pip install` and do not bypass those protections with `--break-system-packages` for ShadowForge.

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should now normally begin with `(.venv)`.

Install ShadowForge:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify the CLI:

```bash
shadowforge --help
```

## 6. Optional: install Ollama for local model features
The current Phase 1 network scan does not require an LLM. Ollama is required only for model discovery/routing features.

After installing Ollama using its supported Linux installation method, verify:

```bash
ollama --version
ollama list
```

ShadowForge requires this model for model operations:

```bash
ollama pull qwen3.5:27b
```

These specialist models are optional:

```bash
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Fallback behavior:

```text
Qwen missing      -> model operations stop
Gemma missing     -> critic role uses Qwen
Devstral missing  -> coding role uses Qwen
Both missing      -> Qwen handles all three roles
```

Check ShadowForge's selected routing:

```bash
shadowforge models
```

If Ollama is not running, this command reports a model-inventory connection error. That does not prevent the Phase 1 Nmap scan command from running.

## 7. Create an authorized scope file
Create a file named `scope.json` in the ShadowForge folder:

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

Replace the example networks with only the IP addresses or CIDR ranges covered by your written authorization.

In Nano, save with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**.

## 8. Run a service-discovery scan
Example:

```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

A successful run prints JSON describing discovered open services.

ShadowForge writes evidence to:

```text
artifacts/evidence.jsonl
```

Evidence records contain execution metadata and a SHA-256 hash chain. Before ShadowForge appends a new record, it verifies every existing record hash and every previous-hash link; a modified or broken chain is rejected.

## 9. Inspect the evidence file
Run:

```bash
cat artifacts/evidence.jsonl
```

The file is JSON Lines format: one JSON record per execution. Viewing the file with `cat` only displays it; ShadowForge's chain validation happens automatically before the next record is appended.

## 10. Common Kali problems

### `externally-managed-environment`
You attempted to install packages into Kali's system Python.

Fix:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Do not use `sudo pip` or `--break-system-packages` for this project.

### `python3: No module named venv`
Install the virtual-environment package:

```bash
sudo apt update
sudo apt install -y python3-venv
```

Then recreate `.venv`.

### `nmap: command not found`
Run:

```bash
sudo apt update
sudo apt install -y nmap
```

### `outside engagement scope`
Do not bypass the check. Confirm that the target is authorized and correct `scope.json` only when your written authorization covers it.

### `ports must ...`
Use only valid ports from 1 through 65535, for example:

```text
22,80,443,8000-8100
```

### `could not query Ollama model inventory`
Verify Ollama is installed and running:

```bash
ollama --version
ollama list
```

### `required primary model ... is not installed`
Install Qwen:

```bash
ollama pull qwen3.5:27b
```

### `File/system error`
Check that `scope.json` exists and that your user can create files under the ShadowForge folder:

```bash
ls -l scope.json
ls -ld . artifacts 2>/dev/null
```

Avoid running ShadowForge with `sudo`; fix directory ownership or permissions instead.

## 11. Update ShadowForge
From the repository folder:

```bash
git status
git pull
```

Then activate the environment and reinstall the editable package if needed:

```bash
source .venv/bin/activate
python -m pip install -e .
```

Do not run `git pull` if you have local changes you do not understand; review `git status` first.

## 12. Leave the virtual environment
Run:

```bash
deactivate
```

## 13. Remove ShadowForge
If you no longer need the local copy, first leave the repository folder, then delete it:

```bash
cd ..
rm -rf ShadowForge
```

Only run the delete command after confirming you are deleting the intended folder.
