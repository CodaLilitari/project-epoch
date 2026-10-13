"""Fixed private Schala presentation contract; never a production admission.

The reference and every recipe input are pinned. There is no caller-provided
hook/allocation catalog. All old first-Attack sections remain prerequisites;
new presentation changes must reproduce the accepted image when reversed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import build_pc07_schala_presentation_v1 as provider
import pc07_private_first_attack_write_contract_v1 as prior
import schala_rom_scaffold as scaffold

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references/pc07_schala_presentation_private_contract_v2.json"
# Deliberately refuses construction until the reviewed exact recipe is sealed.
REFERENCE_SHA256 = "6795e2064dc8754a0c09567427fd089bc333b07b20e94b52a8a2f9cb4ec8d3ad"
SCHEMA = "project-epoch-private-pc07-schala-presentation-intents-v2"
SIZE = 0x800000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_checked(path, size, digest):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("input outside project") from exc
    for item in (path, *path.parents):
        if item.is_symlink() or (item.exists() and getattr(item.stat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("aliased input")
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if type(size) is not int or len(data) != size or sha(data) != digest:
        raise ValueError("pinned input drift: " + str(path))
    return data


def reference():
    if REFERENCE_SHA256 is None:
        raise ValueError("presentation recipe not sealed")
    raw = REFERENCE.read_bytes()
    if sha(raw) != REFERENCE_SHA256:
        raise ValueError("presentation reference drift")
    result = json.loads(raw)
    for item in result["sources"]:
        read_checked(item["path"], item["bytes"], item["sha256"])
    return result


def _base(source, spec):
    image = bytearray(source)
    components = {r["id"]: read_checked(r["path"], r["bytes"], r["sha256"])
                  for r in spec["prior_components"]}
    for name, start, old, new, _ in prior._fixed_spans():
        if image[start:start + len(old)] != old:
            raise ValueError("prior exact preimage drift: " + name)
        if new is None:
            new = components[name]
        if len(new) != len(old):
            raise ValueError("prior component extent")
        image[start:start + len(old)] = new
    if sha(image) != prior.TARGET_SHA256:
        raise ValueError("accepted first-Attack reconstruction mismatch")
    return bytes(image)


def recipe(canonical):
    spec = reference()
    if type(canonical) is not bytes or sha(canonical) != provider.npc.CANONICAL_ROM_SHA256:
        raise ValueError("exact canonical source required")
    source = scaffold.expand_exhirom_scaffold(canonical)
    scaffold.validate_exhirom_scaffold(source, source=canonical)
    base = _base(source, spec)
    image = bytearray(base)
    compiled = provider.compile_provider(canonical)
    sections = []
    for item in spec["new_sections"]:
        start, size = item["file_start"], item["bytes"]
        if item["kind"] == "retail-provider":
            payload = compiled.assets[item["id"]]
            if start != provider.ALLOCATIONS[item["id"]]:
                raise ValueError("named provider placement mismatch")
        elif item["kind"] == "original-helper":
            payload = read_checked(item["path"], size, item["sha256"])
        elif item["kind"] == "instruction-hook":
            payload = bytes.fromhex(item["replacement_hex"])
        else:
            raise ValueError("unknown section kind")
        if (type(start) is not int or type(size) is not int or size <= 0
                or start < 0 or start + size > SIZE or len(payload) != size
                or sha(payload) != item["sha256"]
                or sha(base[start:start + size]) != item["accepted_preimage_sha256"]):
            raise ValueError("exact new section mismatch: " + item["id"])
        sections.append((start, start + size, item["id"]))
        image[start:start + size] = payload
    for a, b in zip(sorted(sections), sorted(sections)[1:]):
        if a[1] > b[0]:
            raise ValueError("overlapping new sections")
    # Each checksum/complement pair sums to 510, so this assignment preserves
    # the sum used to derive it, including the complete bank00 mirror.
    checksum = sum(image) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    for start in (0xFFDC, 0x40FFDC):
        image[start:start + 4] = pair
    if image[:0x10000] != image[0x400000:0x410000] or sum(image) & 0xFFFF != checksum:
        raise ValueError("header/mirror invariant")
    target = bytes(image)
    if sha(target) != spec["target_sha256"]:
        raise ValueError("sealed target identity mismatch")
    inverse = bytearray(target)
    for start, end, _ in sections:
        inverse[start:end] = base[start:end]
    for start in (0xFFDC, 0x40FFDC):
        inverse[start:start + 4] = base[start:start + 4]
    if bytes(inverse) != base:
        raise ValueError("new-section inverse does not restore accepted image")
    return source, target, spec


def _template(spec, output):
    prior.field._validate_destination(output, {"size": SIZE, "sha256": spec["target_sha256"]}, ROOT)
    return {"schema": SCHEMA, "mode": "private-pc07-retail-schala-presentation",
            "source_sha256": prior.SOURCE_SHA256, "source_bytes": SIZE,
            "target_sha256": spec["target_sha256"], "target_bytes": SIZE,
            "recipe_sha256": REFERENCE_SHA256, "output": output,
            "new_sections": copy.deepcopy(spec["new_sections"]),
            "evidence_level": "verified-static-private-diagnostic",
            "production_approval": False, "runtime_qualification": False}


def validate_manifest(manifest):
    spec = reference()
    if type(manifest) is not dict:
        raise ValueError("manifest differs from fixed private recipe")
    prior.field._exact(manifest, _template(spec, manifest.get("output")), "manifest")
    return {"status": "metadata-valid", "schema": SCHEMA,
            "manifest_sha256": sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "recipe_sha256": REFERENCE_SHA256, "production_approval": False,
            "rom_modified": False}


def audit_images(manifest, source, target):
    report = validate_manifest(manifest)
    if type(source) is not bytes or len(source) != SIZE or sha(source) != prior.SOURCE_SHA256:
        raise ValueError("exact inert scaffold required")
    # The scaffold updates the canonical header. Recover only its pinned old
    # bytes via the exact canonical file, then require full scaffold equality.
    canonical = read_checked(provider.npc.DEFAULT_ROM, 0x400000, provider.npc.CANONICAL_ROM_SHA256)
    expected_source, expected_target, spec = recipe(canonical)
    if source != expected_source or type(target) is not bytes or target != expected_target:
        raise ValueError("complete image differs from sealed recipe")
    ranges = [(s, s + len(old)) for _, s, old, _, _ in prior._fixed_spans()]
    ranges += [(r["file_start"], r["file_start"] + r["bytes"]) for r in spec["new_sections"]]
    ranges.sort()
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    cursor = 0
    changed = 0
    for start, end in merged:
        if source[cursor:start] != target[cursor:start]:
            raise ValueError("undeclared image difference")
        changed += sum(a != b for a, b in zip(source[start:end], target[start:end]))
        cursor = end
    if source[cursor:] != target[cursor:]:
        raise ValueError("undeclared image tail difference")
    return {**report, "status": "images-valid", "complete_diff_coverage": True,
            "changed_bytes": changed, "declared_union_spans": merged,
            "target_sha256": sha(target), "accepted_image_inverse": True,
            "full_boot_mirror_verified": True}


def build_manifest(source, target, output):
    result = _template(reference(), output)
    audit_images(result, source, target)
    return result
