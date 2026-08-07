# AGENTS.md

## Project intent
ShadowForge is for authorized security testing. Preserve scope enforcement, explicit operator authorization, evidence collection, and the allowlisted-tool boundary.

## Non-negotiable engineering rules
- Never turn raw LLM output into shell execution.
- Every network-active tool must validate its target through `EngagementScope` before execution.
- New tools must be explicitly registered; no dynamic import-and-execute behavior.
- Network calls require timeouts and useful errors.
- Do not log secrets or API keys.
- Behavior changes require tests.
- Keep test coverage at or above 99%.
- Run `ruff check .`, `coverage run -m pytest`, and `coverage report --fail-under=99` before merge.

## Documentation rules
Update docs whenever installation, CLI arguments, configuration, environment variables, expected output, supported systems, examples, troubleshooting, security assumptions, or limitations change.

Maintain these beginner-facing files:
- `docs/WINDOWS_NOVICE_GUIDE.md`
- `docs/LINUX_NOVICE_GUIDE.md`

Each guide should include prerequisites, exact installation steps, commands, expected successful output, common errors and fixes, and cleanup/uninstall steps when relevant.
