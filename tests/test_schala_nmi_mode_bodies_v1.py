"""Original metadata composition fixtures; no ROM or emulator input.

These exercise the independent composition checks, not a replacement copy
of the preserved abstract CPU walker. Native provenance is never claimed.
"""
import copy
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_nmi_mode_bodies_v1 as a


def closed(entry,kind,depth,site='$C00000'):
    return {'entry':a.cpu(entry),'kind':kind,'entry_m8':True,'entry_x8':False,'entry_irq_masked':True,
        'status':'closed-direct-stack-width-control-flow','frontier':None,
        'return_width_states':[{'site':site,'m8':True,'x8':False,'irq_masked':True}],
        'maximum_additional_bytes_below_callee_entry':depth,
        'maximum_counted_bytes_including_root_call_frame':depth+(2 if kind=='near' else 3),
        'callee_register_value_preservation':False,'nonstack_alias_closure':False,
        'premise_nonstack_writes_do_not_modify_stack_or_saved_status':True,
        'termination_proved':False,'whole_nmi_bound':None}


def fixture():
    mode0=closed(0xCD09F1,'near',12,'$CD0ADD')
    mode0['direct_calls']=[{'site':a.cpu(s),'target':a.cpu(t),'kind':k} for s,t,k,_ in a.CALLS]
    mode12=closed(0xCD088D,'near',0)
    mode12.update(status='open-frontier',frontier={'category':'indexed-jump-dispatch','site':'$CD06B9',
        'incoming_width_state':{'m8':True,'x8':False,'irq_masked':True},'counted_stack_bytes_at_frontier':4,
        'active_call_return_sites':[{'return':'abstract-caller','kind':'near'},
                                  {'return':'$CD092C','kind':'near'}]},
        return_width_states=[],maximum_additional_bytes_below_callee_entry=None,
        maximum_counted_bytes_including_root_call_frame=None,exploratory_observed_local_peak_not_a_bound=10)
    prior=[closed(target,kind,depth) for (_,target,kind,_),depth in zip(a.CALLS,(0,2,0,0,0,2,9,0))]
    return mode0,mode12,prior


