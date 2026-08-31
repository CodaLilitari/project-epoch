#!/usr/bin/env python3
"""Prove Project Epoch's source-only expanded-package command policy v0.

The policy chooses strict decoded-command exclusion for animation command
$1E.  It reuses the completed canonical command grammar and the completed
bank-qualified package/descriptor host model.  It validates synthetic authored
bank images in memory, but it binds no package selector, allocation, hook, ROM,
save, state, trace, or runtime behavior.

Only decoded token starts are authoritative: an operand byte equal to $1E is
allowed.  Every descriptor-selected direct entrypoint, including shared suffix
entrypoints, must close under the strict flat-direct profile and end at command
$00.  No output-file option is provided.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import dataclasses
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Final

import audit_battle_command_grammar_census_v0 as grammar
import audit_schala_player_tech_package_bank_adapter_v0 as adapter


ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_PATH: Final = (
    ROOT / "references" / "schala_expanded_package_command_policy_v0.json"
)

# Filled after the closed policy contract is generated and reviewed.
REFERENCE_SIZE: Final = 6_717
REFERENCE_SHA256: Final = (
    "808f286c37fd9163a776a5b545513aa1a9fb89f4c78281a204af5540f272c1ea"
)

SCHEMA: Final = "project-epoch-schala-expanded-package-command-policy-v0"
REFERENCE_SCHEMA: Final = (
    "project-epoch-schala-expanded-package-command-policy-contract-v0"
)
AUDITOR_VERSION: Final = "schala-expanded-package-command-policy-v0"
POLICY_ID: Final = "decoded-command-1e-exclusion-flat-direct-v0"
STATUS: Final = "pass-source-only-command-1e-exclusion-policy"

GRAMMAR_REFERENCE_SIZE: Final = 12_433
GRAMMAR_REFERENCE_SHA256: Final = (
    "1582aca15e209d8015d5c34fdf4016ee45e75d9872ff76f4933e29f80ce46e0c"
)
ADAPTER_REFERENCE_SIZE: Final = 12_280
ADAPTER_REFERENCE_SHA256: Final = (
    "dab2834afb28ea2b89e814747d4a079fef7a403ec67eba592a7f866c88faa69e"
)

GRAMMAR_AUDITOR_SOURCE_SIZE: Final = 53_608
GRAMMAR_AUDITOR_SOURCE_SHA256: Final = (
    "4d66c6b038cc5c541919b14c499890955e2797bc42300c956aefc98b73d13228"
)
ADAPTER_AUDITOR_SOURCE_SIZE: Final = 35_427
ADAPTER_AUDITOR_SOURCE_SHA256: Final = (
    "9a080e38839d2a0908acb09d8fdce9feb5ca90264fe79f120aeab9d74441c0e2"
)
GRAMMAR_TOKEN_SHAPE_PROFILE_ROW_COUNT: Final = 511
GRAMMAR_TOKEN_SHAPE_PROFILE_SHA256: Final = (
    "25502f827efd57ecaf920896a6216db2ad4278e66a2410ada1b7695a25a95f3d"
)

OBSERVED_OPCODE_COUNT: Final = 127
ALLOWED_OPCODE_COUNT: Final = 123
ALLOWED_OPCODE_VECTOR_SHA256: Final = (
    "2e3ae36cc7cb7a562c2e8ec3f5d67038ce09225953264c2ed5e3cb87a7fb39aa"
)

STOP_OPCODE: Final = 0x00
DEFAULT_STICKY_OBSERVED_OPCODE: Final = 0x01
SUBSCRIPT_CALL_OPCODE: Final = 0x1E
SUBSCRIPT_RETURN_OPCODE: Final = 0x1F
CONDITIONAL_PARENT_RETURN_OPCODE: Final = 0x21
CONDITIONAL_STOP_OPCODE: Final = 0x25
VARIABLE_OPCODE: Final = 0x80
LOOKAHEAD_OPCODE: Final = 0xDA
BANK_SIZE: Final = 0x10000

SYMBOLIC_NAME_RE: Final = re.compile(r"[A-Z][A-Z0-9_]{2,63}")

BANNED_OBSERVED_OPCODE_REASONS: Final = {
    DEFAULT_STICKY_OBSERVED_OPCODE: (
        "canonical default-handler sticky terminal is outside the strict "
        "authored profile"
    ),
    SUBSCRIPT_CALL_OPCODE: (
        "decoded command 1E is forbidden by the final exclusion policy"
    ),
    SUBSCRIPT_RETURN_OPCODE: (
        "command 1F requires a saved parent created by command 1E"
    ),
    CONDITIONAL_PARENT_RETURN_OPCODE: (
        "command 21 may restore a saved parent and is invalid in a flat "
        "direct stream"
    ),
}

LIMITATIONS: Final = (
    "This is a source-only authoring policy and validator, not a package, "
    "selector binding, allocation, hook, or runtime proof.",
    "The allowed opcode profile is limited to commands observed in the "
    "closed canonical primary-package census; observation is possible-context "
    "static evidence, not runtime frequency.",
    "Command 25 is validated along its forced-fallthrough tokenization; its "
    "conditional early-stop runtime branch is not replayed here.",
    "Command 80 with low nibble zero is deliberately forbidden even though "
    "the completed grammar models its one-byte ownership and 256-byte read "
    "lookahead.",
    "The policy validates primary command streams only; auxiliary graphics, "
    "palette, effect, sound, and fixed-bank config-byte readers remain "
    "separate gates.",
    "A future symbolic high package must pass this validator with exact named "
    "source spans before any production implementation is considered.",
)

NONCLAIMS: Final = (
    "No candidate package selector 80-8F is bound.",
    "No Schala action ID, Tech, item, animation, sprite, or logical PC 07 "
    "runtime is defined.",
    "No canonical command or package payload is copied or emitted.",
    "No command-1E handler adaptation or cross-bank subscript registry is "
    "implemented or approved.",
    "No expanded ROM bank, address, allocation, WRAM scratch, hook, helper, "
    "patch, ROM, save, state, trace, or emulator result is approved.",
    "Synthetic conformance bank values and offsets are test identities only, "
    "not free-space or placement claims.",
)


class ExpandedPackageCommandPolicyError(RuntimeError):
    """The policy, dependency, layout, or decoded stream failed closed."""


@dataclasses.dataclass(frozen=True)
class NamedSpan:
    name: str
    bank: int
    start: int
    end_exclusive: int


@dataclasses.dataclass(frozen=True)
class ExpandedPackageLayout:
    source: adapter.PackageSource
    descriptor_span: NamedSpan
    stream_spans: tuple[NamedSpan, ...]


@dataclasses.dataclass(frozen=True)
class PolicyToken:
    bank: int
    offset: int
    opcode: int
    owned_width: int
    known_lookahead_offsets: tuple[int, ...]
    span_name: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _metadata_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _strict_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ExpandedPackageCommandPolicyError(
            f"{label} must be an integer in {minimum:#x}-{maximum:#x}"
        )
    return value


def _dependency_source_identity(
    *,
    module_file: str,
    relative_path: str,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> dict[str, Any]:
    expected_path = (ROOT / relative_path).resolve()
    if Path(module_file).resolve() != expected_path:
        raise ExpandedPackageCommandPolicyError(
            f"{label} imported from an unexpected path"
        )
    try:
        source = expected_path.read_bytes()
    except OSError as exc:
        raise ExpandedPackageCommandPolicyError(
            f"cannot read {label} source"
        ) from exc
    digest = _sha256_bytes(source)
    if len(source) != expected_size or digest != expected_sha256:
        raise ExpandedPackageCommandPolicyError(
            f"{label} source identity drifted"
        )
    return {
        "path": relative_path,
        "size": len(source),
        "sha256": digest,
    }


def _grammar_token_shape_profile_rows() -> list[list[Any]]:
    rows: list[list[Any]] = []
    for opcode in range(0x100):
        payloads: Sequence[int | None]
        if opcode == VARIABLE_OPCODE:
            payloads = tuple(range(0x100))
        else:
            payloads = (None,)
        for first_payload in payloads:
            try:
                shape = grammar.token_shape(opcode, first_payload)
            except grammar.BattleCommandGrammarAuditError as exc:
                raise ExpandedPackageCommandPolicyError(
                    "grammar token-shape profile failed closed"
                ) from exc
            rows.append(
                [
                    opcode,
                    first_payload,
                    shape.owned_width,
                    shape.width_rule,
                    list(shape.known_lookahead_offsets),
                ]
            )
    return rows


def _dependency_interpreter_identities() -> dict[str, Any]:
    grammar_source = _dependency_source_identity(
        module_file=grammar.__file__,
        relative_path="tools/audit_battle_command_grammar_census_v0.py",
        expected_size=GRAMMAR_AUDITOR_SOURCE_SIZE,
        expected_sha256=GRAMMAR_AUDITOR_SOURCE_SHA256,
        label="battle-command grammar auditor",
    )
    adapter_source = _dependency_source_identity(
        module_file=adapter.__file__,
        relative_path=(
            "tools/audit_schala_player_tech_package_bank_adapter_v0.py"
        ),
        expected_size=ADAPTER_AUDITOR_SOURCE_SIZE,
        expected_sha256=ADAPTER_AUDITOR_SOURCE_SHA256,
        label="package-bank adapter auditor",
    )
    shape_rows = _grammar_token_shape_profile_rows()
    shape_digest = _metadata_sha256(shape_rows)
    if (
        len(shape_rows) != GRAMMAR_TOKEN_SHAPE_PROFILE_ROW_COUNT
        or shape_digest != GRAMMAR_TOKEN_SHAPE_PROFILE_SHA256
    ):
        raise ExpandedPackageCommandPolicyError(
            "grammar token-shape interpreter profile drifted"
        )
    return {
        "grammar_auditor_source": grammar_source,
        "package_bank_adapter_source": adapter_source,
        "grammar_token_shape_profile": {
            "row_count": len(shape_rows),
            "sha256": shape_digest,
        },
    }


def _validate_dependency_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        grammar.REFERENCE_SIZE != GRAMMAR_REFERENCE_SIZE
        or grammar.REFERENCE_SHA256 != GRAMMAR_REFERENCE_SHA256
    ):
        raise ExpandedPackageCommandPolicyError(
            "battle-command grammar dependency pin drifted"
        )
    if (
        adapter.REFERENCE_SIZE != ADAPTER_REFERENCE_SIZE
        or adapter.REFERENCE_SHA256 != ADAPTER_REFERENCE_SHA256
    ):
        raise ExpandedPackageCommandPolicyError(
            "package-bank adapter dependency pin drifted"
        )
    try:
        grammar_contract = grammar.load_reference_contract()
        adapter_contract = adapter.load_reference_contract()
    except (
        grammar.BattleCommandGrammarAuditError,
        adapter.PackageBankAdapterError,
    ) as exc:
        raise ExpandedPackageCommandPolicyError(
            f"closed dependency failed: {exc}"
        ) from exc
    _dependency_interpreter_identities()
    return grammar_contract, adapter_contract


def allowed_opcode_profile() -> frozenset[int]:
    grammar_contract, _ = _validate_dependency_contracts()
    frequency = grammar_contract["expected_results"]["stream_census"][
        "observed_opcode_frequency"
    ]
    if not isinstance(frequency, Mapping):
        raise ExpandedPackageCommandPolicyError(
            "grammar observed-opcode frequency shape drifted"
        )
    try:
        observed = {
            int(opcode, 16)
            for opcode, count in frequency.items()
            if type(opcode) is str and type(count) is int and count > 0
        }
    except ValueError as exc:
        raise ExpandedPackageCommandPolicyError(
            "grammar observed-opcode identity drifted"
        ) from exc
    if len(observed) != OBSERVED_OPCODE_COUNT:
        raise ExpandedPackageCommandPolicyError(
            "grammar observed-opcode count drifted"
        )
    if not set(BANNED_OBSERVED_OPCODE_REASONS) <= observed:
        raise ExpandedPackageCommandPolicyError(
            "one policy-banned opcode left the observed canonical profile"
        )
    allowed = frozenset(observed - set(BANNED_OBSERVED_OPCODE_REASONS))
    if len(allowed) != ALLOWED_OPCODE_COUNT:
        raise ExpandedPackageCommandPolicyError(
            "strict allowed-opcode count drifted"
        )
    vector = bytes(sorted(allowed))
    if _sha256_bytes(vector) != ALLOWED_OPCODE_VECTOR_SHA256:
        raise ExpandedPackageCommandPolicyError(
            "strict allowed-opcode vector drifted"
        )
    if STOP_OPCODE not in allowed or CONDITIONAL_STOP_OPCODE not in allowed:
        raise ExpandedPackageCommandPolicyError(
            "strict stop/fallthrough profile drifted"
        )
    return allowed


def _checked_source(source: Any) -> adapter.PackageSource:
    if not isinstance(source, adapter.PackageSource):
        raise ExpandedPackageCommandPolicyError(
            "layout source must be a PackageSource"
        )
    try:
        checked = adapter.make_package_source(
            selector=source.selector,
            bank=source.bank,
            root_offset=source.root_offset,
            allocation_name=source.allocation_name,
            source_kind=source.source_kind,
        )
    except adapter.PackageBankAdapterError as exc:
        raise ExpandedPackageCommandPolicyError(str(exc)) from exc
    if checked.source_kind != "synthetic-test":
        raise ExpandedPackageCommandPolicyError(
            "policy v0 accepts only unbound synthetic conformance sources"
        )
    if not adapter.EPOCH_PACKAGE_SELECTOR_FIRST <= checked.selector <= (
        adapter.EPOCH_PACKAGE_SELECTOR_LAST
    ):
        raise ExpandedPackageCommandPolicyError(
            "policy source lies outside candidate selector domain 80-8F"
        )
    return checked


def _checked_span(span: Any, *, expected_bank: int) -> NamedSpan:
    if not isinstance(span, NamedSpan):
        raise ExpandedPackageCommandPolicyError(
            "layout spans must be NamedSpan objects"
        )
    if type(span.name) is not str or not SYMBOLIC_NAME_RE.fullmatch(span.name):
        raise ExpandedPackageCommandPolicyError(
            "span name must be an explicit uppercase symbolic name"
        )
    bank = _strict_int(span.bank, "span bank", 0, 0xFF)
    start = _strict_int(span.start, "span start", 0, 0xFFFF)
    end = _strict_int(span.end_exclusive, "span end", 1, BANK_SIZE)
    if bank != expected_bank:
        raise ExpandedPackageCommandPolicyError(
            "every descriptor/stream span must inherit the package bank"
        )
    if end <= start:
        raise ExpandedPackageCommandPolicyError("span extent is empty or reversed")
    return NamedSpan(span.name, bank, start, end)


def _spans_overlap(left: NamedSpan, right: NamedSpan) -> bool:
    return (
        left.bank == right.bank
        and left.start < right.end_exclusive
        and right.start < left.end_exclusive
    )


def _checked_layout(
    bank_image: bytes,
    layout: Any,
) -> tuple[
    adapter.PackageDescriptor,
    NamedSpan,
    tuple[NamedSpan, ...],
    dict[int, NamedSpan],
]:
    if type(bank_image) is not bytes or len(bank_image) != BANK_SIZE:
        raise ExpandedPackageCommandPolicyError(
            "policy input must be one immutable 64 KiB synthetic bank image"
        )
    if not isinstance(layout, ExpandedPackageLayout):
        raise ExpandedPackageCommandPolicyError(
            "layout must be an ExpandedPackageLayout"
        )
    source = _checked_source(layout.source)
    descriptor_span = _checked_span(
        layout.descriptor_span,
        expected_bank=source.bank,
    )
    if descriptor_span.name != source.allocation_name:
        raise ExpandedPackageCommandPolicyError(
            "descriptor span name must equal the package-source allocation name"
        )
    if not isinstance(layout.stream_spans, tuple) or not layout.stream_spans:
        raise ExpandedPackageCommandPolicyError(
            "layout requires one or more explicit stream spans"
        )
    stream_spans = tuple(
        _checked_span(span, expected_bank=source.bank)
        for span in layout.stream_spans
    )
    names = [descriptor_span.name, *(span.name for span in stream_spans)]
    if len(names) != len(set(names)):
        raise ExpandedPackageCommandPolicyError("layout span names must be unique")
    for index, left in enumerate((descriptor_span, *stream_spans)):
        for right in (descriptor_span, *stream_spans)[index + 1 :]:
            if _spans_overlap(left, right):
                raise ExpandedPackageCommandPolicyError(
                    "descriptor and stream allocations must be pairwise disjoint"
                )
    try:
        descriptor = adapter.parse_package_descriptor(bank_image, source)
    except adapter.PackageBankAdapterError as exc:
        raise ExpandedPackageCommandPolicyError(str(exc)) from exc
    if not descriptor.entries:
        raise ExpandedPackageCommandPolicyError(
            "expanded descriptor must select at least one direct entrypoint"
        )
    if (
        descriptor_span.start != source.root_offset
        or descriptor_span.end_exclusive != descriptor.end_offset_exclusive
    ):
        raise ExpandedPackageCommandPolicyError(
            "descriptor span must exactly own the parsed descriptor"
        )

    entry_to_span: dict[int, NamedSpan] = {}
    for entrypoint in sorted({entry.script_offset for entry in descriptor.entries}):
        matches = [
            span
            for span in stream_spans
            if span.start <= entrypoint < span.end_exclusive
        ]
        if len(matches) != 1:
            raise ExpandedPackageCommandPolicyError(
                "each descriptor-selected entrypoint must belong to exactly "
                "one stream span"
            )
        entry_to_span[entrypoint] = matches[0]
    used_span_names = {span.name for span in entry_to_span.values()}
    if used_span_names != {span.name for span in stream_spans}:
        raise ExpandedPackageCommandPolicyError(
            "every declared stream span must contain a selected entrypoint"
        )
    return descriptor, descriptor_span, stream_spans, entry_to_span


def _token_signature(token: PolicyToken) -> tuple[Any, ...]:
    return (
        token.opcode,
        token.owned_width,
        token.known_lookahead_offsets,
        token.span_name,
    )


def _register_token(
    token: PolicyToken,
    *,
    tokens: dict[tuple[int, int], PolicyToken],
    coverage: dict[tuple[int, int], tuple[int, int]],
) -> None:
    key = (token.bank, token.offset)
    prior = tokens.get(key)
    if prior is not None and _token_signature(prior) != _token_signature(token):
        raise ExpandedPackageCommandPolicyError(
            "one shared token start decoded inconsistently"
        )
    for relative in range(token.owned_width):
        byte_key = (token.bank, token.offset + relative)
        owner = coverage.get(byte_key)
        if owner is not None and owner != key:
            raise ExpandedPackageCommandPolicyError(
                "descriptor-selected entrypoint begins inside another token"
            )
    tokens.setdefault(key, token)
    for relative in range(token.owned_width):
        coverage.setdefault((token.bank, token.offset + relative), key)


def _decode_policy_token(
    bank_image: bytes,
    *,
    bank: int,
    cursor: int,
    span: NamedSpan,
    allowed_opcodes: frozenset[int],
) -> PolicyToken:
    if not span.start <= cursor < span.end_exclusive:
        raise ExpandedPackageCommandPolicyError(
            "forced fallthrough left its declared stream span before command 00"
        )
    opcode = bank_image[cursor]
    if opcode == SUBSCRIPT_CALL_OPCODE:
        raise ExpandedPackageCommandPolicyError(
            "decoded command 1E is forbidden in every expanded-package stream"
        )
    reason = BANNED_OBSERVED_OPCODE_REASONS.get(opcode)
    if reason is not None:
        raise ExpandedPackageCommandPolicyError(reason)
    if opcode not in allowed_opcodes:
        raise ExpandedPackageCommandPolicyError(
            f"opcode {opcode:02X} is outside the strict observed authoring profile"
        )

    first_payload: int | None = None
    if opcode == VARIABLE_OPCODE:
        if cursor + 1 >= span.end_exclusive:
            raise ExpandedPackageCommandPolicyError(
                "command 80 lacks its first payload byte inside the stream span"
            )
        first_payload = bank_image[cursor + 1]
        if first_payload & 0x0F == 0:
            raise ExpandedPackageCommandPolicyError(
                "command 80 low-nibble-zero wrap is forbidden in authored streams"
            )
    try:
        shape = grammar.token_shape(opcode, first_payload)
    except grammar.BattleCommandGrammarAuditError as exc:
        raise ExpandedPackageCommandPolicyError(str(exc)) from exc
    if cursor + shape.owned_width > span.end_exclusive:
        raise ExpandedPackageCommandPolicyError(
            "command token crosses its declared stream span"
        )
    for relative in shape.known_lookahead_offsets:
        if cursor + relative >= span.end_exclusive:
            raise ExpandedPackageCommandPolicyError(
                "command read-lookahead crosses its declared stream span"
            )
    return PolicyToken(
        bank=bank,
        offset=cursor,
        opcode=opcode,
        owned_width=shape.owned_width,
        known_lookahead_offsets=shape.known_lookahead_offsets,
        span_name=span.name,
    )


def validate_expanded_package_command_policy(
    bank_image: bytes,
    layout: ExpandedPackageLayout,
) -> dict[str, Any]:
    """Validate every descriptor-selected direct/suffix stream in memory."""

    allowed_opcodes = allowed_opcode_profile()
    descriptor, descriptor_span, stream_spans, entry_to_span = _checked_layout(
        bank_image,
        layout,
    )
    try:
        branch_states = (
            adapter.simulate_descriptor_install(
                bank_image,
                descriptor.source,
                a0b3=0,
            ),
            adapter.simulate_descriptor_install(
                bank_image,
                descriptor.source,
                a0b3=1,
            ),
        )
    except adapter.PackageBankAdapterError as exc:
        raise ExpandedPackageCommandPolicyError(str(exc)) from exc
    for branch, state in enumerate(branch_states):
        expected_branch = sorted(
            (entry.owner_slot, entry.script_offset)
            for entry in descriptor.entries
            if entry.branch == branch
        )
        observed_branch = sorted(
            (publication.owner_slot, publication.script_offset)
            for publication in state.publications
        )
        if observed_branch != expected_branch:
            raise ExpandedPackageCommandPolicyError(
                "descriptor branch publication witness drifted"
            )
    tokens: dict[tuple[int, int], PolicyToken] = {}
    coverage: dict[tuple[int, int], tuple[int, int]] = {}
    traces: dict[int, tuple[tuple[int, int], ...]] = {}
    traversal_counts: Counter[tuple[int, int]] = Counter()

    for entrypoint in sorted(entry_to_span):
        span = entry_to_span[entrypoint]
        cursor = entrypoint
        trace: list[tuple[int, int]] = []
        while True:
            token = _decode_policy_token(
                bank_image,
                bank=descriptor.source.bank,
                cursor=cursor,
                span=span,
                allowed_opcodes=allowed_opcodes,
            )
            _register_token(token, tokens=tokens, coverage=coverage)
            key = (token.bank, token.offset)
            trace.append(key)
            traversal_counts[key] += 1
            if token.opcode == STOP_OPCODE:
                break
            cursor += token.owned_width
        traces[entrypoint] = tuple(trace)

    for span in stream_spans:
        expected = {
            (span.bank, offset)
            for offset in range(span.start, span.end_exclusive)
        }
        actual = {key for key in coverage if key in expected}
        if actual != expected:
            raise ExpandedPackageCommandPolicyError(
                "stream span contains unowned bytes or unreachable padding"
            )

    token_rows = [
        [
            token.bank,
            token.offset,
            token.opcode,
            token.owned_width,
            list(token.known_lookahead_offsets),
            token.span_name,
        ]
        for _, token in sorted(tokens.items())
    ]
    trace_rows = [
        [entrypoint, [list(key) for key in traces[entrypoint]]]
        for entrypoint in sorted(traces)
    ]
    coverage_rows = [
        [bank, offset, owner[0], owner[1]]
        for (bank, offset), owner in sorted(coverage.items())
    ]
    raw_1e_count = sum(
        bank_image[offset] == SUBSCRIPT_CALL_OPCODE
        for span in stream_spans
        for offset in range(span.start, span.end_exclusive)
    )
    opcode_counts = Counter(token.opcode for token in tokens.values())
    descriptor_entry_rows = [
        [entry.branch, entry.owner_slot, entry.bank, entry.script_offset]
        for entry in descriptor.entries
    ]
    content_rows = [
        [
            descriptor_span.name,
            descriptor_span.bank,
            descriptor_span.start,
            descriptor_span.end_exclusive,
            _sha256_bytes(
                bank_image[
                    descriptor_span.start : descriptor_span.end_exclusive
                ]
            ),
        ],
        *(
            [
                span.name,
                span.bank,
                span.start,
                span.end_exclusive,
                _sha256_bytes(
                    bank_image[span.start : span.end_exclusive]
                ),
            ]
            for span in stream_spans
        ),
    ]
    termination_rows = [
        [entrypoint, traces[entrypoint][-1][0], traces[entrypoint][-1][1]]
        for entrypoint in sorted(traces)
    ]
    exclusion_proof = {
        "policy_id": POLICY_ID,
        "dependencies": {
            "grammar_reference_sha256": GRAMMAR_REFERENCE_SHA256,
            "adapter_reference_sha256": ADAPTER_REFERENCE_SHA256,
            "allowed_opcode_vector_sha256": ALLOWED_OPCODE_VECTOR_SHA256,
            "interpreter_identities": _dependency_interpreter_identities(),
        },
        "source_identity": [
            descriptor.source.selector,
            descriptor.source.bank,
            descriptor.source.root_offset,
            descriptor.source.allocation_name,
            descriptor.source.source_kind,
        ],
        "content_rows": content_rows,
        "descriptor_entry_rows": descriptor_entry_rows,
        "token_rows": token_rows,
        "trace_rows": trace_rows,
        "termination_rows": termination_rows,
        "coverage_rows": coverage_rows,
    }
    return {
        "status": "pass-all-selected-flat-direct-streams-exclude-command-1e",
        "policy_id": POLICY_ID,
        "expanded_source_1e_absence_proved": True,
        "command_1e_cross_bank_subscripts_resolved": False,
        "package_selector": f"{descriptor.source.selector:02X}",
        "descriptor_relation_count": len(descriptor.entries),
        "mask0_relation_count": len(branch_states[0].publications),
        "mask1_relation_count": len(branch_states[1].publications),
        "both_descriptor_masks_validated": True,
        "distinct_direct_entrypoint_count": len(entry_to_span),
        "stream_span_count": len(stream_spans),
        "unique_token_start_count": len(tokens),
        "unique_owned_byte_count": len(coverage),
        "total_entrypoint_traversal_token_count": sum(
            len(trace) for trace in traces.values()
        ),
        "shared_token_start_count": sum(
            count > 1 for count in traversal_counts.values()
        ),
        "decoded_command_1e_site_count": opcode_counts[
            SUBSCRIPT_CALL_OPCODE
        ],
        "top_level_command_1f_site_count": opcode_counts[
            SUBSCRIPT_RETURN_OPCODE
        ],
        "top_level_command_21_site_count": opcode_counts[
            CONDITIONAL_PARENT_RETURN_OPCODE
        ],
        "raw_byte_equal_1e_inside_stream_span_count": raw_1e_count,
        "command_00_terminal_count": opcode_counts[STOP_OPCODE],
        "command_25_site_count": opcode_counts[CONDITIONAL_STOP_OPCODE],
        "command_80_site_count": opcode_counts[VARIABLE_OPCODE],
        "command_da_site_count": opcode_counts[LOOKAHEAD_OPCODE],
        "descriptor_stream_overlap_count": 0,
        "unowned_stream_byte_count": 0,
        "token_extent_conflict_count": 0,
        "source_content_size": sum(
            row[3] - row[2] for row in content_rows
        ),
        "source_content_ledger_sha256": _metadata_sha256(content_rows),
        "command_exclusion_proof_sha256": _metadata_sha256(
            exclusion_proof
        ),
        "descriptor_entry_ledger_sha256": _metadata_sha256(
            descriptor_entry_rows
        ),
        "token_ledger_sha256": _metadata_sha256(token_rows),
        "trace_ledger_sha256": _metadata_sha256(trace_rows),
        "termination_ledger_sha256": _metadata_sha256(termination_rows),
        "owned_byte_ledger_sha256": _metadata_sha256(coverage_rows),
        "descriptor_span_size": (
            descriptor_span.end_exclusive - descriptor_span.start
        ),
        "stream_span_total_size": sum(
            span.end_exclusive - span.start for span in stream_spans
        ),
        "raw_stream_or_descriptor_bytes_emitted": False,
    }


def _build_conformance_vector() -> tuple[bytes, ExpandedPackageLayout]:
    bank = 0x40
    descriptor_root = 0x1000
    stream_start = 0x2000
    image = bytearray(BANK_SIZE)
    # Two mask-0 owners select one primary entry and its command-00 suffix.
    image[descriptor_root : descriptor_root + 4] = bytes((0xC0, 0x00, 0, 0))
    image[descriptor_root + 4 : descriptor_root + 6] = (
        stream_start.to_bytes(2, "little")
    )
    image[descriptor_root + 6 : descriptor_root + 8] = (
        (stream_start + 2).to_bytes(2, "little")
    )
    # Opcode 02 owns its following operand byte.  The operand deliberately
    # equals 1E; only decoded token starts are subject to the exclusion.
    image[stream_start : stream_start + 3] = bytes((0x02, 0x1E, 0x00))
    source = adapter.make_package_source(
        selector=0x80,
        bank=bank,
        root_offset=descriptor_root,
        allocation_name="EPOCH_POLICY_VECTOR_DESCRIPTOR",
        source_kind="synthetic-test",
    )
    layout = ExpandedPackageLayout(
        source=source,
        descriptor_span=NamedSpan(
            "EPOCH_POLICY_VECTOR_DESCRIPTOR",
            bank,
            descriptor_root,
            descriptor_root + 8,
        ),
        stream_spans=(
            NamedSpan(
                "EPOCH_POLICY_VECTOR_STREAM",
                bank,
                stream_start,
                stream_start + 3,
            ),
        ),
    )
    return bytes(image), layout


def expected_results() -> dict[str, Any]:
    image, layout = _build_conformance_vector()
    return {
        "observed_canonical_opcode_count": OBSERVED_OPCODE_COUNT,
        "strict_allowed_opcode_count": len(allowed_opcode_profile()),
        "strict_allowed_opcode_vector_sha256": ALLOWED_OPCODE_VECTOR_SHA256,
        "banned_observed_opcodes": [
            f"{opcode:02X}" for opcode in sorted(BANNED_OBSERVED_OPCODE_REASONS)
        ],
        "conformance_vector": validate_expanded_package_command_policy(
            image,
            layout,
        ),
    }


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema",
        "version",
        "evidence_level",
        "scope",
        "dependencies",
        "decision",
        "expected_results",
        "limitations",
        "nonclaims",
    }
    if set(contract) != expected_keys:
        raise ExpandedPackageCommandPolicyError(
            "policy reference top-level shape drifted"
        )
    if contract["schema"] != REFERENCE_SCHEMA or contract["version"] != 0:
        raise ExpandedPackageCommandPolicyError(
            "policy reference identity drifted"
        )
    if contract["evidence_level"] != "verified-static":
        raise ExpandedPackageCommandPolicyError(
            "policy reference evidence level drifted"
        )
    if not isinstance(contract["scope"], Mapping):
        raise ExpandedPackageCommandPolicyError("policy scope is invalid")
    dependencies = contract["dependencies"]
    if not isinstance(dependencies, Mapping) or dependencies != {
        "battle_command_grammar_reference": {
            "schema": grammar.REFERENCE_SCHEMA,
            "size": GRAMMAR_REFERENCE_SIZE,
            "sha256": GRAMMAR_REFERENCE_SHA256,
        },
        "package_bank_adapter_reference": {
            "schema": adapter.SCHEMA,
            "size": ADAPTER_REFERENCE_SIZE,
            "sha256": ADAPTER_REFERENCE_SHA256,
        },
        "interpreter_identities": _dependency_interpreter_identities(),
    }:
        raise ExpandedPackageCommandPolicyError(
            "policy dependency contract drifted"
        )
    decision = contract["decision"]
    required_decision = {
        "policy_id": POLICY_ID,
        "command_1e": "forbidden at every decoded token start",
        "raw_byte_scan_is_authority": False,
        "command_1f": "forbidden in flat direct streams",
        "command_21": "forbidden in flat direct streams",
        "command_25": "allowed with forced-fallthrough validation",
        "terminal": "command 00 only",
        "command_80_zero_nibble": "forbidden",
        "command_da_lookahead": "must remain inside its named stream span",
        "opcode_profile": (
            "canonical-census-observed opcodes minus 01,1E,1F,21"
        ),
        "descriptor_stream_overlap": "forbidden for authored Epoch data",
        "stream_span_coverage": "every byte must be token-owned",
        "suffix_entrypoints": (
            "every distinct descriptor-selected pointer is decoded independently"
        ),
        "command_1e_handler_adaptation": False,
        "final_for_profile_v0": True,
    }
    if not isinstance(decision, Mapping) or dict(decision) != required_decision:
        raise ExpandedPackageCommandPolicyError(
            "policy decision contract drifted"
        )
    if contract["expected_results"] != expected_results():
        raise ExpandedPackageCommandPolicyError(
            "policy expected results drifted"
        )
    limitations = contract["limitations"]
    if not isinstance(limitations, list) or limitations != list(LIMITATIONS):
        raise ExpandedPackageCommandPolicyError(
            "policy limitations drifted"
        )
    nonclaims = contract["nonclaims"]
    if not isinstance(nonclaims, list) or nonclaims != list(NONCLAIMS):
        raise ExpandedPackageCommandPolicyError("policy nonclaims drifted")


def load_reference_contract() -> dict[str, Any]:
    try:
        source = REFERENCE_PATH.read_bytes()
    except OSError as exc:
        raise ExpandedPackageCommandPolicyError(
            f"cannot read policy reference: {REFERENCE_PATH.name}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise ExpandedPackageCommandPolicyError(
            "policy reference size drifted"
        )
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise ExpandedPackageCommandPolicyError(
            "policy reference hash drifted"
        )
    try:
        value = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExpandedPackageCommandPolicyError(
            "policy reference is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise ExpandedPackageCommandPolicyError(
            "policy reference is not an object"
        )
    _validate_reference_contract(value)
    return value


def _auditor_source_identity() -> dict[str, Any]:
    source = Path(__file__).resolve().read_bytes()
    return {
        "path": "tools/audit_schala_expanded_package_command_policy_v0.py",
        "size": len(source),
        "sha256": _sha256_bytes(source),
    }


def _attach_artifact_identity(report: dict[str, Any]) -> dict[str, Any]:
    result = dict(report)
    result["artifact_identity"] = {
        "canonical_json_sha256_excluding_artifact_identity": (
            _metadata_sha256(report)
        )
    }
    return result


def build_report() -> dict[str, Any]:
    _validate_dependency_contracts()
    contract = load_reference_contract()
    results = expected_results()
    report = {
        "schema": SCHEMA,
        "version": 0,
        "auditor_version": AUDITOR_VERSION,
        "status": STATUS,
        "evidence_ceiling": (
            "verified-static source-only decoded-command-1E exclusion policy"
        ),
        "scope": dict(contract["scope"]),
        "dependencies": dict(contract["dependencies"]),
        "decision": dict(contract["decision"]),
        "results": results,
        "gates": {
            "closed_grammar_dependency_passed": True,
            "closed_package_bank_adapter_dependency_passed": True,
            "dependency_interpreters_exactly_pinned": True,
            "conformance_vector_decoded_command_1e_excluded": True,
            "conformance_vector_raw_operand_byte_equal_1e_accepted": True,
            "conformance_vector_every_selected_entrypoint_validated": True,
            "descriptor_stream_overlap_forbidden": True,
            "stream_spans_exactly_token_owned": True,
            "command_1e_handler_adaptation_approved": False,
            "symbolic_high_package_bound": False,
            "allocation_or_hook_approved": False,
            "runtime_performed": False,
            "rom_save_state_trace_mutation_performed": False,
            "patch_rom_or_output_file_emitted": False,
        },
        "evidence": {
            "level": "verified-static",
            "source_only": True,
            "metadata_only": True,
            "canonical_rom_accessed": False,
            "runtime": False,
        },
        "reproduction": {
            "command": [
                "python",
                "-B",
                "tools/audit_schala_expanded_package_command_policy_v0.py",
                "--compact",
            ],
            "output": "metadata-only JSON on stdout",
            "output_file_option_available": False,
            "expected_side_effects": "none",
            "expected_stderr": "empty",
            "auditor_source": _auditor_source_identity(),
            "reference_contract": {
                "path": (
                    "references/"
                    "schala_expanded_package_command_policy_v0.json"
                ),
                "size": REFERENCE_SIZE,
                "sha256": REFERENCE_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "nonclaims": list(NONCLAIMS),
    }
    return _attach_artifact_identity(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print compact JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_report()
    except (
        ExpandedPackageCommandPolicyError,
        adapter.PackageBankAdapterError,
        grammar.BattleCommandGrammarAuditError,
        OSError,
        ValueError,
    ) as exc:
        print(f"expanded package command policy failed: {exc}", file=sys.stderr)
        return 1
    if args.compact:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
