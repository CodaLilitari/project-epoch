"""Original synthetic host fixtures; native provenance is separately imported.

The unit donor bytes are deliberately original test data with scoped hash
patches. They never claim to be a canonical config row or a runtime capture.
"""
from __future__ import annotations
import builtins
from contextlib import ExitStack
from dataclasses import FrozenInstanceError,replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import schala_package_preflight_planner_v1 as p
import audit_schala_package_preflight_planner_v1 as a


def context(profile=p.SUCCESS):
    success=profile==p.SUCCESS
    return p.Context(profile,0xC1BBD4 if success else 0xC1BB8B,1,374 if success else 2560,
        (0,0,3,0,0x7E,0x6EA,0x22,0xC1,0xBBD4,False) if success else
        (1,0x100,0x93F5,0,0x7E,0x6EA,0x20,0xC1,0xBB8B,False),
        bytes((0xD0 if success else 0xE9,0x85,0x35,0x83,0x0C,0,0x90,0,0,5,0,1,0,1,0,0x23)),
        bytes.fromhex('0120010300ff080000000000ff000000000000ff00' if success else
                      '8100000000ff000120010200ff0c0000000000ff00'),
        0x93EE if success else 0x93F5,0 if success else 1,8 if success else 12,
        (0,255,255) if success else (1,255,255),(0,1,2,255,255,255,255),
        (0,2,8,0) if success else (3,2,0,0),1,0 if success else 1,0,0 if success else 1,
        p.TRACE_SHA[profile],p.RECORD_SHA[profile])


