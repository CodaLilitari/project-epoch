# Reused canonical action-completion witnesses v1

Date: 2026-09-08. Evidence: `verified-runtime`, explicitly reused from the two
already accepted successful queued-Tech observations. This work performed no
new emulator launch, native execution, ROM mutation, or game-state injection.
The new artifact is a metadata-only audit of evidence already retained locally.

The accepted action has a concrete completion sequence: the package counter
`$7E9876` stays zero across 516 observed waits, an actual byte write changes it
to one at the shared default-handler increment site, the caller subsequently
samples that one, and its separate scene-latch check samples `$7E5D9B=0`.
Cleanup resets both bytes before result application and the action's eventual
return to its queue caller. Two earlier stop-handler observations do not
themselves show a package-counter signal.

This narrows the next completion design. A transport-valid package is not a
lifecycle-completion approval. The current terminal-`$00` authoring policy and
the canonical default-handler completion behavior must remain separate until
an explicit protocol is designed and proved. No package policy, helper,
production selector, hook, allocation, or cleanup path changes here.

## Reproduction and evidence origin

Run from the repository root:

```powershell
python -B -m unittest discover -s tests -p test_package_completion_witness_v1.py
python -B tools/audit_package_completion_witness_v1.py
```

The auditor reads local source and previously accepted private evidence, writes
no files, and prints UTF-8 JSON with LF and one trailing newline. Its CLI
requires equality with
[`references/package_completion_witness_v1.json`](../references/package_completion_witness_v1.json).
Private inputs must be available; the program does not download, fabricate,
recreate, or relaunch missing evidence.

The unchanged
[`collect_package_transaction_evidence_v1.py`](../tools/collect_package_transaction_evidence_v1.py)
first revalidates both full successful transaction traces, their launcher and
collector sources, validation library, tests, isolation helper, exact staged
ROM/SRAM/state/runtime inputs, source archives, launch receipts, and accepted
manifests. Its result must reproduce the previously published transaction
reference, SHA-256
`1cc3030e1bbfe5f167ae69262ec7d78487ec4184e3500915b9dfbda94bea2787`.
The new audit then independently validates the bounded completion projection
from each full trace. It never accepts a caller-supplied projection as proof of
native provenance.

Both retained runs are
`private/test_runs/package_transaction_20260908_final1` and `...final2`.
Each trace contains 1,277 records in 6,113,025 bytes, SHA-256
`fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7`.
The canonical US Rev0 ROM is 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
ROM, SRAM, checkpoint, traces, and screenshots remain ignored private inputs;
the new reference contains identities, ordinals, counts, and interpretations.

The native observation begins at the previously accepted Lavos checkpoint.
That checkpoint's history includes a prepared recovered SRAM image and its
separately recorded checkpoint acquisition and normalization. The accepted
transaction observers themselves use the pinned state and fixed controller
inputs. These are distinct provenance claims. This audit does not turn that
history into an unassisted playthrough or a fresh state acquisition. The
full account remains in
[`schala_package_transaction_observation_v1.md`](schala_package_transaction_observation_v1.md).

## Exact selected sequence

All record numbers below are zero-based ordinals in the accepted JSON trace.
Poll numbers are the collector's input-poll counter; they are not the PPU's
hardware frame count. All selected records remain inside transaction ID 1,
after the resolver scope has closed, with supported actor/type/config/branch
identity `$00/$02/$08/$00`.

| Record | Poll | Observation | Bounded interpretation |
| --- | ---: | --- | --- |
| 49, 50 | 376 | Actual scene and package zero stores; callback PCs `$CCF071/$CCF0EC` | Initial reset writes, each followed by a snapshot readback |
| 73 | 388 | Actual scene zero store, callback PC `$CD0D2B` | Additional observed setup reset |
| 181 | 466 | Actual scene byte `0 → 1`, callback PC `$C15938` | Scene latch becomes busy during the same action |
| 982, 983 | 927 | Actual scene byte `1 → 0`, callback PC `$CD1650`; following snapshot is zero | Last write from the selected scene-clear site before the package signal |
| 993 | 932 | Pre-execution `$C14CF3`, `X=$0004`, `SP=$06D6` | Canonical STZ effective target calculates to `$7E5DB0`; actual owner store/readback absent |
| 1108 | 989 | Pre-execution `$C14CF3`, `X=$0003`, `SP=$06D6` | Canonical STZ effective target calculates to `$7E5DAF`; actual owner store/readback absent |
| 1113 | 991 | Pre-execution `$C14D00`, counter snapshot zero | Shared default-family INC boundary; encoded command byte not captured |
| 1114 | 991 | Actual `$7E9876=1` store, callback PC `$C14D03`, pre-memory zero | The observed counter increment |
| 1115 | 991 | Caller `$C140CE`, counter snapshot one, `SP=$06DC` | Subsequent snapshot at the canonical package-counter reader |
| 1116 | 992 | Caller `$C140E7`, scene snapshot zero | Separate scene-wait boundary sees the satisfied latch |
| 1117, 1118 | 993 | Actual scene and package cleanup resets | Scene zero is rewritten; package one is reset to zero |
| 1119, 1120 | 993 | `$C1AC5A` result wrapper and `$C1EC7F` application entry | Both latch snapshots are zero after cleanup |
| 1253 | 994 | `$C1BC21`, `SP=$06EA` | Same action returns from animation/result wrapper |
| 1275 | 994 | Actual queue-caller resumption `$C185D1`, `SP=$06EC` | Existing full transaction validator proves the dynamic RTS return and queue lifecycle |

