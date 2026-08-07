# ShadowForge Windows Novice Guide

This guide assumes little command-line experience. Use ShadowForge only on systems you have written permission to test.

## 1. Install prerequisites
1. Install Python 3.11 or newer from python.org and select **Add Python to PATH** during setup.
2. Install Nmap for Windows from the official Nmap site using its normal installer.
3. Install Git for Windows if you plan to clone the repository.

## 2. Open PowerShell
Press the Windows key, type `PowerShell`, and open **Windows PowerShell** or **Terminal**.

## 3. Clone and enter ShadowForge
```powershell
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

## 4. Create an isolated Python environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```
If activation is blocked, run `Set-ExecutionPolicy -Scope Process Bypass` and activate again.

## 5. Verify tools
```powershell
python --version
nmap --version
shadowforge --help
```
Success means each command prints version/help information without an error.

## 6. Define your authorized lab
Create `scope.json` in the repository folder:
```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24"]
}
```
Replace the example range with only the IP/CIDR ranges covered by your written authorization.

## 7. Run a scan
```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```
A successful run prints JSON and writes evidence to `artifacts\evidence.jsonl`.

## Troubleshooting
- `python is not recognized`: reinstall Python and enable **Add Python to PATH**, then reopen PowerShell.
- `nmap is not recognized`: reopen PowerShell after Nmap installation; if needed reboot Windows.
- `outside engagement scope`: do not bypass the check. Correct the scope file only if the target is truly authorized.
- `Refusing to run`: add `--authorized` only after confirming written permission.

## Remove the local environment
Deactivate with `deactivate`, then delete the `.venv` folder. Delete the cloned `ShadowForge` folder if you no longer need it.
