# ShadowForge Phase 2 Architecture

## Purpose

Phase 2 connects the local LLM routing layer to the Phase 1 execution harness while preserving deterministic authorization and execution boundaries.

Phase 2 deliberately implements **one bounded proposal per invocation**. It is not a free-running autonomous penetration-testing agent.

## Trust boundary

The model is allowed to propose data. It is not allowed to directly execute commands.

```text
Operator
  |
  | objective + exact target
  v
Qwen planner
  |
  | JSON text only
  v
ActionProposal parser
  |
  +-- exact schema
  +-- exact tool allowlist
  +-- exact target equality
  +-- exact argument allowlist
  +-- port-expression validation
  +-- rationale validation
  |
  v
EngagementScope.require()
  |
  v
operator execution gate
  |
  | --execute + --authorized
  v
Harness.execute()
  |
  v
ToolRegistry
  |
  v
NmapTool
  |
  v
EvidenceStore
  |
  v
Gemma critic or Qwen fallback
```

No model output is passed to `subprocess`, a shell, `eval`, `exec`, dynamic imports, or a generic command runner.

## Operator-controlled target

The operator must provide the target using `--target`.

Example:

```bash
shadowforge --scope scope.json agent \
  "Identify common web services" \
  --target 192.0.2.10
```

The planner is not allowed to select or change the target.

The target is validated against the engagement scope before the model is called. The model response must then contain the exact same target string, and ShadowForge scope-checks that parsed target again.

This intentionally prevents target expansion by the model.

## ActionProposal schema

The Phase 2 parser accepts exactly four top-level fields:

```json
{
  "tool": "nmap_service_scan",
  "target": "192.0.2.10",
  "arguments": {
    "ports": "22,80,443"
  },
  "rationale": "Identify common exposed services."
}
```

No extra top-level fields are accepted.

### Tool policy

The only permitted Phase 2 agent tool is:

```text
nmap_service_scan
```

Any other tool string is rejected before active execution.

### Argument policy

The `arguments` object must contain exactly:

```json
{"ports": "..."}
```

No Nmap flags, scripts, shell fragments, additional arguments, environment variables, file paths, or command strings can be added by the model.

The existing Nmap port validator enforces:

- string input
- individual numeric ports or ascending ranges
- ports from 1 through 65535
- no empty entries
- no reversed ranges
- no arbitrary Nmap flags or script syntax

## Planner prompt

The planner system prompt tells the model to:

- return one JSON object only
- use only `nmap_service_scan`
- keep the exact operator target
- choose only ports for non-destructive service discovery
- never propose shell commands, scripts, credentials, exploitation, persistence, evasion, relay, coercion, or a different target

The prompt is defense in depth. The deterministic parser and policy checks are the actual enforcement layer.

## Prompt-injection handling

The operator objective is untrusted input from the policy layer's perspective.

An objective may attempt to instruct the model to ignore its system prompt or propose a different action. This does not grant additional capability because the response must still pass the fixed `ActionProposal` parser.

For example, a model response proposing:

```json
{
  "tool": "shell",
  "target": "192.0.2.10",
  "arguments": {"command": "..."},
  "rationale": "..."
}
```

is rejected before `Harness.execute()` is reached.

## Dry-run mode

Dry-run is the default:

```bash
shadowforge --scope scope.json agent \
  "Identify common services" \
  --target 192.0.2.10
```

Dry-run:

1. loads the engagement scope
2. validates the operator target
3. calls the primary model
4. parses and validates the proposal
5. prints the proposal
6. does not run Nmap
7. does not create an execution evidence record

Dry-run does not require `--authorized` because it performs no active network tool execution.

## Execution mode

Execution requires both:

```text
--execute
--authorized
```

Example:

```bash
shadowforge --scope scope.json --authorized agent \
  "Identify common services" \
  --target 192.0.2.10 \
  --execute
```

If `--execute` is supplied without `--authorized`, ShadowForge refuses before planning or tool execution.

## Evidence

Execution still uses `Harness.execute()`, so Phase 2 does not create a second evidence path.

The same Phase 1 evidence guarantees remain in force:

- execution ID
- scope name
- target
- tool name
- validated arguments
- status
- duration
- ShadowForge version
- result data
- previous record hash
- current record hash
- full existing-chain verification before append

## Critic

After an executed action, ShadowForge sends the objective, validated proposal, and tool result to the critic role.

Preferred critic:

```text
gemma4:31b
```

Fallback:

```text
qwen3.5:27b
```

The critic is advisory only. It is explicitly instructed not to propose commands or additional tool execution.

The critic has no execution handle and its response is printed as text only.

If the critic fails after the tool has executed, the completed tool result and evidence are preserved. The CLI reports a separate `critique_error` rather than masking the completed action.

## Current model roles

```text
primary -> qwen3.5:27b
critic  -> gemma4:31b -> qwen3.5:27b fallback
coding  -> devstral-small-2:24b -> qwen3.5:27b fallback
```

The coding role is not granted an active execution path in the initial Phase 2 agent loop.

## Explicit exclusions

The initial Phase 2 agent loop does not provide model-controlled:

- arbitrary shell execution
- PowerShell execution
- Python execution
- Nmap NSE selection
- exploit execution
- credential collection
- password spraying
- authentication attacks
- relay or coercion
- persistence
- evasion
- remote command execution
- automatic propagation
- autonomous multi-step execution
- model-selected targets

Adding a new active capability requires a typed action schema, deterministic argument validation, explicit registry entry, scope handling, evidence handling, tests, documentation, and an appropriate approval model.

## Future Phase 2 extensions

Safe next extensions can build on the same pattern:

```text
Model proposal
    -> typed schema
    -> capability policy
    -> scope policy
    -> operator approval when active
    -> Harness.execute()
    -> evidence
```

Examples of future non-destructive adapters may include narrowly scoped LDAP metadata queries, SMB capability enumeration, TLS metadata inspection, or parsing previously collected BloodHound/export data. Each should receive its own schema and validation policy rather than a generic command interface.

## Non-negotiable invariant

All active model-assisted execution must eventually pass through:

```python
Harness.execute(...)
```

A future feature that creates a second direct model-to-process execution path violates the ShadowForge trust model and should not be merged.
