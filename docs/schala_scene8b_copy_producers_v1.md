# Scene 8B copy-pointer producers, v1

Date: 2026-10-03. This finishes an interrupted, unpublished September 8
draft. Evidence: **verified-static**, conditional source analysis. It adds
no native execution, game mutation, allocation, hook or production binding.
The source and tests passed independent peer and root review. The reference
is accepted only within the explicit conditional scope below.

The four scene `$8B` targets previously open at `$CEE7CC` have **three
distinct pointer-producing routines**, preceded by three different emitters.
Their copy-count expressions and typed continuations can now be stated
conditionally. This does not establish legal game inputs, effective memory
ownership, emitter/fill-loop termination, complete scene `$8B` closure or a
whole-NMI stack bound.

For each producer, 64,414 of the 65,536 independent r/s byte pairs either
select a verified physical copy suffix or deliberately skip a zero-count
copy; 1,122 do neither. The two shortened producers skip 291 pairs. The
full producer always calls, including its 290 zero-count pairs, which select
the empty suffix. The common safe-or-skipped relation is `abs(r-s) <= 222`.
That relation is an exhaustive result of these conditional models, not a
game-domain assumption.

The separately named [auditor](../tools/audit_schala_scene8b_copy_producers_v1.py)
and [tests](../tests/test_schala_scene8b_copy_producers_v1.py) preserve the
accepted [scene 8B dispatch packet](schala_scene8b_dispatch_inputs_v1.md)
and [B5/B6 pointer packet](schala_scene_copy_pointer_v1.md). Neither accepted
source nor reference changes. Sharing the final `$CEE7CC` instruction alone
does not justify sharing a producer contract.

## Four paths, three producers

The accepted `$8B` dispatch packet already identifies six reviewed cells
under its conditional B-zero and selector-range premises. Two were closed
by the unchanged walkers. This packet addresses only the other four:

| Selected target | Preceding emitter call | Tail-jumped producer | Postcopy continuation |
| --- | --- | --- | --- |
| `$CD33B5` | `$CD31FE` | `$CD35A5` | `$CD3612` |
| `$CD33BB` | `$CD3273` | `$CD352D` | `$CD35A1` |
| `$CD33C1` | `$CD3273` | `$CD347D` | `$CD34F1` |
| `$CD33CD` | `$CD3337` | `$CD35A5` | `$CD3612` |

Every six-byte entry stub must contain exactly its emitter JSR followed by
its producer JMP. The jump inherits the original scene-handler near frame.
The emitter's separate near frame is already consumed when the producer
starts. The distinct copied-return chain therefore has nine counted bytes,
not the eleven in the B5/B6 caller context.

All three emitters are independently walked by the unchanged accepted
control and value models. Their decoded contexts, source intervals, return
sites and classifications must agree:

| Emitter | Instruction contexts | Sole RTS | Conditional return |
| --- | ---: | --- | --- |
| `$CD31FE` | 58 | `$CD3272` | B0, D0, DBR7E, M8/X16/I1 |
| `$CD3273` | 99 | `$CD3336` | B0, D0, DBR7E, M8/X16/I1 |
| `$CD3337` | 64 | `$CD33B4` | B0, D0, DBR7E, M8/X16/I1 |

Each emitter uses no stack beyond its own two-byte near call frame. These
are returning-path contracts under B0/D0/DBR7E entry and the accepted
nonstack-alias premises. The walks retain both sides of data-dependent
branches. They do not establish termination, pixel results, the ownership
of ordinary destination stores or the current address behind WRAM port
`$2180`. The proof does not pretend those memory effects cannot change
other live inputs; their absence is an explicit composition premise.

## q controls addresses and parity, with four refused alias cases

At each producer entry, native M8/X16/I1, B0, D0, DBR7E and decimal-clear
arithmetic are required. The producer reads q from byte `$7ECAAA`, then
uses the complete byte q as an X16 source index:

