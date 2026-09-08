# Two reviewed NMI mode bodies: conditional composition v1

Date: 2026-09-08. Evidence: `verified-static`, conditional near-call stack,
M/X/I, and direct control flow. Two independent packet reviews passed.
This additive audit reuses the unchanged closure-v2 walker and its accepted
callee contracts. It creates no new native observation and replaces no prior
reference.

The two targets selected by the three reviewed physical mode cells have
different outcomes:

| Near-call target | Conditional result from native M=1, X-width=0, I=1 entry |
| --- | --- |
| `$CD09F1` | Direct stack/width/control-flow closure; sole root RTS at `$CD0ADD`; 12 additional bytes below callee entry, or 14 including its indexed near-call frame |
| `$CD088D` | Open at indexed JMP `$CD06B9`; no complete return contract or stack bound |

The first result is useful composition evidence. All eight callees called
directly by its wrapper already have accepted v2 contracts. Their independent
stack arithmetic agrees with a full traversal from the wrapper entry. The
second result places the remaining scroll-dispatch obligation inside its
exact two-frame caller context. Neither establishes D/DBR or other register
preservation, effective memory addresses, DMA effects, physical stack
ownership, termination, or a whole-NMI maximum.

## Input provenance and scope

The source relation is pinned to
[`schala_nmi_mode_inputs_v1.json`](../references/schala_nmi_mode_inputs_v1.json),
138,037 bytes, SHA-256
`dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530`.
That earlier packet establishes the normal prefix's first mode-dispatch
inputs, including B=0, D=0, DBR=0, M=1, X-width=0, and the three reviewed
physical cells. Its high-bit aliases and unresolved legal mode domain remain
unchanged. The new traversal starts at only two exact target addresses:

| Reviewed low mode byte | Physical cell | Target |
| --- | --- | --- |
| `$00` | `$CD0C83-$CD0C84` | `$CD09F1` |
| `$01` | `$CD0C85-$CD0C86` | `$CD088D` |
| `$02` | `$CD0C87-$CD0C88` | `$CD088D` |

These rows describe the reviewed cells. They do not prove that these are the
only legal mode values or certify the reachability of any hypothetical input.
In particular, this packet does not walk every possible mode-derived target.

The preserved direct-callee reference is
[`schala_package_normal_nmi_closure_v2.json`](../references/schala_package_normal_nmi_closure_v2.json),
321,839 bytes, SHA-256
`413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242`.
The new collector re-executes the unchanged v2 audit against the pinned ROM
and requires byte-exact reproduction of that reference. It separately
re-executes the mode-input collector and requires the same agreement. This
preserves their original source, annotation, CPU documentation, and history
identities rather than accepting unbound summaries.

Canonical input remains the private 4,194,304-byte US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Only original source, metadata, tests, and this report are added. No ROM,
extracted game payload, SRAM, state, or raw emulator trace is published.

## Mode-zero body composition

Starting at `$CD09F1` with an abstract two-byte near return frame, the
unchanged walker explores 1,916 states and 1,398 instruction contexts. Its
only root return is RTS at `$CD0ADD`, with M=1, X-width=0, and I=1. It finds
no unsupported instruction, indexed dispatch, incompatible return frame,
IRQ unmasking, or unbalanced root exit in that direct-control traversal.

That statement is conditional on the walker's existing premises. Every
conditional branch is explored without proving register-valued feasibility;
the finite graph is not a proof that an actual invocation terminates. Typed
push/pop balance assumes saved frames and status values remain intact.

The wrapper's direct-call inventory is checked against canonical instruction
encodings. Its maximum is also calculated separately from the eight prior
callee contracts:

| Call site | Target | Call frame | Live wrapper save | Prior callee additional bytes | Total below mode-body entry |
| --- | --- | ---: | ---: | ---: | ---: |
| `$CD09F1` | `$CD09CE`, long | 3 | 0 | 0 | 3 |
| `$CD0AB4` | `$C1000F`, long | 3 | 0 | 2 | 5 |
| `$CD0ABC` | `$CD0AEE`, near | 2 | 1 | 0 | 3 |
| `$CD0ACC` | `$CD06C4`, near | 2 | 0 | 0 | 2 |
| `$CD0ACF` | `$CD0B1E`, near | 2 | 0 | 0 | 2 |
| `$CD0AD2` | `$D1F426`, long | 3 | 0 | 2 | 5 |
| `$CD0AD6` | `$FDFFF7`, long | 3 | 0 | 9 | 12 |
| `$CD0ADA` | `$CD0ADE`, near | 2 | 0 | 0 | 2 |

The single persistent wrapper byte at `$CD0ABC` comes from PHB at
`$CD0AB8`. Its temporary PHA/PLB pair is already consumed before that call;
PLB at `$CD0ACB` later consumes the saved bank byte. The earlier PHA/PLB
pair at `$CD0AAD/$CD0AAE` also leaves no persistent byte. The wrapper's
noncall local maximum is two bytes. These exact source sites and the wrapper
span are pinned; the composition recipe is reviewer-encoded and not a new
general CPU interpreter.

Sequential calls are combined with a maximum, not a sum. The largest
contribution is the long call at `$CD0AD6`: three bytes for its JSL frame
plus the previously proved nine additional bytes of `$FDFFF7`. This gives
12 bytes below mode-body entry. The indexed JSR at `$CD0C99` contributes
the two-byte root frame, making 14 counted bytes for this conditional mode
body including that frame.

The metadata retains all peak instruction sites from the full walk. They
occur in the palette-animation worker's nested calls at the `$FDE5xx` and
`$FDE8xx` sites, matching the reused `$FDFFF7` contribution. Each prior
callee's complete metadata object also has a canonical JSON hash in the
composition report, so the arithmetic cannot silently borrow a different
width, entry point, or call kind.

