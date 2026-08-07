# ShadowForge Linux Novice Guide

Use ShadowForge only on systems you have written permission to test. Commands below are for Debian/Ubuntu/Kali-style systems.

## 1. Open Terminal
Open your system's Terminal application.

## 2. Install prerequisites
```bash
sudo apt update
sudo apt install -y git nmap python3 python3-venv python3-pip
```

## 3. Clone and enter ShadowForge
```bash
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

## 4. Create an isolated Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 5. Verify tools
```bash
python --version
nmap --version
shadowforge --help
```
Success means version/help information appears without an error.

## 6. Define your authorized lab
Create `scope.json`:
```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24"]
}
```
Replace the example with only the IP/CIDR ranges named in your written authorization.

## 7. Run a scan
```bash
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```
Results print as JSON and evidence is written to `artifacts/evidence.jsonl`.

## Troubleshooting
- `python3: command not found`: rerun the prerequisite install command and inspect any package errors.
- `nmap: command not found`: install it with `sudo apt install -y nmap`.
- `outside engagement scope`: do not bypass the check; correct the scope only when authorization covers the target.
- `Refusing to run`: use `--authorized` only after confirming written permission.

## Cleanup
Run `deactivate`, then remove `.venv` with `rm -rf .venv`. Remove the cloned repository directory if it is no longer needed.
