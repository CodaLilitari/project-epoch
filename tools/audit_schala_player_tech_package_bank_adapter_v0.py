#!/usr/bin/env python3
"""Audit the source-only Schala player-Tech package-bank adapter contract.

The host model keeps the player command, action-config row, package selector,
descriptor root, and direct script entrypoint as separate typed identities.  It
can prove the 128 canonical package sources from a pinned clean ROM and model a
synthetic expanded-bank source, but it writes no image, patch, table payload,
save, state, trace, or output file.

An absent extended binding is the only unbound representation.  Zero is never
treated as free space.  Animation command 1E is deliberately refused because
the canonical handler selects its subscript pointer from fixed bank CE even
when the parent script is bank-qualified.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Final


ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_PATH: Final = (
    ROOT / "references" / "schala_player_tech_package_bank_adapter_v0.json"
)
REFERENCE_SIZE: Final = 12_280
REFERENCE_SHA256: Final = (
    "dab2834afb28ea2b89e814747d4a079f"
    "ef7a403ec67eba592a7f866c88faa69e"
)

SCHEMA: Final = (
    "project-epoch-schala-player-tech-package-bank-adapter-contract-v0"
)
REPORT_SCHEMA: Final = (
    "project-epoch-schala-player-tech-package-bank-adapter-report-v0"
)
CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

CANONICAL_SELECTOR_FIRST: Final = 0x00
CANONICAL_SELECTOR_LAST: Final = 0x7F
EPOCH_PACKAGE_SELECTOR_FIRST: Final = 0x80
EPOCH_PACKAGE_SELECTOR_LAST: Final = 0x8F
SCHALA_FOCUS_PULSE_ACTION_ID: Final = 0x90
CANONICAL_PACKAGE_BANK: Final = 0xCE
BANK_SIZE: Final = 0x10000

EXPECTED_CANONICAL_BANK_VECTOR_SHA256: Final = (
    "8800a8e4e0109253ab8e82ea8119fd88"
    "ebcc17b40b1eaeb0e22c34593961ecde"
)
EXPECTED_CANONICAL_ROOT_VECTOR_SHA256: Final = (
    "074a9bca7aaa630085654200634002e8f"
    "3c0f251a5c3874a5b1c1237d713a4d1"
)
EXPECTED_CANONICAL_LEDGER_SHA256: Final = (
    "a88c3dd658b1d2a07b55417d9aa0eafb"
    "8c9b50efeee9d9b2f12971ced8f28343"
)

ALLOCATION_NAME_RE: Final = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
ALLOWED_SOURCE_KINDS: Final = frozenset({"canonical", "synthetic-test"})

EXPECTED_CANONICAL_DESCRIPTOR_GEOMETRY: Final = {
    "distinct_descriptor_count": 125,
    "selector_to_descriptor_alias_count": 3,
    "selector_mapping_mask0_set_bit_count": 900,
    "selector_mapping_mask1_set_bit_count": 251,
    "selector_mapping_script_pointer_occurrence_count": 1151,
    "distinct_direct_script_entrypoint_count": 841,
    "maximum_descriptor_script_pointer_count": 26,
}


class PackageBankAdapterError(RuntimeError):
    """The source contract, canonical evidence, or host model is invalid."""


class UnboundPackageSelectorError(PackageBankAdapterError):
    """An explicitly unbound Project Epoch package selector was requested."""


class NestedSubscriptUnresolvedError(PackageBankAdapterError):
    """Command 1E was requested before a bank-aware adapter was proved."""


@dataclasses.dataclass(frozen=True)
class PackageSource:
    """One explicit bank-qualified package descriptor root."""

    selector: int
    bank: int
    root_offset: int
    allocation_name: str
    source_kind: str


@dataclasses.dataclass(frozen=True)
class DirectScriptEntry:
    """One descriptor relation with a bank-qualified direct script identity."""

    branch: int
    owner_slot: int
    bank: int
    script_offset: int


@dataclasses.dataclass(frozen=True)
class PackageDescriptor:
    """Parsed two-mask descriptor geometry for one explicit package source."""

    source: PackageSource
    mask0: int
    mask1: int
    end_offset_exclusive: int
    entries: tuple[DirectScriptEntry, ...]


@dataclasses.dataclass(frozen=True)
class RuntimePublication:
    """One exact vanilla-shaped script-slot publication write set."""

    owner_slot: int
    activation_address: int
    activation_word: int
    script_address: int
    script_offset: int
    bank_address: int
    bank_word: int


@dataclasses.dataclass(frozen=True)
class DescriptorInstallState:
    """Host-model state after one complete vanilla-shaped descriptor pass.

    pointer_cursor_final is the physical, half-open consumed extent and may
    equal BANK_SIZE. x_final is the native 16-bit register and wraps to zero
    at that exact endpoint; the two values have distinct namespaces.
    """

    source: PackageSource
    a0b3_input: int
    selected_branch: int
    descriptor_root_word: int
    mask0_initial: int
    mask1_initial: int
    pointer_cursor_final: int
    dp80_word_final: int
    dp82_word_final: int
    a0b3_final: int
    publications: tuple[RuntimePublication, ...]
    accumulator_word_final: int
    x_final: int
    y_final: int
    accumulator_is_8_bit: bool
    indexes_are_16_bit: bool
    direct_page_final: int
    data_bank_final: int
    stack_delta: int
    flag_n_final: int
    flag_z_final: int
    flag_c_final: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise PackageBankAdapterError(
            f"{label} must be a strict integer in {minimum:#x}-{maximum:#x}"
        )
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PackageBankAdapterError(
                f"duplicate JSON key in adapter contract: {key}"
            )
        result[key] = value
    return result


def load_reference_contract() -> dict[str, Any]:
    try:
        encoded = REFERENCE_PATH.read_bytes()
    except OSError as exc:
        raise PackageBankAdapterError(
            f"cannot read adapter contract: {REFERENCE_PATH}"
        ) from exc
    if len(encoded) != REFERENCE_SIZE or sha256(encoded) != REFERENCE_SHA256:
        raise PackageBankAdapterError("adapter contract byte identity drifted")
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageBankAdapterError("adapter contract JSON is invalid") from exc
    if not isinstance(value, dict):
        raise PackageBankAdapterError("adapter contract root must be an object")
    _validate_reference_contract(value)
    return value


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("schema") != SCHEMA
        or contract.get("version") != 0
        or contract.get("evidence_level")
        != "verified-static-geometry-with-source-only-proposal"
    ):
        raise PackageBankAdapterError("adapter contract identity drifted")

    scope = contract.get("scope")
    if not isinstance(scope, dict):
        raise PackageBankAdapterError("adapter scope must be an object")
    required_false = (
        "runtime_performed",
        "production_installable",
        "rom_save_state_trace_mutation",
        "patch_rom_or_output_file_emission",
        "allocation_or_hook_approval",
        "canonical_payload_copied_or_emitted",
        "upstream_machine_code_imported",
    )
    if (
        scope.get("metadata_only") is not True
        or scope.get("source_only") is not True
        or any(scope.get(key) is not False for key in required_false)
    ):
        raise PackageBankAdapterError("adapter scope opened a forbidden gate")

    rom = contract.get("canonical_rom")
    if not isinstance(rom, dict) or (
        rom.get("size") != CANONICAL_ROM_SIZE
        or rom.get("sha1") != CANONICAL_ROM_SHA1
        or rom.get("sha256") != CANONICAL_ROM_SHA256
    ):
        raise PackageBankAdapterError("canonical ROM identity drifted")

    spans = contract.get("canonical_spans")
    expected_span_names = (
        "pc_action_config_reader",
        "pc_tech_package_reader",
        "candidate_tail_transfer_site",
        "pc_tech_package_resolver_parser_core",
        "command_1e_1f_handlers",
        "pc_action_config_table",
        "tech_animation_pointer_table",
    )
    if not isinstance(spans, list) or tuple(
        row.get("name") if isinstance(row, dict) else None for row in spans
    ) != expected_span_names:
        raise PackageBankAdapterError("canonical span inventory drifted")
    for row in spans:
        _validate_span_row(row)

    namespace = contract.get("namespace_contract")
    if not isinstance(namespace, dict) or (
        namespace.get("canonical_physical_package_selectors") != "00-7F"
        or namespace.get("candidate_epoch_package_selectors") != "80-8F"
        or namespace.get("schala_named_tech_action_ids") != "80-8F"
        or namespace.get("schala_basic_attack_action_id") != "90"
        or namespace.get("selector_80_8f_binding_state")
        != "candidate-policy-explicitly-unbound"
        or namespace.get("numeric_equality_creates_mapping") is not False
        or namespace.get("selector_90_policy")
        != "undeclared-and-refused; numeric equality to Focus Pulse action ID 90 creates no package mapping"
        or namespace.get("selector_ff_policy")
        != "undeclared-and-refused; the separate action-ID FF menu reservation is not imported as package-selector evidence"
    ):
        raise PackageBankAdapterError("selector namespace contract drifted")

    source_contract = contract.get("package_source_contract")
    if not isinstance(source_contract, dict) or (
        source_contract.get("unbound_representation")
        != "absence of a PackageSource object; zero is never interpreted as free or unbound"
        or source_contract.get("same_low_offset_different_bank_policy")
        != "distinct identities"
        or source_contract.get("runtime_pointer_publication")
        != "16-bit script offset at 5DBD plus owner*4 and 16-bit bank word at 5DBF plus owner*4"
        or source_contract.get("current_extended_source_kind")
        != "synthetic-test-only; project-epoch-source is refused until a versioned contract names an approved allocation catalog entry"
    ):
        raise PackageBankAdapterError("package-source contract drifted")

    nested = contract.get("nested_script_contract")
    if not isinstance(nested, dict) or (
        nested.get("command_1e_status")
        != "unresolved-and-refused-for-expanded-packages"
        or nested.get("canonical_behavior")
        != "C156E7 reads the indexed subscript pointer from fixed bank CE and C156ED installs bank CE"
    ):
        raise PackageBankAdapterError("command 1E boundary drifted")

    auxiliary = contract.get("auxiliary_config_contract")
    if not isinstance(auxiliary, dict) or (
        auxiliary.get("status") != "independent-adapters-unresolved"
        or auxiliary.get("runtime_support_claimed") is not False
        or not str(auxiliary.get("config_byte_3", "")).startswith(
            "C145F3 reads fixed D1:0060"
        )
        or not str(auxiliary.get("config_byte_4", "")).startswith(
            "C145FF reads fixed CD:692C"
        )
        or not str(auxiliary.get("config_byte_5", "")).startswith(
            "C1460B reads fixed CD:656E"
        )
    ):
        raise PackageBankAdapterError("auxiliary config boundary drifted")

    architecture = contract.get("architecture_recommendation")
    if not isinstance(architecture, dict) or (
        architecture.get("status") != "source-only-proposal"
        or not str(architecture.get("canonical_00_7f", "")).startswith(
            "preserve the canonical resolver and loader path"
        )
        or architecture.get("canonical_root_duplication")
        != "forbidden; do not copy the 128-word canonical resolver into Project Epoch expanded data"
        or architecture.get("hook_selection")
        != "unresolved; the four-byte candidate span is evidence for design, not approval"
    ):
        raise PackageBankAdapterError("adapter architecture recommendation drifted")

    abi = contract.get("candidate_helper_abi")
    if not isinstance(abi, dict) or (
        abi.get("status") != "source-only-candidate-not-approved"
        or abi.get("entry_pc") != "C14612"
        or abi.get("possible_tail_transfer_span") != "C14612-C14616"
        or abi.get("canonical_branch")
        != "for selector 00-7F, re-execute LDA 9877 and ASL A then JML to untouched C14616"
        or abi.get("canonical_rejoin_pc") != "C14616"
        or abi.get("expanded_branch_rejoin_pc") != "C14833"
        or abi.get("entry_widths")
        != "M=0 and X=0; 16-bit accumulator and 16-bit X/Y"
        or abi.get("direct_page") != "0000"
        or abi.get("data_bank") != "7E"
        or abi.get("a0b3_input_contract")
        != "strict 00-FF with adjacent high byte zero; 00 selects mask0 and nonzero selects mask1"
        or abi.get("scratch_policy")
        != "no WRAM or direct-page scratch is approved"
    ):
        raise PackageBankAdapterError("candidate helper ABI drifted")

    expected = contract.get("expected_results")
    if not isinstance(expected, dict) or (
        expected.get("canonical_selector_count") != 128
        or expected.get("canonical_package_bank") != "CE"
        or expected.get("canonical_bank_vector_sha256")
        != EXPECTED_CANONICAL_BANK_VECTOR_SHA256
        or expected.get("canonical_root_vector_sha256")
        != EXPECTED_CANONICAL_ROOT_VECTOR_SHA256
        or expected.get("canonical_selector_bank_root_ledger_sha256")
        != EXPECTED_CANONICAL_LEDGER_SHA256
        or any(
            expected.get(f"canonical_{key}") != value
            for key, value in EXPECTED_CANONICAL_DESCRIPTOR_GEOMETRY.items()
        )
        or expected.get("candidate_epoch_package_selector_count") != 16
        or expected.get("candidate_epoch_package_bound_count") != 0
        or expected.get("action_config_to_epoch_package_mapping_bound") is not False
        or expected.get("host_descriptor_install_state_model_complete") is not True
        or expected.get("focus_pulse_in_player_tech_domain") is not False
        or expected.get("command_1e_cross_bank_subscripts_resolved") is not False
    ):
        raise PackageBankAdapterError("expected adapter results drifted")

    upstream = contract.get("upstream_reconnaissance")
    if not isinstance(upstream, dict) or (
        upstream.get("commit")
        != "20609d50932a84be58f6281d23b3f4e4d4c4e167"
        or upstream.get("repository_license") != "MIT"
        or "no separate Mauron license" not in str(
            upstream.get("embedded_routine_provenance")
        )
        or not str(upstream.get("adoption_policy", "")).startswith(
            "architectural lead only"
        )
    ):
        raise PackageBankAdapterError("upstream adoption boundary drifted")

    limitations = contract.get("limitations")
    nonclaims = contract.get("nonclaims")
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(type(value) is str and value for value in limitations)
        or not isinstance(nonclaims, list)
        or not nonclaims
        or not all(type(value) is str and value for value in nonclaims)
    ):
        raise PackageBankAdapterError("limitations or nonclaims drifted")


def _parse_cpu_address(value: Any, label: str) -> int:
    if type(value) is not str or not re.fullmatch(r"[C-F][0-9A-F]{5}", value):
        raise PackageBankAdapterError(f"{label} must be a canonical HiROM PC")
    return int(value, 16)


def _validate_span_row(row: Any) -> None:
    if not isinstance(row, dict):
        raise PackageBankAdapterError("canonical span must be an object")
    start = _parse_cpu_address(row.get("cpu_start"), "span start")
    end = _parse_cpu_address(row.get("cpu_end_exclusive"), "span end")
    length = _strict_int(row.get("length"), "span length", 1, 0x400000)
    digest = row.get("sha256")
    if (
        end <= start
        or end - start != length
        or type(digest) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or type(row.get("role")) is not str
        or not row["role"]
    ):
        raise PackageBankAdapterError("canonical span geometry drifted")


def read_canonical_rom(path: Path) -> bytes:
    try:
        rom = path.read_bytes()
    except OSError as exc:
        raise PackageBankAdapterError(f"cannot read canonical ROM: {path}") from exc
    if (
        len(rom) != CANONICAL_ROM_SIZE
        or hashlib.sha1(rom).hexdigest() != CANONICAL_ROM_SHA1
        or sha256(rom) != CANONICAL_ROM_SHA256
    ):
        raise PackageBankAdapterError("ROM is not pinned US Rev0 headerless input")
    return rom


def _hirom_file_offset(cpu_address: int) -> int:
    _strict_int(cpu_address, "CPU address", 0xC00000, 0xFFFFFF)
    return cpu_address & 0x3FFFFF


def verify_canonical_spans(
    rom: bytes,
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if type(rom) is not bytes or len(rom) != CANONICAL_ROM_SIZE:
        raise PackageBankAdapterError("canonical span input must be a 4 MiB byte image")
    rows: list[dict[str, Any]] = []
    for spec in contract["canonical_spans"]:
        start = _parse_cpu_address(spec["cpu_start"], "span start")
        end = _parse_cpu_address(spec["cpu_end_exclusive"], "span end")
        start_offset = _hirom_file_offset(start)
        end_offset = _hirom_file_offset(end)
        payload = rom[start_offset:end_offset]
        if (
            len(payload) != spec["length"]
            or sha256(payload) != spec["sha256"]
        ):
            raise PackageBankAdapterError(
                f"canonical span drifted: {spec['name']}"
            )
        rows.append(
            {
                "name": spec["name"],
                "length": spec["length"],
                "sha256": spec["sha256"],
            }
        )
    return tuple(rows)


def make_package_source(
    *,
    selector: int,
    bank: int,
    root_offset: int,
    allocation_name: str,
    source_kind: str,
) -> PackageSource:
    selector = _strict_int(selector, "selector", 0, 0xFF)
    bank = _strict_int(bank, "package bank", 0, 0xFF)
    root_offset = _strict_int(root_offset, "descriptor root", 0, 0xFFFF)
    if root_offset == 0xFFFF:
        raise PackageBankAdapterError("descriptor root FFFF is refused")
    if type(allocation_name) is not str or not ALLOCATION_NAME_RE.fullmatch(
        allocation_name
    ):
        raise PackageBankAdapterError(
            "allocation name must be an explicit uppercase symbolic name"
        )
    if type(source_kind) is not str or source_kind not in ALLOWED_SOURCE_KINDS:
        raise PackageBankAdapterError("package source kind is invalid")
    if source_kind == "canonical" and not (
        selector <= CANONICAL_SELECTOR_LAST
        and bank == CANONICAL_PACKAGE_BANK
        and allocation_name == "CANONICAL_CD5EF0_TECH_PACKAGE"
    ):
        raise PackageBankAdapterError("canonical package-source identity drifted")
    if source_kind != "canonical" and not (
        EPOCH_PACKAGE_SELECTOR_FIRST <= selector <= EPOCH_PACKAGE_SELECTOR_LAST
    ):
        raise PackageBankAdapterError(
            "extended package source lies outside candidate Epoch package selectors 80-8F"
        )
    return PackageSource(
        selector=selector,
        bank=bank,
        root_offset=root_offset,
        allocation_name=allocation_name,
        source_kind=source_kind,
    )


def _validate_package_source(source: Any) -> PackageSource:
    if not isinstance(source, PackageSource):
        raise PackageBankAdapterError("package source must be a PackageSource")
    return make_package_source(
        selector=source.selector,
        bank=source.bank,
        root_offset=source.root_offset,
        allocation_name=source.allocation_name,
        source_kind=source.source_kind,
    )


def build_canonical_sources(rom: bytes) -> tuple[PackageSource, ...]:
    if type(rom) is not bytes or (
        len(rom) != CANONICAL_ROM_SIZE
        or hashlib.sha1(rom).hexdigest() != CANONICAL_ROM_SHA1
        or sha256(rom) != CANONICAL_ROM_SHA256
    ):
        raise PackageBankAdapterError("canonical source build requires pinned ROM bytes")
    table = rom[0x0D5EF0:0x0D5FF0]
    if len(table) != 0x100 or sha256(table) != EXPECTED_CANONICAL_ROOT_VECTOR_SHA256:
        raise PackageBankAdapterError("canonical package-root vector drifted")
    return tuple(
        make_package_source(
            selector=selector,
            bank=CANONICAL_PACKAGE_BANK,
            root_offset=int.from_bytes(
                table[selector * 2 : selector * 2 + 2], "little"
            ),
            allocation_name="CANONICAL_CD5EF0_TECH_PACKAGE",
            source_kind="canonical",
        )
        for selector in range(0x80)
    )


def validate_extended_bindings(
    bindings: Mapping[int, PackageSource] | None,
) -> dict[int, PackageSource]:
    if bindings is None:
        return {}
    if not isinstance(bindings, Mapping):
        raise PackageBankAdapterError("extended bindings must be a mapping")
    result: dict[int, PackageSource] = {}
    for selector, source in bindings.items():
        selector = _strict_int(selector, "extended selector key", 0, 0xFF)
        if not EPOCH_PACKAGE_SELECTOR_FIRST <= selector <= EPOCH_PACKAGE_SELECTOR_LAST:
            raise PackageBankAdapterError(
                "extended binding key lies outside candidate Epoch package selectors 80-8F"
            )
        checked = _validate_package_source(source)
        if checked.selector != selector or checked.source_kind == "canonical":
            raise PackageBankAdapterError("extended binding identity drifted")
        result[selector] = checked
    return result


def resolve_package_source(
    selector: int,
    canonical_sources: Sequence[PackageSource],
    extended_bindings: Mapping[int, PackageSource] | None = None,
) -> PackageSource:
    selector = _strict_int(selector, "package selector", 0, 0xFF)
    if not isinstance(canonical_sources, Sequence) or isinstance(
        canonical_sources, (str, bytes, bytearray)
    ):
        raise PackageBankAdapterError("canonical sources must be a sequence")
    if len(canonical_sources) != 0x80:
        raise PackageBankAdapterError("canonical package-source count must be 128")
    checked_canonical = tuple(
        _validate_package_source(source) for source in canonical_sources
    )
    if any(source.selector != index for index, source in enumerate(checked_canonical)):
        raise PackageBankAdapterError("canonical package-source order drifted")
    checked_extended = validate_extended_bindings(extended_bindings)

    if selector <= CANONICAL_SELECTOR_LAST:
        return checked_canonical[selector]
    if EPOCH_PACKAGE_SELECTOR_FIRST <= selector <= EPOCH_PACKAGE_SELECTOR_LAST:
        try:
            return checked_extended[selector]
        except KeyError as exc:
            raise UnboundPackageSelectorError(
                f"candidate Epoch package selector {selector:02X} is explicitly unbound"
            ) from exc
    if selector == SCHALA_FOCUS_PULSE_ACTION_ID:
        raise PackageBankAdapterError(
            "package selector 90 is undeclared; numeric equality to Focus Pulse action ID 90 creates no mapping"
        )
    if selector == 0xFF:
        raise PackageBankAdapterError(
            "package selector FF is undeclared and refused; the separate action-ID reservation is not package-selector evidence"
        )
    raise PackageBankAdapterError(
        f"package selector {selector:02X} is unassigned and refused"
    )


def parse_package_descriptor(
    bank_image: bytes,
    source: PackageSource,
) -> PackageDescriptor:
    source = _validate_package_source(source)
    if type(bank_image) is not bytes or len(bank_image) != BANK_SIZE:
        raise PackageBankAdapterError(
            "package descriptor input must be one immutable 64 KiB bank image"
        )
    root = source.root_offset
    if root + 4 > BANK_SIZE:
        raise PackageBankAdapterError("package descriptor header crosses its bank")
    mask0 = int.from_bytes(bank_image[root : root + 2], "big")
    mask1 = int.from_bytes(bank_image[root + 2 : root + 4], "big")
    relation_count = mask0.bit_count() + mask1.bit_count()
    end = root + 4 + relation_count * 2
    if end > BANK_SIZE:
        raise PackageBankAdapterError("package descriptor pointer list crosses its bank")

    entries: list[DirectScriptEntry] = []
    cursor = root + 4
    for branch, mask in enumerate((mask0, mask1)):
        for owner_slot in range(16):
            if not mask & (1 << (15 - owner_slot)):
                continue
            script_offset = int.from_bytes(bank_image[cursor : cursor + 2], "little")
            cursor += 2
            if script_offset == 0xFFFF:
                raise PackageBankAdapterError("selected direct script offset FFFF is refused")
            if root <= script_offset < end:
                raise PackageBankAdapterError(
                    "direct script target overlaps its package descriptor"
                )
            entries.append(
                DirectScriptEntry(
                    branch=branch,
                    owner_slot=owner_slot,
                    bank=source.bank,
                    script_offset=script_offset,
                )
            )
    if cursor != end:
        raise PackageBankAdapterError("package descriptor cursor drifted")
    return PackageDescriptor(
        source=source,
        mask0=mask0,
        mask1=mask1,
        end_offset_exclusive=end,
        entries=tuple(entries),
    )


def simulate_descriptor_install(
    bank_image: bytes,
    source: PackageSource,
    *,
    a0b3: int,
) -> DescriptorInstallState:
    """Model the parser's exact branch, cursor, and publication footprints."""

    a0b3 = _strict_int(a0b3, "A0B3 flag-byte input", 0, 0xFF)
    descriptor = parse_package_descriptor(bank_image, source)
    selected_branch = 0 if a0b3 == 0 else 1
    selected_entries = tuple(
        entry
        for entry in descriptor.entries
        if entry.branch == selected_branch
    )
    consumed_pointer_count = descriptor.mask0.bit_count()
    if selected_branch == 1:
        consumed_pointer_count += descriptor.mask1.bit_count()
    pointer_cursor_final = (
        descriptor.source.root_offset + 4 + consumed_pointer_count * 2
    )
    publications = tuple(
        RuntimePublication(
            owner_slot=entry.owner_slot,
            activation_address=0x5DAC + entry.owner_slot,
            activation_word=0x0001,
            script_address=0x5DBD + entry.owner_slot * 4,
            script_offset=entry.script_offset,
            bank_address=0x5DBF + entry.owner_slot * 4,
            bank_word=entry.bank,
        )
        for entry in selected_entries
    )
    return DescriptorInstallState(
        source=descriptor.source,
        a0b3_input=a0b3,
        selected_branch=selected_branch,
        descriptor_root_word=descriptor.source.root_offset,
        mask0_initial=descriptor.mask0,
        mask1_initial=descriptor.mask1,
        pointer_cursor_final=pointer_cursor_final,
        dp80_word_final=0,
        dp82_word_final=descriptor.mask1,
        a0b3_final=0,
        publications=publications,
        accumulator_word_final=0,
        # C1463B-C1463F advances the header cursor with 16-bit INY/TYX;
        # C14666-C14667 consumes pointers with two 16-bit INX operations.
        # Keep the physical extent above, but represent the native register.
        x_final=pointer_cursor_final & 0xFFFF,
        y_final=0x0010,
        accumulator_is_8_bit=True,
        indexes_are_16_bit=True,
        direct_page_final=0,
        data_bank_final=0x7E,
        stack_delta=0,
        flag_n_final=0,
        flag_z_final=1,
        flag_c_final=1,
    )