class Composition(unittest.TestCase):
    def setUp(self):self.mode0,self.mode12,self.prior=fixture()
    def run_model(self):return a.compose(self.mode0,self.mode12,self.prior)
    def rejects(self):
        with self.assertRaises(ValueError):self.run_model()

    def test_independent_component_arithmetic(self):
        r=self.run_model()
        self.assertEqual([c['composed_additional_below_mode_entry'] for c in r['mode0_wrapper_components']],[3,5,3,2,2,5,12,2])
        self.assertEqual(r['mode0_local_noncall_peak_bytes'],2)
        self.assertEqual(r['mode0_composed_additional_below_entry'],12)
        self.assertEqual(r['mode0_conditional_total_including_indexed_near_frame'],14)
        self.assertEqual(r['mode0_wrapper_components'][2]['persistent_wrapper_bytes'],1)
        self.assertEqual(r['mode12_traversal_local_peak_explicitly_not_a_bound'],10)
        self.assertIsNone(r['mode12_additional_stack_bound'])
        for key,value in a.LIMITS.items():self.assertIs(r[key],value)

    def test_maximum_is_not_sum_of_sequential_calls(self):
        r=self.run_model();self.assertNotEqual(r['mode0_composed_additional_below_entry'],sum(c['composed_additional_below_mode_entry'] for c in r['mode0_wrapper_components']))
    def test_missing_prior_callee(self):self.prior.pop();self.rejects()
    def test_duplicate_prior_callee(self):self.prior.append(copy.deepcopy(self.prior[0]));self.rejects()
    def test_prior_long_near_confusion(self):self.prior[0]['kind']='near';self.rejects()
    def test_entry_bank_confusion(self):self.mode0['entry']='$CC09F1';self.rejects()
    def test_root_call_kind_confusion(self):self.mode0['kind']='long';self.rejects()
    def test_entry_width(self):self.mode0['entry_m8']=False;self.rejects()
    def test_entry_boolean_type(self):self.mode0['entry_m8']=1;self.rejects()
    def test_return_width(self):self.prior[0]['return_width_states'][0]['x8']=True;self.rejects()
    def test_return_irq_unmask(self):self.prior[0]['return_width_states'][0]['irq_masked']=False;self.rejects()
    def test_return_boolean_type(self):self.prior[0]['return_width_states'][0]['m8']=1;self.rejects()
    def test_root_return_wrong_site(self):self.mode0['return_width_states'][0]['site']='$CD0ADE';self.rejects()
    def test_extra_root_return(self):self.mode0['return_width_states'].append(dict(self.mode0['return_width_states'][0]));self.rejects()
    def test_prior_open_callee(self):self.prior[6]['status']='open-frontier';self.prior[6]['frontier']={};self.rejects()
    def test_full_walk_composition_mismatch(self):self.prior[6]['maximum_additional_bytes_below_callee_entry']=8;self.prior[6]['maximum_counted_bytes_including_root_call_frame']=11;self.rejects()
    def test_counted_frame_size_mismatch(self):self.prior[0]['maximum_counted_bytes_including_root_call_frame']=2;self.rejects()
    def test_float_depth_is_not_integer(self):self.prior[0]['maximum_additional_bytes_below_callee_entry']=0.0;self.rejects()
    def test_boolean_depth_is_not_integer(self):self.prior[0]['maximum_additional_bytes_below_callee_entry']=False;self.rejects()
    def test_negative_depth(self):self.prior[0]['maximum_additional_bytes_below_callee_entry']=-1;self.rejects()
    def test_missing_wrapper_call(self):self.mode0['direct_calls'].pop();self.rejects()
    def test_extra_wrapper_call(self):self.mode0['direct_calls'].append({'site':'$CD0ADC','target':'$CD0ADE','kind':'near'});self.rejects()
    def test_changed_wrapper_call_target(self):self.mode0['direct_calls'][0]['target']='$CD09CF';self.rejects()
    def test_register_preservation_not_promoted(self):self.mode0['callee_register_value_preservation']=True;self.rejects()
    def test_alias_closure_not_promoted(self):self.prior[1]['nonstack_alias_closure']=True;self.rejects()
    def test_required_stack_alias_premise(self):self.prior[1]['premise_nonstack_writes_do_not_modify_stack_or_saved_status']=False;self.rejects()
    def test_termination_not_promoted(self):self.mode0['termination_proved']=True;self.rejects()
    def test_whole_nmi_bound_not_promoted(self):self.mode0['whole_nmi_bound']=14;self.rejects()
    def test_wrong_frontier_kind(self):self.mode12['frontier']['category']='unsupported-opcode';self.rejects()
    def test_wrong_frontier_site(self):self.mode12['frontier']['site']='$CD16AF';self.rejects()
    def test_wrong_frontier_width(self):self.mode12['frontier']['incoming_width_state']['m8']=False;self.rejects()
    def test_wrong_frontier_frame(self):self.mode12['frontier']['active_call_return_sites'][1]['return']='$CD092D';self.rejects()
    def test_wrong_frontier_count(self):self.mode12['frontier']['counted_stack_bytes_at_frontier']=2;self.rejects()
    def test_float_frontier_count(self):self.mode12['frontier']['counted_stack_bytes_at_frontier']=4.0;self.rejects()
    def test_open_frontier_cannot_gain_bound(self):self.mode12['maximum_additional_bytes_below_callee_entry']=10;self.rejects()
    def test_open_frontier_cannot_gain_return(self):self.mode12['return_width_states']=[{'site':'$CD09CD','m8':True,'x8':False,'irq_masked':True}];self.rejects()
    def test_open_peak_stays_exploratory(self):
        self.mode12['exploratory_observed_local_peak_not_a_bound']=11
        r=self.run_model();self.assertIsNone(r['mode12_additional_stack_bound']);self.assertEqual(r['mode12_traversal_local_peak_explicitly_not_a_bound'],11)
    def test_negative_open_peak(self):self.mode12['exploratory_observed_local_peak_not_a_bound']=-1;self.rejects()
    def test_canonical_guard_before_walker(self):
        with mock.patch.object(a.closure,'walk_direct',side_effect=AssertionError('must not call')):
            for raw in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(raw,{})
    def test_source_read_bounds_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory).resolve()/'original.txt';path.write_bytes(b'original metadata fixture')
            self.assertEqual(a.read_file(path,expected=a.sha(path.read_bytes())),path.read_bytes())
            with self.assertRaises(ValueError):a.read_file(path,maximum=2)
            with self.assertRaises(ValueError):a.read_file(path,expected='0'*64)


if __name__=='__main__':unittest.main()
