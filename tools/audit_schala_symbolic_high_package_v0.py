#!/usr/bin/env python3
"""Audit one source-only symbolic high player-Tech package; emit metadata only.

The canonical action-config donor is read from the pinned private ROM in memory.
Only its first byte changes. Neither config bytes, a bank image, nor a patch are
emitted. Bank 42 and its named spans are synthetic identities, not allocations.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Final

import audit_schala_expanded_package_command_policy_v0 as policy

adapter = policy.adapter

ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_PATH: Final = ROOT / "references/schala_symbolic_high_package_v0.json"
REFERENCE_SIZE: Final = 8164
REFERENCE_SHA256: Final = (
    "37c13271c3632bca6b27a2daa0e5e2820d502a6673b1863b64b29a647df470e2"
)
POLICY_SOURCE_SIZE: Final = 39897
POLICY_SOURCE_SHA256: Final = (
    "5f9417cb5c44d6dd71577bcd48de0a3c90c9d7f2b790c57a26d1e8c4bd5b5c3f"
)
POLICY_REFERENCE_SIZE: Final = 6717
POLICY_REFERENCE_SHA256: Final = (
    "35246c00e274f35a80cfe589cfe3557b7585ff515c7e43747453d161de99f0d9"
)
SCHEMA: Final = "project-epoch-schala-symbolic-high-package-report-v0"
REFERENCE_SCHEMA: Final = "project-epoch-schala-symbolic-high-package-contract-v0"
STATUS: Final = "pass-source-only-symbolic-high-package"
GATE: Final = "BA-SYMBOLIC-HIGH-PACKAGE"
CANONICAL_ROM_SIZE: Final = 4194304
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)
DEFAULT_ROM_PATH: Final = (
    ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc"
)
DONOR_ROW: Final = 0x01
CONFIG_TABLE_FILE_OFFSET: Final = 0x0D45A6
CONFIG_ROW_SIZE: Final = 7
DONOR_SHA256: Final = (
    "d64477971e5fa2a0d679810b37ad90412615d49786671b71ec6aea209bd61313"
)
PRESERVED_CONFIG_SHA256: Final = (
    "cf2dfb5466e64043a0995b97e825a9633d3f68890e1df2a5ac229ed8506e21c7"
)
ADAPTED_CONFIG_SHA256: Final = (
    "88430e3592fe6cd2781c39854771c87bfb458b0557951a6317c974faea316733"
)
SELECTOR: Final = 0x80
BANK: Final = 0x42
DESCRIPTOR_START: Final = 0x2000
DESCRIPTOR_END: Final = 0x2008
STREAM_START: Final = 0x3000
STREAM_END: Final = 0x3001
DESCRIPTOR_NAME: Final = "EPOCH_PKG80_SYMBOLIC_DESCRIPTOR_V0"
STREAM_NAME: Final = "EPOCH_PKG80_SYMBOLIC_STREAM_V0"

NONCLAIMS: Final = (
    "The synthetic selector-80 binding exists only in one explicit local proof mapping; all default high selectors remain unbound.",
    "No Schala action, Tech, item, sprite, sound, animation, or logical PC 07 mapping is defined.",
    "Bank 42 and its named spans are synthetic test identities, not approved expanded allocations or free-space claims.",
    "The one-command terminal stream proves transport and closure only; it has no authored gameplay effect.",
    "Preserved canonical config bytes prove donor equality, not runtime compatibility or independent auxiliary-bank adapters.",
    "No ROM, save, state, trace, assembly, hook, patch, or runtime artifact is created or modified.",
    "No reconstructed canonical config or extracted game payload is printed, stored, or source-controlled by this auditor.",
    "Command 1E remains refused for expanded packages; no cross-bank subscript handler is adapted.",
)


class SymbolicHighPackageError(RuntimeError):
    """A source, donor, interpreter, namespace, or closed contract drifted."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def _metadata_sha256(value: Any) -> str:
    return _sha256(_json_bytes(value))


