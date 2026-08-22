# Project Epoch ROM write-intent guard

Status: `verified-static` validator; current diagnostic builders integrated  
Tool: `tools/validate_rom_write_intents.py`  
Tests: `tests/test_rom_write_intent_guard.py`  
Last updated: 2026-07-26

Tool SHA-256:
`66448eee38a68e3fda2f4fde7c47e4c3988c8bab9fabd208ae5363b5df6fd6cd`  
Focused-test SHA-256:
`eae9a18c317f7fb096d22f33ed090d37a64e9e763b81e6519126698ed881ed94`

## Result

The write-intent guard is a deterministic, fail-closed boundary between
Project Epoch metadata and any future ROM-producing builder. It does not
modify a ROM, assemble code, allocate data, or approve PC `$07`.

The canonical four-megabyte ROM is unknown and denied by default. A write is
valid only when it is exactly one of:

1. a private, nonproduction diagnostic replacement with a named owner, pinned
   canonical source identity, exact span preimage hash, and exact replacement
   hash;
2. an exact instruction-span replacement bound to a trusted, proved hook
   catalog entry, including exact original bytes;
3. a write wholly contained by a trusted, named expanded allocation in the
   simple ExHiROM `$41-$7D` pool; or
4. an exact scaffold-managed header/checksum field. This is a structural
   exception, not general Project Epoch ownership.

Every other classification, unknown JSON field, unproved evidence label,
untrusted allocation/hook, overlapping intent, or undeclared changed byte is
rejected.

## Current evidence state

The source-controlled trusted production allocation and hook catalogs are
both deliberately empty:

```text
APPROVED_PRODUCTION_ALLOCATIONS = ()
APPROVED_PRODUCTION_HOOKS       = ()
```

This matches the current milestone. The suggested expanded bank ownership in
`docs/schala_rom_expansion_architecture.md` is still planning, not ownership,
and no production hook has completed the mandatory runtime matrix. Merely
adding `"approved"` to JSON cannot grant permission; submitted allocation
metadata must equal an entry in the trusted in-code catalog.

Tests inject synthetic trusted catalog entries to prove validation mechanics
without promoting a real allocation or hook.

## Protected ownership

The guard has two layers.

First, the entire canonical vanilla region is default-deny. Private exact
diagnostics and trusted instruction hooks are narrow exceptions; expanded
data cannot be placed there.

Second, hard protected ranges cannot be made writable by relabeling them:

- `EnemyRewardTable`, including retired `$CC:63F6-$CC:642F` “code space”;
- file `$0D400E`, shared by PC `$07` normal-attack indexing and Crono critical
  attack indexing;
- the null PC-name pointer entry 7 that preserves the separate Epoch naming
  path;
- the existing Epoch menu-portrait data and pointer;
- graphics, assembly, animation-boundary, auxiliary-animation, palette, and
  descriptor entries 7/8 that belong to sentinels or NPC actors;
- the complete file `$400000-$40FFFF` boot/low-bank mirror, except the exact
  scaffold-managed header fields; and
- the noncanonical file `$7E0000-$7FFFFF` tail.

The guard validates ROM ranges. It does not by itself prove runtime WRAM
destinations. In particular, a future hook review must still prove that
Schala naming never writes Epoch’s `$7E2C4D-$7E2C52` name field.

The corresponding non-ROM deny contract remains:

- `$7E2830-$7E287F` is vanilla compatibility/tech state until its complete
  relocation is proved;
- `$7E2CA0-$7E2CEF` is only a relocation candidate, not declared free;
- save-slot `$0430-$047F` retains its vanilla meanings and `$0480` is not an
  approved eighth record;
- SRAM `$30:7E00-$30:7FDF` is only a gated sidecar candidate, while
  `$30:7FE0-$30:7FFF` is vanilla global metadata; and
- logical ID `$07` never grants ownership of graphics, portrait, name, save,
  WRAM, or SRAM index 7.

Because the trusted production hook catalog is empty, no current accepted ROM
write can install code that mutates any of those destinations.

## No in-place table extension

Known vanilla table envelopes are explicit metadata. A private table
diagnostic must name one and stay wholly inside it. A trusted instruction hook
may not overlap a known data table. Production table payloads therefore have
one legal home: a named expanded allocation with adapted readers.

