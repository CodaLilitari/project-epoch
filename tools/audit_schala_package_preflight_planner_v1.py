"""Read-only source/evidence preflight audit. No launch, patch or file writes.

The separate pure context planner cannot certify policy or runtime provenance.
This entry point revalidates the accepted evidence and recomputes policy on the
immutable package before emitting metadata. Adapted game bytes never leave RAM.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import stat
import sys

import schala_package_preflight_planner_v1 as planner
import audit_schala_symbolic_high_package_v0 as symbolic
import collect_package_transaction_evidence_v1 as success_evidence
import collect_package_natural_refusal_evidence_v1 as refusal_evidence

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'references/schala_package_preflight_planner_v1.json'
ROM = ROOT / 'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA = '06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
PINS = {
 'planner': ('tools/schala_package_preflight_planner_v1.py',15049,'5b5848d0e47d5c068d61e3728d3044137ac26bcad1da3ba301c28f6b6ebf9640'),
 'symbolic_source': ('tools/audit_schala_symbolic_high_package_v0.py',20486,'e6911a979a60cb06ee78b4b58a410875a2b7acbeb2fce4733bf2795828ad2b5d'),
 'symbolic_reference': ('references/schala_symbolic_high_package_v0.json',8164,'37c13271c3632bca6b27a2daa0e5e2820d502a6673b1863b64b29a647df470e2'),
 'policy_source': ('tools/audit_schala_expanded_package_command_policy_v0.py',39897,'5f9417cb5c44d6dd71577bcd48de0a3c90c9d7f2b790c57a26d1e8c4bd5b5c3f'),
 'policy_reference': ('references/schala_expanded_package_command_policy_v0.json',6717,'35246c00e274f35a80cfe589cfe3557b7585ff515c7e43747453d161de99f0d9'),
 'success_collector': ('tools/collect_package_transaction_evidence_v1.py',9491,'610ced62a320c9a0ae53efd0174ed4e1a661a4db63b1d0a43d15ca2c48a377b4'),
 'refusal_collector': ('tools/collect_package_natural_refusal_evidence_v1.py',13547,'2b2dc9015db25626f544492016a006160a6770dbb1e92b74ce89dc2f986364dd'),
 'success_reference': ('references/package_transaction_observation_v1.json',None,'1cc3030e1bbfe5f167ae69262ec7d78487ec4184e3500915b9dfbda94bea2787'),
 'refusal_reference': ('references/package_natural_refusal_observation_v1.json',32864,'a1318f53d2db33e73288da2c7a1faf8765da58b8696f47441afdcbcf0352114c'),
 'design': ('docs/schala_package_preflight_planner_design_v1.md',19571,'8d569df20932b81d59a6f7f072de729cf046d179cdbd099fee6d0c944d9def05'),
}
TEST_PATH = ROOT / 'tests/test_schala_package_preflight_planner_v1.py'
FALSE_FLAGS = ('production_approved','native_cleanup_approved','action_completion_approved',
               'runtime_integration_proved','runtime_context_certified')


def read(path, maximum=16*1024*1024, expected=None, expected_size=None):
    path = Path(path)
    info = path.lstat()
    planner.require(path.is_absolute() and path.resolve(strict=True) == path
                    and stat.S_ISREG(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,
                    'source-drift','unaliasable regular file required')
    planner.require(info.st_size <= maximum and (expected_size is None or info.st_size == expected_size),
                    'source-drift','bounded file size mismatch')
    with path.open('rb') as stream:
        data = stream.read(maximum+1)
    planner.require(len(data) == info.st_size and len(data) <= maximum,
                    'source-drift','file changed size during bounded read')
    planner.require(expected is None or planner.sha(data) == expected,'source-drift','file SHA mismatch')
    return data


def identity(path, expected=None, size=None):
    data = read(path,256*1024*1024,expected,size)
    return {'path':Path(path).relative_to(ROOT).as_posix(),'size':len(data),'sha256':planner.sha(data)}


def decode(data):
    def pairs(items):
        result = {}
        for k,v in items:
            planner.require(k not in result,'source-drift','duplicate JSON key')
            result[k] = v
        return result
    def bad_constant(value):
        raise planner.PreflightError('source-drift','non-finite JSON constant')
    value = json.loads(data,object_pairs_hook=pairs,parse_constant=bad_constant)
    planner.require(type(value) is dict,'source-drift','JSON object required')
    return value


def dependency_identities():
    result = {key:identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    for module,key in ((planner,'planner'),(symbolic,'symbolic_source'),
                       (success_evidence,'success_collector'),(refusal_evidence,'refusal_collector'),
                       (symbolic.policy,'policy_source')):
        planner.require(Path(module.__file__).resolve() == ROOT/PINS[key][0],
                        'source-drift','imported dependency path differs')
    result['transitive_policy_dependencies'] = symbolic.dependency_identities()
    return result


def _check_record_identities(trace, profile):
    indices = (5,8,9) if profile == planner.SUCCESS else (110,117)
    names = ('queued-tech-entry','target-validation-return','pre-effect-boundary') if profile == planner.SUCCESS else (
             'queued-tech-entry','target-validation-return')
    for i,kind in zip(indices,names):
        planner.require(trace['records'][i]['kind'] == kind and trace['records'][i]['transaction_id'] == 1,
                        'source-drift','wrong accepted invocation record')
    r = trace['records'][indices[-1]]
    planner.require(planner.sha(planner.canonical(r)) == planner.RECORD_SHA[profile],
                    'source-drift','accepted full snapshot identity differs')
    return r,indices


def context_from_accepted_trace(trace, profile):
    """Caller must separately bind/revalidate the full private trace first."""
    r,_ = _check_record_identities(trace,profile)
    w = r['wram']
    context = planner.Context(profile,r['address'],r['transaction_id'],r['frame'],
        tuple(r['cpu'][k] for k in planner.CPU_FIELDS),bytes(r['stack']),bytes.fromhex(r['regions']['queue']),
        w['0006']|(w['0007']<<8),w['B18B'],w['B18C'],tuple(w[k] for k in ('B2EA','B2EB','B2EC')),
        tuple(bytes.fromhex(r['regions']['participant_map'])),tuple(w[k] for k in ('AE91','AE92','AE93','AE94')),
        w['AF22'],w['AF23'],w['B3C8'],w['B3F4'],planner.TRACE_SHA[profile],planner.sha(planner.canonical(r)))
    planner.validate_context(context)
    return context


def load_contexts():
    result,metadata = {},{}
    for profile,module,key,dirname in (
        (planner.SUCCESS,success_evidence,'success_reference','package_transaction_20260908_final1'),
        (planner.REFUSAL,refusal_evidence,'refusal_reference','package_natural_refusal_20260908_final1')):
        path,size,digest = PINS[key]
        reference = decode(read(ROOT/path,expected=digest,expected_size=size))
        # Reuse the accepted full trace, archive, input and runtime validation;
        # never reconstruct a synthetic state and label it native evidence.
        reconstructed = module.collect()
        planner.require(planner.canonical(reference) == planner.canonical(reconstructed),
                        'source-drift','accepted evidence reference no longer reproduces')
        trace_path = ROOT/'private/test_runs'/dirname/'trace.json'
        trace = decode(read(trace_path,expected=planner.TRACE_SHA[profile]))
        module.observer.summarize(trace)
        context = context_from_accepted_trace(trace,profile)
        _,indices = _check_record_identities(trace,profile)
        result[profile] = context
        metadata[profile] = {'accepted_reference':identity(ROOT/path,digest,size),
            'trace':identity(trace_path,planner.TRACE_SHA[profile]),'record_indices':list(indices),
            'boundary':f'{context.boundary:06X}','record_sha256':context.record_sha256,
            'context_sha256':planner.object_sha(context),'full_pair_metadata_reproduced':True,
            'origin':'previously accepted checkpoint-bounded native observation; this import executes no CPU'}
    return result,metadata


def original_package():
    image,layout = symbolic.build_symbolic_source()
    symbolic.validate_symbolic_source(image,layout)
    span = lambda s:planner.Span(s.name,s.bank,s.start,s.end_exclusive)
    return planner.Package(layout.source.selector,layout.source.bank,layout.source.root_offset,
        layout.source.source_kind,image,span(layout.descriptor_span),tuple(span(s) for s in layout.stream_spans))


def association(package):
    planner.validate_package_shape(package)
    return planner.Association(planner.SUCCESS,8,8,planner.DONOR_SHA,planner.SUFFIX_SHA,
        package.selector,package.bank,package.root,package.source_kind,planner.sha(package.image),
        planner.layout_sha(package),planner.POLICY_ID)


def diagnostic_request(donor,package):
    return planner.Request('diagnostic-primary-substitution',8,donor,bytes((0x80,))+donor[1:],
                           (association(package),),package)


def evaluate(context,request):
    """Mandatory policy recomputation; accepts no decision or certificate input."""
    initial = planner.plan(context,request)
    metadata = planner.decision_metadata(initial)
    if initial.status != 'requires-package-policy-validation':
        return metadata
    # The reused validator performs dependency reads. Keep those outside the
    # file-free context function; changes to unused opcodes fail its own pins.
    symbolic.dependency_identities()
    package = request.package
    planner.require(planner.sha(package.image) == initial.image_sha256
                    and planner.layout_sha(package) == initial.layout_sha256
                    and planner.object_sha(request.associations[0]) == initial.association_sha256,
                    'source-drift','qualified request/source identity mismatch')
    p = symbolic.policy
    span = lambda s:p.NamedSpan(s.name,s.bank,s.start,s.end)
    source = p.adapter.make_package_source(selector=package.selector,bank=package.bank,root_offset=package.root,
                allocation_name=package.descriptor.name,source_kind=package.source_kind)
    layout = p.ExpandedPackageLayout(source,span(package.descriptor),tuple(span(s) for s in package.streams))
    try:
        certificate = p.validate_expanded_package_command_policy(package.image,layout)
    except (p.ExpandedPackageCommandPolicyError,p.adapter.PackageBankAdapterError) as exc:
        raise planner.PreflightError('package-policy-refusal',str(exc)) from exc
    planner.require(planner.sha(package.image) == initial.image_sha256
                    and planner.layout_sha(package) == initial.layout_sha256,
                    'source-drift','immutable source changed during policy validation')
    metadata.update(status='transport-valid-source-only',package_evaluation='both-masks-recomputed',
                    policy_certificate_sha256=planner.sha(planner.canonical(certificate)),
                    policy_certificate=certificate)
    return metadata


def require_report_scope(report):
    planner.require(type(report) is dict and report.get('schema') == 'project-epoch-package-preflight-evidence-v1'
                    and report.get('evidence_level') == 'verified-static',
                    'source-drift','source-only report schema/evidence ceiling')
    for key in FALSE_FLAGS:
        planner.require(report.get(key) is False,'source-drift','report claims unproved authority: '+key)
    for decision in report.get('decisions',{}).values():
        for key in FALSE_FLAGS:
            planner.require(decision.get(key) is False,'source-drift','decision claims unproved authority: '+key)


def build_report():
    before = dependency_identities()
    rom = read(ROM,0x400000,ROM_SHA,0x400000)
    symbolic.adapter.verify_canonical_spans(rom,symbolic.adapter.load_reference_contract())
    start = 0xD45A6 + 7*8
    donor = rom[start:start+7]
    contexts,evidence = load_contexts()
    package = original_package()
    request = diagnostic_request(donor,package)
    decisions = {
        'canonical_baseline':evaluate(contexts[planner.SUCCESS],planner.Request('canonical-baseline',8,donor)),
        'diagnostic_primary_substitution':evaluate(contexts[planner.SUCCESS],request),
        'already_refused_cure':evaluate(contexts[planner.REFUSAL],planner.Request('observed-native-refusal')),
    }
    try:
        evaluate(contexts[planner.SUCCESS],replace(request,associations=()))
    except planner.PreflightError as exc:
        planner.require(exc.reason == 'unbound-diagnostic-package','source-drift','wrong default refusal')
        default_refusal = exc.reason
    else:
        raise planner.PreflightError('source-drift','default high binding unexpectedly accepted')
    # Reuse the completed all-128 canonical/default-16 equivalence proof rather
    # than treating equality of action IDs and selectors as a new mapping.
    canonical_sources = symbolic.adapter.build_canonical_sources(rom)
    namespace = symbolic.validate_namespace(canonical_sources,symbolic.build_symbolic_source()[1].source)
    after = dependency_identities()
    planner.require(before == after and read(ROM,0x400000,ROM_SHA,0x400000) == rom,
                    'source-drift','immutable source/input changed during audit')
    report = {
        'schema':'project-epoch-package-preflight-evidence-v1','date':'2026-09-08',
        'evidence_level':'verified-static','scope':'two exact observed contexts imported; new donor association and decisions are host-only transport eligibility',
        'dependencies':before,'auditor':identity(Path(__file__).resolve()),'tests_source':identity(TEST_PATH),
        'canonical_rom':{'size':len(rom),'sha256':planner.sha(rom)},'imported_contexts':evidence,
        'donor':{'physical_action_config_row':'08','file_start':f'{start:06X}','file_end_exclusive':f'{start+7:06X}',
                 'size':7,'sha256':planner.sha(donor),'preserved_plus1_through6_sha256':planner.sha(donor[1:]),
                 'candidate_sha256':planner.sha(request.candidate),'changed_byte_offsets':[0],
                 'preserved_byte_offsets':list(range(1,7)),'preserved_equalities':[True]*6,
                 'auxiliary_evidence':'source-derived donor equality; all live auxiliary fields were not independently traced',
                 'payload_emitted':False},
        'decisions':decisions,'default_diagnostic_refusal':default_refusal,
        'namespace_equivalence':namespace,'symbolic_source_sha256':planner.sha(package.image),
        'layout':planner.layout_metadata(package),'association_sha256':planner.object_sha(request.associations[0]),
        'production_approved':False,'native_cleanup_approved':False,'action_completion_approved':False,
        'runtime_integration_proved':False,'runtime_context_certified':False,
        'inputs_unchanged':True,'new_native_execution':False,'game_payload_emitted':False,
        'limitations':[
            'Exact checkpoint profiles only; no general queue, target, participant or MP-eligibility model.',
            'B3C8 at the pre-effect boundary does not certify the later native MP/status check.',
            'The already refused Cure retains earlier AE actor/config fields and supplies no pre-effect snapshot.',
            'Transport policy validity and terminal00 closure do not prove action completion.',
            'No cleanup, late-refusal recovery, allocation, hook, ROM write, action80..90 or logicalPC07 permission.',
            'Pure context decisions cannot authenticate caller-authored objects as native evidence.',
            'The prepared checkpoint provenance remains distinct from controller-only post-load behavior.',
            'Existing symbolic donor01, policy, production catalogs and accepted native sources remain unchanged.'],
        'reproduce':['python','-B','tools/audit_schala_package_preflight_planner_v1.py'],
        'serialization':'json.dumps(value, indent=2), UTF-8, LF, one trailing newline',
    }
    require_report_scope(report)
    return report


def verify_reference(report,data):
    expected = decode(data)
    require_report_scope(expected)
    planner.require(planner.canonical(report) == planner.canonical(expected),
                    'source-drift','closed preflight reference differs from recomputed result')


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = build_report()
    verify_reference(report,read(REFERENCE))
    sys.stdout.buffer.write((json.dumps(report,indent=2)+'\n').encode('utf-8'))


if __name__ == '__main__':
    main()