class PureAndPolicyTests(unittest.TestCase):
    def setUp(self):
        self.scope=ExitStack();self.addCleanup(self.scope.close)
        self.donor=bytes((8,91,92,93,94,95,96))
        for key,value in (('DONOR_SHA',p.sha(self.donor)),('SUFFIX_SHA',p.sha(self.donor[1:])),
                          ('CANDIDATE_SHA',p.sha(bytes((128,))+self.donor[1:]))):
            self.scope.enter_context(mock.patch.object(p,key,value))
        self.ctx=context();self.package=a.original_package()
        self.request=a.diagnostic_request(self.donor,self.package)

    def reject(self,ctx=None,request=None,reason=None,evaluate=False):
        with self.assertRaises(p.PreflightError) as caught:
            (a.evaluate if evaluate else p.plan)(ctx or self.ctx,request or self.request)
        if reason:self.assertEqual(caught.exception.reason,reason)

    def test_canonical_baseline_keeps_path_without_authored_policy(self):
        with mock.patch.object(a.symbolic.policy,'validate_expanded_package_command_policy',side_effect=AssertionError):
            result=a.evaluate(self.ctx,p.Request('canonical-baseline',8,self.donor))
        self.assertEqual(result['status'],'canonical-path-preserved')
        self.assertEqual(result['package_evaluation'],'not-evaluated')

    def test_pure_candidate_is_only_a_qualified_policy_request(self):
        result=p.plan(self.ctx,self.request)
        self.assertEqual(result.status,'requires-package-policy-validation')
        self.assertEqual(result.image_sha256,p.sha(self.package.image))
        self.assertFalse(result.runtime_context_certified)
        self.assertNotIn('policy_certificate',p.decision_metadata(result))

    def test_auditor_recomputes_both_masks_and_false_authority(self):
        function=a.symbolic.policy.validate_expanded_package_command_policy
        with mock.patch.object(a.symbolic.policy,'validate_expanded_package_command_policy',wraps=function) as called:
            result=a.evaluate(self.ctx,self.request)
        # Dependency-reference validation also checks its own conformance
        # vector; require exactly one call on this actual package envelope.
        self.assertEqual(sum(call.args[0]==self.package.image for call in called.call_args_list),1)
        self.assertEqual(result['status'],'transport-valid-source-only')
        self.assertEqual(result['package_evaluation'],'both-masks-recomputed')
        self.assertEqual(result['policy_certificate']['mask0_relation_count'],1)
        self.assertEqual(result['policy_certificate']['mask1_relation_count'],1)
        for key in a.FALSE_FLAGS:self.assertIs(result[key],False)

    def test_refusal_is_distinct_and_retains_stale_animation_context(self):
        refused=context(p.REFUSAL)
        self.assertEqual(refused.animation_identity,(3,2,0,0))
        with mock.patch.object(a.symbolic.policy,'validate_expanded_package_command_policy',side_effect=AssertionError):
            result=a.evaluate(refused,p.Request('observed-native-refusal'))
        self.assertEqual(result['status'],'native-target-refusal-observed')
        self.assertEqual(result['donor_evaluation'],'not-evaluated')

    def test_refused_context_cannot_certify_a_package_or_donor(self):
        self.reject(context(p.REFUSAL),self.request,'unsupported-context')
        self.reject(context(p.REFUSAL),p.Request('observed-native-refusal',8,self.donor),'unsupported-context')

    def test_refusal_cannot_be_promoted_to_pre_effect(self):
        r=context(p.REFUSAL)
        for changed in (replace(r,af23=0),replace(r,profile=p.SUCCESS),replace(r,boundary=0xC1BBD4),
                        replace(r,animation_identity=(1,2,12,0)),replace(r,record_sha256=p.RECORD_SHA[p.SUCCESS])):
            with self.subTest(change=changed):self.reject(changed,p.Request('observed-native-refusal'))

    def test_cpu_and_frame_context_is_exact(self):
        for index in range(9):
            cpu=list(self.ctx.cpu);cpu[index]^=1
            with self.subTest(cpu_index=index):self.reject(replace(self.ctx,cpu=tuple(cpu)))
        self.reject(replace(self.ctx,cpu=self.ctx.cpu[:-1]+(True,)))
        self.reject(replace(self.ctx,stack=bytes((0,))+self.ctx.stack[1:]))
        self.reject(replace(self.ctx,invocation_id=2))
        self.reject(replace(self.ctx,boundary=0xC14612))

    def test_decimal_flag_is_separate_from_direct_page(self):
        cpu=list(self.ctx.cpu);cpu[6]|=8
        self.assertEqual(cpu[3],0)
        self.reject(replace(self.ctx,cpu=tuple(cpu)))

    def test_bool_integer_and_mutable_schema_inputs_refuse(self):
        for changed in (replace(self.ctx,invocation_id=True),replace(self.ctx,participants=(False,255,255)),
                        replace(self.ctx,queue=bytearray(self.ctx.queue)),replace(self.ctx,stack=list(self.ctx.stack)),
                        replace(self.ctx,cpu=(False,)+self.ctx.cpu[1:]),replace(self.ctx,participant_map=list(self.ctx.participant_map))):
            self.reject(changed)
        self.reject(request=replace(self.request,donor_row=True))
        self.reject(request=replace(self.request,associations=list(self.request.associations)))

    def test_high_action_namespace_refuses(self):
        for action in (0x80,0x90,0xFF):
            q=bytearray(self.ctx.queue);q[6]=action
            self.reject(replace(self.ctx,action_id=action,queue=bytes(q)),reason='unsupported-context')

    def test_logical_pc07_and_bad_participants_refuse(self):
        for parts in ((7,255,255),(0,0,255),(0,255,1),(255,255,255),(3,255,255)):
            self.reject(replace(self.ctx,participants=parts))

    def test_party_mapping_never_aliases_duplicate_or_absent_slots(self):
        for mapping in ((0,0,2,255,255,255,255),(255,1,2,255,255,255,255),(3,1,2,255,255,255,255)):
            self.reject(replace(self.ctx,participant_map=mapping))

    def test_every_queue_byte_and_pointer_mutation_refuses(self):
        for i in range(21):
            q=bytearray(self.ctx.queue);q[i]^=1
            with self.subTest(byte=i):self.reject(replace(self.ctx,queue=bytes(q)))
        self.reject(replace(self.ctx,queue_pointer=0x93F5))

    def test_every_donor_byte_is_pinned(self):
        for i in range(7):
            donor=bytearray(self.donor);donor[i]^=1
            self.reject(request=replace(self.request,donor=bytes(donor)),reason='donor-mismatch')
        self.reject(request=replace(self.request,donor_row=1),reason='donor-mismatch')

    def test_every_preserved_candidate_byte_refuses(self):
        for i in range(1,7):
            candidate=bytearray(self.request.candidate);candidate[i]^=1
            self.reject(request=replace(self.request,candidate=bytes(candidate)),reason='auxiliary-mismatch')

    def test_primary_substitution_must_be_explicit_selector80(self):
        for selector in (8,0x81,0x90):
            self.reject(request=replace(self.request,candidate=bytes((selector,))+self.donor[1:]),reason='donor-mismatch')

    def test_default_registry_is_empty_and_duplicates_refuse(self):
        self.reject(request=replace(self.request,associations=()),reason='unbound-diagnostic-package')
        self.reject(request=replace(self.request,associations=self.request.associations*2),reason='malformed-context')

    def test_every_association_dimension_is_explicit(self):
        binding=self.request.associations[0]
        changes={'profile':p.REFUSAL,'action_id':0x80,'config_row':1,'donor_sha256':'0'*64,
            'suffix_sha256':'0'*64,'package_selector':0x81,'bank':0x43,'root':0x2001,
            'source_kind':'project-epoch-source','image_sha256':'0'*64,'layout_sha256':'0'*64,'policy_id':'other'}
        for key,value in changes.items():
            self.reject(request=replace(self.request,associations=(replace(binding,**{key:value}),)))

    def test_mutable_package_bytes_and_production_namespace_refuse(self):
        for package in (replace(self.package,image=bytearray(self.package.image)),
                        replace(self.package,bank=0xCE),replace(self.package,source_kind='project-epoch-source'),
                        replace(self.package,selector=0x90),replace(self.package,streams=list(self.package.streams))):
            self.reject(request=replace(self.request,package=package))

    def test_pure_context_planner_never_opens_a_file(self):
        with mock.patch.object(builtins,'open',side_effect=AssertionError),mock.patch.object(Path,'open',side_effect=AssertionError),mock.patch.object(Path,'read_bytes',side_effect=AssertionError):
            self.assertEqual(p.plan(self.ctx,self.request).status,'requires-package-policy-validation')

    def test_caller_cannot_supply_a_certificate_or_complete_decision(self):
        with self.assertRaises(TypeError):a.evaluate(self.ctx,self.request,certificate={})
        with self.assertRaises(TypeError):p.Request('diagnostic-primary-substitution',certificate={})
        decision=p.plan(self.ctx,self.request)
        for key in a.FALSE_FLAGS:
            with self.assertRaises(p.PreflightError):p.decision_metadata(replace(decision,**{key:True}))
        with self.assertRaises(p.PreflightError):p.decision_metadata(replace(decision,status='transport-valid-source-only'))

    def test_valid_primary_cannot_hide_invalid_alternate_pointer(self):
        image=bytearray(self.package.image);image[0x2006:0x2008]=b'\xff\xff'
        changed=replace(self.package,image=bytes(image))
        request=a.diagnostic_request(self.donor,changed)
        self.assertEqual(p.plan(self.ctx,request).status,'requires-package-policy-validation')
        self.reject(request=request,reason='package-policy-refusal',evaluate=True)

    def test_decoded_alternate_1e_refuses(self):
        image=bytearray(self.package.image);image[0x2006:0x2008]=(0x3001).to_bytes(2,'little')
        image[0x3001:0x3004]=bytes((0x1E,0,0))
        changed=replace(self.package,image=bytes(image),streams=(self.package.streams[0],p.Span('EPOCH_BAD_ALTERNATE',0x42,0x3001,0x3004)))
        self.reject(request=a.diagnostic_request(self.donor,changed),reason='package-policy-refusal',evaluate=True)

    def test_raw_operand_1e_keeps_the_existing_policy_acceptance(self):
        image,layout=a.symbolic.policy._build_conformance_vector()
        # Relocate only the synthetic bank identity into this planner's
        # bank42 diagnostic namespace; all token bytes/offsets are unchanged.
        span=lambda s:p.Span(s.name,0x42,s.start,s.end_exclusive)
        package=p.Package(0x80,0x42,layout.source.root_offset,'synthetic-test',
            image,span(layout.descriptor_span),tuple(span(s) for s in layout.stream_spans))
        result=a.evaluate(self.ctx,a.diagnostic_request(self.donor,package))
        self.assertEqual(result['policy_certificate']['decoded_command_1e_site_count'],0)
        self.assertGreater(result['policy_certificate']['raw_byte_equal_1e_inside_stream_span_count'],0)

    def test_overlap_unowned_and_mid_token_layouts_refuse(self):
        cases=[replace(self.package,streams=(p.Span('EPOCH_OVERLAP',0x42,0x2000,0x3001),)),
               replace(self.package,streams=(replace(self.package.streams[0],end=0x3002),))]
        image=bytearray(self.package.image);image[0x3000:0x3003]=bytes((2,0x1E,0));image[0x2006:0x2008]=(0x3001).to_bytes(2,'little')
        cases.append(replace(self.package,image=bytes(image),streams=(replace(self.package.streams[0],end=0x3003),)))
        for package in cases:self.reject(request=a.diagnostic_request(self.donor,package),evaluate=True)

    def test_out_of_bank_span_and_duplicate_names_refuse(self):
        for package in (replace(self.package,streams=(replace(self.package.streams[0],end=65537),)),
                        replace(self.package,streams=self.package.streams*2)):
            with self.assertRaises(p.PreflightError):a.diagnostic_request(self.donor,package)

    def test_b3c8_zero_never_claims_mp_eligibility(self):
        result=a.evaluate(self.ctx,self.request)
        self.assertNotIn('mp_eligible',result)
        self.reject(replace(self.ctx,b3c8=1))

    def test_immutable_records_and_unknown_fields(self):
        with self.assertRaises(FrozenInstanceError):self.ctx.af23=1
        with self.assertRaises(TypeError):p.Request('canonical-baseline',unknown=True)


