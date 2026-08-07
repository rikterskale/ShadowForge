# ShadowForge Phase 4 Architecture

## Goal

Phase 4 adds resumable, persistent engagement state to bounded reconnaissance without turning memory into authority.

## Core rule

Persistent state is **untrusted context**. It can help Qwen avoid repeating work and reason about prior observations, but it cannot select new targets, add tools, alter scope, expand argument schemas, increase the step budget, or bypass `Harness.execute()`.

## Flow

```text
operator objective + exact target
        -> optional --session ID
        -> load validated session state
        -> Qwen bounded decision
        -> deterministic policy validation
        -> exact-target + scope validation
        -> hard 1..5 step budget
        -> dry-run or --execute + --authorized
        -> Harness.execute()
        -> allowlisted Nmap / HTTP metadata adapter
        -> hash-chained execution evidence
        -> sanitized persistent observation
        -> atomic session-state save
        -> next bounded decision or completion
        -> advisory critic
```

## Session binding

A session ID is restricted to 1-64 characters containing letters, numbers, dot, underscore, and hyphen. Values containing path separators or traversal syntax are rejected.

The first active run binds the session to:

- exact operator target
- exact normalized objective
- state schema version

A later run cannot reuse the same session ID for another target or objective.

## State location

The default directory is:

```text
artifacts/state/
```

A session named `assessment-01` is stored as:

```text
artifacts/state/assessment-01.json
```

The operator can select another directory with `--state-dir`.

## Stored observations

Only results from the current allowlisted reconnaissance tools can enter persistent memory.

### Nmap

Stored state contains only the bounded service list. At most 256 service records from one result are retained.

### HTTP metadata

Stored state permits only:

- scheme
- port
- status code
- reason
- already-filtered metadata headers
- bounded error text returned by the adapter

Unknown fields such as cookies or authorization material are discarded.

## State validation

On load, ShadowForge validates:

- exact JSON schema
- state format version
- safe session ID
- non-empty target and objective
- optional bounded summary
- maximum of 100 observations
- contiguous observation numbering starting at 1
- observation target equals session target
- status is `ok` or `error`
- tool is currently permitted for persistent state
- result data is sanitized again before model use

Edited or incompatible state is rejected rather than trusted.

## Atomic writes

Session state is written to a temporary file and moved into place with an atomic replace operation. This prevents normal process interruption from leaving a partially written JSON document.

Phase 4 does not yet provide cross-process file locking. Do not run multiple writers against the same session ID concurrently.

## Dry-run behavior

A dry-run may read an existing session to inform the first proposed decision, but it does not create or modify a session-state file and performs no active network action.

## Evidence versus state

`artifacts/evidence.jsonl` remains the tamper-evident execution record. Session state is a resumable working-memory artifact and is not a replacement for evidence.

The two stores serve different purposes:

```text
evidence.jsonl     -> append-only, hash-chained execution history
state/<id>.json    -> validated resumable planner context
```

## Safety boundary

Phase 4 does not add exploit execution, credential attacks, secret retrieval, persistence installation, defense evasion, arbitrary remote commands, generic shell/PowerShell/Python execution, model-selected targets, Nmap NSE selection, unrestricted HTTP behavior, automatic propagation, or unbounded autonomous loops.
