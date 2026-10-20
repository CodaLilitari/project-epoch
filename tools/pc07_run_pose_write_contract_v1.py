"""Private, fixed eight-byte normal-run remap on the accepted V5 image.

No graphics are replaced. One current-source snapshot, two shared guard APIs,
and a complete image diff replace recursive historical build validation.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-private-pc07-run-pose-intents-v1"
SIZE = 0x800000
SOURCE = {"path": "private/test_runs/pc07_worldmap_coda_v5_v1/diagnostic.sfc",
          "bytes": SIZE, "sha256": "ec7e5c089116c37510aea2bacc7a82c4131432eef414bdb8f6ef89723d6c6724"}
PARENT = {"path": "private/test_runs/pc07_worldmap_coda_v5_v1/receipt.json",
          "bytes": 16669, "sha256": "331f30de9e1e3ef6b3dffbc547e3e7e4e52525685b804c5e2eca941a5fa6a576"}
PRIMARY = 0x424000
TIMING = 0x425100
STRIDE = 0x404
# Existing directional walking poses, not newly authored running art.
PAIRS = (("up", (4, 6)), ("down", (8, 10)),
         ("left", (12, 13)), ("right", (14, 15)))
NPC_SPANS = (
    ("npc_descriptor_table", 0x24F023, 0x24F523),
    ("npc09_descriptor", 0x24F050, 0x24F055),
    ("npcCD_descriptor", 0x24F424, 0x24F429),
    ("graphics26_pointer", 0x242072, 0x242075),
    ("graphics26_compressed_packet", 0x19E2CE, 0x19EC5D),
    ("assembly1B_boundary_pair", 0x242351, 0x242357),
    ("assembly1B_payload", 0x1E2B48, 0x1E2EE0),
    ("animation3B_primary_boundary_pair", 0x242676, 0x24267A),
    ("animation3B_primary", 0x2467A0, 0x246830),
    ("animation3B_timing_boundary_pair", 0x242876, 0x24287A),
    ("animation3B_timing", 0x24BC38, 0x24BC5C),
    ("npc09_palette80", 0x240C00, 0x240C18),
    ("npcCD_palette9F", 0x240EE8, 0x240F00),
)
_ACTIVE = None


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def resolve(relative):
    need(type(relative) is str and re.fullmatch(r"[A-Za-z0-9_./-]+", relative), "canonical project path")
    need(all(part not in ("", ".", "..") for part in relative.split("/")), "path traversal refused")
    result = ROOT / relative
    for part in (result, *result.parents):
        need(not part.is_symlink() and not (part.exists() and getattr(part.stat(), "st_file_attributes", 0) & 0x400),
             "aliased project path refused")
    need(result.resolve().is_relative_to(ROOT.resolve()), "outside project")
    return result


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r"private/test_runs/pc07_run_pose_[A-Za-z0-9_-]+/diagnostic\.sfc", relative),
         "fresh private run-pose destination required")
    return resolve(relative)


def read_pin(row):
    raw = resolve(row["path"]).read_bytes()
    need(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "input drift: " + row["path"])
    return raw


def tokens(block, selector, terminator):
    start = selector * 4
    need(start + 8 <= len(block), "initial eight-byte read outside provider")
    end = block.find(bytes([terminator]), start)
    need(end >= start, "unterminated animation")
    return block[start:end]


def derive(source):
    need(type(source) is bytes and len(source) == SIZE, "eight-MiB source")
    need(source[:0x10000] == source[0x400000:0x410000], "inherited boot mirror")
    target = bytearray(source)
    for facing, (_, pair) in enumerate(PAIRS):
        start = PRIMARY + facing * STRIDE + 0x18
        need(source[start:start + 3] == bytes((19, 20, 255)), "fixed run preimage")
        target[start:start + 2] = bytes(pair)
    need(source[TIMING + 0x18:TIMING + 0x1B] == bytes((10, 10, 0)), "shared run timing preimage")
    checksum = sum(target) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    for start in (0xFFDC, 0x40FFDC):
        target[start:start + 4] = pair
    need(sum(target) & 0xFFFF == checksum and target[:0x10000] == target[0x400000:0x410000], "checksum/mirror")
    return bytes(target)


def stream_audit(source, target):
    timing = source[TIMING:TIMING + STRIDE]
    need(timing == target[TIMING:TIMING + STRIDE], "timing must remain unchanged")
    count = 0
    for facing, (_, pair) in enumerate(PAIRS):
        start = PRIMARY + facing * STRIDE
        old = source[start:start + STRIDE]
        new = target[start:start + STRIDE]
        for selector in range(256):
            before = tokens(old, selector, 255)
            after = tokens(new, selector, 255)
            delays = tokens(timing, selector, 0)
            # Existing selector02 starts on the walk terminator: an empty
            # primary/timing suffix is preserved, not rejected or filled in.
            need(len(after) == len(delays) and all(v < 23 for v in after), "frame/timing validity")
            if selector == 6:
                need(before == bytes((19, 20)) and after == bytes(pair) and delays == bytes((10, 10)), "exact run role")
            else:
                need(before == after, "another selector's reached tokens changed")
            count += 1
    return {"entrypoints_checked": count, "changed_selectors": [6], "unchanged_selectors_per_facing": 255,
            "timing_unchanged": True, "assembly_frame_count": 23,
            "evidence_level": "static-stream-reachability-not-native-consumer-proof"}


@contextmanager
def source_snapshot():
    global _ACTIVE
    need(_ACTIVE is None, "nested snapshot refused")
    source = read_pin(SOURCE)
    parent = json.loads(read_pin(PARENT))
    need(parent["emitted"] is True and parent["target_sha256"] == SOURCE["sha256"]
         and parent["artifacts"]["diagnostic.sfc"] == SOURCE, "accepted immediate parent binding")
    need(parent["current_shared_intent"]["status"] == "metadata-valid"
         and parent["current_shared_diff"]["status"] == "images-valid"
         and parent["current_shared_diff"]["complete_diff_coverage"] is True, "accepted parent construction")
    target = derive(source)
    _ACTIVE = {"source": source, "target": target, "target_sha256": sha(target),
               "streams": stream_audit(source, target)}
    try:
        yield _ACTIVE
    finally:
        _ACTIVE = None


def inputs():
    need(_ACTIVE is not None, "one active current-operation snapshot required")
    return _ACTIVE


def template(output):
    output_path(output)
    snap = inputs()
    spans = [("checksum-primary", 0xFFDC, 4), ("checksum-mirror", 0x40FFDC, 4)]
    spans += [("pc07-primary-run-" + name, PRIMARY + i * STRIDE + 0x18, 2)
              for i, (name, _) in enumerate(PAIRS)]
    rows = []
    for name, start, size in spans:
        before = snap["source"][start:start + size]
        after = snap["target"][start:start + size]
        rows.append({"id": name, "file_start": start, "bytes": size,
                     "preimage_sha256": sha(before), "target_sha256": sha(after)})
    return {"schema": SCHEMA, "source": SOURCE, "accepted_parent_receipt": PARENT,
            "target": {"bytes": SIZE, "sha256": snap["target_sha256"]}, "output": output,
            "sections": rows, "stream_audit": snap["streams"], "new_graphics": False,
            "new_allocations": False, "production_approval": False, "native_execution": False,
            "evidence_level": "guarded-private-static-run-remap"}


def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest) == encoded(template(manifest.get("output"))), "fixed run manifest")
    return {"status": "metadata-valid", "schema": SCHEMA, "manifest_sha256": sha(encoded(manifest)),
            "production_approval": False}


def audit_images(manifest, source, target):
    validate_manifest(manifest)
    snap = inputs()
    need(type(source) is bytes and source == snap["source"], "exact accepted source")
    need(type(target) is bytes and target == snap["target"], "exact run-remapped target")
    cursor = changed = 0
    inverse = bytearray(target)
    for row in manifest["sections"]:
        start, end = row["file_start"], row["file_start"] + row["bytes"]
        need(start >= cursor and source[cursor:start] == target[cursor:start], "undeclared image change")
        changed += sum(a != b for a, b in zip(source[start:end], target[start:end]))
        inverse[start:end] = source[start:end]
        cursor = end
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, "complete diff and inverse")
    for name, start, end in NPC_SPANS:
        need(source[start:end] == target[start:end], "original NPC bytes changed: " + name)
    return {"status": "images-valid", "schema": SCHEMA, "declared_sections": 6,
            "changed_bytes": changed, "primary_frame_references_changed": 8,
            "complete_diff_coverage": True, "inverse_restores_parent": True,
            "npc_protected_spans_unchanged": len(NPC_SPANS), "shared_palette_unchanged": True,
            "graphics_and_assembly_unchanged": True, "worldmap_unchanged": True,
            "production_approval": False, "native_execution": False}