```text
r address = $7ECAA4 + q
s address = $7ECAA8 + q
```

The high bit of q is preserved in these addresses. The calculation spans
`$7ECAA4-$7ECBA3` for r and `$7ECAA8-$7ECBA7` for s. Those are possible
effective-address calculations, not declarations that the spans are valid
arrays or jointly owned storage.

Four q values cannot be treated as independent q/r/s inputs:

| q | Alias | Why this packet refuses it |
| ---: | --- | --- |
| 2 | s is `$7ECAAA` | s aliases q's low byte |
| 3 | s is `$7ECAAB` | s aliases the unknown high byte of the later word load |
| 6 | r is `$7ECAAA` | r aliases q's low byte |
| 7 | r is `$7ECAAB` | r aliases the unknown high byte of the later word load |

These four cases are unresolved, rather than silently enumerated as three
independent bytes. The API rejects them before interpretation. All other
252 q values remain conditional parameters; this is not evidence that any
of them belongs to a legal game producer.

Later, each producer reads the **word** at CAAA. Its unknown CAAB high byte
must be removed by the exact immediately following M16 `AND #$0001`.
The interpreter carries an explicit unknown-high marker and rejects any
other next instruction or mask. No branch may use a placeholder flag from
that word load. The three masks are at `$CD3601`, `$CD358C` and `$CD34DC`.
After that mask, q contributes only its parity, adding zero or two to X.

The source factorization is checked at several levels. It pins the exact
initial q/index/input-read sequence, the complete later parity-to-X sequence,
the conditional CPY/BEQ where present, and the shared count kernel. The
concrete interpreter propagates q-dependency tags through registers, flags
and each direct-page byte. It refuses q-dependent control flow and any
remaining q dependency in the count, pointer or source Y. At `$CD3616`,
STY overwrites both bytes of DP45 before count arithmetic can read them.
Every DP read must have a modeled earlier writer. The final X must carry
only q-bit-zero dependence.

The actual exhaustive CPU workload is **393,216 evaluations**: three
producers times q=0/1 times 65,536 r/s pairs. It is accompanied by all 256
q-address geometries and the complete source-use factorization. This is
not a claim to have executed sixteen million q/r/s tuples per producer.
The q=0/1 matrices plus the source-derived dependency restriction justify
the parity reduction only under the explicit stable-input and alias
premises. Original tests also evaluate all 252 admitted q values against
an authored arithmetic specimen, checking the full source index and parity.

## Exact arithmetic and suffix membership

Denote the producer's signed pair count by n. The independent integer
expression compared with actual instruction evaluation is:

```text
h = r                 for $CD35A5
h = floor(r / 2)      for $CD352D and $CD347D
n = h + min(r,s) - max(h + max(r,s) - 222, 0)
count_word = (2*n) mod 65536
pointer_word = ($E7C7 - 6*n) mod 65536
```

All three actual n distributions span -33 through 222. The full and two
shortened expressions differ: r=s=111 gives n=222 for the full producer,
but n=166 for both shortened ones. Their equality at some boundaries does
not make them interchangeable.

The finite evaluator extends the earlier concrete semantics only with
M16 accumulator LSR, X16 CPY direct-page, and BEQ over the actual zero flag.
LSR shifts the entire word and puts old bit zero in carry; CPY compares full
Y against a DP word, establishing carry, sign and zero; BEQ consumes that
zero flag. It never infers equality from an unrelated or stale flag.
These interpretations are checked against the pinned Mesen source:
[word shift and flags](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L602),
[accumulator width](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L648),
[compare and CPY](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L354),
[BEQ](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L173).