def dependency_identities() -> dict[str, Any]:
    source = policy._dependency_source_identity(
        module_file=policy.__file__,
        relative_path="tools/audit_schala_expanded_package_command_policy_v0.py",
        expected_size=POLICY_SOURCE_SIZE,
        expected_sha256=POLICY_SOURCE_SHA256,
        label="expanded-package command policy auditor",
    )
    if (
        policy.REFERENCE_SIZE != POLICY_REFERENCE_SIZE
        or policy.REFERENCE_SHA256 != POLICY_REFERENCE_SHA256
    ):
        raise SymbolicHighPackageError("policy reference dependency pin drifted")
    contract = policy.load_reference_contract()
    return {
        "command_policy_source": source,
        "command_policy_reference": {
            "path": "references/schala_expanded_package_command_policy_v0.json",
            "size": POLICY_REFERENCE_SIZE,
            "sha256": POLICY_REFERENCE_SHA256,
        },
        "transitive_closed_dependencies": contract["dependencies"],
    }


def build_symbolic_source() -> tuple[bytes, policy.ExpandedPackageLayout]:
    """Return original synthetic bytes in memory; never install or emit them."""
    image = bytearray(policy.BANK_SIZE)
    image[DESCRIPTOR_START:DESCRIPTOR_START + 4] = (
        (0x8000).to_bytes(2, "big") * 2
    )
    image[DESCRIPTOR_START + 4:DESCRIPTOR_END] = (
        STREAM_START.to_bytes(2, "little") * 2
    )
    image[STREAM_START:STREAM_END] = bytes((0x00,))
    source = adapter.make_package_source(
        selector=SELECTOR,
        bank=BANK,
        root_offset=DESCRIPTOR_START,
        allocation_name=DESCRIPTOR_NAME,
        source_kind="synthetic-test",
    )
    return bytes(image), policy.ExpandedPackageLayout(
        source=source,
        descriptor_span=policy.NamedSpan(
            DESCRIPTOR_NAME, BANK, DESCRIPTOR_START, DESCRIPTOR_END
        ),
        stream_spans=(policy.NamedSpan(STREAM_NAME, BANK, STREAM_START, STREAM_END),),
    )


def validate_symbolic_source(
    image: bytes, layout: policy.ExpandedPackageLayout
) -> dict[str, Any]:
    dependency_identities()
    expected_image, expected_layout = build_symbolic_source()
    if type(image) is not bytes or image != expected_image:
        raise SymbolicHighPackageError("exact immutable symbolic bank content drifted")
    if layout != expected_layout:
        raise SymbolicHighPackageError("exact named symbolic layout drifted")
    result = policy.validate_expanded_package_command_policy(image, layout)
    required_counts = {
        "descriptor_relation_count": 2,
        "mask0_relation_count": 1,
        "mask1_relation_count": 1,
        "distinct_direct_entrypoint_count": 1,
        "unique_token_start_count": 1,
        "unique_owned_byte_count": 1,
        "command_00_terminal_count": 1,
        "source_content_size": 9,
        "decoded_command_1e_site_count": 0,
        "top_level_command_1f_site_count": 0,
        "top_level_command_21_site_count": 0,
        "unowned_stream_byte_count": 0,
    }
    if any(type(result.get(k)) is not int or result[k] != v
           for k, v in required_counts.items()):
        raise SymbolicHighPackageError("symbolic policy result geometry drifted")
    return {
        "layout": dataclasses.asdict(layout),
        "synthetic_bank_size": len(image),
        "synthetic_bank_sha256": _sha256(image),
        "descriptor_sha256": _sha256(image[DESCRIPTOR_START:DESCRIPTOR_END]),
        "stream_sha256": _sha256(image[STREAM_START:STREAM_END]),
        "descriptor_pointer_occurrence_count": 2,
        "distinct_direct_entrypoint_count": 1,
        "repeated_pointer_alias_count": 1,
        "policy_proof": result,
    }


