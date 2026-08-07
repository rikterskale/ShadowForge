# ShadowForge Windows Novice Guide

This guide assumes little command-line experience. Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.2.0 has two ways to work:

- **Direct scan**: you choose the ports yourself.
- **Agent mode**: Qwen proposes one safe service-discovery scan for the exact target you provide. Agent mode is a dry-run unless you explicitly add `--execute`.

## 1. Install prerequisites

1. Install Python 3.11 or newer from python.org and select **Add Python to PATH** during setup.
2. Install Nmap for Windows from the official Nmap site using its normal installer.
3. Install Git for Windows.
4. Install Ollama for Windows if you want `shadowforge models` or Phase 2 `agent` mode.

## 2. Open PowerShell

Press the Windows key, type `PowerShell`, and open **Windows PowerShell** or **Terminal**.

## 3. Clone and enter ShadowForge

```powershell
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
```

If you are testing a Phase 2 branch before it is merged, switch to the branch named in that pull request.

To update an existing copy later:

```powershell
git status
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

## 7. Create your authorized scope file

Create `scope.json` in the ShadowForge folder:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Replace the example ranges with only the IP/CIDR ranges covered by your written authorization.

## 8. Run a direct scan

```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

You may also use ascending ranges:

```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 80,443,8000-8100
```

Ports must be between 1 and 65535. Empty entries, reversed ranges, and extra Nmap options are rejected.

## 9. Use Phase 2 agent mode safely

Agent mode requires Ollama and Qwen.

The safest first command is a **dry-run**:

```powershell
shadowforge --scope scope.json agent "Identify common web and remote administration services" --target 192.0.2.10
```

A dry-run:

1. checks that the target is in `scope.json`
2. asks Qwen for one structured proposal
3. validates the proposal
4. prints the proposal
5. does **not** run Nmap
6. does **not** create a network-execution evidence record

You should see JSON with:

```text
"mode": "dry-run"
```

and a proposal containing only:

```text
tool
target
arguments -> ports
rationale
```

### What Qwen is allowed to choose

Qwen may choose only the TCP ports for one `nmap_service_scan`.

Qwen cannot change:

- the target you supplied
- the tool name
- the allowed argument fields
- the ShadowForge execution path

If the model tries to add another command, another target, an Nmap script, or an extra field, ShadowForge rejects the proposal before active execution.

## 10. Execute a validated Phase 2 proposal

Only do this after confirming written authorization for the target:

```powershell
shadowforge --scope scope.json --authorized agent "Identify common web and remote administration services" --target 192.0.2.10 --execute
```

Both `--authorized` and `--execute` are required for active agent execution.

The order is:

```text
Your objective
  -> Qwen proposal
  -> schema/policy checks
  -> scope check
  -> Harness.execute()
  -> allowlisted Nmap adapter
  -> evidence
  -> critic review
```

The critic is advisory only and cannot launch another scan.

If the critic fails after the scan already completed, ShadowForge still returns the scan result and reports a separate `critique_error`.

## 11. Review the evidence

Active runs write evidence to:

```text
artifacts\evidence.jsonl
```

Each line records the scope, target, tool, arguments, result, duration, ShadowForge version, execution ID, and hash-chain values.

Before ShadowForge adds another record, it verifies the existing evidence chain.

## 12. Understand the Phase 2 safety boundary

Phase 2 is not a free-running autonomous penetration-testing agent.

It performs one bounded proposal per command and currently permits only non-destructive Nmap service discovery.

It does not give the model a generic PowerShell, command-prompt, Python, or shell executor.

## Troubleshooting

- `python is not recognized`: reinstall Python with **Add Python to PATH**, then reopen PowerShell.
- `nmap is not recognized`: reopen PowerShell after installing Nmap; reboot Windows if needed.
- `ollama is not recognized`: install Ollama, then reopen PowerShell.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `proposal must contain exactly ...`: Qwen returned output outside the fixed Phase 2 schema. No scan was started.
- `tool is not permitted ...`: the model proposed an unsupported tool. No scan was started.
- `proposal target must exactly match ...`: the model changed the target. No scan was started.
- `outside engagement scope`: do not bypass the check. Correct the scope only when written authorization covers the target.
- `Refusing to execute`: active agent mode needs `--execute` and `--authorized`.
- `File/system error`: check the filename/path and permissions.
- `ports must ...`: use forms such as `80`, `22,80,443`, or `8000-8100`.
- `critique_error`: the scan already completed, but the advisory critic failed. Review the returned result and evidence.

## Cleanup or uninstall

Deactivate the Python environment:

```powershell
deactivate
```

Then delete `.venv` if you no longer need the environment. Delete the cloned `ShadowForge` folder if you no longer need the project.

Ollama models can be removed separately:

```powershell
ollama rm qwen3.5:27b
ollama rm gemma4:31b
ollama rm devstral-small-2:24b
```