The shortened variants compare source Y with the end word before calling.
Exactly n=0 takes BEQ and skips the copy. The full producer lacks that skip;
its zero count selects RTS `$CEE7C7` directly. Negative counts are not
converted into empty copies. For example, r=255,s=32 gives n=-1 and pointer
`$CEE7CD`, inside the indirect-jump operand bytes, for all three producers.
r=255,s=0 gives n=-33 and pointer `$CEE88D`, also outside the verified ladder.
Those are static counterexamples to unconditional pointer safety, not
observed game failures or proof of reachable inputs.

The physical copy ladder is regenerated and checked from canonical ROM,
using the unchanged accepted geometry checker: 256 complete instruction
pairs at `$CEE1C7-$CEE7C7`, plus the empty RTS suffix. Each selected word-copy
pair reads at source offset 2*k relative to Y and writes at destination
offset 4*k relative to X. The 257 physical suffixes are distinct from the
producer's admitted 0..222 suffix counts. The word pointer is compared with
bank-relative suffix words; its bank-zero absolute-indirect consumer retains
PBR `$CE`. D zero is required to make the DP producer and absolute-indirect
consumer refer to the same pointer bytes.

For each r/s pair, actual suffix membership or an actual skip is compared
with `abs(r-s) <= 222`. The metadata retains complete n distributions,
boundary witnesses and matrix hashes. Each matrix record is q,r,s,skip as
bytes followed by count, pointer (zero for skip), X and Y as little-endian
words, ordered by r, then s, then q:

| Producer | Safe or skipped | Outside ladder | Skipped | Matrix SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `$CD35A5` | 64,414 | 1,122 | 0 | `f9e198f1d27c1482fe46e91e59163d763edd9785f4f468faf97af6bc94e22cd3` |
| `$CD352D` | 64,414 | 1,122 | 291 | `7b4ec431a4b87dce16d271f6ab1beb041cc48da5fef7bd8e5fd401bebcd01e3e` |
| `$CD347D` | 64,414 | 1,122 | 291 | `7b4ec431a4b87dce16d271f6ab1beb041cc48da5fef7bd8e5fd401bebcd01e3e` |

The shortened matrices match because the tested pointer/count/X/Y/skip
projection is equal. Their subsequent code and memory behavior differ.

## Typed returns and the separate half-fill continuation

At an admitted copy suffix, the exact frame chain is original scene near2,
producer's near2, parity arm's long3, wrapper's near2: nine counted bytes,
or seven below the original scene-handler entry. The pointer jump itself
pushes nothing. Both parity arms are source-checked separately:

| Return instruction | Consumed frame | Next PC | Counted bytes left |
| --- | --- | --- | ---: |
| RTS `$CEE7C7` | Near2 | `$CEE7CB` | 7 |
| RTL `$CEE7CB` | Long3 | `$CD3644` or `$CD3656` | 4 |
| RTS `$CD3656` | Producer Near2 | Its distinct postcopy continuation | 2 |

The `$CD3644` arm executes the exact BRA to `$CD3656`. Typed near and far
returns may not substitute for each other. The accepted historical frontier
for each target, including its distinct producer return address, is
reproduced and checked before these chains are composed.

The full and short producers then execute TDC/SEP20/RTS at `$CD3612` and
`$CD35A1`. The half producer continues at `$CD34F1`, traversing 34 instruction
contexts that include a parity-selected fill loop, before its TDC/SEP20/RTS
at `$CD3529`. The unchanged width/stack walker closes that conditional CFG
with no additional stack bytes. A separate narrow CFG, with identical
decoded-context identity, verifies that every returning path reaches TDC
before SEP20 and reaches SEP20 before RTS. Allowed decoded operations do
not change D or DBR. Thus every proved returning path ends with
B0/D0/DBR7E and M8/X16/I1 under the stated entry/alias premises.

The half-fill loop is **not an empty suffix**, and this packet does not
prove its effective destinations, wraparound behavior, termination or
frame ownership. Its postcopy reload of q and other inputs must retain
the documented lifetime assumptions. A zero-count copy skip still reaches
that continuation. Skipping the copy does not establish that the entire
selected command has no memory effects.