def resolve_command_1e_subscript(*_args: Any, **_kwargs: Any) -> None:
    raise NestedSubscriptUnresolvedError(
        "animation command 1E remains fixed-bank CE and is refused for expanded packages"
    )


def canonical_identity_hashes(
    sources: Sequence[PackageSource],
) -> dict[str, str]:
    if len(sources) != 0x80:
        raise PackageBankAdapterError("canonical identity hash requires 128 sources")
    checked = tuple(_validate_package_source(source) for source in sources)
    if any(source.selector != index for index, source in enumerate(checked)):
        raise PackageBankAdapterError("canonical identity order drifted")
    bank_vector = bytes(source.bank for source in checked)
    root_vector = b"".join(
        source.root_offset.to_bytes(2, "little") for source in checked
    )
    ledger = b"".join(
        bytes((source.selector, source.bank))
        + source.root_offset.to_bytes(2, "little")
        for source in checked
    )
    result = {
        "bank_vector_sha256": sha256(bank_vector),
        "root_vector_sha256": sha256(root_vector),
        "selector_bank_root_ledger_sha256": sha256(ledger),
    }
    if result != {
        "bank_vector_sha256": EXPECTED_CANONICAL_BANK_VECTOR_SHA256,
        "root_vector_sha256": EXPECTED_CANONICAL_ROOT_VECTOR_SHA256,
        "selector_bank_root_ledger_sha256": EXPECTED_CANONICAL_LEDGER_SHA256,
    }:
        raise PackageBankAdapterError("canonical package-source identity drifted")
    return result