The complete trace contains exactly the eight latch writes listed by the new
reference: ordinals 49, 50, 73, 181, 982, 1114, 1117, and 1118. Every write has
a matching immediate following record with the new value in its debugger
snapshot. The selected 1,051-record projection also reconciles both latch
bytes across every included snapshot. An earlier or later action cannot
donate a missing event, because the full trace, exact ordinal set, invocation
identity, event occurrences, and ordered latch ledger are all checked.

There are 517 observations at `$C140CE`: the first 516 sample zero and are
followed by an observed loop resumption at `$C140B0`; the last samples one.
Both stop-handler observations are followed by a still-zero package snapshot
and another loop resumption. This establishes the observed wait sequence,
without counting unobserved CPU reads or claiming the two stop instructions'
owner-byte stores were independently captured.

Record 982 is **not** the last write of zero to the scene latch in the action.
Record 1117 is a later cleanup reset at a different site, with pre-memory
already zero. Preserving that distinction prevents a cleanup write from being
misidentified as the scene operation that released the busy latch.

## CPU, stack, callback, and time boundaries

The new audit requires exact CPU key/type schemas, native mode, `M=1`, `X=0`,
`D=$0000`, `DBR=$7E`, and decimal mode clear at every selected record. Execute
observations must agree with their exact bank-qualified source site and live
PBR/PC. Actual latch callbacks must match their declared bus address, byte
value, live callback PC, stack pointer, and poll. These premises matter: a
canonical PC with the wrong data bank does not establish the claimed WRAM
operand.

All 16 sampled stack bytes are typed bytes. The package wait uses the same
near-call frame throughout. Both stop observations and the increment have
their distinct nested near frames checked; result-wrapper/application frames
and the action's outer return frame are checked separately. The unchanged
full transaction validator remains responsible for its complete action and
queue-return contract. A few selected matching stack samples are not a
general proof of every intervening stack access.

For the increment, records 1113 and 1114 preserve all CPU registers except
the expected instruction PC advance and INC's N/Z effects. The actual byte
changes zero to one, so both N and Z are clear at the callback. The interval
is exactly 40 master clocks and six CPU cycles in the retained trace. This
is the pre-instruction-to-write-callback interval, not a benchmark for the
whole interpreter, action, or completion protocol.

Each selected record has exactly the eight retained timing fields. Full
`memoryManager.masterClock`, full CPU cycles, PPU frame count, and input poll
must be monotonic. The generic 32-bit `masterClock` must equal the low 32 bits
of the full clock, so rollover is allowed explicitly. The clock rate and
bounded raster fields are checked. These are recorded Mesen observations;
this audit does not extend them into an independent physical-SNES timing
measurement.

Execute callbacks occur before the instruction; memory callbacks record the
store while the CPU PC has already advanced and the debugger snapshot still
contains the prior memory byte. The following snapshot supplies readback.
At `$C140CE/$C140E7`, the evidence is a pre-execution debugger snapshot plus
pinned canonical reader/control flow. The original observer did **not**
record independent CPU data-read callbacks for those two instructions.

The original collector restricts owner-publication callbacks to the resolver
scope. By the later stop-handler observations that scope is closed, and its
snapshot set does not contain the owner bytes. Thus `$7E5DB0/$7E5DAF` are
effective-address calculations from pre-execution X/DBR/width and canonical
STZ source, not newly observed writes or post-store owner readbacks. No
script-pointer snapshot is present either. The shared default-family
execution site identifies a handler branch, not the encoded command `$01`;
70 encoded command values share that default handler.

