#!/usr/bin/env python3
"""Validate Schala's authoring-only original item namespace and content."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "content"
    / "schala_item_content_v0.json"
)
FIRST_ITEM_ID = 0xE8
LAST_ITEM_ID = 0xEE
RESERVED_IDS = (0xEF, 0xF0, 0xF1)
SANITIZER_REJECTS_AT = 0xF2
BATTLE_MARKER_FAMILY = frozenset(range(0xF0, 0x100))
SCHALA_EQUIP_MASK = 0x01
MAX_UI_NAME_CHARS = 10
MAX_DESCRIPTION_CHARS = 48
EXPECTED_CLASSES = {
    "weapon": 4,
    "armor": 1,
    "accessory": 1,
    "key": 1,
}
NAMESPACE_STATUS = (
    "verified-static-unclaimed-by-canonical-location-events"
)
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)


def canonical_bytes(content: dict[str, object]) -> bytes:
    return (
        json.dumps(
            content,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_content(path: pathlib.Path = CONTENT_PATH) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_content(content: dict[str, object]) -> None:
    if content.get("schema_version") != 1:
        raise RuntimeError("unsupported Schala item schema")
    if content.get("logical_pc_id") != 7:
        raise RuntimeError("Schala logical PC ID changed")
    if content.get("content_origin") != "project-epoch-original":
        raise RuntimeError("items must be marked Project Epoch original")
    if content.get("rom_encoding_status") != "authoring-only-unmapped":
        raise RuntimeError("items must remain authoring-only until mapped")
    if (
        content.get("candidate_namespace_status")
        != NAMESPACE_STATUS
    ):
        raise RuntimeError("item range must retain its audited namespace label")
    if content.get("candidate_range") != [FIRST_ITEM_ID, LAST_ITEM_ID]:
        raise RuntimeError("candidate item range changed")
    if content.get("reserved_following_ids") != list(RESERVED_IDS):
        raise RuntimeError("following item IDs must remain reserved")
    evidence = content.get("candidate_namespace_evidence")
    expected_evidence = {
        "audit_path": "docs/location_event_item_reference_audit.md",
        "canonical_rom_sha256": CANONICAL_ROM_SHA256,
        "event_pointer_entries_examined": 513,
        "valid_referenced_event_ids": 489,
        "unique_packet_commands_audited": 145_615,
        "candidate_fixed_hits": 0,
        "computed_unresolved": 0,
    }
    if evidence != expected_evidence:
        raise RuntimeError("item namespace audit evidence changed")

    provenance = content.get("provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError("missing item provenance")
    if provenance.get("rom_or_npc_data_imported") is not False:
        raise RuntimeError("ROM or NPC data import is prohibited")
    if provenance.get("copied_vanilla_records") is not False:
        raise RuntimeError("copied vanilla item records are prohibited")

    items = content.get("items")
    if not isinstance(items, list):
        raise RuntimeError("items must be a list")
    if len(items) != LAST_ITEM_ID - FIRST_ITEM_ID + 1:
        raise RuntimeError("unexpected Schala item count")

    ids: list[int] = []
    design_names: set[str] = set()
    ui_names: set[str] = set()
    focus_visuals: set[int] = set()
    classes: collections.Counter[str] = collections.Counter()
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("item entry must be an object")
        item_id = item.get("item_id")
        if not isinstance(item_id, int):
            raise RuntimeError("item ID must be an integer")
        ids.append(item_id)
        if item_id >= SANITIZER_REJECTS_AT:
            raise RuntimeError(f"${item_id:02X}: rejected by sanitizer")
        if item_id in BATTLE_MARKER_FAMILY:
            raise RuntimeError(f"${item_id:02X}: battle marker collision")

        logical_class = item.get("logical_class")
        if logical_class not in EXPECTED_CLASSES:
            raise RuntimeError(f"${item_id:02X}: invalid logical class")
        classes[logical_class] += 1

        for field in ("design_name", "ui_name", "description", "acquisition"):
            value = item.get(field)
            if not isinstance(value, str) or not value:
                raise RuntimeError(f"${item_id:02X}: invalid {field}")
            try:
                value.encode("ascii")
            except UnicodeEncodeError as exc:
                raise RuntimeError(
                    f"${item_id:02X}: {field} must be ASCII"
                ) from exc
        if len(item["ui_name"]) > MAX_UI_NAME_CHARS:
            raise RuntimeError(f"${item_id:02X}: UI name exceeds budget")
        if len(item["description"]) > MAX_DESCRIPTION_CHARS:
            raise RuntimeError(f"${item_id:02X}: description exceeds budget")
        if item["design_name"] in design_names or item["ui_name"] in ui_names:
            raise RuntimeError(f"${item_id:02X}: duplicate item name")
        design_names.add(item["design_name"])
        ui_names.add(item["ui_name"])

        for field in ("price", "equip_mask", "power_or_defense", "magic_defense"):
            value = item.get(field)
            if not isinstance(value, int) or value < 0:
                raise RuntimeError(f"${item_id:02X}: invalid {field}")
        if logical_class == "key":
            if item["equip_mask"] != 0:
                raise RuntimeError("key item must not be equippable")
            if item.get("sellable") is not False or item.get("usable") is not False:
                raise RuntimeError("Pendant Shard must be inert and unsellable")
        elif item["equip_mask"] != SCHALA_EQUIP_MASK:
            raise RuntimeError(
                f"${item_id:02X}: gear must use Schala-only equip mask"
            )

        modifiers = item.get("stat_modifiers")
        if not isinstance(modifiers, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, int)
            or value <= 0
            for key, value in modifiers.items()
        ):
            raise RuntimeError(f"${item_id:02X}: invalid stat modifiers")
        focus_visual = item.get("focus_visual_id")
        if logical_class == "weapon":
            if (
                not isinstance(focus_visual, int)
                or focus_visual in focus_visuals
            ):
                raise RuntimeError(f"${item_id:02X}: invalid Focus visual")
            focus_visuals.add(focus_visual)
        elif focus_visual is not None:
            raise RuntimeError(f"${item_id:02X}: nonweapon has Focus visual")
        if item.get("native_binding") is not None:
            raise RuntimeError(
                f"${item_id:02X}: native binding requires trace approval"
            )

    if ids != list(range(FIRST_ITEM_ID, LAST_ITEM_ID + 1)):
        raise RuntimeError("Schala item IDs must be contiguous $E8-$EE")
    if classes != EXPECTED_CLASSES:
        raise RuntimeError(f"unexpected item class counts: {dict(classes)}")
    if focus_visuals != set(range(4)):
        raise RuntimeError("Focus visuals must be exactly 0 through 3")


def manifest(content: dict[str, object]) -> dict[str, object]:
    validate_content(content)
    items = content["items"]
    classes = collections.Counter(item["logical_class"] for item in items)
    return {
        "content_id": content["content_id"],
        "logical_pc_id": content["logical_pc_id"],
        "content_origin": content["content_origin"],
        "rom_encoding_status": content["rom_encoding_status"],
        "candidate_namespace_status": content["candidate_namespace_status"],
        "canonical_sha256": sha256(canonical_bytes(content)),
        "item_count": len(items),
        "item_range": [FIRST_ITEM_ID, LAST_ITEM_ID],
        "reserved_following_ids": list(RESERVED_IDS),
        "class_counts": dict(sorted(classes.items())),
        "native_bindings_present": any(
            item["native_binding"] is not None for item in items
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "content",
        nargs="?",
        type=pathlib.Path,
        default=CONTENT_PATH,
    )
    args = parser.parse_args()
    print(json.dumps(manifest(load_content(args.content)), indent=2))


if __name__ == "__main__":
    main()
