# Conditional scene-command `$8C/$8D` subdispatch, v1

Date: 2026-09-08. Evidence: `verified-static` under the input and memory
premises below. Source and 34 original-host tests passed independent root and
second-peer review. The accepted reference is emitted. There is no native execution.

The two scene-command handlers each have four adjacent pointer cells that
select four leaf routines. Under native M=1/X=0/I=1, D=`$0000`, DBR=`$7E`,
hidden accumulator B=`$00`, and `(parameter & $7F) < 4`, all eight leaves
return through the existing near frame with A/B zero, D zero, DBR `$7E`, and
M/X/I restored to that entry contract. Their additional software-stack depth
is zero. Neither handler's prefix pushes a new return frame.

The parameter condition is a premise. This audit does **not** establish the
legal values produced by scene scripts, pointer validity, source lifetime,
the value loaded into Y, or the target routines' effective memory addresses.
The complete `$8C/$8D` handlers remain open for arbitrary input. Scene-command
bytes are a separate namespace from Schala actions and package selectors.

## Exact input arithmetic and physical cells

The preserved [scene-handler closure](schala_scene_handler_closure_v1.md)
stops command `$8C` at `$CD:295E` and `$8D` at `$CD:299F`. Each nine-byte
prefix performs:

1. A 16-bit `LDY dp43`, whose source word and resulting Y remain unknown.
2. An 8-bit `LDA [dp40]`, whose long-pointer source and returned parameter
   byte remain unproved.
3. An 8-bit `ASL A`, followed by a 16-bit `TAX`.
4. `JMP (abs,X)` in program bank `$CD`, using the command's table base.

In this native width state, ASL changes only low A. TAX copies the complete
accumulator into 16-bit X, including hidden B. The exact index is therefore:

```text
X = (B << 8) | ((parameter << 1) & $FF)
pointer_low_address = $CD0000 | ((table_base + X) & $FFFF)
pointer_high_address = $CD0000 | ((table_base + X + 1) & $FFFF)
```

Parameter bit 7 is discarded from the resulting low index, although ASL can
put it in carry; this audit makes no carry-preservation claim. The arithmetic
pairs `$00/$80`, `$01/$81`, `$02/$82`, and `$03/$83` select the same four
cells when B is zero. Arithmetic equivalence does not make either byte a
proved legal script parameter.

| Command | Handler prefix | Four reviewed pointer cells, half-open | Selected targets |
| --- | --- | --- | --- |
| `$8C` | `$CD2958-$CD2961` | `$CD2961-$CD2969` | `$CD2969`, `$CD2975`, `$CD2981`, `$CD298D` |
| `$8D` | `$CD2999-$CD29A2` | `$CD29A2-$CD29AA` | `$CD29AA`, `$CD29B6`, `$CD29C2`, `$CD29CE` |

B zero alone still permits **128 distinct physical word starts** per
command. Across all 65,536 B/parameter pairs, each command permits **32,768
distinct starts**, whose low/high reads together cover every byte of bank
`$CD`. This is address arithmetic, not a table census or a list of valid
commands. The auditor exhaustively checks those pairs and records a digest
of B, parameter, computed X and both physical pointer addresses.

The bank boundary is explicit. For `$8C`, B=`$D6` and parameter=`$4F` select
low byte `$CDFFFF` and high byte `$CD0000`; the high read stays in the same
program bank. For `$8D`, B=`$D6` and parameter=`$2E` select the final even
word at `$CDFFFE/$CDFFFF`.

Parameter `$04`, even with B zero, selects the first two bytes of the first
leaf body for either command. Those bytes encode its `REP #$20`; treating
them as a pointer would select `$CD20C2`. The auditor records this occupied
code overlap as a counterexample to a four-cell unconditional domain. It
does not follow that escaped target or assert that a legal producer can
request `$04`. The eight-byte pointer spans are only the four reviewed
adjacent cells, not a proved complete legal producer table.

## Conditional leaf composition