The trace also lacks ISR entry/exit attribution for these observations.
Callback PC `$CD1650` and the canonical scene-clear source do not independently
prove NMI ownership in this observer. That remains separate from the other
interrupt audits.

## Static interpretation and correction provenance

The new auditor re-executes and pins
[`audit_schala_package_completion_contract_v1.py`](../tools/audit_schala_package_completion_contract_v1.py),
9,676 bytes, SHA-256
`76840c5b0edfea07e117745ee0dd70da77dd489eeabb406684d48f2177121214`.
Its independently reviewed reference is 9,212 bytes, SHA-256
`76c5d5a157748717c42301a7cbfd9d00f9f656cdeba048415e77c123d7095766`.
The detailed source semantics and unchanged policy boundary are in
[`schala_package_completion_contract_v1.md`](schala_package_completion_contract_v1.md).

That static packet establishes that command `$00` clears its owner-active
byte, while the shared default handler's `A3D1=0` branch increments `$9876`.
It also corrects a narrow prior annotation: the pinned
[`bank_C1.asm` line 9969](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L9969)
calls the `A3D1`-set branch “consume+end.” Under the contract's `D=0` premise,
`TDC` supplies a zero advance; `$C175BB` clears carry and adds zero to the
pointer words. They are rewritten with their existing values, so the command
pointer does not advance and the package counter does not increment on that
branch. This is **MAP011**, a static correction; the reused runtime trace
does not contain pointer observations that could independently prove it.

The cited annotation is pinned at commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`, file SHA-256
`298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa`.
The half-open canonical default-handler span `$C14CF7..$C14D04` has SHA-256
`3ecae483e18298b9f38e37cbd69662a65e1c6ff345e6f34fc568478d3e38ae6b`;
the pointer-advance span `$C175BB..$C175CC` has SHA-256
`81ec99810c0832f34277d117410919282e14891d51bb3869533e60ae3ef97142`.
These source checks support the reviewed bounded interpretation; hashes alone
do not derive instruction semantics.

The existing cancellation auditor is reused unchanged for the scene-clear
and cleanup source spans. Its whole-ROM pin and assertions are rechecked, and
the new reference retains the `$CD1609..$CD1654` and `$CCF06B..$CCF102` span
identities. This adds no new mapping correction beyond the separately reviewed
MAP011 packet.

## Validation and handoff

The 54 new host tests use original synthetic selected-record envelopes,
including an abstract monotonic clock model. They contain no copied private
trace or game artifact and do not claim hardware reachability. They reject
missing/reordered records, foreign invocation identity, false boolean/float
equalities, wrong CPU addressing/width/PC, altered near frames, unexplained
latch changes, missing readbacks, confused cleanup resets, wrong INC flags or
timing, and full-clock reversals. A valid low-32-bit rollover is accepted.
The full-trace entry point must invoke the unchanged transaction validator
before projecting any records.

Source and tests are checked before and after collection. Both full native
traces reproduce the same bounded result; selected full-record hashes and the
projection hash make the new interpretation reproducible without publishing
their private record payloads. Root and a second independent reviewer both
read the source, ran all 54 tests, and reproduced the same 16,543-byte metadata
result. The second reviewer also read this report's evidence distinctions;
neither review requested a source change.

After both reviews, the reference was emitted once from the frozen auditor.
Two fresh actual CLI processes then reproduced it byte-for-byte, with empty
stderr and zero CR bytes in each output. Both outputs and the reference have
SHA-256 `3ac28c6f572ad5023c99ff8f373d0346598611300bba26597207a71d4585e015`.
These processes reran read-only metadata validation; they performed no new
CPU execution in an emulator.

Final source identities are:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/audit_package_completion_witness_v1.py` | 18,718 | `43e1a33d152a0e8ce4d8844fd3a74225abefe8babf2babe3df1a7814dc240b94` |
| `tests/test_package_completion_witness_v1.py` | 10,087 | `a759373826333b2f83dfa56e46516641be70f268ccceb368966d3848f2a9206e` |
| `references/package_completion_witness_v1.json` | 16,543 | `3ac28c6f572ad5023c99ff8f373d0346598611300bba26597207a71d4585e015` |

The human report's final identity belongs in the shared publication receipt,
so its own hash is not embedded recursively here. Existing successful,
refused, alternate-branch, context, helper, and policy sources remain unchanged.

The remaining work is an explicit completion protocol compatible with the
package authoring policy, followed by its own proof plan. This witness does
not approve rewriting a terminal, setting completion state from a helper,
resuming after a late refusal, or installing an eighth-character hook.