def validate_config_pair(donor: bytes, candidate: bytes) -> dict[str, Any]:
    if type(donor) is not bytes or type(candidate) is not bytes:
        raise SymbolicHighPackageError("config rows must be immutable bytes")
    if len(donor) != CONFIG_ROW_SIZE or len(candidate) != CONFIG_ROW_SIZE:
        raise SymbolicHighPackageError("config row size drifted")
    if _sha256(donor) != DONOR_SHA256 or donor[0] >= 0x80:
        raise SymbolicHighPackageError("canonical donor row identity drifted")
    if candidate[0] != SELECTOR:
        raise SymbolicHighPackageError("candidate config byte 0 must select package 80")
    if candidate[1:] != donor[1:]:
        raise SymbolicHighPackageError("preserved config bytes 1 through 6 drifted")
    changed = [i for i, (a, b) in enumerate(zip(donor, candidate)) if a != b]
    if changed != [0]:
        raise SymbolicHighPackageError("config substitution must change exactly byte 0")
    if (
        _sha256(donor[1:]) != PRESERVED_CONFIG_SHA256
        or _sha256(candidate) != ADAPTED_CONFIG_SHA256
    ):
        raise SymbolicHighPackageError("config content hash drifted")
    return {
        "donor_physical_action_config_row": "01",
        "donor_file_offset": f"{CONFIG_TABLE_FILE_OFFSET + DONOR_ROW * CONFIG_ROW_SIZE:06X}",
        "row_size": CONFIG_ROW_SIZE,
        "donor_sha256": _sha256(donor),
        "adapted_sha256": _sha256(candidate),
        "preserved_bytes_1_through_6_sha256": _sha256(donor[1:]),
        "changed_byte_offsets": changed,
        "preserved_byte_offsets": list(range(1, 7)),
        "preserved_byte_equalities": [True] * 6,
        "canonical_auxiliary_bytes_3_4_5_equal": True,
        "candidate_package_selector": "80",
        "donor_payload_emitted": False,
        "adapted_payload_emitted": False,
    }


def _require_canonical_rom(rom: bytes) -> None:
    if type(rom) is not bytes or (
        len(rom) != CANONICAL_ROM_SIZE or _sha256(rom) != CANONICAL_ROM_SHA256
    ):
        raise SymbolicHighPackageError("requires pinned immutable US Rev0 ROM bytes")


def reconstruct_config_pair(rom: bytes) -> tuple[bytes, bytes]:
    _require_canonical_rom(rom)
    start = CONFIG_TABLE_FILE_OFFSET + DONOR_ROW * CONFIG_ROW_SIZE
    donor = rom[start:start + CONFIG_ROW_SIZE]
    candidate = bytes((SELECTOR,)) + donor[1:]
    validate_config_pair(donor, candidate)
    return donor, candidate


def validate_namespace(
    canonical_sources: Sequence[adapter.PackageSource],
    symbolic_source: adapter.PackageSource,
) -> dict[str, Any]:
    if adapter.validate_extended_bindings(None) != {}:
        raise SymbolicHighPackageError("default extended package registry is not empty")
    explicit = {SELECTOR: symbolic_source}
    canonical_rows = []
    for selector in range(0x80):
        plain = adapter.resolve_package_source(selector, canonical_sources)
        explicit_result = adapter.resolve_package_source(selector, canonical_sources, explicit)
        if plain != canonical_sources[selector] or explicit_result != plain:
            raise SymbolicHighPackageError("canonical package path changed")
        canonical_rows.append(dataclasses.asdict(plain))
    for selector in range(0x80, 0x90):
        try:
            adapter.resolve_package_source(selector, canonical_sources)
        except adapter.UnboundPackageSelectorError:
            pass
        else:
            raise SymbolicHighPackageError("default high package selector unexpectedly bound")
        if selector == SELECTOR:
            if adapter.resolve_package_source(selector, canonical_sources, explicit) != symbolic_source:
                raise SymbolicHighPackageError("explicit synthetic selector binding drifted")
        else:
            try:
                adapter.resolve_package_source(selector, canonical_sources, explicit)
            except adapter.UnboundPackageSelectorError:
                pass
            else:
                raise SymbolicHighPackageError("undeclared synthetic selector unexpectedly bound")
    try:
        adapter.resolve_command_1e_subscript()
    except adapter.NestedSubscriptUnresolvedError:
        pass
    else:
        raise SymbolicHighPackageError("expanded command 1E refusal drifted")
    return {
        "canonical_selector_equivalence_count": 128,
        "canonical_source_identity_ledger_sha256": _metadata_sha256(canonical_rows),
        "default_high_selector_bound_count": 0,
        "default_high_selector_refusal_count": 16,
        "explicit_synthetic_mapping_selectors": ["80"],
        "explicit_synthetic_mapping_bound_count": 1,
        "remaining_explicit_high_selector_refusal_count": 15,
        "production_high_selector_bound_count": 0,
        "schala_action_mapping_bound": False,
        "command_1e_refusal_preserved": True,
    }