Every selected leaf has a twelve-byte straight-line body. It selects 16-bit
A, loads and stores a word through absolute-Y addressing, executes TDC,
selects 8-bit A and returns. TDC copies the full known-zero D into A/B.
The pointer dispatch is a JMP, so the leaf consumes the scene handler's
existing near frame rather than introducing another frame.

| Command | Cell | Return instruction | Additional stack below handler entry | A/B, D, DBR at return |
| --- | ---: | --- | ---: | --- |
| `$8C` | 0 | `$CD2974` | 0 | `$0000`, `$0000`, `$7E` |
| `$8C` | 1 | `$CD2980` | 0 | `$0000`, `$0000`, `$7E` |
| `$8C` | 2 | `$CD298C` | 0 | `$0000`, `$0000`, `$7E` |
| `$8C` | 3 | `$CD2998` | 0 | `$0000`, `$0000`, `$7E` |
| `$8D` | 0 | `$CD29B5` | 0 | `$0000`, `$0000`, `$7E` |
| `$8D` | 1 | `$CD29C1` | 0 | `$0000`, `$0000`, `$7E` |
| `$8D` | 2 | `$CD29CD` | 0 | `$0000`, `$0000`, `$7E` |
| `$8D` | 3 | `$CD29D9` | 0 | `$0000`, `$0000`, `$7E` |

For each target the unchanged accepted direct-call model and value model
must agree on every decoded byte interval, absence of callees, sole return
site and entry width state. The composition requires zero additional bytes,
exactly two counted root-near-frame bytes, no leftover frame, and exact
integer/boolean types in the return evidence. Unsupported control flow,
unknown returned B, differing source coverage, an extra call or a promoted
memory/timing claim refuses.

The return proof is conditional on ordinary writable stack and no nonstack
CPU, DMA or asynchronous alias changing its live cells or canonical code.
It does not certify the absolute-Y reads/writes. Y came from the unproved
DP43 source word, and no lifetime or ownership model is supplied here.
There is no whole-NMI depth bound or claim about other scene-handler returns.

## Provenance, reproduction and handoff

The input is the exact 4,194,304-byte headerless US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Six disjoint named spans pin both nine-byte prefixes, both eight-byte selected
pointer spans, and the two 48-byte leaf-body unions. The public output
contains instruction metadata, addresses and hashes, with no extracted ROM
blob or game fixture.

The [new auditor](../tools/audit_schala_scene8c8d_subdispatch_v1.py) imports the
unchanged accepted scene-handler control model and scroll value model. It
pins their exact sources and references, regenerates both references and
requires exact UTF-8/LF equality, then checks every inherited source before
and after the new composition. Its own source and tests are also checked
for drift. The human report is outside those executable input identities.

Primary CPU semantic provenance is inherited from those accepted references
at Mesen commit `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. In particular,
the pinned CPU's accumulator-width ASL, destination-index-width TAX and
program-bank indirect-JMP word read support the prefix interpretation.
Hashes pin that reviewed source; they do not automatically infer semantics.
The private disassembly labels the region as an included binary extent and
is navigation only. The actual ROM bytes drive this result.

```powershell
python -B -m unittest discover -s tests -p test_schala_scene8c8d_subdispatch_v1.py
python -B tools/audit_schala_scene8c8d_subdispatch_v1.py
```

The 34 original-host tests include complete B/parameter arithmetic, input
aliases, nonzero hidden B, both bank-end geometries, strict byte types,
eight independently executable TDC/JMP/RTS miniatures and adversarial
contract changes. The miniature bodies are original specimens; they do not
contain canonical game bytes or use a private ROM. Native traces are neither
created nor replayed by this packet.

The [accepted reference](../references/schala_scene8c8d_subdispatch_v1.json)
is 48,468 UTF-8/LF bytes, SHA-256
`8b25fb718642c968e18fffebbccae6fe8c33ee0d229e337400485320b0dd3e5d`.
Both independent reviewers reproduced the exact CLI result. The next useful
gate is a source/lifetime proof for the parameter producers and DP43/Y, or a
separate constrained consumer design that actually enforces the declared
input predicate. This conditional result alone supplies neither.
