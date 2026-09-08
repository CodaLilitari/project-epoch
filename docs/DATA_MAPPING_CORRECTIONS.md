# Project Epoch data-mapping correction register

This register identifies exact claims that were wrong, ambiguous, or
superseded, then links the evidence supporting the replacement. A correction
can concern our own model or documentation; it need not accuse an external
author or change a ROM address. Dated reports remain unchanged as history.
The [current character map](project_epoch_corrected_character_data_map_v1.md)
and its [machine-readable ledger](../references/project_epoch_corrected_character_data_map_v1.json)
remain the consolidated map. The [developer log](DEVELOPER_LOG.md) records the
work chronology.

## Maintenance and evidence rules

Assign stable `MAP-NNN` IDs. Each entry must state the date recorded, affected
namespace, old claim and exact revision, corrected conclusion, supporting
reader or counterexample, evidence level, and practical consequence. Pin
external sources to commits or exact dated posts where possible. An old
claim can have been accurate for its historical source and become stale
after an upstream change; label that as superseded, not retrospectively false.

Canonical-ROM conclusions below use headerless Chrono Trigger US Rev0,
4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The independently byte-matched disassembly pin is
`dscotton/ct_disassembly@eeae27acdb6565e96d1d796a3d60792c250c0aa1`.
Addresses and hashes can be published; raw ROM or extracted bytes remain
private. A CPU test of an original synthetic helper is not a Chrono Trigger
runtime trace.

| ID | Recorded | Classification | Affected namespace |
| --- | --- | --- | --- |
| MAP-001 | 2026-09-08 | Reproducible Project Epoch model defect, corrected | Physical descriptor extent versus native 16-bit CPU X |
| MAP-002 | 2026-09-08 | Project Epoch presentation error, corrected | Inclusive document endpoints versus half-open JSON extents |
| MAP-003 | 2026-09-08 | External growth annotation contradicted; project wording qualified | Growth/progression arrays versus base/live record fields |
| MAP-004 | 2026-09-08 | Historical upstream concern superseded by later implementation | Owner-mask positions versus counts and pointer alias identity |
| MAP-005 | 2026-09-08 | External active-runner annotation contradicted | Descriptor owner transport versus active-script dispatch |
| MAP-006 | 2026-09-08 | Project architecture instruction narrowed | Cross-bank calls versus tail transfers retaining a near-call frame |
| MAP-007 | 2026-09-08 | External cancellation/refund annotation contradicted | Shared queued-Tech success/failure finalization |
| MAP-008 | 2026-09-08 | External instruction-width decode contradicted | IRQ-path 16-bit immediate operands versus apparent WRAM writes |

## MAP-001 — exact bank end is not an out-of-range CPU register