def validate_branch_transport(
    image: bytes, source: adapter.PackageSource
) -> dict[str, Any]:
    states = []
    for flag in range(0x100):
        state = adapter.simulate_descriptor_install(image, source, a0b3=flag)
        branch = int(flag != 0)
        cursor = DESCRIPTOR_START + 6 + branch * 2
        expected = adapter.DescriptorInstallState(
            source=source, a0b3_input=flag, selected_branch=branch,
            descriptor_root_word=DESCRIPTOR_START, mask0_initial=0x8000,
            mask1_initial=0x8000, pointer_cursor_final=cursor,
            dp80_word_final=0, dp82_word_final=0x8000, a0b3_final=0,
            publications=(adapter.RuntimePublication(
                owner_slot=0, activation_address=0x5DAC, activation_word=1,
                script_address=0x5DBD, script_offset=STREAM_START,
                bank_address=0x5DBF, bank_word=BANK,
            ),),
            accumulator_word_final=0, x_final=cursor, y_final=0x10,
            accumulator_is_8_bit=True, indexes_are_16_bit=True,
            direct_page_final=0, data_bank_final=0x7E, stack_delta=0,
            flag_n_final=0, flag_z_final=1, flag_c_final=1,
        )
        if state != expected:
            raise SymbolicHighPackageError("symbolic descriptor branch transport drifted")
        states.append(dataclasses.asdict(state))
    return {
        "a0b3_flag_byte_inputs_checked": 256,
        "mask0_input_count": 1,
        "mask1_input_count": 255,
        "publication_count_per_input": 1,
        "same_bank_qualified_direct_entry_for_both_branches": True,
        "complete_install_state_ledger_sha256": _metadata_sha256(states),
        "evidence_level": "verified-static",
        "runtime_write_performed": False,
    }


def expected_reference() -> dict[str, Any]:
    """Closed metadata contract; no canonical row is embedded or emitted."""
    image, layout = build_symbolic_source()
    return {
        "schema": REFERENCE_SCHEMA,
        "version": 0,
        "gate": GATE,
        "evidence_level": "verified-static",
        "dependencies": dependency_identities(),
        "canonical_rom": {"size": CANONICAL_ROM_SIZE, "sha256": CANONICAL_ROM_SHA256},
        "donor_contract": {
            "physical_action_config_row": "01",
            "table_file_offset": "0D45A6",
            "row_file_offset": "0D45AD",
            "row_size": 7,
            "donor_sha256": DONOR_SHA256,
            "preserved_bytes_1_through_6_sha256": PRESERVED_CONFIG_SHA256,
            "adapted_sha256": ADAPTED_CONFIG_SHA256,
            "changed_byte_offsets": [0],
            "candidate_package_selector": "80",
            "donor_selection": "explicit canonical row 01; retain every existing nonprimary config byte without interpreting it as a Schala binding",
            "auxiliary_reader_contract": adapter.load_reference_contract()["auxiliary_config_contract"],
        },
        "expected_symbolic_source": validate_symbolic_source(image, layout),
        "expected_branch_transport": validate_branch_transport(image, layout.source),
        "scope": {
            "source_only": True,
            "canonical_rom_access": "read-only-pinned-input",
            "metadata_only": True,
            "default_high_registry_empty": True,
            "explicit_binding_lifetime": "local proof mapping only",
            "production_installable": False,
            "allocation_or_hook_approved": False,
            "runtime_performed": False,
            "output_file_option_available": False,
        },
        "nonclaims": list(NONCLAIMS),
    }


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    if type(contract) is not dict or _json_bytes(contract) != _json_bytes(expected_reference()):
        raise SymbolicHighPackageError("closed symbolic package reference content drifted")


