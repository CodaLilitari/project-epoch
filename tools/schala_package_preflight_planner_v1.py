"""Pure, deliberately narrow canonical-donor context planner; no file access.

This module never certifies runtime provenance, command-policy validity or
action completion. Its qualified request needs the separate pinned auditor.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re

POLICY_ID = 'decoded-command-1e-exclusion-flat-direct-v0'
SUCCESS = 'observed-lavos-luminaire-pre-effect-v1'
REFUSAL = 'observed-lavos-cure-target-refusal-v1'
DONOR_ROW = 8
DONOR_SHA = '044dfdb673f9506789daf42470a7d5173f70354169f6ecc5006235783a46b334'
SUFFIX_SHA = '642eb9302b2906890aceb5baf58a28e11dfdaff1ed15d1233db7c401bb5f1a96'
CANDIDATE_SHA = '9c747786b110ff2b63c293e3cacefa0fb84e436f48257cd139742e0a339dbf3e'
TRACE_SHA = {
    SUCCESS: 'fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7',
    REFUSAL: '63f94fff2b81292b593073e1197b7a8b8778cf6f4b217e2caa02adb0d61efd15',
}
RECORD_SHA = {
    SUCCESS: 'b9ddf0bea98b713a8b13cbc89540c4f3f71fc23e2547909054b4c8112b2b6fa5',
    REFUSAL: 'b798a62edf5e1eee2d469e47866ec69b149351daa66706e345cd7a37e10fb0bb',
}
CPU_FIELDS = ('a', 'x', 'y', 'd', 'dbr', 'sp', 'ps', 'k', 'pc', 'emulationMode')


class PreflightError(ValueError):
    def __init__(self, reason: str, detail: str):
        self.reason = reason
        super().__init__(reason + ': ' + detail)


def require(condition, reason, detail):
    if not condition:
        raise PreflightError(reason, detail)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def integer(value, low, high, name):
    require(type(value) is int and low <= value <= high, 'malformed-context', name)


def digest(value, name):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'malformed-context', name)


def byte_tuple(value, size, name):
    require(type(value) is tuple and len(value) == size, 'malformed-context', name)
    for b in value:
        integer(b, 0, 255, name)


@dataclass(frozen=True)
class Context:
    profile: str
    boundary: int
    invocation_id: int
    input_poll: int
    cpu: tuple
    stack: bytes
    queue: bytes
    queue_pointer: int
    queue_owner_slot: int
    action_id: int
    participants: tuple
    participant_map: tuple
    animation_identity: tuple
    af22: int
    af23: int
    b3c8: int
    b3f4: int
    trace_sha256: str
    record_sha256: str


@dataclass(frozen=True)
class Span:
    name: str
    bank: int
    start: int
    end: int


@dataclass(frozen=True)
class Package:
    selector: int
    bank: int
    root: int
    source_kind: str
    image: bytes
    descriptor: Span
    streams: tuple


@dataclass(frozen=True)
class Association:
    profile: str
    action_id: int
    config_row: int
    donor_sha256: str
    suffix_sha256: str
    package_selector: int
    bank: int
    root: int
    source_kind: str
    image_sha256: str
    layout_sha256: str
    policy_id: str


@dataclass(frozen=True)
class Request:
    mode: str
    donor_row: int | None = None
    donor: bytes | None = None
    candidate: bytes | None = None
    associations: tuple = ()
    package: Package | None = None


@dataclass(frozen=True)
class Decision:
    status: str
    profile: str
    context_sha256: str
    package_evaluation: str
    donor_evaluation: str
    donor_sha256: str | None = None
    suffix_sha256: str | None = None
    candidate_sha256: str | None = None
    image_sha256: str | None = None
    layout_sha256: str | None = None
    association_sha256: str | None = None
    policy_id: str | None = None
    production_approved: bool = False
    native_cleanup_approved: bool = False
    action_completion_approved: bool = False
    runtime_integration_proved: bool = False
    runtime_context_certified: bool = False


def _plain(value):
    """Private canonical identity projection; never emit snapshot byte payload."""
    if type(value) is bytes:
        return {'size': len(value), 'sha256': sha(value)}
    if type(value) is tuple:
        return [_plain(v) for v in value]
    if type(value) in (Context, Span, Package, Association, Request, Decision):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    return value


def object_sha(value):
    return sha(canonical(_plain(value)))


def layout_metadata(package):
    return {'selector': package.selector, 'bank': package.bank, 'root': package.root,
            'source_kind': package.source_kind, 'descriptor': _plain(package.descriptor),
            'streams': _plain(package.streams)}


def layout_sha(package):
    return sha(canonical(layout_metadata(package)))


def validate_context(context):
    require(type(context) is Context, 'malformed-context', 'exact immutable Context required')
    require(type(context.profile) is str and context.profile in (SUCCESS, REFUSAL),
            'unsupported-context', 'profile')
    for k in ('boundary', 'invocation_id', 'input_poll', 'queue_pointer', 'queue_owner_slot',
              'action_id', 'af22', 'af23', 'b3c8', 'b3f4'):
        integer(getattr(context, k), 0, 0xFFFFFF if k == 'boundary' else 65535, k)
    require(type(context.cpu) is tuple and len(context.cpu) == len(CPU_FIELDS),
            'malformed-context', 'CPU tuple')
    for name, v in zip(CPU_FIELDS[:-1], context.cpu[:-1]):
        integer(v, 0, 255 if name in ('dbr', 'ps', 'k') else 65535, 'CPU ' + name)
    require(context.cpu[-1] is False, 'malformed-context', 'native CPU required')
    require(type(context.stack) is bytes and len(context.stack) == 16,
            'malformed-context', '16 immutable sampled stack bytes')
    require(type(context.queue) is bytes and len(context.queue) == 21,
            'malformed-context', '21 immutable queue bytes')
    byte_tuple(context.participants, 3, 'participants')
    byte_tuple(context.participant_map, 7, 'participant map')
    byte_tuple(context.animation_identity, 4, 'animation identity')
    digest(context.trace_sha256, 'trace SHA'); digest(context.record_sha256, 'record SHA')
    require(context.action_id < 0x80 and context.queue_owner_slot < 3,
            'unsupported-context', 'canonical action and supported queue owner required')
    live = [p for p in context.participants if p != 255]
    require(live and all(p < 7 for p in live) and len(set(live)) == len(live),
            'malformed-context', 'participants must be distinct canonical logical PCs')
    require(context.participants == tuple(live) + (255,) * (3-len(live)),
            'malformed-context', 'absent participants must trail')
    mapped = [p for p in context.participant_map if p != 255]
    require(all(p < 3 for p in mapped) and len(mapped) == len(set(mapped)),
            'malformed-context', 'invalid or duplicate mapped battle slot')
    require(all(context.participant_map[p] < 3 for p in live),
            'malformed-context', 'participant is absent from party map')
    require(context.queue_pointer == 0x93EE + context.queue_owner_slot * 7,
            'malformed-context', 'queue pointer/owner mismatch')
    row = context.queue[context.queue_owner_slot*7:context.queue_owner_slot*7+7]
    require(row[6] == context.action_id and row[1] == 0x20 and row[2] == 1,
            'malformed-context', 'unsupported or inconsistent queued Tech fields')

    # Closed, observed profile assertions. They do not define a general queue,
    # target or MP-feasibility model, and hashes alone are not provenance.
    success = context.profile == SUCCESS
    expected = {
        'boundary': 0xC1BBD4 if success else 0xC1BB8B,
        'invocation_id': 1, 'input_poll': 374 if success else 2560,
        'cpu': (0, 0, 3, 0, 0x7E, 0x06EA, 0x22, 0xC1, 0xBBD4, False) if success else
               (1, 0x100, 0x93F5, 0, 0x7E, 0x06EA, 0x20, 0xC1, 0xBB8B, False),
        'stack': bytes((0xD0 if success else 0xE9,0x85,0x35,0x83,0x0C,0,0x90,0,0,5,0,1,0,1,0,0x23)),
        'queue': bytes.fromhex('0120010300ff080000000000ff000000000000ff00' if success else
                               '8100000000ff000120010200ff0c0000000000ff00'),
        'queue_pointer': 0x93EE if success else 0x93F5,
        'queue_owner_slot': 0 if success else 1, 'action_id': 8 if success else 12,
        'participants': (0,255,255) if success else (1,255,255),
        'participant_map': (0,1,2,255,255,255,255),
        'animation_identity': (0,2,8,0) if success else (3,2,0,0),
        'af22': 1, 'af23': 0 if success else 1, 'b3c8': 0, 'b3f4': 0 if success else 1,
        'trace_sha256': TRACE_SHA[context.profile], 'record_sha256': RECORD_SHA[context.profile],
    }
    for name, wanted in expected.items():
        require(getattr(context, name) == wanted, 'unsupported-context', 'exact profile differs: ' + name)


def validate_package_shape(package):
    require(type(package) is Package, 'malformed-context', 'exact immutable Package required')
    for k in ('selector', 'bank', 'root'):
        integer(getattr(package, k), 0, 65535 if k == 'root' else 255, 'package ' + k)
    require(package.selector == 0x80 and package.bank == 0x42 and package.source_kind == 'synthetic-test'
            and type(package.source_kind) is str,
            'unsupported-context', 'only explicit synthetic bank42 selector80 in v1')
    require(type(package.image) is bytes and len(package.image) == 65536,
            'malformed-context', 'exact immutable bank envelope required')
    require(type(package.streams) is tuple and 1 <= len(package.streams) <= 32,
            'malformed-context', 'immutable bounded stream spans')
    names = []
    for span in (package.descriptor,) + package.streams:
        require(type(span) is Span, 'malformed-context', 'exact immutable Span required')
        require(type(span.name) is str and re.fullmatch('[A-Z][A-Z0-9_]{2,63}', span.name) is not None,
                'malformed-context', 'symbolic span name')
        for k in ('bank', 'start', 'end'):
            integer(getattr(span, k), 0, 255 if k == 'bank' else 65536, 'span ' + k)
        require(span.bank == package.bank and 0 <= span.start < span.end <= 65536,
                'malformed-context', 'span bank/bounds')
        names.append(span.name)
    require(len(names) == len(set(names)), 'malformed-context', 'duplicate allocation name')
    require(package.root == package.descriptor.start, 'malformed-context', 'descriptor root mismatch')
    # Overlap and complete token/descriptor extents deliberately remain subject
    # to the mandatory existing policy; this shape pass is not a certificate.


def validate_association(association, context, package):
    require(type(association) is Association, 'malformed-context', 'exact immutable Association required')
    for k in ('profile', 'source_kind', 'policy_id'):
        require(type(getattr(association, k)) is str, 'malformed-context', 'association ' + k)
    for k in ('action_id', 'config_row', 'package_selector', 'bank', 'root'):
        integer(getattr(association, k), 0, 65535 if k == 'root' else 255, 'association ' + k)
    for k in ('donor_sha256', 'suffix_sha256', 'image_sha256', 'layout_sha256'):
        digest(getattr(association, k), k)
    expected = Association(context.profile, 8, 8, DONOR_SHA, SUFFIX_SHA, package.selector,
                           package.bank, package.root, 'synthetic-test', sha(package.image),
                           layout_sha(package), POLICY_ID)
    require(association == expected, 'source-drift', 'explicit action/config/package association mismatch')


def plan(context: Context, request: Request) -> Decision:
    validate_context(context)
    require(type(request) is Request and type(request.mode) is str,
            'malformed-context', 'exact immutable Request required')
    require(type(request.associations) is tuple, 'malformed-context', 'immutable association tuple')
    context_hash = object_sha(context)
    if context.profile == REFUSAL:
        require(request == Request('observed-native-refusal'), 'unsupported-context',
                'already refused context accepts no donor/package request')
        return Decision('native-target-refusal-observed', context.profile, context_hash,
                        'not-evaluated', 'not-evaluated')
    require(request.mode in ('canonical-baseline', 'diagnostic-primary-substitution'),
            'unsupported-context', 'request mode')
    integer(request.donor_row, 0, 255, 'donor row')
    require(request.donor_row == DONOR_ROW and type(request.donor) is bytes and len(request.donor) == 7
            and sha(request.donor) == DONOR_SHA and request.donor[0] == 8,
            'donor-mismatch', 'exact source-derived canonical row08 required')
    require(sha(request.donor[1:]) == SUFFIX_SHA, 'donor-mismatch', 'donor suffix identity')
    if request.mode == 'canonical-baseline':
        require(request.candidate is None and not request.associations and request.package is None,
                'unsupported-context', 'canonical pass-through accepts no replacement')
        return Decision('canonical-path-preserved', context.profile, context_hash, 'not-evaluated',
                        'canonical-source-equality', DONOR_SHA, SUFFIX_SHA)
    require(type(request.candidate) is bytes and len(request.candidate) == 7,
            'donor-mismatch', 'immutable seven-byte candidate required')
    require(request.candidate[1:] == request.donor[1:], 'auxiliary-mismatch', 'preserve every byte +1..+6')
    require(request.candidate[0] == 0x80 and sha(request.candidate) == CANDIDATE_SHA,
            'donor-mismatch', 'only byte+0 substitution to selector80')
    require(len(request.associations) != 0, 'unbound-diagnostic-package', 'default high registry is empty')
    require(len(request.associations) == 1, 'malformed-context', 'one explicit association; no duplicate selectors')
    validate_package_shape(request.package)
    validate_association(request.associations[0], context, request.package)
    return Decision('requires-package-policy-validation', context.profile, context_hash,
                    'not-yet-evaluated', 'canonical-donor-equality', DONOR_SHA, SUFFIX_SHA,
                    CANDIDATE_SHA, sha(request.package.image), layout_sha(request.package),
                    object_sha(request.associations[0]), POLICY_ID)


def decision_metadata(decision):
    require(type(decision) is Decision, 'malformed-context', 'exact Decision required')
    for name in ('production_approved', 'native_cleanup_approved', 'action_completion_approved',
                 'runtime_integration_proved', 'runtime_context_certified'):
        require(getattr(decision, name) is False, 'unsupported-context', 'no authority: ' + name)
    require(decision.status in ('native-target-refusal-observed', 'canonical-path-preserved',
                                'requires-package-policy-validation'),
            'unsupported-context', 'pure context function cannot certify transport')
    return _plain(decision)
