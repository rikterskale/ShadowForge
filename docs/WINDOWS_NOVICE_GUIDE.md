# ShadowForge Windows Novice Guide

Use ShadowForge only on systems and networks you have written permission to test.

ShadowForge 0.4.0 supports direct scans, one-action agent mode, bounded multi-step recon, and optional persistent recon sessions.

## 1. Install prerequisites

Install Python 3.11 or newer, Nmap, Git for Windows, and Ollama. When installing Python, select **Add Python to PATH**.

Open PowerShell and verify:

```powershell
python --version
nmap --version
git --version
ollama --version
```

## 2. Clone and install ShadowForge

```powershell
git clone https://github.com/rikterskale/ShadowForge.git
cd ShadowForge
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
shadowforge --help
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Install local models

Required:

```powershell
ollama pull qwen3.5:27b
```

Optional:

```powershell
ollama pull gemma4:31b
ollama pull devstral-small-2:24b
```

Check routing:

```powershell
ollama list
shadowforge models
```

Gemma and Devstral fall back to Qwen when missing. Qwen itself is required for model-assisted commands.

## 4. Create scope.json

```json
{
  "name": "authorized-lab",
  "targets": ["192.0.2.0/24", "2001:db8::/32"]
}
```

Replace the examples with only targets covered by written authorization.

## 5. Direct scan

```powershell
shadowforge --scope scope.json --authorized scan 192.0.2.10 --ports 22,80,443
```

## 6. Agent dry-run

```powershell
shadowforge --scope scope.json agent "Identify common web services" --target 192.0.2.10
```

Dry-run performs no network action.

## 7. Bounded recon dry-run

```powershell
shadowforge --scope scope.json recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --max-steps 3
```

`--max-steps` must be between 1 and 5. Dry-run validates only the first decision.

## 8. Active bounded recon

Only after confirming written authorization:

```powershell
shadowforge --scope scope.json --authorized recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --max-steps 3 --execute
```

Allowed active tools remain only constrained Nmap service discovery and a single root HTTP metadata `HEAD /` request. There is no generic shell or command runner.

## 9. Start a persistent Phase 4 session

Use a short session name containing letters, numbers, dot, underscore, or hyphen:

```powershell
shadowforge --scope scope.json --authorized recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --session assessment-01 --max-steps 3 --execute
```

The session is stored at:

```text
artifacts\state\assessment-01.json
```

Run the same command later with the same session name, target, and objective to resume from prior sanitized observations.

## 10. Use another state directory

```powershell
shadowforge --scope scope.json recon "Identify exposed services and collect safe web metadata" --target 192.0.2.10 --session assessment-01 --state-dir C:\ShadowForgeState
```

A dry-run can read existing state but does not create or modify the state file.

## 11. Understand state versus evidence

Execution evidence is written to:

```text
artifacts\evidence.jsonl
```

Persistent working memory is written to:

```text
artifacts\state\<session>.json
```

Evidence is hash-chained. Session state is resumable planner context and is treated as untrusted data.

## 12. What persistent state stores

Only sanitized Nmap service records and filtered HTTP metadata are stored. Cookies, authorization headers, unknown tools, cross-target observations, malformed ordering, and unknown fields are rejected or removed.

A session can hold at most 100 observations. Do not run two ShadowForge processes that write to the same session at the same time.

## Troubleshooting

- `python is not recognized`: reinstall Python with **Add Python to PATH**, then reopen PowerShell.
- `nmap is not recognized`: reopen PowerShell after installing Nmap.
- `ollama is not recognized`: install Ollama and reopen PowerShell.
- `required primary model ...`: run `ollama pull qwen3.5:27b`.
- `session must ...`: use a name such as `assessment-01`; do not use slashes, spaces, or `..` path traversal.
- `session ... is bound to target ...`: use the original target or create another session name.
- `session objective does not match ...`: use the exact original objective or create another session.
- `could not read session state`: the state file is malformed or unreadable; preserve it for troubleshooting, then use a new session if appropriate.
- `max_steps must ...`: choose 1 through 5.
- `outside engagement scope`: do not bypass the check.
- `Refusing to execute`: active model-assisted execution requires both `--authorized` and `--execute`.

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

Delete `.venv`, state files, evidence, or the cloned repository only after confirming they are no longer needed.
