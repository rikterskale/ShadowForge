# AGENTS.md

## Project intent
ShadowForge is for authorized security testing. Preserve scope enforcement, explicit operator authorization, evidence integrity, and the allowlisted-tool boundary.

## Non-negotiable engineering rules
- Never turn raw LLM output into shell execution.
- All model-driven active actions must use a typed/structured proposal and deterministic validation layer.
- All active execution must enter through `Harness.execute()`; do not create an alternate model-to-process path.
- Models may propose data, but code owns capability selection, target checks, argument validation, approval gates, and execution.
- Every network-active tool must validate its target through `EngagementScope` before execution.
- Scope logic must support mixed IPv4/IPv6 entries without weakening authorization checks.
- Model-selected target expansion is not allowed. Phase 2 proposals must match the operator-supplied target exactly unless a future reviewed schema explicitly defines otherwise.
- New tools must be explicitly registered; no dynamic import-and-execute behavior.
- New model-assisted active capabilities require their own typed action schema and argument policy. Do not add a generic command schema.
- Network and process calls require timeouts and useful errors.
- Validate tool arguments before starting external processes.
- Dry-run must remain the default for model-assisted planning.
- Active agent execution must require explicit operator authorization and an explicit execution flag.
- Critics/review models are advisory only and must not receive an execution handle.
- A critic failure after active execution must not hide or invalidate an already-evidenced tool result.
- Do not log secrets or API keys.
- Preserve full evidence-chain verification and reproducibility metadata.
- Behavior changes require tests, including negative/error-path and policy-bypass tests.
- Keep statement and branch coverage at or above 99%.
- Pin third-party GitHub Actions to immutable commit SHAs.
- Keep direct CI tooling versions pinned in `requirements-ci.txt`.
- Preserve first-class Windows, Ubuntu/Linux, and Kali Linux support.
- Kali installation must use a virtual environment; do not instruct users to use `sudo pip` or `--break-system-packages`.

## Phase 2 action policy
The initial Phase 2 `agent` command is intentionally bounded:

- operator supplies the exact target
- Qwen proposes one action only
- only `nmap_service_scan` is allowed
- proposal arguments must contain only `ports`
- port expressions use the existing strict validator
- proposal target must exactly equal the operator target
- target is scope-checked before the model call and after proposal parsing
- no active action occurs unless both `--execute` and `--authorized` are supplied
- the post-execution critic cannot launch follow-on actions

Do not broaden this into arbitrary command execution or automatic multi-step propagation without a separately reviewed architecture and explicit policy controls.

## Required validation before merge
Run or confirm CI equivalents of:
```bash
python -m pip install -r requirements-ci.txt
python -m pip install -e .
ruff check .
coverage run -m pytest
coverage report --fail-under=99
python -m build
python -m pip check
pip-audit -r requirements-ci.txt
```

CI must validate supported Windows and Ubuntu environments, validate the project in an official Kali rolling container, and pass CodeQL.

## Documentation rules
Update docs whenever installation, CLI arguments, model behavior, proposal schemas, capability policy, approval behavior, configuration, environment variables, expected output, supported systems, examples, troubleshooting, security assumptions, evidence format, or limitations change.

Maintain these beginner-facing files:
- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`
- `docs/KALI_NOVICE_GUIDE.md`

Maintain the Phase 2 design reference:
- `docs/PHASE2_ARCHITECTURE.md`

Each novice guide should include prerequisites, exact installation steps, commands, expected successful output, common errors and fixes, model fallback behavior, dry-run versus active execution, evidence location, and cleanup/uninstall steps when relevant.