def canonical_descriptor_geometry(
    rom: bytes,
    sources: Sequence[PackageSource],
) -> dict[str, int]:
    """Parse all real CE descriptors and return payload-free geometry."""

    if type(rom) is not bytes or (
        len(rom) != CANONICAL_ROM_SIZE
        or hashlib.sha1(rom).hexdigest() != CANONICAL_ROM_SHA1
        or sha256(rom) != CANONICAL_ROM_SHA256
    ):
        raise PackageBankAdapterError(
            "canonical descriptor geometry requires pinned ROM bytes"
        )
    if len(sources) != 0x80:
        raise PackageBankAdapterError(
            "canonical descriptor geometry requires 128 sources"
        )
    checked = tuple(_validate_package_source(source) for source in sources)
    if any(source.selector != index for index, source in enumerate(checked)):
        raise PackageBankAdapterError("canonical descriptor source order drifted")
    bank_image = rom[0x0E0000:0x0F0000]
    if len(bank_image) != BANK_SIZE:
        raise PackageBankAdapterError("canonical CE package bank is truncated")
    descriptors = tuple(
        parse_package_descriptor(bank_image, source) for source in checked
    )
    distinct_roots = {descriptor.source.root_offset for descriptor in descriptors}
    distinct_scripts = {
        (entry.bank, entry.script_offset)
        for descriptor in descriptors
        for entry in descriptor.entries
    }
    result = {
        "distinct_descriptor_count": len(distinct_roots),
        "selector_to_descriptor_alias_count": len(descriptors) - len(distinct_roots),
        "selector_mapping_mask0_set_bit_count": sum(
            descriptor.mask0.bit_count() for descriptor in descriptors
        ),
        "selector_mapping_mask1_set_bit_count": sum(
            descriptor.mask1.bit_count() for descriptor in descriptors
        ),
        "selector_mapping_script_pointer_occurrence_count": sum(
            len(descriptor.entries) for descriptor in descriptors
        ),
        "distinct_direct_script_entrypoint_count": len(distinct_scripts),
        "maximum_descriptor_script_pointer_count": max(
            len(descriptor.entries) for descriptor in descriptors
        ),
    }
    if result != EXPECTED_CANONICAL_DESCRIPTOR_GEOMETRY:
        raise PackageBankAdapterError("canonical descriptor geometry drifted")
    return result


