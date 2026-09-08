"""Read-only complete-diff contract for one original, private SNES test cartridge.

This namespace accepts a literal blank image only. It never accepts a game ROM,
an inert game scaffold, a production mode, or caller-supplied allocation catalogs.
Authorship is a reviewed source assertion; hashes identify it, not prove it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

SCHEMA = "project-epoch-original-snes-diagnostic-intents-v1"
MODE = "private-original-diagnostic"
SIZE = 0x800000
BLANK_SHA256 = "9f9b02f5ee6cbef5e018c1ee424095fc21a842ea6968c0d36114b5930dab2ba1"
OWNER = "project-epoch-original-package-test-v1"
TITLE = b"EPOCH PACKAGE TEST   "
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = frozenset({
    "asm/original_snes_package_cartridge_v1.asm",
    "asm/schala_package_helper_v2_stack.asm",
    "tools/build_original_snes_package_cartridge_v1.py",
    "tools/original_snes_package_fixtures_v1.py",
    "tools/original_snes_diagnostic_write_contract_v1.py",
    "tools/validate_rom_write_intents.py",
})
# Exact starts and maximum lengths, exclusive of all game allocation catalogs.
SECTIONS = {
    "original-boot": (0x008000, 0x1000, "original-code"),
    "original-header": (0x00FFC0, 0x40, "original-header"),
    "boot-mirror": (0x408000, 0x1000, "exact-mirror"),
    "header-mirror": (0x40FFC0, 0x40, "exact-mirror"),
    "original-helper": (0x410000, 0x4000, "original-code"),
    "authored-packages": (0x420000, 0x2000, "original-package-fixtures"),
    "immutable-registry": (0x430000, 0x800, "original-registry"),
}


class OriginalDiagnosticIntentError(ValueError):
    """The distinct original-diagnostic intent or image contract was rejected."""


def fail(message):
    raise OriginalDiagnosticIntentError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fields(value, keys, context):
    if type(value) is not dict or set(value) != set(keys):
        fail(f"{context}: exact fields required")


def integer(value, low, high, context):
    if type(value) is not int or not low <= value <= high:
        fail(f"{context}: integer outside allowed bounds")


def digest(value, context):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        fail(f"{context}: lowercase SHA-256 required")


def relative_path(value, context):
    if (type(value) is not str or not value or "\\" in value or ":" in value
            or any(c in value for c in "\x00\r\n")
            or any(p in {"", ".", ".."} for p in value.split("/"))
            or PurePosixPath(value).is_absolute()):
        fail(f"{context}: canonical relative POSIX path required")
    for component in value.split("/"):
        if (component[-1:] in {".", " "}
                or any(ord(c) < 32 or c in '<>:"\\|?*' for c in component)
                or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])", component.split(".")[0].rstrip(" "))):
            fail(f"{context}: Windows reserved or aliasing path component")
    return PurePosixPath(value)


def output_path(value, workspace_root=ROOT):
    """Resolve containment and aliases without creating any directory or file."""
    path = relative_path(value, "output")
    if path.parts[:2] != ("private", "test_runs") or len(path.parts) < 4 or path.suffix != ".sfc":
        fail("output: require a new .sfc inside private/test_runs/<run>/")
    root = Path(workspace_root).resolve(strict=True)
    lexical = root.joinpath(*path.parts)
    allowed = root / "private" / "test_runs"
    # Reject any existing symlink/junction/reparse alias, even one pointing inward.
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            fail("output: filesystem aliases are forbidden")
    resolved = lexical.resolve(strict=False)
    if not resolved.is_relative_to(allowed) or resolved == allowed:
        fail("output: resolved path escaped private test runs")
    if lexical.exists():
        fail("output: existing output is forbidden")
    if any(p.exists() and not p.is_dir() for p in lexical.parents if p != root and p.is_relative_to(root)):
        fail("output: parent is not a directory")
    return resolved


def validate_manifest(manifest, *, workspace_root=ROOT):
    fields(manifest, {"schema", "build_mode", "source", "target", "sources", "sections", "output"}, "manifest")
    if manifest["schema"] != SCHEMA or manifest["build_mode"] != MODE:
        fail("only the distinct original private diagnostic schema and mode are accepted")
    fields(manifest["source"], {"kind", "size", "sha256"}, "source")
    if manifest["source"] != {"kind": "literal-all-ff-8mib", "size": SIZE, "sha256": BLANK_SHA256}:
        fail("source must be the pinned literal all-FF image")
    integer(manifest["source"]["size"], SIZE, SIZE, "source size")
    fields(manifest["target"], {"size", "sha256"}, "target")
    integer(manifest["target"]["size"], SIZE, SIZE, "target size")
    digest(manifest["target"]["sha256"], "target")
    if manifest["target"]["sha256"] == BLANK_SHA256:
        fail("target cannot be the unchanged blank image")
    sources = manifest["sources"]
    if type(sources) is not list or len(sources) != len(SOURCE_PATHS):
        fail("all exact original source identities are required")
    paths = []
    for source in sources:
        fields(source, {"path", "size", "sha256", "provenance"}, "source artifact")
        relative_path(source["path"], "source artifact")
        if source["path"] not in SOURCE_PATHS or source["provenance"] != "reviewed-original-project-source":
            fail("source artifact is outside the reviewed original source namespace")
        integer(source["size"], 1, 0x100000, "source artifact size")
        digest(source["sha256"], "source artifact")
        paths.append(source["path"])
    if paths != sorted(SOURCE_PATHS):
        fail("source artifacts must be complete, unique and sorted")
    sections = manifest["sections"]
    if type(sections) is not list or len(sections) != len(SECTIONS):
        fail("all seven distinct diagnostic sections are required")
    seen = []
    last_end = 0
    for section in sections:
        fields(section, {"id", "file_start", "size", "owner", "payload_kind", "evidence_level", "source_paths", "preimage_sha256", "replacement_sha256"}, "section")
        section_id = section["id"]
        if type(section_id) is not str or section_id not in SECTIONS or section_id in seen:
            fail("unknown or duplicate diagnostic section")
        start, capacity, kind = SECTIONS[section_id]
        integer(section["file_start"], start, start, section_id + " start")
        integer(section["size"], 1, capacity, section_id + " size")
        if section_id in {"original-header", "header-mirror"} and section["size"] != 64:
            fail("header section must be exactly 64 bytes")
        if section_id == "immutable-registry" and section["size"] != 0x500:
            fail("registry must be exactly 16 bindings plus 16 target sets")
        if section["owner"] != OWNER or section["payload_kind"] != kind or section["evidence_level"] != "verified-static":
            fail("diagnostic section ownership, kind or evidence mismatch")
        section_sources = section["source_paths"]
        if (type(section_sources) is not list or not section_sources
                or any(type(p) is not str or p not in SOURCE_PATHS for p in section_sources)
                or section_sources != sorted(set(section_sources))):
            fail("section source paths must be nonempty, unique, sorted and declared")
        if section["file_start"] < last_end:
            fail("sections must be sorted and disjoint")
        digest(section["preimage_sha256"], section_id + " preimage")
        digest(section["replacement_sha256"], section_id + " replacement")
        if section["preimage_sha256"] != sha(bytes([0xFF]) * section["size"]):
            fail("section preimage is not the exact blank span")
        if section["preimage_sha256"] == section["replacement_sha256"]:
            fail("declared section must actually change bytes")
        last_end = start + section["size"]
        seen.append(section_id)
    for primary, mirror in (("original-boot", "boot-mirror"), ("original-header", "header-mirror")):
        a = next(s for s in sections if s["id"] == primary)
        b = next(s for s in sections if s["id"] == mirror)
        if any(a[k] != b[k] for k in ("size", "replacement_sha256", "source_paths")):
            fail("mirror metadata must exactly match its original section")
    output_path(manifest["output"], workspace_root)
    return {"schema": SCHEMA, "status": "metadata-valid", "build_mode": MODE,
            "manifest_sha256": sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")),
            "production_approval": False, "rom_modified": False}


def audit_images(manifest, source, target, *, workspace_root=ROOT):
    report = validate_manifest(manifest, workspace_root=workspace_root)
    if type(source) is not bytes or len(source) != SIZE or sha(source) != BLANK_SHA256:
        fail("observed source is not the exact blank image")
    if type(target) is not bytes or len(target) != SIZE or sha(target) != manifest["target"]["sha256"]:
        fail("observed target identity mismatch")
    root = Path(workspace_root).resolve(strict=True)
    for artifact in manifest["sources"]:
        path = root.joinpath(*PurePosixPath(artifact["path"]).parts)
        info = path.lstat()
        if (path.resolve(strict=True) != path or not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            fail("source artifact aliases are forbidden")
        with path.open("rb") as stream:
            data = stream.read(artifact["size"] + 1)
        if len(data) != artifact["size"] or sha(data) != artifact["sha256"]:
            fail("original source artifact identity changed: " + artifact["path"])
    counts = {}
    cursor = 0
    for section in manifest["sections"]:
        start, end = section["file_start"], section["file_start"] + section["size"]
        if target[cursor:start] != source[cursor:start]:
            fail(f"undeclared changed bytes before section {section['id']}")
        payload = target[start:end]
        if sha(payload) != section["replacement_sha256"]:
            fail("observed section replacement mismatch: " + section["id"])
        counts[section["id"]] = sum(byte != 0xFF for byte in payload)
        if counts[section["id"]] == 0:
            fail("declared section has no changes")
        cursor = end
    if target[cursor:] != source[cursor:]:
        fail("undeclared changed bytes after final section")
    by_id = {s["id"]: s for s in manifest["sections"]}
    for a_id, b_id in (("original-boot", "boot-mirror"), ("original-header", "header-mirror")):
        a, b = by_id[a_id], by_id[b_id]
        if target[a["file_start"]:a["file_start"]+a["size"]] != target[b["file_start"]:b["file_start"]+b["size"]]:
            fail("observed original/mirror bytes differ")
    header = target[0xFFC0:0x10000]
    if len(TITLE) != 21 or header[:21] != TITLE or header[21:28] != bytes([0x35, 0x02, 0x0D, 0x03, 0x01, 0x33, 0x00]):
        fail("original cartridge title or fixed header fields differ")
    complement, checksum = int.from_bytes(header[28:30], "little"), int.from_bytes(header[30:32], "little")
    if complement ^ checksum != 0xFFFF or checksum != sum(target) & 0xFFFF:
        fail("original cartridge checksum or complement invalid")
    boot_end = 0x8000 + by_id["original-boot"]["size"]
    for offset in range(32, 64, 2):
        vector = int.from_bytes(header[offset:offset+2], "little")
        if not 0x8000 <= vector < boot_end:
            fail("vector is outside the actual original boot span")
    return {**report, "status": "images-valid", "source_sha256": BLANK_SHA256,
            "target_sha256": sha(target), "changed_bytes_by_section": counts,
            "changed_byte_count": sum(counts.values()), "complete_diff_coverage": True,
            "source_artifacts_verified": True, "mirrors_verified": True,
            "header_verified": True, "evidence_level": "verified-static"}
