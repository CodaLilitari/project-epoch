# Original package-test cartridge: reproducible guarded build v1

Date: 2026-09-08. Evidence: `verified-static`. Two fresh builds produce the
same original eight-MiB test image, SHA-256
`1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b`.
The image and SRAM remain ignored under `private/test_runs/`. This report
certifies source construction and complete-diff auditing. It contains no
runtime, game-hook, production-allocation or PC `$07` claim.

The [design](original_snes_package_cartridge_design_v1.md) separates this
original diagnostic from the existing canonical-ROM and inert-scaffold
contracts. There is no source-ROM argument or extracted-game input. Asar
assembles original `norom` components into new `.bin` files. Python combines
them in memory with authored fixtures, starting from the literal eight-MiB
all-`$FF` image. Both intent validation and the complete image audit pass
through explicit APIs in `tools/validate_rom_write_intents.py` before the first
cartridge write. The builder repeats those checks at the write boundary.

## Source and storage contract

The [separate strict guard](../tools/original_snes_diagnostic_write_contract_v1.py)
accepts only its original-diagnostic schema, private mode and exact blank
source, SHA-256
`9f9b02f5ee6cbef5e018c1ee424095fc21a842ea6968c0d36114b5930dab2ba1`.
It rejects canonical/inert images, production modes, caller catalogs,
unknown fields and any undeclared changed byte. The existing guard module's
AST is identical after removing only the two added wrapper functions. Its
production hook and allocation catalogs remain empty.

Each of seven original diagnostic sections has an exact start, bounded
extent, source identities, preimage/replacement hashes, owner and payload
kind. The observed built extents are:

| Original section | File start | Bytes | Role |
| --- | --- | ---: | --- |
| Boot | `$008000` | 290 | Original reset, idle loop, handlers and observation tails |
| Header | `$00FFC0` | 64 | Original title, fixed cartridge fields and vectors |
| Boot mirror | `$408000` | 290 | Exact boot bytes under the low-bank ExHiROM mapping |
| Header mirror | `$40FFC0` | 64 | Exact header copy |
| Helper | `$410000` | 577 | Separately relocated, unchanged original v2 include |
| Package fixtures | `$420000` | 897 | Four original descriptor/terminal packages and declared fill |
| Immutable registry | `$430000` | 1,280 | Sixteen bindings plus sixteen direct-target arrays |

The audit proves all 2,655 changed bytes belong to these sections and all
remaining bytes equal the blank source. Both mirrors agree exactly. It checks
the original 21-byte title `EPOCH PACKAGE TEST   `, map `$35`, cartridge type
`$02`, ROM/SRAM size codes `$0D/$03`, country/license/version `$01/$33/$00`,
checksum/complement and full-image checksum. Every vector lies within the
actual boot extent. The builder chooses reset `$008000`, NMI `$008080`, IRQ
`$008090` and an original trap at `$0080A0`; the runtime must prove their
behavior separately.

Output must be a new file in a new run directory under `private/test_runs/`.
Checks reject traversal, filesystem aliases, reserved Windows device names,
`CONIN$`/`CONOUT$`, spaces before device-name extensions, trailing dots/spaces,
invalid characters and existing files. Source reads are bounded, regular and
unaliasable. The builder rechecks paths and creates final artifacts exclusively;
it never overwrites a prior artifact. These are ordinary filesystem checks,
not a claim of protection against a hostile kernel or concurrent filesystem
replacement between system calls.

## Original packages and code placement

The [fixture builder](../tools/original_snes_package_fixtures_v1.py) authors four
terminal-only packages at synthetic selectors `$80-$83`. Their primary and
alternate masks include full sixteen-owner transport, sparse positions, and
one empty branch in each direction. Shared pointers retain their aliases.
The immutable registry contains those four exact bindings and twelve zero,
unbound records. Every target array has only the descriptor's distinct direct
entrypoints, followed by zero reserve bytes.

All four packages pass the existing interpreter-pinned command policy: both
masks, every direct/shared entrypoint, exact disjoint named spans, complete
token ownership and terminal `$00`. Decoded `$1E` remains forbidden. The
certificate separately pins the policy source/reference and its transitive
grammar/adapter identities; those are certification dependencies, not payload
sources. All 256 branch bytes per binding produce the expected transport in
the host model. None of the streams supplies action effects or independently
completes the game's paired animation/effect latch contract.

The original [v2 helper](schala_package_helper_v2_stack.md) is included without
source changes, assembled at `$410000` with immutable registry `$430000`,
targets `$430100`, and original tails `$008100/$008110/$008120`. The separate
entry bridge at `$008060` transfers to the helper. This 577-byte assembly has
SHA-256 `7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b`.
The 290-byte boot component has SHA-256
`785fbd007bcfe71e802a32ac69fce5dfc169c7c7045812b3a2b54fc5e5eed1e5`.
The new placement does not inherit the v2 synthetic WRAM execution proof.

## Review, history and reproduction

Independent review preceded the first image write. It covered the guard,
legacy-AST equivalence, original raw assembly, fixture certificates, registry
transport, headers, paths and writer ordering. All 43 focused tests pass:
eight builder/fixture tests, nineteen diagnostic-guard tests and sixteen
legacy-guard regressions.

Review found and fixed Windows path aliases, preparation commands that omitted
`--prepare-only`, completion metadata that initially hashed intended SRAM
instead of rereading its written bytes, and missing direct policy-source and
post-assembly Asar identities. Asar's exact 501,248-byte executable is checked
before and after assembly and before the image write. Fixtures/certificates
are regenerated at that boundary. Final completion rereads both actual image
and SRAM. No cartridge was written before these fixes and review passed.

The first two preparation-only runs are preserved as historical source
revisions. The independent final preparation, `review_prepare3`, retains all
six exact original source snapshots and reconstructs entirely in memory.
None contains a ROM, SRAM or completion receipt. The actual `build1` and
`build2` directories contain identical ROM/SRAM/component bytes, their own
pre-write audited receipts, and completed observed-hash receipts. Their
path-bearing manifest identities remain distinct rather than being forced
into an artificial identical-manifest claim.

The zero 8,192-byte SRAM has SHA-256
`9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47`.
All exact identities and historical scopes are in the
[metadata reference](../references/original_snes_package_cartridge_v1.json).

```powershell
python -B -m unittest discover -s tests -p test_original_snes_package_cartridge_v1.py
python -B -m unittest discover -s tests -p test_original_snes_diagnostic_write_contract_v1.py
python -B -m unittest discover -s tests -p test_rom_write_intent_guard.py
python -B tools/build_original_snes_package_cartridge_v1.py --output-dir private/test_runs/original_package_NEW_UNIQUE --prepare-only
python -B tools/build_original_snes_package_cartridge_v1.py --output-dir private/test_runs/original_package_NEW_BUILD
python -B tools/collect_original_snes_package_cartridge_evidence_v1.py
```

The read-only collector rehashes both actual builds, checks exact source
snapshots, regenerates fixtures and reconstructs each image in memory. The
write-time guard deliberately refuses an already existing output. Therefore
the read-only reaudit declares a distinct, never-created replay output path,
and explicitly verifies that only this path and its manifest hash differ
from the historical intent/audit. No image or directory is created by the
collector. This keeps overwrite refusal intact while proving the existing
bytes again.

The next experiment must observe actual helper execution in ROM, immutable
registry and descriptor CPU reads, exact publications, final context, stack
lifetimes and full WRAM differences in a separately numbered native matrix.
Original interrupt scheduling, real-game NMI closure, cancellation, named game
placement, auxiliary readers and eighth-character integration remain distinct.
