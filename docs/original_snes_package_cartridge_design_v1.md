# Original package-test cartridge: guard and implementation design

Status: implemented and independently reviewed, 2026-09-08, during the six-hour
continuation. Two private builds now reproduce identical original image bytes
after both intent and complete-diff audits. The
[build report](original_snes_package_cartridge_v1.md) and
[metadata reference](../references/original_snes_package_cartridge_v1.json)
record `verified-static` evidence. The proposed runtime experiments below
remain separate gates; this build result proves no native execution.

The remaining transport experiment should execute the original stack helper
from ROM and read an immutable ROM registry. The current v1/v2 experiments
execute helper code in synthetic WRAM and reuse an unchanged original SHA
benchmark. Those completed or in-progress experiments retain their exact
inputs and scope. They must not be repurposed silently.

## Separate original-image contract

Add an explicitly named original-diagnostic API to
`tools/validate_rom_write_intents.py`. Keep the existing canonical/inert
`validate_manifest` and `audit_images` source kinds, classifications, trusted
catalog defaults, and behavior unchanged. In particular, both production
catalogs remain empty. The new API must not accept a Chrono Trigger source
image, an inert game scaffold, or a production build mode.

The new read-only contract will accept only the exact eight-MiB all-`$FF`
image, SHA-256
`9f9b02f5ee6cbef5e018c1ee424095fc21a842ea6968c0d36114b5930dab2ba1`.
That image is a literal original diagnostic starting state. This is a new
guarded source contract, not an exception to the complete-diff requirement.

Use a separate strict manifest schema and a private-only build mode. Every
section must have its fixed diagnostic ID, exact start, bounded size, owner,
payload kind, original-source identities, preimage hash and replacement hash.
Caller-provided production allocation/hook catalogs are forbidden. These
test sections never confer ownership in a game image.

Proposed half-open capacities:

| Diagnostic section | File span | Purpose |
| --- | --- | --- |
| Original boot and interrupt code | `$008000-$009000` | Original reset, NMI/IRQ/trap handlers and observed route tails |
| Exact boot mirror | `$408000-$409000` | Same bytes under ExHiROM low-bank mapping |
| Header and vectors | `$00FFC0-$010000` | Exact 64-byte original cartridge header |
| Exact header mirror | `$40FFC0-$410000` | Same header bytes |
| Original helper code | `$410000-$414000` | Relocated original v2 include, executed from ROM |
| Authored descriptor/stream fixtures | `$420000-$422000` | Deliberate direct-stream packages with source-defined spans |
| Immutable diagnostic registry/targets | `$430000-$430800` | Sixteen 16-byte bindings and sixteen 64-byte target sets |

The full-image audit must verify the pinned blank source, target identity,
all section preimages/replacements, nonoverlap, exact mirrored content,
original title/map/ROM/SRAM fields, vectors within the actual boot section,
both checksum/complement pairs, and every changed byte. Everything outside
the declared sections remains `$FF`. Output is restricted to a new path
under ignored `private/test_runs/`; the builder must also enforce canonical
filesystem containment and refuse existing outputs.

## Build without writing an unaudited ROM

Assemble source components as raw `norom` binaries, as the current native
helper harness already does. Never ask Asar to mutate a cartridge image.
Construct the target only in memory from the literal blank source and named
component bytes, finalize the original headers there, then run both strict
intent validation and the complete image audit through the new guard API.
Write the private `.sfc` only after both succeed. Preserve source/component,
tool, manifest, final-image, and zero-SRAM hashes plus reproduction commands.
No game ROM, extracted game bytes, or source ROM path is an input.

The original v2 helper already qualifies its registry and target reads with
long addresses. A separately assembled diagnostic can therefore bind
`PE_PH2_BINDINGS=$430000` and `PE_PH2_TARGETS=$430100`, while retaining the
existing source-bank acceptance of `$41/$42`. This is a new assembly identity
and runtime experiment. It does not inherit v2's WRAM-registry evidence.

Author the descriptor and flat direct stream bytes deliberately. Their
transport target lists must be derived from the same decoded package
certificate, with exact disjoint section bounds, both masks, complete token
ownership, and terminal `$00`. A numeric selector `$80` exists only inside
this diagnostic. The game still has no production high-selector binding.

## Review and execution gates

First add adversarial guard tests proving rejection of canonical/inert
sources, a production mode, changed or oversized sections, overlaps,
uncovered changes, mirrored-byte damage, invalid vectors/checksums, path
escapes, unexpected fields, and stale hashes. Run the existing canonical
write-guard tests as regressions. Independently review the new API and builder
before generating the first cartridge. Any rejection remains a failure;
there is no bypass flag or fallback writer.

Then run a separately scoped Mesen matrix that observes every helper PC,
actual immutable ROM-registry/descriptor read, exact publication, live stack
access, final CPU state, and full WRAM difference. Original interrupt fixtures
and their scheduling retain separate evidence. The existing game-handler
closure, production placement, cancellation, auxiliary readers, and PC `$07`
integration remain outstanding even if this original-cartridge matrix passes.
