# Scene8B half-fill v1: conditional termination and write geometry

2026-10-03. Accepted additive `verified-static` evidence after independent peer
and root review. No native run, game mutation, allocation or legal-script approval.

The half producer's continuation at `$CD34F1` always enters one of two
store-before-test loops. With the stated stable local inputs, positive byte
`s` produces exactly `s` word stores. **`s=0` produces 16,384 word stores and
one 16-bit X wrap.** A zero-count copy skip therefore does not make this
continuation empty. The earlier copy-safe relation `abs(r-s)<=222` also
admits positive `s` values whose fill reaches beyond the comparison interval
between the two canonical fill bases.

This report preserves the accepted [copy-producer v1 report](schala_scene8b_copy_producers_v1.md)
and its source/reference unchanged. That packet explicitly left half-fill
termination and memory effects open. This result closes a narrower local
conditional calculation; it does not correct a contrary published v1 claim
or establish a vanilla runtime bug.

## Exact local contract

Entry is `$CD34F1`, after the earlier emitter and optional copy have returned.
The CPU is native M16/X16, D=`$0000`, DBR=`$7E`, with binary arithmetic.
DP `$47/$48` contains zero-extended byte `s`. The word read at `$7ECAAA`
contains low byte `q` and an otherwise unknown high byte at CAAB. The word at
DP `$7C` chooses the frame arm through bit0. The word at `$7EBA00` supplies
the fill value. Register/status/code changes by asynchronous activity are
excluded from this local model.

The earlier independent-input exclusions remain: `q=2,3,6,7` select r/s
bytes that alias CAAA/CAAB. This packet does not turn those aliases into
independent inputs or declare the remaining 252 q values a legal game domain.

The prefix writes DP45 twice: first `4*s`, then `T=4*s+2*(q&1)`.
It initializes X to `X0=2*(q&1)`. Its word AND `$0001` removes every CAAB bit
and all q bits above bit0 from this local calculation. The earlier producer's
full-q source selection remains a separate operation. DP45 must remain
fixed after the second setup store and throughout the selected loop.

The odd frame arm stores at `$7EC4E1+X`; the even arm stores at `$7EC161+X`.
Each iteration stores a word, increments X four times modulo 65,536, then
compares the full X word with DP45. The recurrence after k iterations is

```
X_k = (2*(q&1) + 4*k) mod 65536
T   = 2*(q&1) + 4*s
```

For a general fixed target, termination requires `T-X0` to be divisible by
four modulo 65,536. The first positive solution is used because the initial
equality is not tested before the store. The period is 16,384. In the source
setup the target is always in the matching congruence class, so every byte s
terminates under the local assumptions: k=s for s1..255; k=16,384 for s0.
This is not a bound on the preceding emitter or the complete command.

The final TDC/SEP20/RTS returns A/B0 and M8/X16 while preserving D0/DBR7E.
No instruction in this continuation changes Y or adds stack bytes. The
accepted two-byte near frame remains inherited; its physical ownership is
not inferred by this calculation.

## Physical writes and counterexamples

For the canonical recurrence, store i (zero based) writes the two bytes
`base+2*(q&1)+4*i` and the next address. Absolute-X addition is 24 bit:
crossing `$7EFFFF` carries into bank `$7F`. A word's high byte can itself be
the first byte in the next bank. The zero case writes 32,768 distinct indexed
WRAM bytes. Both DP45 setup word stores are also counted: total ordinary CPU
byte-store events are `2*k+4`, including same-value stores. No write value or
raw canonical body is emitted as game data.

The base difference is `$C4E1-$C161=$380`. Equal-width intervals beginning
at each base are useful **comparison envelopes, not approved allocations**.
Every indexed write remains within its selected comparison envelope exactly
when `1<=s<=224`, for either q parity and either frame parity. This predicate
does not establish ownership of any byte inside either interval.

Each following example passes the earlier copy suffix arithmetic predicate.
The collector additionally replays its actual canonical half-producer prefix
through the unchanged accepted evaluator.

