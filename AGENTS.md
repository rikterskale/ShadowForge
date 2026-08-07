# AGENTS.md

## Project intent
ShadowForge is for authorized security testing. Preserve scope enforcement, explicit operator authorization, evidence integrity, and the allowlisted-tool boundary.

## Non-negotiable engineering rules
- Never turn raw LLM output into shell execution.
- Future model-driven actions must use a structured proposal/validation layer and must enter active execution through `Harness.execute()`.
- Every network-active tool must validate its target through `EngagementScope` before execution.
- Scope logic must support mixed IPv4/IPv6 entries without weakening authorization checks.
- New tools must be explicitly registered; no dynamic import-and-execute behavior.
- Network and process calls require timeouts and useful errors.
- Validate tool arguments before starting external processes.
- Do not log secrets or API keys.
- Preserve the evidence hash chain and reproducibility metadata.
- Behavior changes require tests, including negative/error-path tests.
- Keep statement and branch coverage at or above 99%.
- Pin third-party GitHub Actions to immutable commit SHAs.
- Keep direct CI tooling versions pinned in `requirements-ci.txt`.

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

CI must also validate supported Windows and Linux environments, and CodeQL must pass.

## Documentation rules
Update docs whenever installation, CLI arguments, model behavior, configuration, environment variables, expected output, supported systems, examples, troubleshooting, security assumptions, evidence format, or limitations change.

Maintain these beginner-facing files:
- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`

Each guide should include prerequisites, exact installation steps, commands, expected successful output, common errors and fixes, model fallback behavior when applicable, evidence location, and cleanup/uninstall steps when relevant.