class EvidenceBoundaryTests(unittest.TestCase):
    def test_dependency_identity_drift_rejects_before_evidence(self):
        pins=dict(a.PINS);path,size,_=pins['planner'];pins['planner']=(path,size,'0'*64)
        with mock.patch.object(a,'PINS',pins),self.assertRaises(p.PreflightError):a.dependency_identities()

    def test_strict_json_duplicate_and_nonfinite_refusal(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]'):
            with self.assertRaises(p.PreflightError):a.decode(raw)

    def test_bounded_regular_read_refuses_size_and_hash_drift(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d).resolve()/'source.json';path.write_bytes(b'{}')
            self.assertEqual(a.read(path,2,p.sha(b'{}'),2),b'{}')
            for kwargs in ({'maximum':1},{'expected':'0'*64},{'expected_size':3}):
                with self.assertRaises(p.PreflightError):a.read(path,**kwargs)
            with self.assertRaises(p.PreflightError):a.read(Path(d).resolve())

    def test_report_completion_claim_and_type_sensitive_reference_refuse(self):
        report={'schema':'project-epoch-package-preflight-evidence-v1','evidence_level':'verified-static',
                **{k:False for k in a.FALSE_FLAGS},'decisions':{}}
        a.verify_reference(report,json.dumps(report).encode())
        for key in a.FALSE_FLAGS:
            changed={**report,key:True}
            with self.assertRaises(p.PreflightError):a.verify_reference(report,json.dumps(changed).encode())
        with self.assertRaises(p.PreflightError):a.verify_reference(report,json.dumps({**report,'extra':1}).encode())

    def test_full_accepted_record_hash_prevents_partial_snapshot_forgery(self):
        trace={'records':[{} for _ in range(10)]}
        for i,kind in ((5,'queued-tech-entry'),(8,'target-validation-return'),(9,'pre-effect-boundary')):
            trace['records'][i]={'kind':kind,'transaction_id':1}
        with self.assertRaises(p.PreflightError):a.context_from_accepted_trace(trace,p.SUCCESS)


if __name__=='__main__':unittest.main()