The preceding emitter and the copied route are sequential, so their local
depths compose as max(original near2 + emitter near2, original near2 +
producer contribution7) = 9. This is a conditional route count. It proves
no legal selector/q/r/s domain, game-stack allocation, asynchronous reader
isolation, physical memory ownership or whole-NMI bound.

## Provenance, development correction and reproduction

The canonical input is the headerless 4,194,304-byte US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The selected canonical spans are `$CD31FE-$CD33D9`, `$CD347D-$CD3657`, and
`$CEE1C1-$CEE7CF`, all end-exclusive. Their exact hashes are in the metadata.
No canonical body, ROM data or native trace is emitted as a tracked payload.

The collector fully regenerates both accepted prerequisite references:
scene8B dispatch v1 and B5/B6 copy-pointer v1. It compares their complete
serialized bytes with the pinned references before composing this result.
It checks the new source/tests, both prerequisite source/test/reference
triples, and their merged 37-file transitive identity set before and after work.
The Mesen instruction source is pinned to commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`, 27,673 bytes, SHA-256
`9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`.
Seven reviewed semantic spans are hashed separately. Source hashes identify
reviewed semantics; they do not automatically derive an interpretation.

The first October 3 exhaustive attempt refused immediately because **our
unpublished September 8 draft compared a 16-bit pointer word with 24-bit
suffix addresses**. It raised `derived suffix-safe input relation differs`.
The corrected comparison uses bank-relative words on both sides. This was
an implementation defect in our draft, not a conflicting upstream data map.
The original 25,175-byte draft, SHA-256
`8c3d5c9bb76e9831149adc04639dd567c6d00659e51b2290a93ab2ad5831e8e3`,
and a private development receipt are preserved under
`private/test_runs/scene8b_copy_producers_20261003_resume/`.

An added adversarial test initially expected the later count/source guard;
the mutated parity-to-Y specimen correctly failed earlier when CPY/BEQ
made the branch depend on q. Its expected error was corrected without
weakening the interpreter. All 52 tests now pass. They cover exact q alias
refusal, high-bit address selection, hidden B/D/DBR/decimal premises,
full-word LSR and carry, CPY/BEQ skip behavior, unknown-high mask dependence,
tainted control/count refusal, source drift, typed continuations, final
TDC/SEP dominance, emitter return values and historical frontier preservation.

```powershell
python -B -m unittest discover -s tests -p test_schala_scene8b_copy_producers_v1.py -v
python -B tools/audit_schala_scene8b_copy_producers_v1.py
```

CLI metadata uses UTF-8 with LF and one trailing newline. Two fresh author CLI processes
produce identical 171,599-byte outputs with empty stderr, SHA-256
`f3fc3cf0999d0782f80c76a39ace13332dc31ef895482391e3e3282512d14ee6`.
The source is 29,492 bytes, SHA-256
`9a9619921c7cb310c8f0ad545109fe9b3c16cb04c63e3787b025c4087a39aec1`;
tests are 16,150 bytes, SHA-256
`60b316d31947f86703d6ba46384930f25a3f7aa04fc1db293f24d1fff6c2ae19`.
Both processes reproduce the same bytes and preserve the source/test
identities. A separate peer and root each passed all 52 tests and independently
reproduced those exact metadata bytes. The peer also ran 9,072 additional
canonical cases: all 252 admitted q values, three producers, and twelve
boundary r/s pairs. Their complete executed context and numerical projections
matched the corresponding parity representative. That supports the declared
factorization; it does not turn the conditional inputs into a legal domain.
The reference is `references/schala_scene8b_copy_producers_v1.json`.

The next useful work is to prove the legal q/selector/r/s producer domains
and their lifetime, then close emitter/WRAM-port and half-fill memory effects.
The four refused aliases need their own constrained model. None of those
requirements is discharged by the shared copy address or these conditional
return and arithmetic results.