def load_reference_contract() -> dict[str, Any]:
    raw = REFERENCE_PATH.read_bytes()
    if len(raw) != REFERENCE_SIZE or _sha256(raw) != REFERENCE_SHA256:
        raise SymbolicHighPackageError("symbolic package reference identity drifted")
    try:
        contract = json.loads(raw, object_pairs_hook=adapter._reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, adapter.PackageBankAdapterError) as exc:
        raise SymbolicHighPackageError("symbolic reference JSON invalid") from exc
    _validate_reference_contract(contract)
    return contract


def build_report(rom: bytes) -> dict[str, Any]:
    _require_canonical_rom(rom)
    contract = load_reference_contract()
    canonical_spans = adapter.verify_canonical_spans(rom, adapter.load_reference_contract())
    canonical_sources = adapter.build_canonical_sources(rom)
    donor, candidate = reconstruct_config_pair(rom)
    image, layout = build_symbolic_source()
    results = {
        "config_substitution": validate_config_pair(donor, candidate),
        "symbolic_source": validate_symbolic_source(image, layout),
        "branch_transport": validate_branch_transport(image, layout.source),
        "namespace": validate_namespace(canonical_sources, layout.source),
        "canonical_spans_verified": list(canonical_spans),
    }
    _require_canonical_rom(rom)
    source = Path(__file__).resolve().read_bytes()
    report = {
        "schema": SCHEMA,
        "version": 0,
        "gate": GATE,
        "status": STATUS,
        "evidence_level": "verified-static",
        "evidence_ceiling": "source-only synthetic package, exact canonical donor preservation, and host descriptor transport",
        "scope": contract["scope"],
        "dependencies": contract["dependencies"],
        "canonical_rom": contract["canonical_rom"],
        "results": results,
        "gates": {
            "one_source_only_symbolic_high_package_proved": True,
            "closed_interpreter_dependencies_passed": True,
            "canonical_nonprimary_config_bytes_preserved": True,
            "both_descriptor_branches_proved": True,
            "repeated_pointer_alias_proved": True,
            "flat_direct_decoded_command_1e_exclusion_passed": True,
            "default_production_high_selectors_remain_unbound": True,
            "action_mapping_bound": False,
            "allocation_or_hook_approved": False,
            "runtime_performed": False,
            "rom_save_state_trace_mutation_performed": False,
            "canonical_payload_emitted": False,
            "patch_rom_or_output_file_emitted": False,
        },
        "reproduction": {
            "command": ["python", "-B", "tools/audit_schala_symbolic_high_package_v0.py", "--rom", "<pinned-private-US-Rev0-ROM>", "--compact"],
            "output": "deterministic metadata-only JSON on stdout",
            "output_file_option_available": False,
            "expected_side_effects": "none",
            "auditor_source": {
                "path": "tools/audit_schala_symbolic_high_package_v0.py",
                "size": len(source), "sha256": _sha256(source),
            },
            "reference_contract": {
                "path": "references/schala_symbolic_high_package_v0.json",
                "size": REFERENCE_SIZE, "sha256": REFERENCE_SHA256,
            },
        },
        "nonclaims": list(NONCLAIMS),
    }
    report["artifact_identity"] = {
        "canonical_json_sha256_excluding_artifact_identity": _metadata_sha256(report)
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM_PATH)
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_report(args.rom.read_bytes())
    except (
        SymbolicHighPackageError, policy.ExpandedPackageCommandPolicyError,
        adapter.PackageBankAdapterError, policy.grammar.BattleCommandGrammarAuditError,
        OSError, ValueError,
    ) as exc:
        print(f"symbolic high package audit failed: {exc}", file=sys.stderr)
        return 1
    if args.compact:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
