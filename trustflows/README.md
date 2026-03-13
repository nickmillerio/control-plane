# TrustFlows — Control Plane Surface

This directory is the **Langroot-specific TrustFlow control-plane surface**. It
contains canonical, versioned definitions of trust state machines that run
inside the AXIOM TrustFlowEngine, as well as the glue-tooling that validates
and loads them.

---

## Directory Layout

```
trustflows/
├── README.md                  ← you are here
├── validate_flows.py          ← offline schema validator (Python 3.9+)
├── .gitkeep                   ← preserves directory in git
└── definitions/               ← canonical JSON definitions (source-of-truth)
    ├── publisher_onboarding_v1.json
    ├── creator_patch_v1.json
    ├── indexer_crawl_v1.json
    └── federation_handshake_v1.json
```

`definitions/` is the **only** location that AXIOM TrustFlowEngine reads at
boot-time when this control-plane is mounted. Every file in that directory is
treated as a TrustFlow definition.

---

## Versioning Policy

| Rule | Detail |
|------|--------|
| **Immutable once published** | A definition file that has been referenced by a live AXIOM node must never be edited in place. |
| **New version = new file** | Increment the suffix: `publisher_onboarding_v2.json`, etc. |
| **Old versions kept** | Do not delete old definition files; they may still be referenced by in-flight sessions. |
| **Deprecation** | Add `"deprecated": true` and `"superseded_by": "publisher_onboarding_v2"` to the root object of the old file when a newer version exists. |

---

## Schema

Every definition file must be valid JSON and conform to the AXIOM TrustFlow
schema (see `axiom-kernel` for the canonical proto definition). The minimum
required top-level keys are:

```json
{
  "flow_id":     "<string>",
  "version":     "<semver string>",
  "description": "<string>",
  "states":      [ /* TrustState objects */ ],
  "transitions": [ /* TrustTransition objects */ ]
}
```

### TrustState object

```json
{
  "state_id":             "<string>",
  "trust_floor":          0.0,
  "ttl_seconds":          0,
  "capabilities":         [],
  "requires_cba_binding": false,
  "is_terminal":          false,
  "is_suspended":         false
}
```

### TrustTransition object

```json
{
  "from_state":   "<state_id>",
  "to_state":     "<state_id>",
  "trigger":      "<string>",
  "gates":        [ { "type": "SCORE_FLOOR", "param": "0.0" } ],
  "side_effects": [ "emit:trust_event:<event_name>" ]
}
```

---

## Validation

Run the offline validator before committing any new definition:

```bash
python control-plane/trustflows/validate_flows.py
```

The validator:
1. Loads every `*.json` file in `definitions/`.
2. Checks required top-level keys (`flow_id`, `version`, `description`, `states`, `transitions`).
3. Checks that every `from_state` / `to_state` in `transitions` references a
   declared `state_id` in `states`.
4. Exits non-zero on any failure — suitable for CI.

---

## Loading into AXIOM TrustFlowEngine

When the Langroot control-plane is mounted as an AXIOM assembly, the engine
discovers flow definitions via the `TRUSTFLOW_DEFINITIONS_PATH` environment
variable (defaults to `control-plane/trustflows/definitions`). At startup the
engine:

1. Scans the directory for `*.json` files.
2. Deserialises each file into a `TrustFlowDefinition` proto.
3. Registers the flow under its `flow_id`.
4. Rejects duplicate `flow_id` values (versioning is handled by filename suffix,
   not by the `version` field alone).

Langroot-specific flows **must not** override AXIOM built-in flow IDs. Use the
`langroot.` namespace prefix for all `flow_id` values defined here, e.g.
`langroot.publisher_onboarding`.

---

## Relationship to AXIOM

> `trustflows/` is Langroot-specific. `axiom-kernel` is platform-agnostic.

These definitions **align** to the AXIOM schema but are **not** part of the
AXIOM core distribution. They are integration glue owned by the Foundations
Control Plane team. If a pattern here proves universally useful, it should be
proposed upstream to `axiom-kernel` as a generic flow.