**Old source:** Project Epoch's
[`simulate_descriptor_install` at baseline `cd0c9bc`, line 720](https://github.com/andreipemberton/project-epoch/blob/cd0c9bc1204705e63685a22aecd168fd10021979/tools/audit_schala_player_tech_package_bank_adapter_v0.py#L720)
assigned `x_final=pointer_cursor_final`. This was our implementation defect,
not an erroneous external table address.

**Counterexample:** an original descriptor occupies `[$FFFA,$10000)`, mask 0
contains one selected owner, and mask 1 is empty. After consuming the one
pointer, the exact physical cursor is 65,536. The previous host model returned
65,536 for both that extent and X. A physical half-open endpoint can equal
the bank size; a 16-bit X register cannot.

**Corrected result:** retain `pointer_cursor_final = $10000` as the consumed
physical extent and set `x_final = pointer_cursor_final & $FFFF`, yielding
`$0000`. Reject extents beyond the bank. Do not change final N/Z/C to describe
the wrapped index: the resolver's final 8-bit load of the cleared `$A0B3`
establishes N=0/Z=1 and the final `CPY #$0010` establishes C=1.

**Evidence and provenance:** the pinned canonical resolver contains 16-bit
`INY`/`TYX` at `$C1:463B-$C1:463F` and two `INX` instructions for each consumed
pointer at `$C1:4666-$C1:4667`. The source and preimage contracts are retained
in the [bank adapter reference](../references/schala_player_tech_package_bank_adapter_v0.json).
The [independent mapping audit](mapping_independent_audit_2026_09_08.md#native-x-was-outside-its-declared-16-bit-domain-at-an-exact-bank-end)
records the failing fixture and corrected-source SHA-256
`3ea222fdcc45028a174989769fa726a04a09506b5b65d071bceed855d60774f3`.
The [adapter tests](../tests/test_schala_player_tech_package_bank_adapter_v0.py)
cover preceding `$FFFF`, primary and alternate exact ends, an empty end-bank
header, and a one-byte overflow. The later
[native helper matrix](schala_package_helper_conformance_v0.md) executes the
same boundary in the original synthetic helper.

**Evidence level:** canonical instruction semantics and host correction are
`verified-static`; execution of the original helper's corresponding cases is
`verified-runtime`, synthetic scope only. No new canonical ROM location,
free-space region, game hook, or live integration is established.

## MAP-002 — compact range endpoints were mislabeled

**Old source:** the
[character map at baseline `cd0c9bc`, line 41](https://github.com/andreipemberton/project-epoch/blob/cd0c9bc1204705e63685a22aecd168fd10021979/docs/project_epoch_corrected_character_data_map_v1.md#L41)
claimed every range was half-open. Its compact subsystem and record-byte
tables actually use inclusive endpoints, while explicitly labeled detailed
window tables use exclusive ends.

**Corrected result:** the compact saved-PC span `$0200-$042F` includes both
endpoints and contains `$230` bytes, exactly seven `$50` records. Its JSON
representation ends at exclusive `$0430`. The JSON and the canonical windows
were already correct; the Markdown's blanket rule was wrong.

**Evidence and provenance:** the
[current range convention](project_epoch_corrected_character_data_map_v1.md#evidence-and-ownership-rules)
now distinguishes those two notations. The
[machine-readable map](../references/project_epoch_corrected_character_data_map_v1.json)
provides `start`, `end_exclusive`, and `size`. The
[September 8 audit](mapping_independent_audit_2026_09_08.md#the-map-rendering-mixed-inclusive-and-exclusive-endpoint-conventions)
independently re-read all 21 canonical graphics, assembly, and primary-animation
windows and matched their bounds and hashes. The
[map tests](../tests/test_project_epoch_corrected_data_map.py) validate its
metadata and document coverage.

**Evidence level:** `verified-static`. This correction changes presentation,
not any boundary address or storage-ownership conclusion. Never use an
ambiguous compact range to infer an extra byte of free storage.

## MAP-003 — growth order and record order are different schemas

**Wrong external annotation:**
[`data/stat_growth.asm`, line 2, at the pinned disassembly revision](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/data/stat_growth.asm#L2)
labels the growth-table fields as `pow, sta, spd, mag, hit, eva, mdef`.
That annotation does not match the consumers of the `$CC:25FA` growth rows.

**Project wording that also needed correction:**
[AGENTS at `cd0c9bc`, line 165](https://github.com/andreipemberton/project-epoch/blob/cd0c9bc1204705e63685a22aecd168fd10021979/AGENTS.md#L165)
said broadly that Schala's stat arrays must use the growth order. Without
distinguishing the structures, that instruction could incorrectly reorder
base/live record fields that were already mapped correctly.

Our earlier
[community reconnaissance at `cd0c9bc`, line 69](https://github.com/andreipemberton/project-epoch/blob/cd0c9bc1204705e63685a22aecd168fd10021979/docs/community_modding_reconnaissance_2026-07-27.md#L69)
also described the Data Crystal SRAM map's Magic-before-Hit order as
misleading. That criticism was too broad: Magic-before-Hit is correct for
the base/live record structure. The old report remains historical; its
stat-order criticism must be read with this correction. This does not
retract the independent objection to interpreting `$0430` as an eighth PC.

**Corrected schemas:**

| Structure | Index order | Address or record offsets |
| --- | --- | --- |
| Growth/progression row | Power, Stamina, Speed, Hit, Evade, Magic, Magic Defense | Seven-byte rows at `$CC:25FA` |
| Level-1 recomputation baselines | Power, Stamina, unused Speed, Hit, Evade, Magic, Magic Defense | Record `+$2F-$35` |
| Base stats | Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense | Record `+$0B-$11` |
| Equipment-adjusted live stats | Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense | Record `+$36-$3C` |

**Evidence and provenance:** the canonical `Battle_LevelUp_RecomputeStats`
reader at `$C1:F630` maps growth indices 3, 4, and 5 to record `+$0F` (Hit),
`+$10` (Evade), and `+$0E` (Magic), respectively. Index 2's Speed recomputation
is skipped. The exact mapping is tabulated in the
[PC initialization audit](pc_init_record_schema_audit.md#stat-baseline-and-growth-semantics)
and enforced by the
[hash-gated auditor](../tools/audit_pc_init_record_schema.py) and its
[tests](../tests/test_pc_init_record_schema_audit.py).
The pinned growth-table SHA-256 is
`899a8c7c2858b9e0190a37c5866fdb073c6167f2ab32be509cde49777fe8e94d`;
the disassembly annotation file's pinned SHA-256 is
`64e5973ed6eb02bf9bc7d0213a54f5f01caee850429279c8672cc2fc7da03fa9`.
These pins identify the data and erroneous annotation; the reader establishes
which stat each position actually affects.

**Evidence level:** the register/record mapping above is `verified-static`
from the canonical instruction and source contract. Earlier project documents
call the growth order runtime-confirmed; this entry does not claim a newly
performed runtime replay. The [September 8 audit](mapping_independent_audit_2026_09_08.md#growthprogression-and-baselive-record-stat-order-must-stay-separate)
reconfirmed the schema distinction and corrected the current instruction.

**Consequence:** serializers must name each schema explicitly. Reusing one
order for both silently swaps Magic, Hit, and Evade. The correction supplies
no missing PC `$07` record, growth family, or production allocation.

## MAP-004 — ctrando's sparse-position concern is historical

**Earlier source statement:** our
[August survey as preserved at `cd0c9bc`, lines 99-101](https://github.com/andreipemberton/project-epoch/blob/cd0c9bc1204705e63685a22aecd168fd10021979/docs/eighth_playable_character_external_research_2026-08-22.md#L99-L101)
reported that the reader reduced exact descriptor masks to role counts and
could lose sparse owner positions while emitting fresh pointers. Its upstream
comparison was explicitly pinned to
[`Pseudoarc/ctrando@20609d50932a84be58f6281d23b3f4e4d4c4e167`](https://github.com/Pseudoarc/ctrando/commit/20609d50932a84be58f6281d23b3f4e4d4c4e167).

**New evidence:** upstream
[`c7c57a33d6a552560a5afc4309754b6b723e6e3b`, August 26](https://github.com/Pseudoarc/ctrando/commit/c7c57a33d6a552560a5afc4309754b6b723e6e3b)
retains absent positions as `None`, reads the main/miss mask bits separately,
and reconstructs masks from those positions. The subsequent
[`590befca24206ab9aa1b33537223b7a1f90a3624`, August 30](https://github.com/Pseudoarc/ctrando/commit/590befca24206ab9aa1b33537223b7a1f90a3624)
fixes authoring operations to assign fixed positions and preserve the intended
script class. These August changes were inspected in the September 8 refresh;
their discovery date must not be substituted for their commit dates.

**Corrected conclusion:** the sparse-position objection no longer describes
the inspected newer implementation. This is an upstream improvement that
supersedes part of our historical assessment, not evidence that the historical
assessment was false at its pinned revision. The separate question of exact
pointer-alias and shared-suffix preservation remains unproved by this review.
Do not merge those two questions into a single verdict about upstream quality.

**Evidence and provenance:** the
[dated source refresh](online_research_2026_09_08.md#ctrando-active-through-september-7-plus-a-corrected-historical-caveat)
records the exact comparison and current inspected head
`d6a28183183ae18fbf62a357c09f3dffc227710e`. No upstream allocator choice, game
script, machine-code payload, or hook was imported. The
[bank-adapter provenance section](schala_player_tech_package_bank_adapter_v0.md#external-design-reference-and-provenance-boundary)
now states the historical qualification.

**Evidence level:** `documented`, commit-pinned source inspection. This entry
reports the completed September 8 inspection and does not claim a fresh
upstream runtime test. Project Epoch retains exact masks, bank-qualified
entrypoints, alias and token ownership, and independent integration gates.

## MAP-005 — active-script checks are not an eight-slot loop

**Wrong source:**
[`dscotton/ct_disassembly` at `eeae27ac`, `bank_C1.asm:9811`](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L9811)
describes the active-script runner as running "for 8 slots".

**Corrected result:** canonical `$C1:4BBE-$C1:4C9E` contains thirteen possible
owner checks, `$00-$04` and `$08-$0F`, with conditional gates. This is not a
guarantee that thirteen scripts execute. Owners `$05-$07` have no direct
dispatch in this routine; that does not make them globally unused. The
sixteen-bit descriptor transport remains a different namespace and is still
correctly tested across all sixteen bits.

**Evidence and provenance:** independently checked every canonical
`LDA $5DAC+owner` and corresponding `LDY #owner` against the pinned US Rev0
ROM. The 224-byte half-open span has SHA-256
`d65a749d8401c79fae00a9ba24b85ea0b1e83246a06448735339834e0747945e`.
The [integration design](schala_package_resolver_integration_design_v0.md#mapping-correction-with-cited-wrong-source)
records the exact gates and byte-matched upstream-file identity.

**Evidence level:** `verified-static`. Do not translate descriptor capacity
into claims about the active consumer, player capacity, or free owner slots.

## MAP-006 — a cross-bank tail transfer must preserve its existing call frame

**Overbroad project instruction:**
[`schala_rom_expansion_architecture.md:272` at `a01ab3a`](https://github.com/andreipemberton/project-epoch/blob/a01ab3af3ab2c1c1d22c24828ac0ad51ed5d0c84/docs/schala_rom_expansion_architecture.md#L272)
said to use `JSL/RTL` for cross-bank runtime helpers without distinguishing
new calls from intercepted tail transfers.

**Corrected rule:** `JSL/RTL` is appropriate for a deliberately matched long
call and return. The package resolver already has a near `JSR` return frame.
Its proposed interception uses `JML` into the helper and `JML` back to a
bank-correct continuation, retaining that original frame. Do not execute
`RTL` against a two-byte near-return address or `RTS` from the expanded bank
without a separately proved trampoline.

**Evidence and provenance:** the [integration design](schala_package_resolver_integration_design_v0.md)
pins the dispatcher, exact four-byte hook candidate, common loader, and
ordinary caller. The [placement review](schala_package_placement_interrupt_review_v0.md)
records the historical instruction and its correction. The new
[clean-ROM observation](schala_package_resolver_observation_v0.md) reproduces
return words `$432A/$40AF` and SP transitions `$06D8/$06DA/$06DC` in a real
ordinary PC invocation. The original synthetic helper separately preserves
its call frame at both tested code origins.

**Evidence level:** `verified-static` call semantics, supplemented by
`verified-runtime` for the bounded canonical return chain. This does not
select a rejection trampoline or authorize a production hook.

## MAP-007 — queued-Tech finalization is shared by success and failure

**Wrong source:**
[`dscotton/ct_disassembly` at `eeae27ac`, `bank_C1.asm:23863`](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L23863)
describes `$C1:BDB3` as failed/cancelled-action handling and characterizes its
timing work as a partial gauge refund.

**Corrected result:** `$C1:BDB3` is shared queued-Tech participant and timing
finalization. The successful path's four-byte `JSL` at `$C1:BC56` returns
directly to `$C1:BC5A`, which calls `$C1:BDB3`. Earlier validation failures
also reach that tail. Reaching the routine therefore does not demonstrate
cancellation or a refund of previously charged MP.

**Evidence and provenance:** canonical half-open `$C1:BC4A-$C1:BC60` is
22 bytes with SHA-256
`2258622ba95551f41347b852f03148795064fb55c5932ae7b92b40f3fa6e4f70`.
The complete named finalizer span `$C1:BDB3-$C1:BF46` is 403 bytes with
SHA-256 `b3281d8212fb9d53d70068adff23d3281d86defa936fc07174fb07c79f4c15bc`.
The [cancellation contract](schala_package_cancellation_contract_v1.md)
and [read-only verifier](../tools/audit_package_cancellation_boundaries_v1.py)
also prove that the queued-Tech path charges participant MP before animation
and applies pending results after normal animation return. Their
[metadata reference](../references/package_cancellation_boundaries_v1.json)
binds 19 spans and 32 selected instruction assertions to the exact canonical
US Rev0 ROM and pinned annotation source.

**Evidence level:** `verified-static`. A late resolver refusal is not semantic
action cancellation. An earlier preflight before effect preparation is a
candidate design; its participant, queue, finalizer, and late-failure policy
still require separate proof.

## MAP-008 — two IRQ-path operands were mistaken for `$AAEB` writes

**Wrong source:**
[`dscotton/ct_disassembly` at `eeae27ac`, `bank_FD.asm:6032`](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_FD.asm#L6032)
and [line 6050](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_FD.asm#L6050)
decode `$FD:E21B` and `$FD:E247` as eight-bit `AND #$00`, each followed by
`ASL $AAEB`.

**Corrected result:** the audited IRQ path executes `REP #$21` at `$FD:E160`
and retains M=0 at both sites. Each sequence is a 16-bit `AND #$0E00`, then
`XBA`, then `TAX`. The apparent `ASL` opcode is an immediate operand byte.
Neither sequence writes to `$AAEB`; this does not establish any other meaning
or ownership for that address.

**Evidence and provenance:** the two half-open spans `$FD:E21B-$FD:E220`
and `$FD:E247-$FD:E24C` each have five bytes and SHA-256
`ea507cc8d6ab6f2681420c5099a90369d6f0ef195c8e1b6a82b3075464391a4a`.
The [interrupt closure report](schala_package_interrupt_closure_v1.md)
cites the unchanged upstream file and the width-setting path. Its
[fail-closed auditor](../tools/audit_schala_package_interrupt_closure_v1.py)
tracks width and typed call/status frames through 401 instruction starts
(404 width contexts), reaches all six corrected instruction boundaries,
and rejects unsupported paths. The
[metadata reference](../references/schala_package_interrupt_closure_v1.json)
binds the exact corpus, source, and results.

**Evidence level:** `verified-static` within the bounded, non-nested IRQ CPU
closure. Data-dependent DMA sources, the complete NMI tree, interrupt nesting,
and global stack headroom remain separate obligations.
