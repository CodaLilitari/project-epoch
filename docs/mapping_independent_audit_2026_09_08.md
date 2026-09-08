# Project Epoch independent mapping audit, 2026-09-08

Evidence level: `verified-static` and deterministic host verification.

Baseline reviewed: Git `cd0c9bc` (`Close expanded package command 1E exclusion
policy`). This audit opened no emulator and produced no ROM, patch, SRAM,
state, trace, extracted asset, production allocation, or hook.

## Result

The corrected character map and the latest battle-package topology, command
grammar, bank adapter, and expanded-command policy are consistent within
their stated static scope. The canonical graphics, assembly, and primary
animation window hashes were independently recomputed for all seven PCs:
all 21 windows match the machine-readable map's exact start, end, size, and
SHA-256. This does not verify every address or semantic assertion in the
entire project, nor does it promote any supported-slot result to PC `$07`.

One reproducible native-register boundary defect escaped the existing tests.
It was repaired in the source-only package adapter. Two ambiguous working
instructions were also clarified during this review. Neither required a ROM
mapping change.

## Findings and corrections

### Native X was outside its declared 16-bit domain at an exact bank end

Before the correction, `simulate_descriptor_install` returned
`pointer_cursor_final = 65536` and `x_final = 65536` for a valid synthetic
descriptor occupying `[$FFFA,$10000)`, with mask 0 selecting one direct
entrypoint and mask 1 empty. The expanded-command policy also accepted this
fixture. A physical half-open extent of `$10000` is legitimate; a native
16-bit X value of `$10000` is impossible.

The canonical resolver's pinned machine span and byte-matched disassembly
show four 16-bit `INY` operations followed by `TYX` at `$C1:463B-$C1:463F`,
then two `INX` operations per consumed pointer at `$C1:4666-$C1:4667`.
`x_final` now records the physical cursor modulo `$10000` while
`pointer_cursor_final` continues to identify the exact consumed physical
extent. This preserves exact-bank-end descriptors and rejects any physical
extent beyond the bank.

The final flags are deliberately unchanged: the final 8-bit `LDA $A0B3`
loads zero and sets `N=0/Z=1`; the final `CPY #$0010` sets `C=1`. These are
independent of the wrapped X register. New tests cover the preceding `$FFFF`
cursor, exact-end primary and alternate masks, an empty exact-end header,
and a pointer list extending one byte beyond the bank.

### The map rendering mixed inclusive and exclusive endpoint conventions

The original prose said that every range was half-open, but the compact
subsystem and record-byte ranges use inclusive endpoints: `$0200-$042F`
contains the seven `$50`-byte saved records. The JSON correctly ends this
range at exclusive `$0430`, and the detailed window tables explicitly label
their exclusive endpoints. The prose now distinguishes these conventions;
the canonical JSON and ROM windows were already correct.

### Growth/progression and base/live record stat order must stay separate

The corrected map already distinguishes these schemas:

- Growth/progression: Power, Stamina, Speed, Hit, Evade, Magic, Magic Defense.
- Base/live record fields: Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense.

The previous broad AGENTS wording about "Schala's stat arrays" could be read
as applying the growth order to both schemas. It now explicitly preserves
the difference. The old disassembly label is misleading for the growth
table, but Magic-before-Hit is correct for the base/live record fields.

## Verification

Canonical ROM identity was checked in memory before canonical reads:

- Size: 4,194,304 bytes, headerless US Rev0.
- SHA-256: `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
- SHA-1 pin used by the canonical adapter reader:
  `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`.

The four existing battle topology/grammar/adapter/policy suites passed 79
tests before the correction. The corrected-map, PC initialization, and PC7
battle-progression suites passed another 29 tests, for 108 initial tests
with no failures or skips. The native-X counterexample was found after these
passes; therefore these passes alone did not establish complete boundary
coverage. After the correction, all 27 package-adapter tests passed,
including the new boundary cases and canonical-ROM checks.

All 21 canonical window hashes were also checked directly, independently of
the metadata-only corrected-map test: read the pinned ROM in memory, convert
each `snes-rom-bus` start/end from the three window arrays to headerless
HiROM file offsets, slice the half-open extent, and compare its size and
SHA-256 to the JSON. The tested arrays were `pc_graphics_windows`,
`pc_assembly_windows`, and `pc_animation_windows`, with seven entries each.

Reproduce the focused tests from the repository root:

```powershell
python -B -m unittest tests.test_battle_command_grammar_census_v0 tests.test_battle_action_package_topology_v0 tests.test_schala_player_tech_package_bank_adapter_v0 tests.test_schala_expanded_package_command_policy_v0 -q
python -B -m unittest tests.test_project_epoch_corrected_data_map tests.test_pc_init_record_schema_audit tests.test_pc7_battle_progression_boundaries -q
```

For the canonical tests, provide the existing ignored input at the exact
path resolved by the tests; an unavailable input causes explicit skips and
must not be represented as a current canonical verification. `-B` suppresses
bytecode-cache writes. The tests do not launch an emulator or mutate ROMs.

Corrected adapter source identity:

- Path: `tools/audit_schala_player_tech_package_bank_adapter_v0.py`.
- Size: 35,887 bytes.
- SHA-256: `3ea222fdcc45028a174989769fa726a04a09506b5b65d071bceed855d60774f3`.

The unchanged canonical adapter reference remains 12,280 bytes, SHA-256
`dab2834afb28ea2b89e814747d4a079fef7a403ec67eba592a7f866c88faa69e`.
Dependent source pins and proof identities must be refreshed against the
corrected source before a new symbolic proof is accepted; updating a pin
without reproducing the affected proof is not verification.

## Bounded next gate

`BA-SYMBOLIC-HIGH-PACKAGE` can proceed as a source-only host proof after
dependent pins pass. It should reconstruct canonical PC action-config row
`$01` only from the pinned clean ROM, replace only byte `+0` with selector
`$80`, and prove byte-for-byte equality for `+1..+6`. The donor's provenance
does not assign Schala visual meaning to its auxiliary values.

Use exact named synthetic descriptor and original stream spans, exercise
both descriptor masks and every selected suffix entrypoint, and pass the
existing decoded-`$1E` exclusion validator. An intentionally minimal
terminal-only stream can prove transport and namespace plumbing; it cannot
prove an animation. Preserve canonical `$00-$7F` resolution and fail closed
for absent high bindings and unsupported selector domains. Publish metadata,
hashes, source, and tests only.

The gate must retain the independent auxiliary-reader, location-event
context/lifetime, live-record relocation, save lifecycle/timing, production
hook/allocation, and PC `$07` runtime boundaries. No runtime success or
complete eighth playable character follows from a symbolic package proof.

## Independent review of the resumed symbolic package

The subsequent `BA-SYMBOLIC-HIGH-PACKAGE` implementation was reviewed after
its source, reference, and tests were declared stable. The review found no
additional defect in canonical donor provenance, config preservation, or
default/explicit selector separation. All 24 focused symbolic-package tests
passed locally, including the canonical-ROM cases, and the metadata-only
report was independently reproduced.

The input path first validates the complete immutable ROM identity, then
reads physical action-config row `$01` at file `$0D45AD`. The complete donor,
its preserved six-byte suffix, and the adapted candidate have separate
SHA-256 pins. Candidate byte `+0` changes to `$80`; each of `+1..+6` remains
exactly equal. Independent one-byte mutations at every candidate offset
`+0..+6` were refused. The shared auxiliary bytes are preserved donor data,
not newly expanded auxiliary readers or a Schala effect assignment.

The report constructs canonical sources through the existing pinned-ROM
builder. Their canonical identity ledger still matches the adapter's closed
128-selector contract. Independent checks observed:

- all 128 canonical selectors resolve identically with or without the local
  synthetic `$80` binding;
- all 16 high selectors refuse when no explicit binding is supplied;
- the local `$80` binding leaves the other 15 high selectors unbound;
- all 112 undeclared selectors `$90-$FF` remain refused;
- command `$1E` remains refused for expanded packages.

The symbolic package uses one terminal-only original stream and repeated
direct pointers selected by the two descriptor masks. Its significance is
source transport, exact ownership, and closure. It provides no animation,
gameplay, production selector registration, or PC `$07` runtime evidence.

Reviewed artifact identities:

- Symbolic auditor: 20,486 bytes, SHA-256
  `e6911a979a60cb06ee78b4b58a410875a2b7acbeb2fce4733bf2795828ad2b5d`.
- Symbolic reference: 8,164 bytes, SHA-256
  `37c13271c3632bca6b27a2daa0e5e2820d502a6673b1863b64b29a647df470e2`.
- Report canonical JSON SHA-256, excluding its artifact-identity field:
  `dcae013742fea5d0b70acffe80a7d8a174e23d72504d7dba28899382e17a8965`.

Reproduce this gate and its focused suite:

```powershell
python -B tools/audit_schala_symbolic_high_package_v0.py --rom <pinned-private-US-Rev0-ROM> --compact
python -B -m unittest tests.test_schala_symbolic_high_package_v0 -q
```

The gate passes at the source-only static evidence level. Later game-facing
work still requires the independent runtime and allocation gates above.
