"""Fixed private first-Attack image contract; read-only, nonproduction namespace.

API: build_manifest(source, target, output), validate_manifest(manifest), and
audit_images(manifest, source, target), all with optional workspace_root. The
source is the exact inert scaffold, never a caller-approved cartridge. There
are 34 fixed sections: the twelve field sections, sixteen battle hooks, five
learned-state operand relocations, and one original 215-byte allocation.
output_path requires a fresh destination; audits may re-read an existing exact
target. The builder owns exclusive directory/file creation. No function writes.

The pinned field contract supplies its unchanged strict type/path primitives.
No hook/allocation catalog argument exists; production catalogs stay empty.
Native entry/stack/interrupt/whole-span admission belongs to the collector.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path, PurePosixPath
import stat

import pc07_private_expanded_write_contract_v1 as field
import schala_rom_scaffold as scaffold

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-private-pc07-first-attack-intents-v1"
MODE = "private-pc07-first-ordinary-attack-diagnostic"
OWNER = "project-epoch-private-pc07-first-attack-v1"
SIZE = 0x800000
SOURCE_SHA256 = "26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93"
PRIOR_FIELD_SHA256 = "cb33610be9adceaf12298a820e63c9a2aedaf32fb5b231ef54a8b14caa3cd51c"
TARGET_SHA256 = "6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa"
TARGET_CHECKSUM = 0x4D6E
TARGET_HEADER_PAIR = bytes.fromhex("91b26e4d")
BATTLE_START = 0x410100
BATTLE_SIZE = 215
BATTLE_SHA256 = "39410b2ccdc09a9ad3667f363d7358bf91f552ee20d145d33c8cfc3c76a9849b"
BATTLE_BYTE_SUM = 23694
BATTLE_SOURCE = "asm/pc07_first_attack_adapters_v1.asm"

# id, CPU PC, exact whole-instruction preimage, immutable helper entry, tail.
HOOKS = (
    ("setup-map-publication", 0xFDB298, "a88a99beb1", 0x410100, "ea"),
    ("empty-single-tech", 0xC1C975, "bdffaec9ff", 0x410110, "ea"),
    ("empty-dual-tech", 0xC1CA29, "bdffaec9ff", 0x410110, "ea"),
    ("empty-triple-tech", 0xC1CCDA, "bdffaec9ff", 0x410110, "ea"),
    ("weapon-owner", 0xFDAF55, "9f4c1c00", 0x41011C, ""),
    ("battle-name", 0xCCE616, "bf46f8cc", 0x410031, ""),
    ("battle-graphics-indices", 0xCCE980, "b980290a4818798029aa", 0x41014B, "488aeaeaeaea"),
    ("initial-turn-slot", 0xC18050, "bdbeb11a", 0x410161, ""),
    ("attack-action", 0xC1BFFF, "bf8325cc", 0x410043, ""),
    ("attack-first-participant", 0xC1D55E, "bf9f24cc", 0x410172, ""),
    ("effect-actor-slot", 0xC1D605, "bdbeb1c9ff", 0x4101B3, "ea"),
    ("mp-actor-slot", 0xC1D760, "bdbeb1aa", 0x4101C6, ""),
    ("attack-approach", 0xC14A44, "bf3cf6cc", 0x410055, ""),
    ("attack-normal-selector", 0xC143C4, "bf0040cd", 0x410067, ""),
    ("attack-path-selector", 0xC143F8, "bf0740cd", 0x410079, ""),
    ("attack-critical-selector", 0xC1438B, "bf0e40cd", 0x41008B, ""),
)
LEARNED_PATCHES = (
    (0x01C9A9, "bd3728", "bda72c"), (0x01CA56, "bd3e28", "bdae2c"),
    (0x01CB26, "bd3e28", "bdae2c"), (0x01CD08, "bd4d28", "bdbd2c"),
    (0x01CDEE, "bd4d28", "bdbd2c"),
)
SOURCE_PINS = field.SOURCE_PINS + (
    ("tools/pc07_private_expanded_write_contract_v1.py", 15819,
     "b8bb7cec02a5041658922a842cc29a086e45edeef82d12059f436d794e39f376"),
    (BATTLE_SOURCE, 5190, "290d3335b0c4143895a5804ed1b20273108f6fc231859ff08733e1af9a33fbd1"),
    ("private/research/pc07_battle_adapters_20261013/assembled_hook_manifest_v1.json", 38556,
     "ea41d24c92de9757093c8c4874672a7efa06a696adf733b9094976987883addb"),
    ("private/research/pc07_battle_adapters_20261013/span_semantics_audit_v1.json", 4446,
     "23aa9fac0322af0ea71b681d7aa8b99b76790eeca1e8325852f9e3627cfaa8e5"),
    ("private/research/pc07_battle_adapters_20261013/claude_disposition_v1.txt", 6987,
     "b61185bad2b57a08e8cb2ec242fdf310f4797178d8bc5e34a34dd1e4e2405742"),
    ("references/ct_disassembly/bank_C1.asm", 2768817,
     "298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa"),
    ("references/ct_disassembly/bank_CC.asm", 290190,
     "d60669a2de45ce888298b5d1e4a88739173bb707a8293ddadbeffb2eeab2eb7d"),
    ("references/ct_disassembly/bank_FD.asm", 691286,
     "0f8a0d59e97de7d60945fdfef1b614217e3d673cca1e14f543234d789a87779e"),
)
ALLOCATIONS = (
    {"id": "pc07-private-field-and-donor-readers-v2", "file_start": 0x410000,
     "snes_start": 0x410000, "size": 157, "sha256": field.HELPER_SHA256,
     "source": "asm/pc07_donor_read_adapters_v2.asm", "production_approval": False},
    {"id": "pc07-private-first-attack-adapters-v1", "file_start": BATTLE_START,
     "snes_start": BATTLE_START, "size": BATTLE_SIZE, "sha256": BATTLE_SHA256,
     "source": BATTLE_SOURCE, "production_approval": False},
)
CONTEXT = {
    "purpose": "private fixed-slot2 first ordinary-Attack diagnostic only",
    "evidence_level": "source-validated-private-diagnostic",
    "accepted_field_reconstruction_sha256": PRIOR_FIELD_SHA256,
    "battle_entry_abi": {"E": 0, "M_flag": 1, "X_flag": 0, "D": 0,
                         "DBR": 0x7E, "hidden_B": 0, "decimal_flag": 0},
    "party_slots": [0, 1, 7], "candidate_slot": 2,
    "field_helper_keeps_separate_existing_abi": True,
    "requires_debugger_fixture_preparation": True,
    "requires_native_abi_and_span_observation": True,
    "production_approval": False, "playable_pc_proof": False,
    "game_allocation_proof": False, "runtime_proof": False,
    "computed_dispatch_closure": False, "weapon_plus4_live_consumer_proved": False,
}
PrivateFirstAttackIntentError = field.PrivateExpandedIntentError
fail, sha = field.fail, field.sha


def output_path(value, workspace_root=ROOT):
    return field.output_path(value, workspace_root)


def hook_manifest():
    return [{"id": name, "pc": pc, "file_offset": pc & 0x3FFFFF,
             "preimage_hex": old, "helper_entry": helper, "return_pc": pc + 4,
             "continuation_pc": pc + len(bytes.fromhex(old)),
             "replacement_hex": (b"\x22" + helper.to_bytes(3, "little") + bytes.fromhex(tail)).hex()}
            for name, pc, old, helper, tail in HOOKS]


def _fixed_spans():
    spans = [(name, start, old, TARGET_HEADER_PAIR if name in ("checksum", "checksum-mirror") else new, kind)
             for name, start, old, new, kind in field._fixed_spans()]
    for row in hook_manifest():
        spans.append((row["id"], row["file_offset"], bytes.fromhex(row["preimage_hex"]),
                      bytes.fromhex(row["replacement_hex"]), "private-battle-hook"))
    spans.extend((f"learned-{st:06x}", st, bytes.fromhex(old), bytes.fromhex(new), "canonical-operand-only")
                 for st, old, new in LEARNED_PATCHES)
    spans.append(("original-battle-component", BATTLE_START, b"\xff" * BATTLE_SIZE, None, "original-helper-component"))
    return sorted(spans, key=lambda row: row[1])


def _payload_digest(name, new):
    return sha(new) if new is not None else (BATTLE_SHA256 if name == "original-battle-component" else field.HELPER_SHA256)


def _template(output):
    return {"schema": SCHEMA, "build_mode": MODE,
            "source": {"kind": "pinned-inert-exhirom-scaffold", "size": SIZE, "sha256": SOURCE_SHA256},
            "target": {"size": SIZE, "sha256": TARGET_SHA256},
            "sources": [{"path": p, "size": n, "sha256": h,
                         "provenance": "pinned-private-diagnostic-source-context"} for p, n, h in SOURCE_PINS],
            "context": copy.deepcopy(CONTEXT), "allocations": copy.deepcopy(list(ALLOCATIONS)),
            "hooks": hook_manifest(), "sections": [
                {"id": name, "file_start": st, "size": len(old), "owner": OWNER,
                 "payload_kind": kind, "preimage_sha256": sha(old),
                 "replacement_sha256": _payload_digest(name, new)}
                for name, st, old, new, kind in _fixed_spans()], "output": output}


def _verify_sources(workspace_root):
    root = field._root(workspace_root)
    for relative, size, digest in SOURCE_PINS:
        path, info = field._inspect_path(root, PurePosixPath(relative).parts)
        if info is None or not stat.S_ISREG(info.st_mode):
            fail("source missing or nonregular: " + relative)
        with path.open("rb") as stream:
            data = stream.read(size + 1)
        if len(data) != size or sha(data) != digest:
            fail("source identity drift: " + relative)


def validate_manifest(manifest, *, workspace_root=ROOT):
    if type(manifest) is not dict or "output" not in manifest:
        fail("manifest: exact fields required")
    field._exact(manifest, _template(manifest["output"]), "manifest")
    field._validate_destination(manifest["output"], manifest["target"], workspace_root)
    _verify_sources(workspace_root)
    return {"schema": SCHEMA, "status": "metadata-valid",
            "manifest_sha256": sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "source_artifacts_verified": True, "rom_modified": False,
            "production_approval": False, "playable_pc_proof": False,
            "game_allocation_proof": False, "runtime_proof": False}


def audit_images(manifest, source, target, *, workspace_root=ROOT):
    report = validate_manifest(manifest, workspace_root=workspace_root)
    if type(source) is not bytes or len(source) != SIZE or sha(source) != SOURCE_SHA256:
        fail("observed source is not the pinned inert scaffold")
    try:
        scaffold.validate_exhirom_scaffold(source)
    except ValueError as exc:
        fail("source scaffold invariants: " + str(exc))
    if type(target) is not bytes or len(target) != SIZE or sha(target) != TARGET_SHA256:
        fail("observed target identity mismatch")
    for row in hook_manifest():
        if scaffold.exhirom_snes_to_file(row["pc"]) != row["file_offset"]:
            fail("hook mapping mismatch")
    for allocation in ALLOCATIONS:
        for delta in (0, allocation["size"] - 1):
            if scaffold.exhirom_snes_to_file(allocation["snes_start"] + delta) != allocation["file_start"] + delta:
                fail("allocation mapping mismatch")
    if scaffold.exhirom_snes_to_file(0x00448D) is not None:
        fail("bank00 low half is not a ROM alias")
    counts, cursor = {}, 0
    for name, start, old, new, _ in _fixed_spans():
        end = start + len(old)
        if start < cursor or end > SIZE:
            fail("fixed section overlap or extent")
        if source[start:end] != old:
            fail("exact canonical/scaffold preimage mismatch: " + name)
        if target[cursor:start] != source[cursor:start]:
            fail("undeclared changes before " + name)
        payload = target[start:end]
        if new is None:
            expected_sum = BATTLE_BYTE_SUM if name == "original-battle-component" else field.HELPER_BYTE_SUM
            if sha(payload) != _payload_digest(name, None) or sum(payload) != expected_sum:
                fail("immutable component mismatch: " + name)
        elif payload != new:
            fail("exact replacement mismatch: " + name)
        counts[name] = sum(a != b for a, b in zip(old, payload, strict=True))
        cursor = end
    if target[cursor:] != source[cursor:]:
        fail("undeclared changes after final section")
    if len(counts) != 34:
        fail("fixed section count")
    compat = sum(counts[f"compat-{p:06x}"] for p, _, _ in field.COMPAT_PATCHES)
    learned = sum(counts[f"learned-{p:06x}"] for p, _, _ in LEARNED_PATCHES)
    if (compat, learned) != (14, 10):
        fail("fixed operand-change counts")
    if target[:0x10000] != target[0x400000:0x410000]:
        fail("full boot-bank mirror mismatch")
    checksum = sum(target) & 65535
    if checksum != TARGET_CHECKSUM:
        fail("target checksum mismatch")
    for offset in (0xFFDC, 0x40FFDC):
        pair = target[offset:offset + 4]
        if pair != TARGET_HEADER_PAIR or int.from_bytes(pair[:2], "little") ^ checksum != 65535 or int.from_bytes(pair[2:], "little") != checksum:
            fail("checksum/complement pair mismatch")
    # Revert only the new battle sections to reproduce the exact accepted field
    # image. This is a full-image identity check, not a caller assertion.
    previous = bytearray(target)
    for row in hook_manifest():
        start = row["file_offset"]
        previous[start:row["continuation_pc"] & 0x3FFFFF] = bytes.fromhex(row["preimage_hex"])
    for start, old, _ in LEARNED_PATCHES:
        previous[start:start + 3] = bytes.fromhex(old)
    previous[BATTLE_START:BATTLE_START + BATTLE_SIZE] = b"\xff" * BATTLE_SIZE
    for start in (0xFFDC, 0x40FFDC):
        previous[start:start + 4] = field.TARGET_HEADER_PAIR
    if sha(previous) != PRIOR_FIELD_SHA256:
        fail("accepted field reconstruction mismatch")
    return {**report, "status": "images-valid", "evidence_level": "verified-static-private-diagnostic",
            "source_sha256": sha(source), "target_sha256": sha(target),
            "changed_bytes_by_section": counts, "changed_byte_count": sum(counts.values()),
            "complete_diff_coverage": True, "source_scaffold_verified": True,
            "accepted_field_reconstruction_verified": True,
            "mapping_verified": True, "full_boot_mirror_verified": True,
            "checksum_verified": True, "compatibility_changed_bytes": compat + learned}


def build_manifest(source, target, output, *, workspace_root=ROOT):
    manifest = _template(output)
    audit_images(manifest, source, target, workspace_root=workspace_root)
    return manifest
