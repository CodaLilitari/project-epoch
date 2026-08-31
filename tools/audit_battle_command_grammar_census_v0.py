#!/usr/bin/env python3
"""Audit the canonical battle-animation command grammar and stream closure.

The auditor accepts only the pinned headerless Chrono Trigger US Rev0 ROM,
reads it without mutation, reuses the already-closed primary package topology,
and emits a metadata-only JSON report.  It tokenizes every bank-qualified
direct script in the config-selected structural supplement, follows command
$1E through the fixed $CE subscript table, and verifies exact token agreement
for every shared byte.

No ROM bytes, script bytes, script offsets, pointer lists, save data, emulator
state, raw traces, patches, or output files are emitted.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from collections.abc import Mapping, Sequence
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Final

import audit_battle_action_package_topology_v0 as topology


ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_PATH: Final = (
    ROOT / "references" / "battle_command_grammar_census_v0.json"
)

# Filled after the closed contract is generated and independently reviewed.
REFERENCE_SIZE: Final = 12_433
REFERENCE_SHA256: Final = (
    "1582aca15e209d8015d5c34fdf4016ee45e75d9872ff76f4933e29f80ce46e0c"
)

SCHEMA: Final = "project-epoch-battle-command-grammar-census-v0"
REFERENCE_SCHEMA: Final = (
    "project-epoch-battle-command-grammar-census-contract-v0"
)
AUDITOR_VERSION: Final = "battle-command-grammar-census-v0"
STATUS: Final = (
    "pass-lossless-canonical-command-tokenization-and-fixed-ce-"
    "subscript-closure-metadata-only"
)

DISPATCHED_OPCODE_END_EXCLUSIVE: Final = 0xDB
VARIABLE_OPCODE: Final = 0x80
DEFAULT_HANDLER_OFFSET: Final = 0x4CF7
SUBSCRIPT_CALL_OPCODE: Final = 0x1E
RETURN_OPCODE: Final = 0x1F
CONDITIONAL_RETURN_OPCODE: Final = 0x21
CONDITIONAL_STOP_OPCODE: Final = 0x25
STOP_OPCODE: Final = 0x00
LOOKAHEAD_OPCODE: Final = 0xDA


class BattleCommandGrammarAuditError(RuntimeError):
    """The canonical input, grammar, stream closure, or contract drifted."""


@dataclasses.dataclass(frozen=True)
class SpanSpec:
    name: str
    label: str
    start: int
    end_exclusive: int
    expected_sha256: str


@dataclasses.dataclass(frozen=True)
class TokenShape:
    owned_width: int
    width_rule: str
    known_lookahead_offsets: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class DecodedToken:
    bank: int
    offset: int
    opcode: int
    owned_width: int
    width_rule: str
    flow: str
    handler_family: str | None
    known_lookahead_offsets: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class RootTopology:
    declared_roots: frozenset[tuple[int, int]]
    config_roots: frozenset[tuple[int, int]]
    descriptor_spans: tuple[tuple[int, int, int], ...]


@dataclasses.dataclass(frozen=True)
class DescriptorIntersectionSummary:
    rows: tuple[tuple[int, int, int, int, int, int, int], ...]
    reached_spans: frozenset[tuple[int, int, int]]
    token_starts_inside: frozenset[tuple[int, int]]
    intersecting_token_keys: frozenset[tuple[int, int]]
    owned_bytes_inside: frozenset[tuple[int, int]]
    entrypoints_reaching: frozenset[tuple[int, int]]


MACHINE_SPANS: Final = (
    SpanSpec(
        "primary_dispatcher",
        "Battle_AnimScriptRun command dispatch loop",
        0xC14C9E,
        0xC14CF0,
        "f9eee9ad39ebab931c5a65d55bbff455"
        "85670770b528be2f10d65e9cc7dab561",
    ),
    SpanSpec(
        "command_handler_corpus",
        "all dispatched command handlers before pointer advance",
        0xC14CF0,
        0xC175BB,
        "2e54923e7d873642dee437596a09c58c"
        "a7d63c6fe34aedb5cfcbbc6432c63281",
    ),
    SpanSpec(
        "pointer_advance",
        "Battle_AnimScriptAdvance",
        0xC175BB,
        0xC175CC,
        "81ec99810c0832f34277d117410919282"
        "e14891d51bb3869533e60ae3ef97142",
    ),
    SpanSpec(
        "command_dispatch_table",
        "219-word command dispatch table for opcodes 00-DA",
        0xC17A6B,
        0xC17C21,
        "59145c787a5a5c57c59de7992ec0e17"
        "d5c6a64f32ef9e1e3273d174f90e8d995",
    ),
    SpanSpec(
        "fixed_ce_subscript_table",
        "256-word command-1E target table",
        0xCE0000,
        0xCE0200,
        "cc7d3a05e105d5ce76f187d78b89f"
        "edcda7d42751761d7b51b7d4bd1df669687",
    ),
    SpanSpec(
        "movement_width_witnesses",
        "commands 13-18 width setup",
        0xC151EE,
        0xC15437,
        "52f0db121fcb4a284a6deed9a6087c50"
        "f7985842cceaca6a3055ab3d1115025a",
    ),
    SpanSpec(
        "counter_width_witnesses",
        "commands 3B and 3C consuming width",
        0xC15991,
        0xC159B9,
        "43755b8967cc9c23bfe069f12634228c"
        "d8a02f830ca74ebfdfcad2465f2f1862",
    ),
    SpanSpec(
        "variable_80_witness",
        "command 80 low-nibble loop and computed advance",
        0xC1621B,
        0xC1623C,
        "281d1ad004b46d3cb6ec76e68cb183f"
        "40659b75257348865fba3df1d2a4f752e",
    ),
    SpanSpec(
        "effect_98_9d_width_witnesses",
        "commands 98-9D shared width setup",
        0xC16299,
        0xC16751,
        "76667c8601e56657acfd755f87c5ede2"
        "2cfd97e0e9a68c4e0bfe8f6cb8375688",
    ),
    SpanSpec(
        "c5_width_witness",
        "command C5 consuming width",
        0xC16FEF,
        0xC16FFC,
        "24560275988e4ccf693bd7eef963487e"
        "27281e3e201a7b7a6634d6a467f5c11e",
    ),
    SpanSpec(
        "da_lookahead_width_witness",
        "command DA reads +1 and advances only 1",
        0xC17579,
        0xC175BB,
        "948c3682ab3c00f58ce4df5264a7e019"
        "c88222dbddab593c87745a44e3a37613",
    ),
)


# Total token extents for dispatched opcodes 00-DA.  These are the eventual
# consuming deltas used for lossless tokenization, not a claim that every
# handler advances immediately on every invocation.  Opcode 80 is computed
# from its first payload byte and is the sole variable-width entry.
FIXED_TOKEN_WIDTHS: Final[tuple[int | None, ...]] = (
    1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    3, 1, 2, 4, 2, 3, 3, 1, 2, 3, 1, 2, 2, 2, 2, 1,
    2, 1, 3, 2, 2, 2, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    3, 2, 2, 2, 2, 1, 1, 2, 1, 1, 3, 2, 2, 2, 2, 2,
    2, 3, 2, 4, 1, 2, 2, 2, 2, 3, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2,
    2, 4, 4, 4, 4, 1, 1, 1, 1, 2, 1, 2, 3, 1, 1, 1,
    1, 1, 2, 2, 2, 2, 3, 2, 2, 2, 3, 3, 1, 1, 1, 1,
    None, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 3, 2, 3, 2, 3, 2, 1, 1,
    1, 1, 1, 1, 3, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    5, 4, 5, 4, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 2, 1, 1, 1, 1, 3, 4, 2, 1,
)

if len(FIXED_TOKEN_WIDTHS) != DISPATCHED_OPCODE_END_EXCLUSIVE:
    raise RuntimeError("internal command-width vector geometry is invalid")
if FIXED_TOKEN_WIDTHS[VARIABLE_OPCODE] is not None:
    raise RuntimeError("opcode 80 must remain the sole variable-width entry")
if any(
    width is None
    for opcode, width in enumerate(FIXED_TOKEN_WIDTHS)
    if opcode != VARIABLE_OPCODE
):
    raise RuntimeError("unexpected variable-width command")


DECLARED_ROUTE_NAMES: Final = (
    "pc_normal_attack",
    "pc_named_tech",
    "pc_internal_type2_config",
    "enemy_attack",
    "enemy_tech",
    "battle_item",
)
CONFIG_ROUTE_NAMES: Final = (
    "pc_normal_attack",
    "pc_action_physical",
    "enemy_attack",
    "enemy_tech",
    "battle_item",
)

SCRIPT_RANGES: Final = {
    0xCD: (0x6E0C, 0x10000),
    0xCE: (0x0000, 0xE000),
}

CORRECTION_WITNESSES: Final = (
    {
        "opcode": "15",
        "verified_owned_width": 3,
        "reason": "handler stores consuming delta 03 after two operands",
    },
    {
        "opcode": "18",
        "verified_owned_width": 2,
        "reason": "handler consumes one coordinate-table selector",
    },
    {
        "opcode": "3B",
        "verified_owned_width": 2,
        "reason": "handler reads one immediate and advances 02",
    },
    {
        "opcode": "3C",
        "verified_owned_width": 2,
        "reason": "handler reads one variable selector and advances 02",
    },
    {
        "opcode": "9B",
        "verified_owned_width": 2,
        "reason": "shared target-mode path stores consuming delta 02",
    },
    {
        "opcode": "C5",
        "verified_owned_width": 2,
        "reason": "handler reads one parameter and stores consuming delta 02",
    },
    {
        "opcode": "DA",
        "verified_owned_width": 1,
        "reason": "handler reads relative +1 but advances only 01",
    },
)


LIMITATIONS: Final = (
    "This is a static possible-context tokenization of the config-selected "
    "primary package supplement, not runtime reachability or frequency.",
    "The width vector is a reviewer-encoded static interpretation of the "
    "pinned canonical handler corpus; hashes detect byte drift but do not "
    "automatically derive handler semantics.",
    "Eventual consuming widths do not prove that wait and conditional "
    "handlers advance on every invocation or terminate at runtime.",
    "Command 21 is modeled with both fallthrough and saved-parent-return "
    "possibilities; command 25 is modeled with both fallthrough and script "
    "stop possibilities.",
    "The command-1E closure follows the canonical fixed CE target table only; "
    "it does not approve expanded nested-script targets or a high-package "
    "policy.",
    "Auxiliary animation, graphics, palette, effect, sound, and fixed-bank "
    "readers remain outside this command-tokenization tranche.",
    "No command stream is assigned a visual, story, balance, or gameplay "
    "meaning by this report.",
)


NONCLAIMS: Final = (
    "No logical PC 07, Schala action, player-Tech package selector 80-8F, "
    "original Tech, item, sprite, or battle runtime is bound.",
    "No production hook, allocation, expanded-bank reader, helper, ROM "
    "mutation, patch, save, state, trace, or emulator runtime result is "
    "produced.",
    "No unused opcode, default-handler opcode, marker byte, table entry, "
    "stream gap, or neighboring byte is claimed free space.",
    "The complete command grammar does not by itself prove a safe expanded "
    "package, command-1E adaptation, or auxiliary-table adaptation.",
    "Unkeyed hashes in this report are reproducibility and drift checks, not "
    "authentication or ownership claims.",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _metadata_ledger_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _hex2(value: int) -> str:
    return f"{value:02X}"


def _hex4(value: int) -> str:
    return f"{value:04X}"


def _hex6(value: int) -> str:
    return f"{value:06X}"


def _slice_snes(rom: bytes, start: int, end_exclusive: int) -> bytes:
    try:
        start_offset = topology.snes_hirom_to_file(start)
        end_offset = topology.snes_hirom_to_file(end_exclusive)
    except topology.BattlePackageTopologyAuditError as exc:
        raise BattleCommandGrammarAuditError(str(exc)) from exc
    if end_offset <= start_offset:
        raise BattleCommandGrammarAuditError(
            "bounded SNES extent does not map forward"
        )
    result = rom[start_offset:end_offset]
    if len(result) != end_offset - start_offset:
        raise BattleCommandGrammarAuditError("bounded ROM read truncated")
    return result


def _observe_span(rom: bytes, spec: SpanSpec) -> dict[str, Any]:
    payload = _slice_snes(rom, spec.start, spec.end_exclusive)
    digest = _sha256_bytes(payload)
    if digest != spec.expected_sha256:
        raise BattleCommandGrammarAuditError(
            f"machine witness drifted: {spec.name}"
        )
    return {
        "name": spec.name,
        "label": spec.label,
        "start": _hex6(spec.start),
        "end_exclusive": _hex6(spec.end_exclusive),
        "size": len(payload),
        "sha256": digest,
    }


def _dispatch_handlers(rom: bytes) -> tuple[int, ...]:
    payload = _slice_snes(rom, 0xC17A6B, 0xC17C21)
    if len(payload) != DISPATCHED_OPCODE_END_EXCLUSIVE * 2:
        raise BattleCommandGrammarAuditError(
            "command dispatch table geometry drifted"
        )
    handlers = tuple(
        int.from_bytes(payload[index : index + 2], "little")
        for index in range(0, len(payload), 2)
    )
    if len(set(handlers)) != 115:
        raise BattleCommandGrammarAuditError(
            "command handler-family count drifted"
        )
    if handlers.count(DEFAULT_HANDLER_OFFSET) != 70:
        raise BattleCommandGrammarAuditError(
            "default-handler opcode count drifted"
        )
    if handlers[STOP_OPCODE] != 0x4CF0:
        raise BattleCommandGrammarAuditError("command 00 handler drifted")
    if handlers[SUBSCRIPT_CALL_OPCODE] != 0x56CC:
        raise BattleCommandGrammarAuditError("command 1E handler drifted")
    if handlers[RETURN_OPCODE] != 0x56FB:
        raise BattleCommandGrammarAuditError("command 1F handler drifted")
    if handlers[VARIABLE_OPCODE] != 0x621B:
        raise BattleCommandGrammarAuditError("command 80 handler drifted")
    if handlers[LOOKAHEAD_OPCODE] != 0x7579:
        raise BattleCommandGrammarAuditError("command DA handler drifted")
    return handlers


def _handler_families(
    handlers: Sequence[int],
) -> tuple[str, ...]:
    family_by_address = {
        address: f"H{index:03d}"
        for index, address in enumerate(sorted(set(handlers)))
    }
    return tuple(family_by_address[address] for address in handlers)


def flow_for_opcode(opcode: int, handlers: Sequence[int]) -> str:
    if type(opcode) is not int or not 0 <= opcode <= 0xFF:
        raise BattleCommandGrammarAuditError(
            f"invalid command opcode: {opcode!r}"
        )
    if opcode >= DISPATCHED_OPCODE_END_EXCLUSIVE:
        return "undispatched-sticky-marker"
    if handlers[opcode] == DEFAULT_HANDLER_OFFSET:
        return "default-handler-sticky"
    if opcode == STOP_OPCODE:
        return "stop-current-script"
    if opcode == SUBSCRIPT_CALL_OPCODE:
        return "fixed-ce-subscript-call-with-parent-continuation"
    if opcode == RETURN_OPCODE:
        return "restore-saved-parent"
    if opcode == CONDITIONAL_RETURN_OPCODE:
        return "conditional-fallthrough-or-restore-saved-parent"
    if opcode == CONDITIONAL_STOP_OPCODE:
        return "conditional-fallthrough-or-stop"
    return "eventual-sequential-fallthrough"


def token_shape(opcode: int, first_payload_byte: int | None = None) -> TokenShape:
    """Return the engine-owned token extent without reading a ROM stream.

    Command 80 stores the low nibble N, reads N bytes starting at relative +1,
    and advances N+1.  For N=0, the decrement loop wraps and reads 256 bytes
    while the computed advance remains 1; those 256 bytes are lookahead, not
    token ownership.  Command DA has a fixed one-byte token but reads +1.
    """

    if type(opcode) is not int or not 0 <= opcode <= 0xFF:
        raise BattleCommandGrammarAuditError(
            f"invalid command opcode: {opcode!r}"
        )
    if opcode >= DISPATCHED_OPCODE_END_EXCLUSIVE:
        return TokenShape(1, "undispatched-marker-byte", ())
    if opcode == VARIABLE_OPCODE:
        if type(first_payload_byte) is not int or not 0 <= first_payload_byte <= 0xFF:
            raise BattleCommandGrammarAuditError(
                "command 80 requires its first payload byte"
            )
        count = first_payload_byte & 0x0F
        if count == 0:
            return TokenShape(
                1,
                "low-nibble-zero-wrap: owned=1, read-lookahead=256",
                tuple(range(1, 257)),
            )
        return TokenShape(
            count + 1,
            "low-nibble-N: owned=N+1",
            (),
        )
    width = FIXED_TOKEN_WIDTHS[opcode]
    if type(width) is not int or width < 1:
        raise BattleCommandGrammarAuditError(
            f"invalid fixed token width for opcode {opcode:02X}"
        )
    lookahead = (1,) if opcode == LOOKAHEAD_OPCODE else ()
    rule = "fixed"
    if opcode == LOOKAHEAD_OPCODE:
        rule = "fixed-owned-1-with-read-lookahead-at-plus-1"
    return TokenShape(width, rule, lookahead)


def _grammar_rows(
    handlers: Sequence[int],
    families: Sequence[str],
) -> list[dict[str, Any]]:
    if len(handlers) != DISPATCHED_OPCODE_END_EXCLUSIVE:
        raise BattleCommandGrammarAuditError("handler vector length drifted")
    rows: list[dict[str, Any]] = []
    for opcode in range(0x100):
        flow = flow_for_opcode(opcode, handlers)
        if opcode == VARIABLE_OPCODE:
            width: int | str = "low-nibble-N; N=0 owns 1, else owns N+1"
        elif opcode < DISPATCHED_OPCODE_END_EXCLUSIVE:
            value = FIXED_TOKEN_WIDTHS[opcode]
            if type(value) is not int:
                raise BattleCommandGrammarAuditError(
                    "fixed grammar row unexpectedly lacks width"
                )
            width = value
        else:
            width = 1
        row = {
            "opcode": _hex2(opcode),
            "dispatch": (
                "table-00-DA"
                if opcode < DISPATCHED_OPCODE_END_EXCLUSIVE
                else "dispatcher-exit-DB-FF"
            ),
            "handler_family": (
                families[opcode]
                if opcode < DISPATCHED_OPCODE_END_EXCLUSIVE
                else None
            ),
            "owned_width": width,
            "flow": flow,
            "known_lookahead_relative_offsets": (
                [1] if opcode == LOOKAHEAD_OPCODE else []
            ),
            "width_authority": (
                "canonical-handler-static-analysis"
                if opcode < DISPATCHED_OPCODE_END_EXCLUSIVE
                else "dispatcher-boundary"
            ),
        }
        rows.append(row)
    return rows


def _grammar_summary(
    handlers: Sequence[int],
    families: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    flow_counts = Counter(row["flow"] for row in rows)
    fixed_width_counts = Counter(
        int(row["owned_width"])
        for row in rows
        if type(row["owned_width"]) is int
    )
    default_opcodes = [
        opcode
        for opcode, handler in enumerate(handlers)
        if handler == DEFAULT_HANDLER_OFFSET
    ]
    width_ledger = [
        [opcode, FIXED_TOKEN_WIDTHS[opcode]]
        for opcode in range(DISPATCHED_OPCODE_END_EXCLUSIVE)
    ]
    handler_relation_ledger = [
        [opcode, families[opcode]]
        for opcode in range(DISPATCHED_OPCODE_END_EXCLUSIVE)
    ]
    family_widths: dict[str, set[int | None]] = {}
    family_counts = Counter(families)
    for opcode, family in enumerate(families):
        family_widths.setdefault(family, set()).add(
            FIXED_TOKEN_WIDTHS[opcode]
        )
    multi_width_families = {
        family: widths
        for family, widths in family_widths.items()
        if len(widths) > 1
    }
    if multi_width_families:
        raise BattleCommandGrammarAuditError(
            "one canonical handler family has inconsistent owned widths"
        )
    return {
        "opcode_domain_count": 256,
        "dispatch_table_opcode_count": DISPATCHED_OPCODE_END_EXCLUSIVE,
        "undispatched_marker_opcode_count": (
            0x100 - DISPATCHED_OPCODE_END_EXCLUSIVE
        ),
        "distinct_handler_family_count": len(set(handlers)),
        "shared_handler_family_count": sum(
            count > 1 for count in family_counts.values()
        ),
        "handler_family_with_multiple_owned_width_count": 0,
        "default_handler_opcode_count": len(default_opcodes),
        "fixed_width_opcode_count": 255,
        "variable_width_opcode_count": 1,
        "variable_width_opcode": _hex2(VARIABLE_OPCODE),
        "width_derivation_mode": (
            "reviewer-encoded canonical-handler static analysis"
        ),
        "community_parser_role": "comparison lead only; not authority",
        "flow_class_counts": {
            key: flow_counts[key] for key in sorted(flow_counts)
        },
        "fixed_owned_width_counts": {
            str(key): fixed_width_counts[key]
            for key in sorted(fixed_width_counts)
        },
        "fixed_width_ledger_sha256": _metadata_ledger_sha256(width_ledger),
        "handler_relation_ledger_sha256": _metadata_ledger_sha256(
            handler_relation_ledger
        ),
        "default_opcode_ledger_sha256": _metadata_ledger_sha256(
            default_opcodes
        ),
        "grammar_ledger_sha256": _metadata_ledger_sha256(list(rows)),
        "correction_witnesses": list(CORRECTION_WITNESSES),
        "da_owned_width": 1,
        "da_known_lookahead_relative_offsets": [1],
        "command_80_zero_nibble_owned_width": 1,
        "command_80_zero_nibble_read_lookahead_count": 256,
    }


def _extract_root_topology(rom: bytes) -> RootTopology:
    try:
        topology.audit_rom(rom)
        contexts = topology._build_route_contexts(rom)
        route_descriptors: dict[
            str, dict[int, topology.PackageDescriptor]
        ] = {}
        for route_name, route_spec in topology.ROUTE_SPECS.items():
            _, descriptors = topology._analyze_route(
                rom,
                route_spec,
                contexts[route_name],
            )
            route_descriptors[route_name] = descriptors
    except topology.BattlePackageTopologyAuditError as exc:
        raise BattleCommandGrammarAuditError(
            f"package-topology dependency failed: {exc}"
        ) from exc

    declared = frozenset().union(
        *(
            topology._physical_script_set(route_descriptors[name])
            for name in DECLARED_ROUTE_NAMES
        )
    )
    config = frozenset().union(
        *(
            topology._physical_script_set(route_descriptors[name])
            for name in CONFIG_ROUTE_NAMES
        )
    )
    if not declared or not config or not declared < config:
        raise BattleCommandGrammarAuditError(
            "declared/config-selected root-set relationship drifted"
        )

    descriptor_map: dict[tuple[int, int], topology.PackageDescriptor] = {}
    for name in CONFIG_ROUTE_NAMES:
        for descriptor in route_descriptors[name].values():
            key = (descriptor.bank, descriptor.root_offset)
            prior = descriptor_map.setdefault(key, descriptor)
            if prior != descriptor:
                raise BattleCommandGrammarAuditError(
                    "shared descriptor decoded inconsistently"
                )
    spans = tuple(
        sorted(
            (
                descriptor.bank,
                descriptor.root_offset,
                descriptor.end_offset_exclusive,
            )
            for descriptor in descriptor_map.values()
        )
    )
    return RootTopology(declared, config, spans)


def _root_summary(roots: RootTopology) -> dict[str, Any]:
    declared_rows = [list(row) for row in sorted(roots.declared_roots)]
    config_rows = [list(row) for row in sorted(roots.config_roots)]
    supplement_rows = [
        list(row)
        for row in sorted(roots.config_roots - roots.declared_roots)
    ]

    def counts_by_bank(values: frozenset[tuple[int, int]]) -> dict[str, int]:
        counts = Counter(bank for bank, _ in values)
        return {_hex2(bank): counts[bank] for bank in sorted(counts)}

    return {
        "declared_direct_root_count": len(roots.declared_roots),
        "declared_direct_root_count_by_bank": counts_by_bank(
            roots.declared_roots
        ),
        "config_selected_direct_root_count": len(roots.config_roots),
        "config_selected_direct_root_count_by_bank": counts_by_bank(
            roots.config_roots
        ),
        "config_supplement_only_root_count": len(supplement_rows),
        "declared_is_strict_subset_of_config_selected": True,
        "declared_direct_root_ledger_sha256": _metadata_ledger_sha256(
            declared_rows
        ),
        "config_selected_direct_root_ledger_sha256": (
            _metadata_ledger_sha256(config_rows)
        ),
        "config_supplement_only_root_ledger_sha256": (
            _metadata_ledger_sha256(supplement_rows)
        ),
        "selected_descriptor_span_count": len(roots.descriptor_spans),
        "selected_descriptor_span_ledger_sha256": (
            _metadata_ledger_sha256([list(row) for row in roots.descriptor_spans])
        ),
    }


def _bank_file_offset(bank: int, offset: int) -> int:
    if type(bank) is not int or bank not in SCRIPT_RANGES:
        raise BattleCommandGrammarAuditError(
            f"unsupported script bank: {bank!r}"
        )
    if type(offset) is not int or not 0 <= offset < 0x10000:
        raise BattleCommandGrammarAuditError(
            f"script offset outside bank: {offset!r}"
        )
    return ((bank & 0x3F) << 16) + offset


def _read_script_byte(rom: bytes, bank: int, offset: int) -> int:
    file_offset = _bank_file_offset(bank, offset)
    if file_offset >= len(rom):
        raise BattleCommandGrammarAuditError("script read truncated")
    return rom[file_offset]


def _validate_script_extent(bank: int, offset: int, width: int) -> None:
    if type(width) is not int or width < 1:
        raise BattleCommandGrammarAuditError("invalid token extent")
    start, end_exclusive = SCRIPT_RANGES[bank]
    if not start <= offset < end_exclusive:
        raise BattleCommandGrammarAuditError(
            f"script entry outside audited range in bank {bank:02X}"
        )
    if offset + width > end_exclusive:
        raise BattleCommandGrammarAuditError(
            f"script token crosses audited range in bank {bank:02X}"
        )


def _target_table(rom: bytes) -> tuple[int, ...]:
    payload = _slice_snes(rom, 0xCE0000, 0xCE0200)
    return tuple(
        int.from_bytes(payload[index : index + 2], "little")
        for index in range(0, len(payload), 2)
    )


def _decode_token(
    rom: bytes,
    *,
    bank: int,
    offset: int,
    handlers: Sequence[int],
    families: Sequence[str],
) -> DecodedToken:
    _validate_script_extent(bank, offset, 1)
    opcode = _read_script_byte(rom, bank, offset)
    first_payload = None
    if opcode == VARIABLE_OPCODE:
        _validate_script_extent(bank, offset, 2)
        first_payload = _read_script_byte(rom, bank, offset + 1)
    shape = token_shape(opcode, first_payload)
    _validate_script_extent(bank, offset, shape.owned_width)
    for relative in shape.known_lookahead_offsets:
        _validate_script_extent(bank, offset + relative, 1)
        _read_script_byte(rom, bank, offset + relative)
    return DecodedToken(
        bank=bank,
        offset=offset,
        opcode=opcode,
        owned_width=shape.owned_width,
        width_rule=shape.width_rule,
        flow=flow_for_opcode(opcode, handlers),
        handler_family=(
            families[opcode]
            if opcode < DISPATCHED_OPCODE_END_EXCLUSIVE
            else None
        ),
        known_lookahead_offsets=shape.known_lookahead_offsets,
    )


def _token_signature(token: DecodedToken) -> tuple[Any, ...]:
    return (
        token.opcode,
        token.owned_width,
        token.width_rule,
        token.flow,
        token.handler_family,
        token.known_lookahead_offsets,
    )


def _register_token(
    token: DecodedToken,
    *,
    tokens: dict[tuple[int, int], DecodedToken],
    coverage: dict[tuple[int, int], tuple[int, int]],
) -> None:
    key = (token.bank, token.offset)
    prior = tokens.get(key)
    if prior is not None and _token_signature(prior) != _token_signature(token):
        raise BattleCommandGrammarAuditError(
            "one token start decoded inconsistently"
        )
    for relative in range(token.owned_width):
        byte_key = (token.bank, token.offset + relative)
        owner = coverage.get(byte_key)
        if owner is not None and owner != key:
            raise BattleCommandGrammarAuditError(
                "command token extents overlap at different starts"
            )
    tokens.setdefault(key, token)
    for relative in range(token.owned_width):
        coverage.setdefault((token.bank, token.offset + relative), key)


def _terminal_kind(token: DecodedToken) -> str | None:
    if token.flow == "stop-current-script":
        return "stop-current-script"
    if token.flow == "restore-saved-parent":
        return "restore-saved-parent"
    if token.flow == "default-handler-sticky":
        return "default-handler-sticky"
    if token.flow == "undispatched-sticky-marker":
        return "undispatched-sticky-marker"
    return None


def _maximum_nested_depth(
    entry_targets: Mapping[tuple[int, int], frozenset[tuple[int, int]]],
    direct_roots: frozenset[tuple[int, int]],
) -> int:
    memo: dict[tuple[int, int], int] = {}

    def visit(entry: tuple[int, int], active: frozenset[tuple[int, int]]) -> int:
        if entry in active:
            raise BattleCommandGrammarAuditError(
                "command-1E entrypoint graph contains a cycle"
            )
        if entry in memo:
            return memo[entry]
        targets = entry_targets.get(entry, frozenset())
        if not targets:
            memo[entry] = 0
            return 0
        value = 1 + max(
            visit(target, active | {entry}) for target in targets
        )
        memo[entry] = value
        return value

    return max(visit(root, frozenset()) for root in direct_roots)


def _descriptor_intersection_summary(
    *,
    tokens: Mapping[tuple[int, int], DecodedToken],
    entry_traces: Mapping[
        tuple[int, int], Sequence[tuple[int, int]]
    ],
    descriptor_spans: Sequence[tuple[int, int, int]],
) -> DescriptorIntersectionSummary:
    rows: list[tuple[int, int, int, int, int, int, int]] = []
    reached_spans: set[tuple[int, int, int]] = set()
    token_starts_inside: set[tuple[int, int]] = set()
    intersecting_token_keys: set[tuple[int, int]] = set()
    owned_bytes_inside: set[tuple[int, int]] = set()
    for token_key, token in sorted(tokens.items()):
        for descriptor_bank, descriptor_start, descriptor_end in (
            descriptor_spans
        ):
            if descriptor_bank != token.bank:
                continue
            overlap_start = max(token.offset, descriptor_start)
            overlap_end = min(
                token.offset + token.owned_width,
                descriptor_end,
            )
            if overlap_start >= overlap_end:
                continue
            rows.append(
                (
                    token.bank,
                    token.offset,
                    token.opcode,
                    descriptor_start,
                    descriptor_end,
                    overlap_start,
                    overlap_end,
                )
            )
            reached_spans.add(
                (descriptor_bank, descriptor_start, descriptor_end)
            )
            intersecting_token_keys.add(token_key)
            if descriptor_start <= token.offset < descriptor_end:
                token_starts_inside.add(token_key)
            owned_bytes_inside.update(
                (token.bank, offset)
                for offset in range(overlap_start, overlap_end)
            )
    entrypoints_reaching = frozenset(
        entry
        for entry, trace in entry_traces.items()
        if any(token_key in intersecting_token_keys for token_key in trace)
    )
    return DescriptorIntersectionSummary(
        rows=tuple(rows),
        reached_spans=frozenset(reached_spans),
        token_starts_inside=frozenset(token_starts_inside),
        intersecting_token_keys=frozenset(intersecting_token_keys),
        owned_bytes_inside=frozenset(owned_bytes_inside),
        entrypoints_reaching=entrypoints_reaching,
    )


def _stream_census(
    rom: bytes,
    *,
    roots: RootTopology,
    handlers: Sequence[int],
    families: Sequence[str],
) -> dict[str, Any]:
    target_table = _target_table(rom)
    pending = deque(sorted(roots.config_roots))
    queued = set(roots.config_roots)
    nested_targets: set[tuple[int, int]] = set()
    tokens: dict[tuple[int, int], DecodedToken] = {}
    coverage: dict[tuple[int, int], tuple[int, int]] = {}
    entry_traces: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {}
    entry_terminals: dict[tuple[int, int], str] = {}
    entry_targets: dict[
        tuple[int, int], frozenset[tuple[int, int]]
    ] = {}
    call_edges: set[tuple[int, int, int, int, int]] = set()

    while pending:
        entry = pending.popleft()
        if entry in entry_traces:
            continue
        bank, offset = entry
        _validate_script_extent(bank, offset, 1)
        local_starts: set[tuple[int, int]] = set()
        trace: list[tuple[int, int]] = []
        targets_from_entry: set[tuple[int, int]] = set()
        cursor = offset
        while True:
            key = (bank, cursor)
            if key in local_starts:
                raise BattleCommandGrammarAuditError(
                    "sequential command tokenization contains a cycle"
                )
            if len(trace) >= 0x10000:
                raise BattleCommandGrammarAuditError(
                    "one stream exceeded the bounded token limit"
                )
            local_starts.add(key)
            token = _decode_token(
                rom,
                bank=bank,
                offset=cursor,
                handlers=handlers,
                families=families,
            )
            _register_token(
                token,
                tokens=tokens,
                coverage=coverage,
            )
            trace.append(key)

            terminal = _terminal_kind(token)
            if terminal is not None:
                entry_terminals[entry] = terminal
                break

            if token.opcode == SUBSCRIPT_CALL_OPCODE:
                operand = _read_script_byte(rom, bank, cursor + 1)
                target = (0xCE, target_table[operand])
                _validate_script_extent(target[0], target[1], 1)
                nested_targets.add(target)
                targets_from_entry.add(target)
                call_edges.add(
                    (bank, cursor, operand, target[0], target[1])
                )
                if target not in queued:
                    queued.add(target)
                    pending.append(target)

            cursor += token.owned_width

        entry_traces[entry] = tuple(trace)
        entry_targets[entry] = frozenset(targets_from_entry)

    if set(entry_traces) != queued:
        raise BattleCommandGrammarAuditError(
            "not every queued direct/nested entrypoint was decoded"
        )
    if not nested_targets:
        raise BattleCommandGrammarAuditError(
            "canonical command-1E closure unexpectedly became empty"
        )
    if not nested_targets <= set(entry_traces):
        raise BattleCommandGrammarAuditError(
            "not every command-1E target was decoded"
        )

    token_rows = [
        [
            token.bank,
            token.offset,
            token.opcode,
            token.owned_width,
            token.width_rule,
            token.flow,
            token.handler_family,
            list(token.known_lookahead_offsets),
        ]
        for _, token in sorted(tokens.items())
    ]
    coverage_rows = [
        [bank, offset, owner[0], owner[1]]
        for (bank, offset), owner in sorted(coverage.items())
    ]
    entry_rows = [
        [
            entry[0],
            entry[1],
            len(entry_traces[entry]),
            entry_terminals[entry],
        ]
        for entry in sorted(entry_traces)
    ]
    call_rows = [list(row) for row in sorted(call_edges)]
    descriptor_intersections = _descriptor_intersection_summary(
        tokens=tokens,
        entry_traces=entry_traces,
        descriptor_spans=roots.descriptor_spans,
    )

    opcode_counts = Counter(token.opcode for token in tokens.values())
    flow_counts = Counter(token.flow for token in tokens.values())
    terminal_counts = Counter(entry_terminals.values())
    direct_terminal_counts = Counter(
        entry_terminals[entry] for entry in roots.config_roots
    )
    nested_terminal_counts = Counter(
        entry_terminals[entry] for entry in nested_targets
    )
    width80_counts = Counter(
        token.owned_width
        for token in tokens.values()
        if token.opcode == VARIABLE_OPCODE
    )
    zero80_count = sum(
        1
        for token in tokens.values()
        if token.opcode == VARIABLE_OPCODE
        and token.width_rule.startswith("low-nibble-zero-wrap")
    )
    operands = {row[2] for row in call_edges}
    edge_targets = {(row[3], row[4]) for row in call_edges}
    nested_with_calls = {
        entry
        for entry in nested_targets
        if entry_targets.get(entry, frozenset())
    }
    nested_trace_opcode_counts = Counter(
        tokens[token_key].opcode
        for entry in nested_targets
        for token_key in entry_traces[entry]
    )

    if edge_targets != nested_targets:
        raise BattleCommandGrammarAuditError(
            "command-1E edge/target closure drifted"
        )
    if any(
        token.opcode == LOOKAHEAD_OPCODE
        and token.owned_width != 1
        for token in tokens.values()
    ):
        raise BattleCommandGrammarAuditError(
            "command-DA ownership drifted"
        )
    if any(
        entry_terminals[entry] != "restore-saved-parent"
        for entry in nested_targets
    ):
        raise BattleCommandGrammarAuditError(
            "canonical nested target no longer ends in command 1F"
        )
    if any(
        entry_terminals[entry] == "restore-saved-parent"
        for entry in roots.config_roots
    ):
        raise BattleCommandGrammarAuditError(
            "a direct package stream unexpectedly ends in command 1F"
        )

    max_depth = _maximum_nested_depth(
        entry_targets,
        roots.config_roots,
    )
    return {
        "direct_entrypoint_count": len(roots.config_roots),
        "nested_entrypoint_count": len(nested_targets),
        "closure_entrypoint_count": len(entry_traces),
        "unique_token_start_count": len(tokens),
        "unique_owned_byte_count": len(coverage),
        "total_entrypoint_traversal_token_count": sum(
            len(trace) for trace in entry_traces.values()
        ),
        "minimum_tokens_per_entrypoint": min(
            len(trace) for trace in entry_traces.values()
        ),
        "maximum_tokens_per_entrypoint": max(
            len(trace) for trace in entry_traces.values()
        ),
        "distinct_observed_opcode_count": len(opcode_counts),
        "unobserved_dispatched_opcode_count": len(
            set(range(DISPATCHED_OPCODE_END_EXCLUSIVE)) - set(opcode_counts)
        ),
        "observed_opcode_frequency": {
            _hex2(opcode): opcode_counts[opcode]
            for opcode in sorted(opcode_counts)
        },
        "observed_flow_frequency": {
            key: flow_counts[key] for key in sorted(flow_counts)
        },
        "entrypoint_terminal_counts": {
            key: terminal_counts[key] for key in sorted(terminal_counts)
        },
        "direct_entrypoint_terminal_counts": {
            key: direct_terminal_counts[key]
            for key in sorted(direct_terminal_counts)
        },
        "nested_entrypoint_terminal_counts": {
            key: nested_terminal_counts[key]
            for key in sorted(nested_terminal_counts)
        },
        "command_1e_site_count": opcode_counts[SUBSCRIPT_CALL_OPCODE],
        "command_1e_distinct_operand_count": len(operands),
        "command_1e_distinct_target_count": len(edge_targets),
        "command_1e_operand_to_target_alias_count": (
            len(operands) - len(edge_targets)
        ),
        "command_1f_site_count": opcode_counts[RETURN_OPCODE],
        "nested_entrypoint_with_command_1e_count": len(nested_with_calls),
        "nested_command_21_conditional_return_site_count": (
            nested_trace_opcode_counts[CONDITIONAL_RETURN_OPCODE]
        ),
        "nested_command_25_conditional_stop_site_count": (
            nested_trace_opcode_counts[CONDITIONAL_STOP_OPCODE]
        ),
        "maximum_transitive_command_1e_depth": max_depth,
        "command_21_conditional_return_site_count": opcode_counts[
            CONDITIONAL_RETURN_OPCODE
        ],
        "command_25_conditional_stop_site_count": opcode_counts[
            CONDITIONAL_STOP_OPCODE
        ],
        "command_80_site_count": opcode_counts[VARIABLE_OPCODE],
        "command_80_owned_width_frequency": {
            str(width): width80_counts[width]
            for width in sorted(width80_counts)
        },
        "command_80_zero_nibble_site_count": zero80_count,
        "command_da_lookahead_site_count": opcode_counts[LOOKAHEAD_OPCODE],
        "default_handler_sticky_site_count": flow_counts[
            "default-handler-sticky"
        ],
        "undispatched_marker_site_count": flow_counts[
            "undispatched-sticky-marker"
        ],
        "token_extent_overlap_conflict_count": 0,
        "token_start_inside_selected_descriptor_count": len(
            descriptor_intersections.token_starts_inside
        ),
        "owned_token_byte_inside_selected_descriptor_count": len(
            descriptor_intersections.owned_bytes_inside
        ),
        "selected_descriptor_span_reached_by_token_count": len(
            descriptor_intersections.reached_spans
        ),
        "entrypoint_reaching_selected_descriptor_count": len(
            descriptor_intersections.entrypoints_reaching
        ),
        "descriptor_token_intersection_ledger_sha256": (
            _metadata_ledger_sha256(
                [list(row) for row in descriptor_intersections.rows]
            )
        ),
        "entrypoint_reaching_descriptor_ledger_sha256": (
            _metadata_ledger_sha256(
                [
                    list(row)
                    for row in sorted(
                        descriptor_intersections.entrypoints_reaching
                    )
                ]
            )
        ),
        "all_nested_fallthrough_traces_end_in_restore_parent": True,
        "no_direct_entrypoint_ends_in_restore_parent": True,
        "token_ledger_sha256": _metadata_ledger_sha256(token_rows),
        "owned_byte_ledger_sha256": _metadata_ledger_sha256(coverage_rows),
        "entrypoint_termination_ledger_sha256": _metadata_ledger_sha256(
            entry_rows
        ),
        "command_1e_edge_ledger_sha256": _metadata_ledger_sha256(call_rows),
        "nested_target_ledger_sha256": _metadata_ledger_sha256(
            [list(row) for row in sorted(nested_targets)]
        ),
        "opcode_frequency_ledger_sha256": _metadata_ledger_sha256(
            [[opcode, opcode_counts[opcode]] for opcode in sorted(opcode_counts)]
        ),
    }


def observe_rom(rom: bytes) -> dict[str, Any]:
    """Return the closed semantic result before reference comparison."""

    try:
        topology.validate_canonical_rom(rom)
    except topology.BattlePackageTopologyAuditError as exc:
        raise BattleCommandGrammarAuditError(str(exc)) from exc
    for span in MACHINE_SPANS:
        _observe_span(rom, span)
    handlers = _dispatch_handlers(rom)
    families = _handler_families(handlers)
    rows = _grammar_rows(handlers, families)
    roots = _extract_root_topology(rom)
    return {
        "grammar": _grammar_summary(handlers, families, rows),
        "direct_roots": _root_summary(roots),
        "stream_census": _stream_census(
            rom,
            roots=roots,
            handlers=handlers,
            families=families,
        ),
    }


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema",
        "version",
        "evidence_level",
        "scope",
        "expected_results",
        "limitations",
        "nonclaims",
    }
    if set(contract) != expected_keys:
        raise BattleCommandGrammarAuditError(
            "reference contract top-level shape drifted"
        )
    if contract["schema"] != REFERENCE_SCHEMA or contract["version"] != 1:
        raise BattleCommandGrammarAuditError(
            "reference contract identity drifted"
        )
    if contract["evidence_level"] != "verified-static":
        raise BattleCommandGrammarAuditError(
            "reference evidence level drifted"
        )
    if not isinstance(contract["scope"], Mapping):
        raise BattleCommandGrammarAuditError("reference scope is invalid")
    expected = contract["expected_results"]
    if not isinstance(expected, Mapping) or set(expected) != {
        "grammar",
        "direct_roots",
        "stream_census",
    }:
        raise BattleCommandGrammarAuditError(
            "reference expected-results shape drifted"
        )
    limitations = contract["limitations"]
    if not isinstance(limitations, list) or not all(
        type(value) is str for value in limitations
    ):
        raise BattleCommandGrammarAuditError(
            "reference limitations are invalid"
        )
    if limitations != list(LIMITATIONS):
        raise BattleCommandGrammarAuditError(
            "reference limitations drifted"
        )
    nonclaims = contract["nonclaims"]
    if not isinstance(nonclaims, list) or not all(
        type(value) is str for value in nonclaims
    ):
        raise BattleCommandGrammarAuditError(
            "reference nonclaims are invalid"
        )
    if nonclaims != list(NONCLAIMS):
        raise BattleCommandGrammarAuditError(
            "reference nonclaims drifted"
        )


def load_reference_contract() -> dict[str, Any]:
    try:
        source = REFERENCE_PATH.read_bytes()
    except OSError as exc:
        raise BattleCommandGrammarAuditError(
            f"cannot read reference contract: {REFERENCE_PATH.name}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise BattleCommandGrammarAuditError(
            "reference contract size drifted"
        )
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise BattleCommandGrammarAuditError(
            "reference contract hash drifted"
        )
    try:
        value = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BattleCommandGrammarAuditError(
            "reference contract is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise BattleCommandGrammarAuditError(
            "reference contract is not an object"
        )
    _validate_reference_contract(value)
    return value


def _rom_identity(rom: bytes) -> dict[str, Any]:
    try:
        return topology.validate_canonical_rom(rom)
    except topology.BattlePackageTopologyAuditError as exc:
        raise BattleCommandGrammarAuditError(str(exc)) from exc


def _auditor_source_identity() -> dict[str, Any]:
    source_path = Path(__file__).resolve()
    source = source_path.read_bytes()
    return {
        "path": "tools/audit_battle_command_grammar_census_v0.py",
        "size": len(source),
        "sha256": _sha256_bytes(source),
    }


def _attach_artifact_identity(report: dict[str, Any]) -> dict[str, Any]:
    result = dict(report)
    result["artifact_identity"] = {
        "canonical_json_sha256_excluding_artifact_identity": (
            _metadata_ledger_sha256(report)
        )
    }
    return result


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pinned_contract = load_reference_contract()
    if contract is None:
        contract = pinned_contract
    else:
        _validate_reference_contract(contract)
        if contract != pinned_contract:
            raise BattleCommandGrammarAuditError(
                "caller-supplied reference contract differs from pinned file"
            )
    observed = observe_rom(rom)
    if observed != contract["expected_results"]:
        raise BattleCommandGrammarAuditError(
            "canonical command grammar or stream census drifted"
        )

    handlers = _dispatch_handlers(rom)
    families = _handler_families(handlers)
    grammar_rows = _grammar_rows(handlers, families)
    report = {
        "schema": SCHEMA,
        "version": 1,
        "auditor_version": AUDITOR_VERSION,
        "status": STATUS,
        "evidence_ceiling": (
            "verified-static metadata-only config-selected primary-package "
            "tokenization and fixed-CE command-1E closure"
        ),
        "scope": dict(contract["scope"]),
        "inputs": {
            "rom": _rom_identity(rom),
            "package_topology_dependency": {
                "schema": topology.SCHEMA,
                "reference_sha256": topology.REFERENCE_SHA256,
                "authority": "closed verified-static dependency",
            },
            "reference_contract": {
                "path": "references/battle_command_grammar_census_v0.json",
                "size": REFERENCE_SIZE,
                "sha256": REFERENCE_SHA256,
            },
        },
        "machine_code_contract": [
            _observe_span(rom, span) for span in MACHINE_SPANS
        ],
        "grammar": {
            "rows": grammar_rows,
            "summary": observed["grammar"],
            "handler_addresses_emitted": False,
            "raw_dispatch_words_emitted": False,
        },
        "direct_roots": observed["direct_roots"],
        "stream_census": observed["stream_census"],
        "gates": {
            "canonical_rom_hash_matched": True,
            "package_topology_dependency_passed": True,
            "all_machine_witnesses_matched": True,
            "all_256_opcode_bytes_classified": True,
            "all_config_selected_direct_roots_terminated": True,
            "all_discovered_nested_targets_terminated": True,
            "all_nested_fallthrough_traces_end_in_command_1f": True,
            "all_shared_token_starts_agree": True,
            "all_owned_token_extents_are_disjoint": True,
            "canonical_descriptor_token_alias_is_exactly_pinned": True,
            "raw_script_or_pointer_rows_emitted": False,
            "expanded_command_1e_policy_approved": False,
            "symbolic_high_package_bound": False,
            "runtime_performed": False,
            "rom_save_state_trace_mutation_performed": False,
            "patch_rom_or_output_file_emitted": False,
            "allocation_or_hook_approved": False,
        },
        "evidence": {
            "level": "verified-static",
            "runtime": False,
            "static_only": True,
            "canonical_rom_read_only": True,
            "metadata_only": True,
        },
        "reproduction": {
            "command": [
                "python",
                "-B",
                "tools/audit_battle_command_grammar_census_v0.py",
                "<canonical-us-rev0-headerless-rom>",
                "--compact",
            ],
            "output": "metadata-only JSON on stdout",
            "output_file_option_available": False,
            "expected_exit_code": 0,
            "expected_stderr": "empty",
            "expected_side_effects": "none",
            "auditor_source": _auditor_source_identity(),
            "reference_contract": {
                "path": "references/battle_command_grammar_census_v0.json",
                "size": REFERENCE_SIZE,
                "sha256": REFERENCE_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "nonclaims": list(NONCLAIMS),
    }
    return _attach_artifact_identity(report)


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise BattleCommandGrammarAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != topology.CANONICAL_ROM_SIZE:
            raise BattleCommandGrammarAuditError(
                f"expected {topology.CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except BattleCommandGrammarAuditError:
        raise
    except OSError as exc:
        raise BattleCommandGrammarAuditError(
            f"cannot read ROM input: {path}"
        ) from exc
    return audit_rom(rom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "rom",
        type=Path,
        help="headerless Chrono Trigger US Rev0 ROM; read-only",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print compact JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_rom_path(args.rom)
    except (BattleCommandGrammarAuditError, OSError, ValueError) as exc:
        print(f"battle command grammar audit failed: {exc}", file=sys.stderr)
        return 1
    if args.compact:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