The wrapper's half-open source span `$CD09F1..$CD0ADE` is 237 bytes,
SHA-256
`224aaf43ca64993c9e7b861ee95ebc4b98ccbd1e579abf60f32384712dab37c7`.
No game byte payload is emitted by the auditor.

## Modes one and two remain open

Starting at `$CD088D` with the same near-entry M/X/I premises, the walker
reaches the indexed JMP at `$CD06B9` after exploring 475 states and 388
instruction contexts. This is the first stopping frontier in that traversal,
not a statement that every possible route must execute it.

The frontier still has M=1, X-width=0, and I=1. Its four counted stack bytes
are two exact typed near frames:

1. The mode target's abstract root near frame, from the indexed JSR.
2. The nested near frame whose return address is `$CD092C`, from the call
   to `$CD06B4` at `$CD0929`.

The existing v2 reference already identifies `$CD06B4` as open at this same
indexed jump. The new result locates that unresolved callee in the selected
mode body's caller context. It does not assign an opaque return to the jump
or traverse its hypothetical table targets.

The exploratory local peak encountered before traversal stopped is ten bytes
below the mode target's entry. It is explicitly **not a bound**. The metadata
leaves both the additional stack bound and total bound null and supplies no
complete root return contract. An unfinished branch traversal cannot certify
that the mode body never returns, either.

The half-open scroll-dispatch span `$CD06B4..$CD06BC` is eight bytes,
SHA-256
`0016098af9a67c4facae3dd092e328de1da7bb6e0c74f4ec5075db44779827d7`.
The unchanged next obligations include the `$CA92` producer domain, incoming
hidden B at the local eight-bit ASL/full TAX, actual table extent, and the
selected target's return and effective-address contracts.

## Register values and memory remain distinct obligations

Balanced typed stack frames do not establish the values returned in A, X,
Y, D, or DBR. The new report keeps these claims false, even for `$CD09F1`.
The source gives concrete reasons to avoid silently treating the mode body
as register-preserving:

- Mode zero explicitly publishes DBR=`$7E` through a PHA/PLB pair at
  `$CD0AAB..$CD0AAF`, then uses TDC in a temporary-bank setup. Interpreting
  that temporary DBR requires the D-register value at that point.
- Its palette-animation worker saves D and DBR, installs D=`$0500`, and
  later pulls D and DBR. The source recipe is visible at
  `$FDE39C..$FDE3AC` and `$FDE434..$FDE437`; saved-value integrity and
  nonstack aliases remain outside this typed-stack model.
- Modes one and two publish DBR=`$7E` before reaching the open scroll
  dispatcher. Their later B value and `$CA92` domain are not supplied by
  the earlier first-call mode-input proof.

Named span hashes retain these source observations without turning them into
a full register-value analysis. The underlying v2 result explicitly leaves
`callee_register_value_preservation` and `nonstack_alias_closure` false.

Hardware register setup and DMA are also outside the proof. Syntactic store
operands in the retained walker output are not a complete effective-address
or DMA-write ledger. Ordinary writable stack memory, no interfering aliases,
and no intervening asynchronous handler are explicit conditional premises.
This work provides no sampled physical SP, stack reserve recommendation,
interrupt-timing bound, or permission to install a helper in the game.

No new contradiction of a published data map was found in this bounded
composition. It refines the existing unresolved mode frontier and preserves
the prior source labels and their limitations.

## Reproduction, tests, and handoff

```powershell
python -B -m unittest discover -s tests -p test_schala_nmi_mode_bodies_v1.py
python -B tools/audit_schala_nmi_mode_bodies_v1.py
```

The [auditor](../tools/audit_schala_nmi_mode_bodies_v1.py) writes no files and
prints UTF-8/LF JSON with one trailing newline. The final output belongs in
[`references/schala_nmi_mode_bodies_v1.json`](../references/schala_nmi_mode_bodies_v1.json).
Before and after collection it checks its own source/tests and the two frozen
dependency sources/references. Both underlying accepted references are
reproduced before the new target walks are accepted.

The 40 original host tests exercise independent component arithmetic,
maximum-versus-sum composition, exact call/frame namespaces, changed or
missing prior callees, mismatched widths/I, altered return sites, false
boolean/float equalities, open-frontier bound leakage, and attempted scope
promotion. The fixtures are original metadata objects; they contain no
copied private trace or game payload. The unchanged closure walker is not
reimplemented in these tests.

Root and a second independent reviewer read the source/report, ran all 40
tests, and reproduced the same 160,900-byte metadata result. The second
review also checked the canonical wrapper push/pull sites, its one persistent
PHB byte, the independent maximum composition, and the unresolved typed
frames at `$CD06B9`. Neither review required a source change.

After both reviews, the reference was emitted once. Two fresh actual CLI
processes then reproduced that reference byte-for-byte, each with empty
stderr and zero CR bytes. The reference and both outputs have SHA-256
`f3057c1cf9d0b354a318e3e67b2c760fdf9d8bfc49784d4efed344ba997a8d85`.
These executions revalidated source metadata and performed no native emulator
run. Auditor source is 13,937 bytes, SHA-256
`9b685d63e68153d1c7d56213af5b1211237c3f36d067046a9e854ae5beb34187`;
tests are 8,308 bytes, SHA-256
`3bccabc53eda3357079a2db236c37cbd81e1cf139c6e5c5ec913ee0facb38833`.
The final human-report identity belongs in the shared publication receipt.

The next useful work is the open scroll-dispatch input/target contract and
separate register-value/effective-address analysis. Completion of this
conditional mode-zero composition leaves the production hook/allocation
catalogs, high package bindings, and logical PC `$07` integration gates
unchanged.
