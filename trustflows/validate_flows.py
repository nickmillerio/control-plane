#!/usr/bin/env python3
"""
validate_flows.py — Offline schema validator for Langroot TrustFlow definitions.

Usage:
    python control-plane/trustflows/validate_flows.py

Exits with code 0 if all definitions are valid, non-zero otherwise.
Suitable for use in CI.
"""

import json
import sys
from pathlib import Path

DEFINITIONS_DIR = Path(__file__).parent / "definitions"

REQUIRED_TOP_LEVEL_KEYS = {"flow_id", "version", "description", "states", "transitions"}
REQUIRED_STATE_KEYS = {"state_id", "trust_floor", "ttl_seconds", "capabilities",
                       "requires_cba_binding", "is_terminal", "is_suspended"}
REQUIRED_TRANSITION_KEYS = {"from_state", "to_state", "trigger", "gates", "side_effects"}


def validate_file(path: Path) -> list[str]:
    """Return a list of error strings for the given definition file."""
    errors: list[str] = []

    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    # Top-level keys
    missing_top = REQUIRED_TOP_LEVEL_KEYS - data.keys()
    if missing_top:
        errors.append(f"Missing top-level keys: {sorted(missing_top)}")

    # States
    states = data.get("states", [])
    if not isinstance(states, list) or len(states) == 0:
        errors.append("'states' must be a non-empty list")
    declared_state_ids: set[str] = set()
    for i, state in enumerate(states):
        if not isinstance(state, dict):
            errors.append(f"states[{i}] is not an object")
            continue
        missing_state = REQUIRED_STATE_KEYS - state.keys()
        if missing_state:
            errors.append(f"states[{i}] missing keys: {sorted(missing_state)}")
        sid = state.get("state_id")
        if sid:
            if sid in declared_state_ids:
                errors.append(f"Duplicate state_id: '{sid}'")
            declared_state_ids.add(sid)

    # Transitions
    transitions = data.get("transitions", [])
    if not isinstance(transitions, list):
        errors.append("'transitions' must be a list")
    for i, tx in enumerate(transitions):
        if not isinstance(tx, dict):
            errors.append(f"transitions[{i}] is not an object")
            continue
        missing_tx = REQUIRED_TRANSITION_KEYS - tx.keys()
        if missing_tx:
            errors.append(f"transitions[{i}] missing keys: {sorted(missing_tx)}")

        from_state = tx.get("from_state")
        to_state = tx.get("to_state")
        if from_state and from_state not in declared_state_ids:
            errors.append(
                f"transitions[{i}] references unknown from_state: '{from_state}'"
            )
        if to_state and to_state not in declared_state_ids:
            errors.append(
                f"transitions[{i}] references unknown to_state: '{to_state}'"
            )

    return errors


def main() -> int:
    if not DEFINITIONS_DIR.exists():
        print(f"ERROR: definitions directory not found: {DEFINITIONS_DIR}", file=sys.stderr)
        return 1

    definition_files = sorted(DEFINITIONS_DIR.glob("*.json"))
    if not definition_files:
        print(f"WARNING: No JSON files found in {DEFINITIONS_DIR}")
        return 0

    total_errors = 0
    for path in definition_files:
        errors = validate_file(path)
        if errors:
            print(f"FAIL  {path.name}")
            for err in errors:
                print(f"      - {err}")
            total_errors += len(errors)
        else:
            print(f"OK    {path.name}")

    print()
    if total_errors:
        print(f"Validation failed: {total_errors} error(s) in {len(definition_files)} file(s).")
        return 1
    print(f"All {len(definition_files)} definition(s) passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
