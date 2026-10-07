"""Read-only contract for one private PC07 native field-helper diagnostic.

This is a separate fixed namespace, not a production catalog or an approval API.
Only the pinned inert ExHiROM scaffold and the twelve exact sections below are
accepted. The component contains other source-owned routines, but this image
installs only the field hook. No playable-PC, game-allocation or runtime proof is
implied. No function here writes an image, creates a directory, or assembles code.

API:
    build_manifest(source, target, output, *, workspace_root=ROOT) -> dict
    validate_manifest(manifest, *, workspace_root=ROOT) -> metadata receipt
    audit_images(manifest, source, target, *, workspace_root=ROOT) -> diff receipt

Images must be bytes. Metadata has exact fields and literal source identities.
Validation reads source artifacts and checks filesystem paths without modifying
them. A preexisting destination must be regular and match the manifest target
exactly, permitting read-only re-audit. output_path separately requires a fresh
destination for creation. The builder must create its run directory exclusively,
may assemble there first, and must revalidate before exclusive image emission.
A path check does not reserve a name or eliminate a later filesystem race.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

import schala_rom_scaffold as scaffold

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-private-pc07-expanded-field-intents-v1"
MODE = "private-pc07-native-field-diagnostic"
OWNER = "project-epoch-private-pc07-field-helper-v1"
SIZE = 0x800000
SCAFFOLD_SHA256 = "26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93"
HELPER_START = 0x410000
HELPER_SIZE = 157
HELPER_SHA256 = "315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7"
HELPER_BYTE_SUM = 15951
SOURCE_CHECKSUM = 0x396E
SOURCE_HEADER_PAIR = bytes.fromhex("91c66e39")
FIELD_PREIMAGE = bytes.fromhex("8d0242c8a905")
FIELD_REPLACEMENT = bytes.fromhex("22000041eaea")

# Complete instruction spans; exactly two operand bytes change at each site.
COMPAT_PATCHES = (
    (0x0282E4, bytes.fromhex("9c5728"), bytes.fromhex("9cc72c")),
    (0x0282E7, bytes.fromhex("a25728"), bytes.fromhex("a2c72c")),
    (0x0282EA, bytes.fromhex("a05928"), bytes.fromhex("a0c92c")),
    (0x02830E, bytes.fromhex("99a927"), bytes.fromhex("99192c")),
    (0x02B9AF, bytes.fromhex("a25728"), bytes.fromhex("a2c72c")),
    (0x3FF86D, bytes.fromhex("bd3728"), bytes.fromhex("bda72c")),
    (0x3FF9A2, bytes.fromhex("393728"), bytes.fromhex("39a72c")),
)
_DELTA = (sum(sum(new) - sum(old) for _, old, new in COMPAT_PATCHES)
          + 2 * (sum(FIELD_REPLACEMENT) - sum(FIELD_PREIMAGE))
          + HELPER_BYTE_SUM - HELPER_SIZE * 255)
TARGET_CHECKSUM = (SOURCE_CHECKSUM + _DELTA) & 0xFFFF
TARGET_HEADER_PAIR = ((TARGET_CHECKSUM ^ 0xFFFF).to_bytes(2, "little")
                      + TARGET_CHECKSUM.to_bytes(2, "little"))

# These literal identities cannot be supplied or replaced by a caller catalog.
SOURCE_PINS = (
    ("asm/pc07_donor_read_adapters_v2.asm", 2541,
     "df0584a820d3b6b4994298cc1f0d6b3ffc4089797b42c5d6c6217d02a4e5a914"),
    ("private/test_runs/pc07_donor_native_source_v2/source_review.json", 4571,
     "5b1ea5cff78b79f2f1a12a008e6731873eb20adb9535012bf482f540e484c7ca"),
    ("references/ct_disassembly/bank_C0.asm", 2800445,
     "b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8"),
    ("tools/schala_compat_menu_v1.py", 7734,
     "4b679c79791a8d2ec879f2f9e1e5ad5b46bb4655f59c7d00d217cc3613c35f59"),
    ("tools/schala_rom_scaffold.py", 13386,
     "a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a"),
)
CONTEXT = {
    "purpose": "private native field-helper diagnostic only",
    "evidence_level": "source-validated-private-diagnostic",
    "hook_snes": 0xC0448D,
    "helper_entry_snes": 0x410000,
    "hook_return_snes": 0xC04491,
    "original_continuation_snes": 0xC04493,
    "component_provenance": "reviewed-original-project-source",
    "production_approval": False,
    "playable_pc_proof": False,
    "game_allocation_proof": False,
    "runtime_proof": False,
}


class PrivateExpandedIntentError(ValueError):
    """The fixed private expanded-image contract was rejected."""


def fail(message):
    raise PrivateExpandedIntentError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _exact(value, expected, context):
    """Typed equality: bools, floats, tuples and unknown keys cannot alias JSON."""
    if type(value) is not type(expected):
        fail(context + ": exact type required")
    if type(expected) is dict:
        if set(value) != set(expected):
            fail(context + ": exact fields required")
        for key in expected:
            _exact(value[key], expected[key], context + "." + key)
    elif type(expected) is list:
        if len(value) != len(expected):
            fail(context + ": exact list required")
        for index, item in enumerate(expected):
            _exact(value[index], item, f"{context}[{index}]")
    elif value != expected:
        fail(context + ": fixed value mismatch")


def _digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        fail("target: lowercase SHA-256 required")


def _root(workspace_root):
    try:
        lexical = Path(workspace_root).absolute()
        resolved = lexical.resolve(strict=True)
        if lexical != resolved or not resolved.is_dir():
            fail("workspace root must be an existing canonical directory")
        # Also reject an aliased ancestor of the supplied workspace root.
        for path in (lexical, *lexical.parents):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                fail("workspace root aliases are forbidden")
        return resolved
    except OSError as exc:
        fail("workspace root unavailable: " + str(exc))


def _inspect_path(root, parts):
    """Reject all existing symlink/reparse ancestors, including inward aliases."""
    current = root
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return current.joinpath(*parts[index + 1:]), None
        except OSError as exc:
            fail("path inspection failed: " + str(exc))
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            fail("filesystem aliases are forbidden")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            fail("path parent is not a directory")
    return current, info


def _output_candidate(value, workspace_root):
    if (type(value) is not str or "\\" in value or ":" in value
            or any(ord(c) < 32 for c in value)):
        fail("output: canonical relative POSIX path required")
    parts = value.split("/")
    if (len(parts) != 4 or parts[:2] != ["private", "test_runs"]
            or parts[-1] != "diagnostic.sfc"):
        fail("output: require private/test_runs/<run>/diagnostic.sfc")
    for part in parts:
        if (part in {"", ".", ".."} or part[-1:] in {".", " "}
                or any(c in '<>:"\\|?*' for c in part)
                or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])",
                                part.split(".")[0].rstrip(" "))):
            fail("output: reserved or aliasing path component")
    root = _root(workspace_root)
    path, info = _inspect_path(root, parts)
    if not path.resolve(strict=False).is_relative_to(root / "private" / "test_runs"):
        fail("output escaped private test runs")
    return path, info


def output_path(value, workspace_root=ROOT):
    """Require a fresh private/test_runs/<run>/diagnostic.sfc for creation."""
    path, info = _output_candidate(value, workspace_root)
    if info is not None:
        fail("output: existing destination is forbidden for creation")
    return path


def _validate_destination(value, target, workspace_root):
    path, info = _output_candidate(value, workspace_root)
    if info is None:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_size != SIZE:
        fail("output: existing target must be a regular file of exact target size")
    try:
        with path.open("rb") as stream:
            data = stream.read(SIZE + 1)
    except OSError as exc:
        fail("output: existing target unreadable: " + str(exc))
    if len(data) != SIZE or sha(data) != target["sha256"]:
        fail("output: existing target identity mismatch")


def _sources():
    return [{"path": path, "size": size, "sha256": digest,
             "provenance": "pinned-private-diagnostic-source-context"}
            for path, size, digest in SOURCE_PINS]


def _verify_sources(workspace_root):
    root = _root(workspace_root)
    for relative, size, digest in SOURCE_PINS:
        path, info = _inspect_path(root, PurePosixPath(relative).parts)
        if info is None or not stat.S_ISREG(info.st_mode):
            fail("source artifact missing or nonregular: " + relative)
        try:
            with path.open("rb") as stream:
                data = stream.read(size + 1)
        except OSError as exc:
            fail("source artifact unreadable: " + str(exc))
        if len(data) != size or sha(data) != digest:
            fail("source artifact identity changed: " + relative)


def _fixed_spans():
    spans = [(f"compat-{start:06x}", start, old, new, "canonical-operand-only")
             for start, old, new in COMPAT_PATCHES]
    spans += [("field-hook", 0x00448D, FIELD_PREIMAGE, FIELD_REPLACEMENT, "private-field-hook"),
              ("field-hook-boot-mirror", 0x40448D, FIELD_PREIMAGE, FIELD_REPLACEMENT, "exact-boot-mirror"),
              ("checksum", 0x00FFDC, SOURCE_HEADER_PAIR, TARGET_HEADER_PAIR, "computed-header-pair"),
              ("checksum-mirror", 0x40FFDC, SOURCE_HEADER_PAIR, TARGET_HEADER_PAIR, "computed-header-pair"),
              ("original-helper-component", HELPER_START, b"\xff" * HELPER_SIZE, None, "original-helper-component")]
    return sorted(spans, key=lambda span: span[1])


def _sections():
    return [{"id": name, "file_start": start, "size": len(old),
             "owner": OWNER, "payload_kind": kind,
             "evidence_level": "source-validated-private-diagnostic",
             "preimage_sha256": sha(old),
             "replacement_sha256": HELPER_SHA256 if new is None else sha(new)}
            for name, start, old, new, kind in _fixed_spans()]


def _template(target_sha256, output):
    return {"schema": SCHEMA, "build_mode": MODE,
            "source": {"kind": "pinned-inert-exhirom-scaffold", "size": SIZE,
                       "sha256": SCAFFOLD_SHA256},
            "target": {"size": SIZE, "sha256": target_sha256},
            "sources": _sources(), "context": copy.deepcopy(CONTEXT),
            "sections": _sections(), "output": output}


def validate_manifest(manifest, *, workspace_root=ROOT):
    """Validate fixed metadata, pinned artifacts and private destination; no writes."""
    if type(manifest) is not dict or set(manifest) != set(_template("", "")):
        fail("manifest: exact fields required")
    target = manifest["target"]
    if type(target) is not dict or set(target) != {"size", "sha256"}:
        fail("target: exact fields required")
    _digest(target["sha256"])
    if target["sha256"] == SCAFFOLD_SHA256:
        fail("target cannot be the unchanged scaffold")
    _exact(manifest, _template(target["sha256"], manifest["output"]), "manifest")
    _validate_destination(manifest["output"], target, workspace_root)
    _verify_sources(workspace_root)
    return {"schema": SCHEMA, "build_mode": MODE, "status": "metadata-valid",
            "manifest_sha256": sha(json.dumps(manifest, sort_keys=True,
                                               separators=(",", ":")).encode("utf-8")),
            "source_artifacts_verified": True, "rom_modified": False,
            "production_approval": False, "playable_pc_proof": False,
            "game_allocation_proof": False, "runtime_proof": False}


def audit_images(manifest, source, target, *, workspace_root=ROOT):
    """Require the exact source, exact replacements and complete changed-byte coverage."""
    report = validate_manifest(manifest, workspace_root=workspace_root)
    if type(source) is not bytes or len(source) != SIZE or sha(source) != SCAFFOLD_SHA256:
        fail("observed source is not the pinned inert scaffold")
    try:
        scaffold.validate_exhirom_scaffold(source)
    except ValueError as exc:
        fail("source scaffold invariants: " + str(exc))
    if type(target) is not bytes or len(target) != SIZE or sha(target) != manifest["target"]["sha256"]:
        fail("observed target identity mismatch")
    # C0 maps the first half; 41 maps its own expanded file bank. 00:448D is
    # NOT a ROM alias. 40:448D is mirrored to preserve the full boot-bank copy.
    for bus, file in ((0xC0448D, 0x448D), (0x40448D, 0x40448D), (0x410000, 0x410000)):
        if scaffold.exhirom_snes_to_file(bus) != file:
            fail("ExHiROM mapping drift")
    if scaffold.exhirom_snes_to_file(0x00448D) is not None:
        fail("bank00 low half must not be treated as a ROM alias")
    counts, cursor = {}, 0
    for name, start, old, new, _ in _fixed_spans():
        end = start + len(old)
        if source[start:end] != old:
            fail("canonical/scaffold preimage mismatch: " + name)
        if target[cursor:start] != source[cursor:start]:
            fail("undeclared changed bytes before " + name)
        payload = target[start:end]
        if new is None:
            if sha(payload) != HELPER_SHA256 or sum(payload) != HELPER_BYTE_SUM:
                fail("immutable helper component mismatch")
        elif payload != new:
            fail("exact replacement mismatch: " + name)
        counts[name] = sum(a != b for a, b in zip(old, payload, strict=True))
        cursor = end
    if target[cursor:] != source[cursor:]:
        fail("undeclared changed bytes after helper")
    if sum(counts[f"compat-{start:06x}"] for start, _, _ in COMPAT_PATCHES) != 14:
        fail("compatibility substitutions must change exactly fourteen bytes")
    if target[:0x10000] != target[0x400000:0x410000]:
        fail("full boot-bank mirror differs")
    checksum = sum(target) & 0xFFFF
    if checksum != TARGET_CHECKSUM or TARGET_HEADER_PAIR != bytes.fromhex("982267dd"):
        fail("computed target checksum differs")
    for start in (0xFFDC, 0x40FFDC):
        pair = target[start:start + 4]
        if (pair != TARGET_HEADER_PAIR or int.from_bytes(pair[:2], "little") ^ checksum != 0xFFFF
                or int.from_bytes(pair[2:], "little") != checksum):
            fail("checksum/complement pair differs")
    return {**report, "status": "images-valid", "evidence_level": "verified-static-private-diagnostic",
            "source_sha256": sha(source), "target_sha256": sha(target),
            "changed_bytes_by_section": counts, "changed_byte_count": sum(counts.values()),
            "complete_diff_coverage": True, "source_scaffold_verified": True,
            "mapping_verified": True, "full_boot_mirror_verified": True,
            "checksum_verified": True, "compatibility_changed_bytes": 14}


def build_manifest(source, target, output, *, workspace_root=ROOT):
    """Construct metadata for the fixed image only; audit before returning it."""
    if type(target) is not bytes:
        fail("target must be bytes")
    manifest = _template(sha(target), output)
    audit_images(manifest, source, target, workspace_root=workspace_root)
    return manifest
