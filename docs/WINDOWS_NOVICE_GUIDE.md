# ShadowForge Windows Novice Guide

This guide assumes little command-line experience. Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.3.0 has three ways to work:

- **Direct scan**: you choose the Nmap ports yourself.
- **Agent mode**: Qwen proposes one safe Nmap service-discovery action.
- **Recon mode**: Qwen may make a bounded sequence of up to five safe reconnaissance decisions using only service discovery and root HTTP metadata probing.

## 1. Install prerequisites

1. Install Python 3.11 or newer from python.org and select **Add Python to PATH**.
2. Install Nmap for Windows using its normal installer.
3. Install Git for Windows.
4. Install Ollama for Windows for `models`, `agent`, or `recon` mode.

## 2. Open PowerShell

Open **PowerShell** or **Windows Terminal**.

## 3. Clone and install ShadowForge

```powershell
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
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

Verify:

```powershell
python --version
nmap --version
shadowforge --help
```

## 4. Install local LLMs

Qwen is required for model-assisted modes:

```powershell
ollama pull qwen3.5:27b
```

Optional specialists:

```powershell
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check routing:

```powershell
ollama list
shadowforge models
```

If Gemma or Devstral is missing, its role falls back to Qwen. If Qwen is missing, model-assisted commands stop with a setup error.

## 5. Create your authorized scope

Create `scope.json`:

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Replace the examples with only ranges covered by your written authorization.

## 6. Direct scan

```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

Ports must be 1 through 65535. Extra Nmap flags and scripts are rejected.

## 7. Phase 2 single-action agent

Dry-run first:

```powershell
shadowforge --scope scope.json agent "Identify common web and administration services" --target 192.0.2.10
```

Dry-run validates one Qwen proposal and performs no network action.

To execute that bounded action:

```powershell
shadowforge --scope scope.json --authorized agent "Identify common web and administration services" --target 192.0.2.10 --execute
```

Both `--authorized` and `--execute` are required for active model-assisted execution.

## 8. Phase 3 recon dry-run

Phase 3 adds a hard step budget. A dry-run still plans only the first decision and performs no active network action:

```powershell
shadowforge --scope scope.json recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --max-steps 3
```

`--max-steps` must be between 1 and 5.

Phase 3 allows only:

- `nmap_service_scan` with a validated `ports` field
- `http_metadata_probe` with exactly `scheme` and integer `port`

The HTTP probe sends one `HEAD /` request, follows no redirects, and does not collect cookies.

## 9. Execute bounded Phase 3 recon

Only after confirming written authorization:

```powershell
shadowforge --scope scope.json --authorized recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --max-steps 3 --execute
```

The sequence is:

```text
objective + exact target
  -> Qwen decision
  -> deterministic schema/policy validation
  -> scope check
  -> Harness.execute()
  -> evidence
  -> result returned as untrusted data
  -> next bounded decision or completion
```

The model cannot change the target, invent tools, add shell commands, choose arbitrary HTTP paths, or exceed the step budget.

## 10. Review evidence

Active runs write to:

```text
artifacts\evidence.jsonl
```

Before adding a record, ShadowForge verifies the existing SHA-256 hash chain. Each active Phase 3 step gets its own evidence record.

## Troubleshooting

- `python is not recognized`: reinstall Python with **Add Python to PATH** and reopen PowerShell.
- `nmap is not recognized`: reopen PowerShell after installing Nmap.
- `ollama is not recognized`: install Ollama and reopen PowerShell.
- `could not query Ollama model inventory`: make sure Ollama is running.
- `required primary model ... is not installed`: run `ollama pull qwen3.5:27b`.
- `tool is not permitted ...`: the deterministic policy blocked the model decision.
- `decision target must exactly match ...`: the model tried to change the operator target.
- `HTTP metadata probe requires one IP address`: use one authorized IP, not a CIDR, for HTTP probing.
- `max_steps must ...`: choose 1 through 5.
- `outside engagement scope`: do not bypass the check; correct the scope only when authorization covers the target.
- `Refusing to execute`: active model-assisted execution needs both `--execute` and `--authorized`.
- `critique_error`: active steps already completed and were evidenced; only the advisory critic failed.

## Update

```powershell
git status
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Cleanup

```powershell
deactivate
```

Delete `.venv` and the cloned repository only if you no longer need them. Ollama models can be removed with `ollama rm <model-name>`.