This rejects the recurring unsafe pattern of appending a record after a table:

- an eighth `$50` record after `CharInitData` would overwrite starting tech
  state;
- command/target/property/MP tables have differently owned data immediately
  after their documented ends;
- basic-action, HP, MP, and TP rows likewise cannot grow in place.

An exact preimage does not turn adjacent data into free space.

## Strict manifest shape

Schema version 1 requires:

```json
{
  "schema_version": 1,
  "manifest_id": "stable-lowercase-id",
  "build_mode": "production",
  "source_kind": "project-epoch-inert-exhirom-8mib",
  "source_size": 8388608,
  "source_sha256": "<pinned inert scaffold sha256>",
  "target_size": 8388608,
  "target_sha256": "<complete target sha256>",
  "output_path": null,
  "allocations": [],
  "writes": []
}
```

Production manifests must start from the pinned inert ExHiROM scaffold. They
must not name a full-ROM output path. Private diagnostics must start from the
pinned canonical US Rev0 source and name a normalized `.sfc` or `.smc` path
below `private/`.

Each write record includes:

```text
write_id
classification
file_start / size
owner
payload_kind
evidence
preimage_sha256 / replacement_sha256
allocation_id | hook_id | table_id | header_field_id
replacement_hex (exact hooks only)
```

Unused binding fields are JSON `null`. Lists must be sorted so the canonical
manifest hash is stable. Unknown fields are errors rather than ignored
forward-compatibility guesses.

## Read-only artifact audit

Metadata validation proves that the declaration is internally legal. The
stronger API also compares already-existing images:

```python
report = audit_images(manifest, source_bytes, target_bytes)
```

It verifies:

- full source and target size/hash identity;
- every declared span’s complete preimage and replacement SHA-256;
- every changed byte belongs to exactly one declared, nonoverlapping span;
- every declared span actually changes at least one byte; and
- there are no undeclared differences;
- managed map-mode/ROM-size fields retain the required ExHiROM values; and
- managed checksum/complement pairs are internally valid and match the whole
  target image.

The CLI is read-only:

```powershell
python tools/validate_rom_write_intents.py manifest.json
python tools/validate_rom_write_intents.py manifest.json `
  --source private/path/source.sfc `
  --target private/path/target.sfc
```

It prints a deterministic JSON report and writes nothing.

The focused tests also audit the existing private Schala-over-Lucca smoke
against its real source/target images when those ignored files exist. The
smoke builder now invokes `audit_images` before it may write its private ROM
and embeds both the strict intent manifest and audit report in its diagnostic
manifest. This integration does not make the diagnostic production-safe: it
still replaces explicitly named Lucca-owned data and is rejected as a
production build.

The Lucca-to-Magus clone builder also runs the guard. Its static mode passes
only as a nonproduction, exact-preimage replacement of named Lucca-owned
tables and assets. Its preserved provisional runtime mode is required to
receive `expected-rejected-retired-unsafe` because it overlaps the protected
`EnemyRewardTable`; that mode remains explicit opt-in and cannot become a
production input.

## Integration gate

Every future ROM-writing builder should:

1. construct the strict manifest before applying any write;
2. validate it against source-controlled trusted catalogs;
3. assert each preimage immediately before writing;
4. build only in ignored private space;
5. invoke `audit_images` on the completed artifact;
6. refuse patch generation unless complete diff coverage passes; and
7. emit the guard report, tool hash, manifest hash, source/target hashes,
   reproduction command, and evidence level.

The private Schala supported-slot smoke and the Lucca-to-Magus diagnostic are
integrated. Production builders remain unimplemented, and both trusted
production catalogs remain empty.

## Evidence boundary

`verified-static`:

- strict manifest parsing and deterministic hashing;
- canonical default-deny behavior;
- exact diagnostic, hook, allocation, and header rules;
- protected-range and in-place-table-extension rejection;
- complete read-only diff coverage and exact preimage checking; and
- current catalogs containing no approved production data writes or hooks.

Not proved:

- any production allocation or hook;
- assembler output or BPS reproducibility;
- runtime safety of any future hook;
- SRAM/WRAM destination safety; or
- a playable Schala PC `$07`.
