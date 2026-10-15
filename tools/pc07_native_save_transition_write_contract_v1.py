"""Fixed private native-save-transition diagnostic; no production allocation admission.

reference() verifies the sealed metadata and all source/component pins.
compile_events(canonical) returns two dictionaries containing private in-memory
decoded/encoded bytes and their exact source_cpu addresses. recipe(canonical)
returns (inert_scaffold, target_image, reference). build_manifest and both audit
APIs are read-only. The caller must use the shared guard before exclusive output.
No caller-provided hook, allocation, payload, codec or provenance is accepted.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

import pc07_private_first_attack_write_contract_v1 as prior
import schala_rom_scaffold as scaffold

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references/pc07_native_save_transition_private_contract_v1.json"
REFERENCE_SHA256 = "fcce6a139df856692646e4adb04424a6470f54b362d587535b481a403417d391"
SCHEMA = "project-epoch-private-pc07-native-save-transition-intents-v1"
REFERENCE_SCHEMA = "project-epoch-private-pc07-native-save-transition-recipe-v1"
OWNER = "project-epoch-private-pc07-native-save-transition-v1"
SIZE = 0x800000
CANONICAL_PATH = "private/input/rom_archive/Chrono Trigger (USA).sfc"
CANONICAL_SHA256 = "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
POINTER_START = 0x3CFD5F
POINTER_PREIMAGE = bytes.fromhex("c8dcfa02e2fa")
POINTER_REPLACEMENT = bytes.fromhex("000044001044")
CODEC = "private/research/pc07_native_event_source_20261013/literal_event_codec_v1.py"
NATIVE_COMPILER = "private/research/pc07_native_control_transform_20261013/transform_v1.py"
SAVE_COMPILER = "private/research/pc07_native_save_transition_transform_20261013/transform_v1.py"
SECOND_DECODER = "private/research/ctrando_20609d5/src/ctrando/compression/ctcompression.py"
EVENTS = (
    (0x125, 0x440000, 2553, "d81b7bfc4db23d95adc8a576ba2472e1cd005ab8e43cf997fda3e5e3da29a51d",
     2879, "67e8f6c1ec34c029243cbfb8907ba5f1c94335a827c7424826261de2c9068672"),
    (0x126, 0x441000, 1925, "75990bc5522be5b153461f67b35dcbdbf77da98284f00c52a2cc24962af8be40",
     2172, "71960d5b5a1694315d130c05224fb5cdbeb70492b276e81fc1c3c73cbb61119a"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_checked(path, size, digest):
    """Read an exact regular unaliased project file, without creating outputs."""
    if type(size) is not int or size < 0 or type(digest) is not str or len(digest) != 64:
        raise ValueError("invalid pinned input identity")
    root = prior.field._root(ROOT)
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError("input outside project") from exc
    if ".." in relative.parts or not relative.parts:
        raise ValueError("invalid input path")
    prior.field._inspect_path(root, relative.parts)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("pinned input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if len(data) != size or sha(data) != digest:
        raise ValueError("pinned input drift: " + str(path))
    return data


def _event_metadata():
    return [{"id": f"event-{event:04x}", "event_id": event, "source_cpu": address,
             "file_start": address, "decoded_bytes": decoded_size, "decoded_sha256": decoded_sha,
             "encoded_bytes": encoded_size, "encoded_sha256": encoded_sha,
             "end_exclusive": address + encoded_size, "production_allocation": False}
            for event, address, decoded_size, decoded_sha, encoded_size, encoded_sha in EVENTS]


def _new_sections():
    return [{"id": "event-pointer-rows-0125-0126", "file_start": POINTER_START,
             "bytes": 6, "kind": "canonical-event-pointer-rows",
             "preimage_hex": POINTER_PREIMAGE.hex(), "replacement_hex": POINTER_REPLACEMENT.hex(),
             "preimage_sha256": sha(POINTER_PREIMAGE), "sha256": sha(POINTER_REPLACEMENT)}] + [
        {"id": row["id"], "file_start": row["file_start"], "bytes": row["encoded_bytes"],
         "kind": "fixed-expanded-event", "preimage_sha256": sha(b"\xff" * row["encoded_bytes"]),
         "sha256": row["encoded_sha256"]} for row in _event_metadata()]


def _validate_spec(spec):
    if (type(spec) is not dict or spec.get("schema") != REFERENCE_SCHEMA
            or spec.get("prior_image_sha256") != prior.TARGET_SHA256
            or spec.get("source_sha256") != prior.SOURCE_SHA256
            or spec.get("source_bytes") != SIZE or spec.get("target_bytes") != SIZE):
        raise ValueError("fixed native-event reference shape")
    prior.field._exact(spec["events"], _event_metadata(), "reference.events")
    prior.field._exact(spec["new_sections"], _new_sections(), "reference.new_sections")
    for row in spec["events"]:
        start, end = row["source_cpu"], row["end_exclusive"]
        if (start >> 16 != 0x44 or (end - 1) >> 16 != 0x44
                or scaffold.exhirom_snes_to_file(start) != row["file_start"]
                or scaffold.exhirom_snes_to_file(end - 1) != end - 1):
            raise ValueError("fixed one-bank ExHiROM event extent")
    spans = sorted((r["file_start"], r["file_start"] + r["bytes"]) for r in spec["new_sections"])
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError("overlapping event allocations")
    if POINTER_START != 0x3CF9F0 + 0x125 * 3:
        raise ValueError("canonical pointer-row identity")


def reference():
    if REFERENCE_SHA256 is None:
        raise ValueError("native-event recipe not sealed")
    # Bound the metadata before JSON parsing. The literal digest owns its schema.
    prior.field._inspect_path(prior.field._root(ROOT), REFERENCE.relative_to(ROOT).parts)
    with REFERENCE.open("rb") as stream:
        raw = stream.read(0x20001)
    if len(raw) > 0x20000 or sha(raw) != REFERENCE_SHA256:
        raise ValueError("native-event reference drift")
    spec = json.loads(raw)
    _validate_spec(spec)
    seen = set()
    for row in spec["sources"]:
        if row["path"] in seen:
            raise ValueError("duplicate source pin")
        seen.add(row["path"])
        read_checked(row["path"], row["bytes"], row["sha256"])
    for row in spec["prior_components"]:
        if row["path"] not in seen:
            raise ValueError("component absent from exact source pins")
        read_checked(row["path"], row["bytes"], row["sha256"])
    for row in spec["assembly_components"]:
        if row["source"] not in seen:
            raise ValueError("assembly source absent from exact pins")
    return spec


def _load(path):
    name = "epoch_native_save_transition_" + sha(path.encode())[:12]
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load exact event source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _canonical(canonical):
    if type(canonical) is not bytes or len(canonical) != 0x400000 or sha(canonical) != CANONICAL_SHA256:
        raise ValueError("exact canonical source required")
    if canonical[POINTER_START:POINTER_START + 6] != POINTER_PREIMAGE:
        raise ValueError("exact six-byte canonical pointer preimage")


def _compile_events(canonical, spec):
    # reference() has pinned these and every transitive project source before
    # execution. The older post-return-only transform is imported for its parser,
    # never called; no saved packet/snapshot is an input to this recipe.
    codec = _load(CODEC)
    selected = _load("tools/transform_pc07_selected_event_v1.py")
    escape = _load("tools/transform_pc07_escape_event_v1.py")
    native = _load(NATIVE_COMPILER)
    save_transition = _load(SAVE_COMPILER)
    decoder_row = next(r for r in spec["sources"] if r["path"] == SECOND_DECODER)
    decoder_source = read_checked(SECOND_DECODER, decoder_row["bytes"], decoder_row["sha256"])
    tree = ast.parse(decoder_source)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "decompress_py"]
    if len(functions) != 1:
        raise ValueError("pinned second decoder identity")
    namespace = {"ByteString": bytes}
    exec(compile(ast.Module(body=functions, type_ignores=[]), SECOND_DECODER, "exec"), namespace)
    packets = [selected.transform_from_rom(canonical).packet,
               save_transition.transform_packet(native.transform_packet(escape.transform_from_rom(canonical).packet).packet).packet]
    result = []
    for row, decoded in zip(spec["events"], packets):
        encoded = codec.literal_packet(decoded)
        if (len(decoded) != row["decoded_bytes"] or sha(decoded) != row["decoded_sha256"]
                or len(encoded) != row["encoded_bytes"] or sha(encoded) != row["encoded_sha256"]):
            raise ValueError("fixed compiled event identity")
        offset = row["source_cpu"] & 0xFFFF
        buffer = b"\xff" * offset + encoded + b"\xa5" * 8
        first = selected.PARSER.decompress_packet(buffer, offset)
        if (first.data != decoded or first.compressed_size != len(encoded)
                or namespace["decompress_py"](buffer, offset) != decoded):
            raise ValueError("independent host decoder mismatch")
        result.append({**row, "decoded": decoded, "encoded": encoded})
    return result


def compile_events(canonical):
    """Return private bytes in memory only; this function never writes payloads."""
    _canonical(canonical)
    return _compile_events(canonical, reference())


def _base(source, spec):
    image = bytearray(source)
    components = {r["id"]: read_checked(r["path"], r["bytes"], r["sha256"])
                  for r in spec["prior_components"]}
    for name, start, old, new, _ in prior._fixed_spans():
        if image[start:start + len(old)] != old:
            raise ValueError("prior exact preimage drift: " + name)
        replacement = components[name] if new is None else new
        if len(replacement) != len(old):
            raise ValueError("prior component extent")
        image[start:start + len(old)] = replacement
    if sha(image) != prior.TARGET_SHA256:
        raise ValueError("accepted first-Attack reconstruction mismatch")
    return bytes(image)


def _target(base, events):
    image = bytearray(base)
    payloads = {r["id"]: r["encoded"] for r in events}
    for row in _new_sections():
        start, size = row["file_start"], row["bytes"]
        old = base[start:start + size]
        replacement = (POINTER_REPLACEMENT if row["kind"] == "canonical-event-pointer-rows"
                       else payloads[row["id"]])
        if sha(old) != row["preimage_sha256"] or len(replacement) != size or sha(replacement) != row["sha256"]:
            raise ValueError("new section preimage/payload: " + row["id"])
        image[start:start + size] = replacement
    checksum = sum(image) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    for start in (0xFFDC, 0x40FFDC):
        image[start:start + 4] = pair
    if image[:0x10000] != image[0x400000:0x410000] or sum(image) & 0xFFFF != checksum:
        raise ValueError("complete boot mirror/checksum invariant")
    inverse = bytearray(image)
    for row in _new_sections():
        start, size = row["file_start"], row["bytes"]
        inverse[start:start + size] = base[start:start + size]
    for start in (0xFFDC, 0x40FFDC):
        inverse[start:start + 4] = base[start:start + 4]
    if bytes(inverse) != base:
        raise ValueError("new event inverse does not restore accepted image")
    return bytes(image), checksum


def recipe(canonical):
    _canonical(canonical)
    spec = reference()
    source = scaffold.expand_exhirom_scaffold(canonical)
    scaffold.validate_exhirom_scaffold(source, source=canonical)
    base = _base(source, spec)
    target, checksum = _target(base, _compile_events(canonical, spec))
    if sha(target) != spec["target_sha256"] or checksum != spec["target_checksum"]:
        raise ValueError("sealed complete native-event target identity")
    return source, target, spec


def _sections(spec):
    checksum = spec["target_checksum"]
    pair = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    rows = []
    for name, start, old, new, kind in prior._fixed_spans():
        if start in (0xFFDC, 0x40FFDC):
            new = pair
        digest = prior._payload_digest(name, new)
        rows.append({"id": name, "file_start": start, "bytes": len(old), "kind": kind,
                     "preimage_sha256": sha(old), "sha256": digest, "owner": OWNER})
    rows.extend({"id": r["id"], "file_start": r["file_start"], "bytes": r["bytes"],
                 "kind": r["kind"], "preimage_sha256": r["preimage_sha256"],
                 "sha256": r["sha256"], "owner": OWNER} for r in spec["new_sections"])
    rows.sort(key=lambda r: r["file_start"])
    if len(rows) != 37 or any(a["file_start"] + a["bytes"] > b["file_start"] for a, b in zip(rows, rows[1:])):
        raise ValueError("fixed 37-section disjoint recipe")
    return rows


def _template(spec, output):
    prior.field._validate_destination(output, {"size": SIZE, "sha256": spec["target_sha256"]}, ROOT)
    return {"schema": SCHEMA, "mode": "private-pc07-native-save-transition-diagnostic",
            "source": {"kind": "pinned-inert-exhirom-scaffold", "bytes": SIZE, "sha256": prior.SOURCE_SHA256},
            "target": {"bytes": SIZE, "sha256": spec["target_sha256"]},
            "recipe_sha256": REFERENCE_SHA256, "output": output,
            "sections": _sections(spec), "events": copy.deepcopy(spec["events"]),
            "evidence_level": "verified-static-private-diagnostic",
            "production_approval": False, "runtime_qualification": False,
            "record_roster_fixture_still_required": True,
            "native_save_transition_proved": False}


def validate_manifest(manifest):
    spec = reference()
    if type(manifest) is not dict:
        raise ValueError("manifest differs from fixed private recipe")
    prior.field._exact(manifest, _template(spec, manifest.get("output")), "manifest")
    return {"status": "metadata-valid", "schema": SCHEMA,
            "manifest_sha256": sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "recipe_sha256": REFERENCE_SHA256, "production_approval": False, "rom_modified": False}


def audit_images(manifest, source, target):
    report = validate_manifest(manifest)
    if type(source) is not bytes or len(source) != SIZE or sha(source) != prior.SOURCE_SHA256:
        raise ValueError("exact inert scaffold required")
    if type(target) is not bytes or len(target) != SIZE:
        raise ValueError("exact target bytes required")
    canonical = read_checked(CANONICAL_PATH, 0x400000, CANONICAL_SHA256)
    expected_source, expected_target, spec = recipe(canonical)
    if source != expected_source or target != expected_target:
        raise ValueError("complete image differs from sealed recipe")
    cursor = changed = 0
    rows = _sections(spec)
    for row in rows:
        start, end = row["file_start"], row["file_start"] + row["bytes"]
        if source[cursor:start] != target[cursor:start]:
            raise ValueError("undeclared image difference")
        if sha(source[start:end]) != row["preimage_sha256"] or sha(target[start:end]) != row["sha256"]:
            raise ValueError("exact section preimage/replacement mismatch")
        changed += sum(a != b for a, b in zip(source[start:end], target[start:end]))
        cursor = end
    if source[cursor:] != target[cursor:]:
        raise ValueError("undeclared image tail difference")
    return {**report, "status": "images-valid", "complete_diff_coverage": True,
            "changed_bytes": changed, "declared_sections": len(rows),
            "declared_union_spans": [[r["file_start"], r["file_start"] + r["bytes"]] for r in rows],
            "target_sha256": sha(target), "accepted_image_inverse": True,
            "full_boot_mirror_verified": True, "both_host_decoders_exact": True,
            "native_execution": False}


def build_manifest(source, target, output):
    result = _template(reference(), output)
    audit_images(result, source, target)
    return result
