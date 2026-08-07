# ShadowForge Phase 3 Architecture

## Goal

Phase 3 adds bounded multi-step reconnaissance without creating a generic autonomous command runner.

## Execution flow

```text
operator objective + exact target
        -> Qwen decision
        -> strict decision schema
        -> per-tool argument policy
        -> exact-target check
        -> EngagementScope.require()
        -> hard step budget (1..5)
        -> dry-run or explicit execution gate
        -> Harness.execute()
        -> allowlisted adapter
        -> verified evidence
        -> result fed back as untrusted data
        -> next bounded decision or completion
        -> advisory critic
```

## Allowed active tools

### nmap_service_scan

Only the existing validated `ports` expression is accepted. No NSE scripts, extra flags, source spoofing, or arbitrary Nmap options are model-controlled.

### http_metadata_probe

The target must be one IP address. Arguments are exactly:

```json
{"scheme": "http", "port": 80}
```

or HTTPS with a valid TCP port. The adapter sends exactly one `HEAD /` request, does not follow redirects, and records only allowlisted metadata headers. `Set-Cookie` is intentionally excluded.

## Planner decisions

The planner returns exactly one action or one completion object per turn. Extra fields or capabilities are rejected.

Prior tool results are labeled as untrusted data. If a target-controlled banner or HTTP header contains instructions for the model, those instructions have no direct authority: the next output still must pass the same deterministic policy and scope checks.

## Step budget

`--max-steps` is restricted to 1 through 5. The orchestrator cannot exceed this value. A planner completion decision can stop earlier.

Dry-run returns only the first validated decision and performs no active tool execution.

## Approval boundary

Active recon requires both:

```text
--execute
--authorized
```

The authorization flag remains an operator acknowledgement; it does not expand scope.

## Critic boundary

The critic receives the run results after active execution and can provide advisory interpretation only. It has no tool or harness handle. Critic failure is reported separately and does not invalidate already-recorded execution evidence.

## Explicit exclusions

Phase 3 does not add generic shell/PowerShell/Python execution, exploits, credential attacks, password spraying, secret retrieval, relay/coercion, persistence, evasion, arbitrary remote commands, propagation, model-selected targets, arbitrary HTTP methods/paths, Nmap NSE selection, or unbounded autonomous execution.

## Future extension rule

Every new active capability must have:

1. an explicit tool registration,
2. a typed/deterministic argument policy,
3. scope semantics,
4. bounded timeouts and errors,
5. evidence behavior,
6. negative-path tests,
7. novice documentation,
8. no alternate execution route around `Harness.execute()`.
