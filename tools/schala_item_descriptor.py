#!/usr/bin/env python3
"""Build Project Epoch's original high-ID item descriptor table.

This freezes the allocation-neutral version-1 binary layout for Schala's
$E8-$EE item overlay. It does not install records, allocate expanded ROM
space, encode descriptions, or assign native engine bindings.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import struct
from typing import Any

import validate_schala_items as items


DESCRIPTOR_VERSION = 1
DESCRIPTOR_SIZE = 0x20
DESCRIPTOR_COUNT = 7
TABLE_SIZE = DESCRIPTOR_SIZE * DESCRIPTOR_COUNT

CLASS_IDS = {
    "weapon": 0,
    "armor": 1,
    "accessory": 2,
    "key": 3,
}
CLASS_NAMES = {value: key for key, value in CLASS_IDS.items()}

FLAG_SELLABLE = 0x01
FLAG_USABLE = 0x02
FLAG_EQUIPPABLE = 0x04
FLAG_KEY_ITEM = 0x08
FLAG_FOCUS_WEAPON = 0x10
KNOWN_FLAGS = (
    FLAG_SELLABLE
    | FLAG_USABLE
    | FLAG_EQUIPPABLE
    | FLAG_KEY_ITEM
    | FLAG_FOCUS_WEAPON
)

STAT_MAGIC = 0x01
STAT_MAGIC_DEFENSE = 0x02
KNOWN_STAT_MASK = STAT_MAGIC | STAT_MAGIC_DEFENSE

NO_FOCUS_VISUAL = 0xFF
MAX_U24 = 0xFFFFFF


class ItemDescriptorError(ValueError):
    """Raised when an overlay descriptor is structurally invalid."""


@dataclasses.dataclass(frozen=True)
class OverlayItemDescriptorV1:
    item_id: int
    logical_class: int
    sort_class: int
    flags: int
    price: int
    equip_mask: int
    power_or_defense: int
    magic_defense: int
    stat_mask: int
    magic_amount: int
    magic_defense_amount: int
    element_resist_mask: int
    focus_visual_id: int
    secondary: bytes = bytes(5)
    description_ptr: int = 0
    weapon_visual_ptr: int = 0


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_u8(value: int, field: str) -> None:
    if not isinstance(value, int) or not 0 <= value <= 0xFF:
        raise ItemDescriptorError(f"{field} must fit in one byte")


def _require_u16(value: int, field: str) -> None:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        raise ItemDescriptorError(f"{field} must fit in two bytes")


def _require_u24(value: int, field: str) -> None:
    if not isinstance(value, int) or not 0 <= value <= MAX_U24:
        raise ItemDescriptorError(f"{field} must fit in three bytes")


def validate_descriptor(value: OverlayItemDescriptorV1) -> None:
    for field in (
        "item_id",
        "logical_class",
        "sort_class",
        "flags",
        "equip_mask",
        "power_or_defense",
        "magic_defense",
        "stat_mask",
        "magic_amount",
        "magic_defense_amount",
        "element_resist_mask",
        "focus_visual_id",
    ):
        _require_u8(getattr(value, field), field)
    _require_u16(value.price, "price")
    _require_u24(value.description_ptr, "description_ptr")
    _require_u24(value.weapon_visual_ptr, "weapon_visual_ptr")
    if len(value.secondary) != 5:
        raise ItemDescriptorError("secondary must be exactly five bytes")

    if value.logical_class not in CLASS_NAMES:
        raise ItemDescriptorError("unknown logical class")
    if value.sort_class != value.logical_class:
        raise ItemDescriptorError("v1 sort class must equal logical class")
    if value.flags & ~KNOWN_FLAGS:
        raise ItemDescriptorError("unknown descriptor flags")
    if value.stat_mask & ~KNOWN_STAT_MASK:
        raise ItemDescriptorError("unknown stat modifier bits")
    if not value.stat_mask & STAT_MAGIC and value.magic_amount:
        raise ItemDescriptorError("Magic amount set without stat-mask bit")
    if (
        not value.stat_mask & STAT_MAGIC_DEFENSE
        and value.magic_defense_amount
    ):
        raise ItemDescriptorError(
            "Magic Defense amount set without stat-mask bit"
        )
    if value.element_resist_mask:
        raise ItemDescriptorError(
            "v1 Schala items do not define elemental resistance"
        )
    if any(value.secondary):
        raise ItemDescriptorError(
            "v1 secondary bytes are reserved and must be zero"
        )

    logical_class = CLASS_NAMES[value.logical_class]
    if logical_class == "key":
        required = FLAG_KEY_ITEM
        prohibited = (
            FLAG_SELLABLE
            | FLAG_USABLE
            | FLAG_EQUIPPABLE
            | FLAG_FOCUS_WEAPON
        )
        if value.flags != required or value.flags & prohibited:
            raise ItemDescriptorError("key-item flags are not canonical")
        if value.equip_mask:
            raise ItemDescriptorError("key item must not be equippable")
    else:
        if not value.flags & FLAG_EQUIPPABLE:
            raise ItemDescriptorError("gear must be marked equippable")
        if value.flags & FLAG_KEY_ITEM:
            raise ItemDescriptorError("gear cannot be marked as a key item")
        if value.equip_mask != items.SCHALA_EQUIP_MASK:
            raise ItemDescriptorError(
                "Schala gear must use logical-PC-7 equip bit"
            )

    if logical_class == "weapon":
        if not value.flags & FLAG_FOCUS_WEAPON:
            raise ItemDescriptorError("weapon must be a Focus weapon")
        if not 0 <= value.focus_visual_id <= 3:
            raise ItemDescriptorError("Focus visual ID must be 0 through 3")
    else:
        if value.flags & FLAG_FOCUS_WEAPON:
            raise ItemDescriptorError("nonweapon cannot be a Focus weapon")
        if value.focus_visual_id != NO_FOCUS_VISUAL:
            raise ItemDescriptorError(
                "nonweapon Focus visual must use the null sentinel"
            )
        if value.weapon_visual_ptr:
            raise ItemDescriptorError(
                "nonweapon cannot have a weapon-visual pointer"
            )


def encode_descriptor(value: OverlayItemDescriptorV1) -> bytes:
    validate_descriptor(value)
    encoded = bytearray(DESCRIPTOR_SIZE)
    struct.pack_into(
        "<BBBBHBBBBBBBB",
        encoded,
        0,
        value.item_id,
        value.logical_class,
        value.sort_class,
        value.flags,
        value.price,
        value.equip_mask,
        value.power_or_defense,
        value.magic_defense,
        value.stat_mask,
        value.magic_amount,
        value.magic_defense_amount,
        value.element_resist_mask,
        value.focus_visual_id,
    )
    encoded[0x0E:0x13] = value.secondary
    encoded[0x14:0x17] = value.description_ptr.to_bytes(3, "little")
    encoded[0x18:0x1B] = value.weapon_visual_ptr.to_bytes(3, "little")
    return bytes(encoded)


def decode_descriptor(encoded: bytes) -> OverlayItemDescriptorV1:
    if len(encoded) != DESCRIPTOR_SIZE:
        raise ItemDescriptorError(
            f"descriptor must be exactly 0x{DESCRIPTOR_SIZE:X} bytes"
        )
    if encoded[0x13] or encoded[0x17] or any(encoded[0x1B:0x20]):
        raise ItemDescriptorError("descriptor reserved bytes must be zero")
    fields = struct.unpack_from("<BBBBHBBBBBBBB", encoded, 0)
    value = OverlayItemDescriptorV1(
        item_id=fields[0],
        logical_class=fields[1],
        sort_class=fields[2],
        flags=fields[3],
        price=fields[4],
        equip_mask=fields[5],
        power_or_defense=fields[6],
        magic_defense=fields[7],
        stat_mask=fields[8],
        magic_amount=fields[9],
        magic_defense_amount=fields[10],
        element_resist_mask=fields[11],
        focus_visual_id=fields[12],
        secondary=encoded[0x0E:0x13],
        description_ptr=int.from_bytes(encoded[0x14:0x17], "little"),
        weapon_visual_ptr=int.from_bytes(encoded[0x18:0x1B], "little"),
    )
    validate_descriptor(value)
    return value


def descriptor_from_item(
    item: dict[str, Any],
    *,
    description_ptr: int = 0,
    weapon_visual_ptr: int = 0,
) -> OverlayItemDescriptorV1:
    logical_class_name = item["logical_class"]
    logical_class = CLASS_IDS[logical_class_name]
    flags = 0
    flags |= FLAG_SELLABLE if item["sellable"] else 0
    flags |= FLAG_USABLE if item["usable"] else 0
    flags |= FLAG_EQUIPPABLE if logical_class_name != "key" else 0
    flags |= FLAG_KEY_ITEM if logical_class_name == "key" else 0
    flags |= FLAG_FOCUS_WEAPON if logical_class_name == "weapon" else 0

    modifiers = item["stat_modifiers"]
    unknown_modifiers = set(modifiers) - {"magic", "magic_defense"}
    if unknown_modifiers:
        raise ItemDescriptorError(
            "unsupported stat modifiers: "
            + ", ".join(sorted(unknown_modifiers))
        )
    stat_mask = 0
    stat_mask |= STAT_MAGIC if "magic" in modifiers else 0
    stat_mask |= (
        STAT_MAGIC_DEFENSE if "magic_defense" in modifiers else 0
    )

    focus_visual = item["focus_visual_id"]
    return OverlayItemDescriptorV1(
        item_id=item["item_id"],
        logical_class=logical_class,
        sort_class=logical_class,
        flags=flags,
        price=item["price"],
        equip_mask=item["equip_mask"],
        power_or_defense=item["power_or_defense"],
        magic_defense=item["magic_defense"],
        stat_mask=stat_mask,
        magic_amount=modifiers.get("magic", 0),
        magic_defense_amount=modifiers.get("magic_defense", 0),
        element_resist_mask=0,
        focus_visual_id=(
            focus_visual if focus_visual is not None else NO_FOCUS_VISUAL
        ),
        secondary=bytes(5),
        description_ptr=description_ptr,
        weapon_visual_ptr=weapon_visual_ptr,
    )


def build_unbound_table(
    content: dict[str, object],
) -> tuple[bytes, tuple[OverlayItemDescriptorV1, ...]]:
    items.validate_content(content)
    source_items = content["items"]
    if not isinstance(source_items, list):
        raise ItemDescriptorError("content items must be a list")
    descriptors = tuple(
        descriptor_from_item(item) for item in source_items
    )
    encoded = b"".join(encode_descriptor(value) for value in descriptors)
    if len(descriptors) != DESCRIPTOR_COUNT or len(encoded) != TABLE_SIZE:
        raise ItemDescriptorError("unexpected descriptor-table shape")
    if tuple(value.item_id for value in descriptors) != tuple(
        range(items.FIRST_ITEM_ID, items.LAST_ITEM_ID + 1)
    ):
        raise ItemDescriptorError("descriptor IDs are not contiguous")
    return encoded, descriptors


def manifest(content: dict[str, object]) -> dict[str, object]:
    encoded, descriptors = build_unbound_table(content)
    return {
        "schema_version": 1,
        "descriptor_version": DESCRIPTOR_VERSION,
        "descriptor_size": DESCRIPTOR_SIZE,
        "descriptor_count": len(descriptors),
        "table_size": len(encoded),
        "table_sha256": sha256(encoded),
        "item_ids": [value.item_id for value in descriptors],
        "class_ids": CLASS_IDS,
        "description_pointers_bound": any(
            value.description_ptr for value in descriptors
        ),
        "weapon_visual_pointers_bound": any(
            value.weapon_visual_ptr for value in descriptors
        ),
        "allocation_status": "unbound",
        "rom_installable": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "content",
        nargs="?",
        type=pathlib.Path,
        default=items.CONTENT_PATH,
    )
    args = parser.parse_args()
    content = items.load_content(args.content)
    print(json.dumps(manifest(content), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