def build_report(rom: bytes, contract: Mapping[str, Any]) -> dict[str, Any]:
    _validate_reference_contract(contract)
    if type(rom) is not bytes or (
        len(rom) != CANONICAL_ROM_SIZE
        or hashlib.sha1(rom).hexdigest() != CANONICAL_ROM_SHA1
        or sha256(rom) != CANONICAL_ROM_SHA256
    ):
        raise PackageBankAdapterError("report requires pinned canonical ROM bytes")
    span_results = verify_canonical_spans(rom, contract)
    sources = build_canonical_sources(rom)
    identities = canonical_identity_hashes(sources)
    descriptor_geometry = canonical_descriptor_geometry(rom, sources)
    return {
        "schema": REPORT_SCHEMA,
        "status": "pass-source-only-unbound-no-installation",
        "evidence_level": "verified-static-geometry-with-source-only-proposal",
        "canonical_rom": {
            "size": len(rom),
            "sha1": hashlib.sha1(rom).hexdigest(),
            "sha256": sha256(rom),
        },
        "verified_spans": list(span_results),
        "canonical_package_sources": {
            "selector_count": len(sources),
            "bank": "CE",
            **identities,
            "descriptor_geometry": descriptor_geometry,
            "payload_emitted": False,
        },
        "epoch_candidate_package_sources": {
            "selector_domain": "80-8F",
            "selector_count": 16,
            "bound_count": 0,
            "allocation_status": "unbound",
            "same_numbered_action_mapping": False,
        },
        "focus_pulse": {
            "action_id": "90",
            "player_tech_package_domain": False,
            "architecture": "separate PC normal-Attack path",
        },
        "nested_scripts": {
            "command_1e_cross_bank_resolved": False,
            "policy": "refused-for-expanded-packages",
        },
        "auxiliary_config_readers": {
            "expanded_bank_safe": False,
            "independent_adapters_required": True,
            "config_bytes": [3, 4, 5],
        },
        "host_descriptor_install_state": {
            "complete_for_declared_geometry": True,
            "a0b3_branches": [0, 1],
            "owner_bit_count": 16,
            "exact_word_publication_footprints": True,
            "runtime_performed": False,
        },
        "scope": {
            "metadata_only": True,
            "source_only": True,
            "runtime_performed": False,
            "production_installable": False,
            "rom_mutated": False,
            "patch_or_output_file_emitted": False,
            "allocation_or_hook_approved": False,
            "upstream_machine_code_imported": False,
        },
        "limitations": list(contract["limitations"]),
        "nonclaims": list(contract["nonclaims"]),
    }


def _default_rom_path() -> Path:
    configured = os.environ.get("CT_US_REV0_ROM")
    if configured:
        return Path(configured)
    return (
        ROOT
        / "private"
        / "input"
        / "rom_archive"
        / "Chrono Trigger (USA).sfc"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the metadata-only Schala player-Tech package-bank adapter contract"
        )
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=_default_rom_path(),
        help="private pinned headerless Chrono Trigger US Rev0 ROM",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract = load_reference_contract()
        rom = read_canonical_rom(args.rom)
        report = build_report(rom, contract)
    except PackageBankAdapterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