| q / r / s / frame | Copy pairs | Fill result |
| --- | ---: | --- |
| 0 / 1 / 0 / even | 0, skipped | 16,384 words; first `$7EC161/62`, last `$7FC15D/5E` |
| 0 / 2 / 0 / even | 1 | Same 16,384-word fill; copy success does not prevent the wrap |
| 1 / 1 / 0 / odd | 0, skipped | 16,384 words; first `$7EC4E3/E4`, last `$7FC4DF/E0` |
| 0 / 224 / 224 / even | 222 | 224 words; last `$7EC4DD/DE` remains in the comparison interval |
| 0 / 225 / 225 / even | 222 | Word225 writes `$7EC4E1/E2`, the other canonical base |
| 1 / 226 / 226 / odd | 222 | Word226 writes `$7EC867/68` |

The final pair also appears in the accepted
`references/schala_package_irq_memory_contract_v2.json` as the beginning of
the MVN destination at `$CEEEB9`. The collector checks that exact source-use
record and its reference hash. This establishes an overlap with a separately
identified engine destination; it proves neither concurrent execution nor
a runtime corruption event.

The positive225/226 examples do not depend on an own write changing q.
The long zero cases do eventually write CAAA or CAAB. The local loop has
already read that word and does not reload it, so those writes do not defeat
the fixed-DP45 termination calculation. They do defeat a stronger claim
that q/CAAB remain unchanged throughout the entire selected path. The model
explicitly refuses a later external reload after an aliased local store;
it never substitutes a stale input for that read.

## Direct-writer candidate and remaining obligation

A source-authored `$8A -> $AB -> $8B` sequence could establish a narrower
useful local domain. For slot0, deliberately choose initializer parameter
`$20` (half selector2, slot0), r1..127, AB parameter `$00` or `$01`, then draw
q0. Slot1 uses `$21`, AB `$80` or `$81`, then draw q1. Under stable command
parameters and preserved inputs, AB selects one of the two primary coordinate
pairs just clamped by `$CD2436`; its Y helper clamps to `$08..$D4` (8..212).
Thus s8..212 and `abs(r-s)<=211`. The collector checks all 26,035 pairs in
this proposed arithmetic rectangle. This is a reviewer-derived writer
candidate, not an automatically proved instruction-level script composition.

The source sites explain why no broader domain follows:

- `$8A` at `$CD2FED` masks its own slot index with1 but stores raw r/s.
  It does not write the draw command's q.
- `$8B` at `$CD2FB7 -> $CD3189` writes its own unmasked parameter to CAAA.
  Matching a previous initializer's slot is an additional relation.
- `$AB` at `$CD24F3` gives the stated s bound only for parameters00/01/80/81.
  Other values select later coordinate bytes that this clamp did not cover.
- `$89` at `$CD2FBC` computes `min((old_s+delta)&255,211)` under binary
  arithmetic. Its upper clamp permits zero: old_s1 plus deltaFF produces0.
  A chosen `$8A -> $89 -> $8B` sequence can therefore reach the local r1/s0
  counterexample, conditional on the same source-lifetime premises.
- `$D4` can saturate r to zero; `$D3` uses a dynamic upper comparison.
  `$CD10B6` writes the CAAB/CAAC word, leaving variable CAAB. The separate
  B5/B6 clear at `$CD1F99` does not constrain the 8B draw's own q store.

The eight exact writer spans and six command-pointer cells are pinned in the
metadata. Their meanings are reviewer-derived from canonical bytes; hashes
identify the reviewed source and do not mechanically derive semantics.
No rooted canonical script, same-slot lifetime, complete indexed/indirect
writer census, WRAM-port/DMA closure or emitter ownership is proved here.
The next obligation is to connect a constrained writer sequence to an actual
consumer without an intervening writer or asynchronous invalidation.

## Evidence and reproduction

The headerless 4,194,304-byte canonical ROM has SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The exact 60-byte continuation `$CD34F1-$CD352D` has SHA-256
`b9df1c83b5d4336c44848cef615acc9c51da614efd37e63403d7d0ddbddc70c8`.
Its two loops are separately hashed. Source navigation used recovered
`bank_CD.asm`, upstream commit `eeae27acdb6565e96d1d796a3d60792c250c0aa1`;
canonical span hashes are the executable-source authority in this packet.

