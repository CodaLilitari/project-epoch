# Schala recruitment content foundation v0

Status: authoring-only, unmapped  
Evidence level: `hypothesis`  
Target identity: logical playable PC `$07`  
Runtime status: not encoded and not runtime-verified

## Scope

This foundation turns the "Silent Palace" direction in
`docs/schala_character_design_v0.md` into an original, machine-readable
narrative state machine. It contains no Chrono Trigger dialogue, event bytes,
map data, graphics, guessed opcodes, guessed addresses, or claimed free space.
No ROM was read or edited to create it.

The graph gives Schala agency over recruitment and treats Magus as an optional
dialogue participant rather than a gate. It specifies these bounded paths:

| Condition | Authoring outcome |
|---|---|
| Magus present | Two original dialogue lines lead to the same choice |
| Magus absent | An alternate original Schala line leads to the same choice |
| Decline | No joined-state or one-time-grant mutation |
| Accept with an open slot | Register logical PC `$07` and request active-party insertion |
| Accept with a full party | Register logical PC `$07` in reserve and request party exchange |
| Already recruited | Return without roster insertion or duplicate grants |
| New Game+ with retained state | The already-recruited guard wins before every other branch |
| New Game+ with reset state | The normal path may recruit once behind the same grant guard |

The one-time authoring grant names three starting techs (Astral Pin, Veil, and
Crescent Wake) and the original Glass Focus and Regent Mantle. These are
content references only; no action or item record is installed.

## Machine-readable source

`assets/source/schala/v0/content/schala_recruitment_content_v0.json`

- 28 graph nodes: 7 branches, 11 original dialogue nodes, 1 choice, 4 symbolic
  actions, and 5 terminal outcomes.
- 7 acceptance scenarios covering the required branch matrix.
- 29 explicit runtime/event-engine dependencies.
- Every state variable, graph node, and engine dependency is
  `unmapped` with a null binding.
- Canonical normalized SHA-256:
  `fbffbc7bd9bed555ed7966ed62f6b9b247b4403986fef358711e9e00e13520eb`
- Source-file SHA-256:
  `00c750b2f9be163c75d75af947d1ea2a2ee39d16adfc0640e9292ad487b66412`

## Validator and focused tests

`tools/validate_schala_recruitment_content.py` validates the exact schema,
logical PC identity, original-content provenance, null binding inventory,
graph references and reachability, guarded one-time grant, symbolic effect
allowlist, and all seven acceptance scenarios by executing the authoring graph.
It rejects any supplied address, opcode, table, encoded value, or node binding.

Validator SHA-256:
`455e430158a21c8059baaa2b8b6ec8ef2055b56b11ba1358f2744e3bb15ae034`

`tests/test_validate_schala_recruitment_content.py` adds 11 focused tests,
including negative tests for identity drift, copied/imported provenance,
runtime bindings, dangling branches, an unguarded duplicate grant, an
incomplete full-party path, and a missing New Game+ idempotence case.

Focused-test SHA-256:
`fb53525f86ed92c05d44a84d948b40e4c2c29d2312e23c849782bd5bdaa8c460`

Reproduce from the project root:

```powershell
python tools/validate_schala_recruitment_content.py
python -m unittest -v tests.test_validate_schala_recruitment_content
```

Observed result: 11 focused tests passed.

## Implementation gates

This specification does not prove or authorize a ROM implementation. Before
encoding it, trace and approve at least:

1. Event entry, flag/counter storage, text encoding, choices, and script space.
2. Logical PC `$07` roster, active-party, reserve, and party-exchange paths.
3. Runtime-record initialization and the original field, battle, and portrait
   graphics routes.
4. Starting-tech and original-item grant paths with a persistent one-time
   guard.
5. Save/load, erase, reset, and New Game+ transfer semantics for both
   recruitment flags.
6. The Silent Palace map/object route, guest Veil demonstration, music, and
   sound-effect restoration.

The graph's symbolic `commit_recruitment` node precedes its capacity branch.
That is narrative scenario ordering, not an interruption-safe write contract,
and must not be compiled literally. The separate host-tested,
runtime-unverified ordering contract in
`docs/schala_recruitment_transaction_contract.md` stages reserve state
reversibly, requires a caller-supplied complete-grant witness before live
commit, and defers exact-slot checksum binding to a later save boundary. The
witness is a host assertion; runtime grant observation remains required.

Until those gates have runtime evidence, all graph operations are semantic
requests rather than event-engine instructions.