Mesen semantics are pinned to commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. Nineteen individually hashed
line spans identify word shift/add, INX/CPX flags, current-zero branches,
24-bit absolute-X addressing, word high-byte carry, direct-page addressing,
WRAM mirrors and the final width/value operations. The new original interpreter
does not run Mesen and is not a general CPU emulator.

The collector runs all 1,024 combinations of q0/1, two frame parities and
256 s values against canonical code. It compares every actual write with
the independent recurrence, including exact count, ordered physical
addresses, fill values, DP setup, X wrap, return state and boundary crossings.
It separately runs 144 endpoint interpretations (72 low/high pairs), checks
64,512 admitted-q/high-byte mask combinations, and checks all65,536 possible
frame-word parities algebraically. These are factorization checks over the
source-pinned masks, not 65,536 complete native executions.

The accepted copy source/tests/reference and 41 inherited dependency
identities are checked before and after collection. Six selected canonical
copy-prefix examples are replayed. **The earlier full prerequisite collectors
and their exhaustive producer censuses are not regenerated here.** The
prerequisite scope is stated identically in the emitted metadata.

```powershell
python -B -m unittest discover -s tests -p test_schala_scene8b_half_fill_v1.py -v
python -B tools/audit_schala_scene8b_half_fill_v1.py
python -B tools/audit_schala_scene8b_half_fill_v1.py --output private/test_runs/half_fill_review.json
```

Default stdout and explicit output are binary UTF-8/LF JSON with one trailing
newline. Importing the tool reads neither the ROM nor prerequisite files.
Original test programs cover store-before-test zero behavior, word compare,
both kinds of bank carry, parity, boundaries224/225/226, unknown-high mask
independence, current flags, stale-read refusal and source/premise mutations.
No reference file is emitted before root review.

The frozen author run passes all 38 tests. A fresh default-stdout CLI and a
fresh `--output` CLI produce the same 44,048 bytes, with empty stderr and
SHA-256 `97c7c22478aa688e6ceacb4508c3fc6b947dfdcc43930c0a8569402c6c7f10af`.
The explicit-output process also has empty stdout. Both outputs contain
no CR bytes. The new source is 27,649 bytes, SHA-256
`0b71d1b3c08b94acfc2781bcefebaaf174c39a5e18b52b9ffa8932eee0f6fa7a`;
the tests are 12,403 bytes, SHA-256
`0667fd0da67493b8848aa073a1ebc2cafd09c1c8ec5b223e36d475993ec7a035`.
The proposed metadata is retained privately for independent reproduction;
the intended accepted reference path is
`references/schala_scene8b_half_fill_v1.json`.

Development began as the separately preserved October3 private finite
analysis. The additive source and tests are new; earlier accepted packets
and the original private reproduction remain unchanged. Independent review,
final frozen hashes and reference acceptance are recorded separately when
completed. No work is backdated to the interrupted September8 draft.

## Independent acceptance — 2026-10-03

Root read the complete source, tests and report, passed all 38 tests, and
reproduced both CLI forms in fresh processes. Both outputs equal the author's
and independent peer's 44,048-byte metadata with the SHA-256 above. The accepted
[reference](../references/schala_scene8b_half_fill_v1.json) contains metadata;
canonical code, input images and execution ledgers remain private.

The peer independently ran 112 mutable-memory CPU examples, including sixteen
that actually overwrite q/CAAB, and compared every ordered DP/indexed write
and final A/X/M/DP45 value. It also ran all 65,536 frame words at s1 and all
64,512 admitted q/high combinations at s1 through the actual local interpreter.
Four additional original fixtures cover single-byte q/CAAB reloads, a store's
high-byte alias to live DP45, and a word crossing into bank7F. These are static
host interpretations, not native executions or rooted legal-input evidence.

The exact independent challenge script is
`private/test_runs/scene8b_half_fill_peer_review_20261003/independent_checks.py`,
SHA-256 `8c3b6608963a51045d43fb31f8d2195b0a3d3378f61574bb3ecfa9afc346d0c5`.
Its receipt hashes to
`97803b72c7f63149bcdb44d44094d138bf1beb839ea7b850392d37b403884dbc`.
Root's two outputs and receipt are under
`private/test_runs/scene8b_half_fill_root_review_20261003/`.
The source and test hashes remain exactly those in the frozen author report.
Only this living narrative gained the acceptance record.
