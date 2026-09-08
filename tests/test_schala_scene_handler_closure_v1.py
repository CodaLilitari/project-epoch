"""Original short opcode/metadata specimens; no private ROM or trace needed."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene_handler_closure_v1 as a


def reader(blob,entry=0xCD4000,others=None):
    memory={entry+i:value for i,value in enumerate(blob)}
    memory.update(others or {})
    def read(address,length):
        return bytes(memory.get(address+i,0x00) for i in range(length))
    return read


def specimen():
    targets=[0xCD4000+4*i for i in range(121)]
    cells=[]
    for i,command in enumerate(range(0x80,0xFA)):
        cell=a.inputs.index_contract(command,0)
        cell.update(target=f'{targets[i%121]:06X}',in_reviewed_122_cell_prefix=True,
            command_reachability_proved=False,pointer_bytes_sha256='0'*64)
        cells.append(cell)
    contracts=[a.walk_direct(reader(bytes([0x60]),t),t,'near') for t in targets]
    return cells,contracts,copy.deepcopy(contracts)


class DecoderContracts(unittest.TestCase):
    def walk(self,blob,*,m8=True,x8=False,kind='near'):
        return a.walk_direct(reader(bytes(blob)),0xCD4000,kind,entry_m8=m8,entry_x8=x8)

    def test_ten_extensions_decode_exact_lengths_for_all_widths(self):
        for opcode,(_,length) in a.EXTENSIONS.items():
            for m8 in (False,True):
                for x8 in (False,True):
                    with self.subTest(opcode=opcode,m8=m8,x8=x8):
                        row=self.walk([opcode]+[0x12]*(length-1)+[0x60],m8=m8,x8=x8)
                        self.assertIsNone(row['frontier'])
                        self.assertEqual(row['maximum_additional_bytes_below_callee_entry'],0)
                        self.assertEqual(row['return_width_states'],[{'site':f'${0xCD4000+length:06X}',
                            'm8':m8,'x8':x8,'irq_masked':True}])

    def test_new_opcodes_are_not_silently_added_to_old_walker(self):
        before=dict(a.base.FIXED)
        for opcode,(_,length) in a.EXTENSIONS.items():
            row=a.base.walk_direct(reader(bytes([opcode]+[0x12]*(length-1)+[0x60])),0xCD4000,'near')
            self.assertEqual(row['frontier']['category'],'unsupported-opcode')
        self.assertEqual(a.base.FIXED,before)

    def test_memory_rmw_write_widths_and_alias_limits(self):
        for opcode in (0x06,0x26,0x2E):
            for m8 in (False,True):
                row=self.walk([opcode]+[0x12]*(a.EXTENSIONS[opcode][1]-1)+[0x60],m8=m8)
                self.assertEqual(row['syntactic_write_operands'][0]['width_bytes'],1 if m8 else 2)
                self.assertIs(row['syntactic_write_operands'][0]['effective_address_and_aliasing_proved'],False)
                self.assertIs(row['nonstack_alias_closure'],False)

    def test_reads_and_tyx_are_not_reported_as_writes(self):
        for opcode,(_,length) in a.EXTENSIONS.items():
            if opcode not in (0x06,0x26,0x2E):
                self.assertEqual(self.walk([opcode]+[0x12]*(length-1)+[0x60])['syntactic_write_operands'],[])

    def test_indirect_jmp_remains_explicit_frontier(self):
        row=self.walk([0x6C,0x40,0x00,0x60])
        self.assertEqual(row['frontier']['category'],'indirect-jump-dispatch')
        self.assertIsNone(row['maximum_additional_bytes_below_callee_entry'])

    def test_indexed_jumps_and_calls_remain_frontiers(self):
        for opcode,category in ((0x7C,'indexed-jump-dispatch'),(0xFC,'indexed-call-dispatch')):
            self.assertEqual(self.walk([opcode,0x40,0x00,0x60])['frontier']['category'],category)

    def test_unsupported_opcode_remains_frontier(self):
        self.assertEqual(self.walk([0x00,0x60])['frontier']['category'],'unsupported-opcode')

    def test_width_and_typed_status_restoration(self):
        row=self.walk([0x08,0xC2,0x30,0x48,0xB7,0x12,0x68,0x28,0x60])
        self.assertIsNone(row['frontier']);self.assertEqual(row['maximum_additional_bytes_below_callee_entry'],3)
        self.assertEqual(row['return_width_states'][0]['m8'],True)
        self.assertEqual(row['return_width_states'][0]['x8'],False)

    def test_unknown_status_and_consumed_return_refuse(self):
        for blob,category in (([0x28,0x60],'unknown-status-value'),([0x68,0x60],'return-frame-consumed')):
            self.assertEqual(self.walk(blob)['frontier']['category'],category)

    def test_irq_unmask_and_stack_assignment_refuse(self):
        for opcode,category in ((0x58,'irq-unmasking'),(0x9A,'stack-pointer-assignment'),(0xFB,'processor-mode-transition')):
            self.assertEqual(self.walk([opcode,0x60])['frontier']['category'],category)

    def test_near_long_and_bank_changes_cannot_forge_return(self):
        self.assertEqual(self.walk([0x6B])['frontier']['category'],'return-kind-mismatch')
        read=reader(bytes([0x5C,0x00,0x50,0xCE]),others={0xCE5000:0x60})
        self.assertEqual(a.walk_direct(read,0xCD4000,'near')['frontier']['category'],'near-return-bank-mismatch')

    def test_conditional_loop_is_not_termination_proof(self):
        row=self.walk([0xD0,0xFE,0x60]);self.assertIsNone(row['frontier'])
        self.assertIs(row['termination_proved'],False)
        row=self.walk([0x80,0xFE]);self.assertEqual(row['frontier']['category'],'no-balanced-return')

    def test_cross_instruction_branch_overlap_refuses(self):
        row=self.walk([0xD0,0x01,0xB7,0x60,0x60])
        self.assertEqual(row['frontier']['category'],'overlapping-decode')

    def test_exact_declared_walker_ast_derivation(self):
        result=a.verify_walker_derivation();self.assertTrue(result['only_declared_ast_changes'])
        self.assertFalse(result['prior_module_mutated'])


class MetadataContracts(unittest.TestCase):
    def setUp(self):self.cells,self.rows,self.old=specimen()
    def result(self):return a.project(self.cells,self.rows,self.old)
    def reject(self):
        with self.assertRaises(ValueError):self.result()

    def test_complete_cells_and_target_deduplication(self):
        result=self.result();self.assertEqual(result['summary']['reviewed_physical_cells'],122)
        self.assertEqual(result['summary']['distinct_targets'],121)
        self.assertEqual(result['cell_to_contract_relation'][0]['commands'],[0x80,0xF9])
        for key,value in a.LIMITS.items():self.assertIs(result[key],value)

    def test_missing_cell_refuses(self):self.cells.pop();self.reject()
    def test_duplicate_cell_refuses(self):self.cells[-1]=copy.deepcopy(self.cells[0]);self.reject()
    def test_missing_contract_refuses(self):self.rows.pop();self.reject()
    def test_duplicate_contract_refuses(self):self.rows[-1]=copy.deepcopy(self.rows[0]);self.reject()
    def test_wrong_cell_address_refuses(self):self.cells[0]['pointer_byte_addresses'][0]+=2;self.reject()
    def test_float_cell_address_refuses(self):self.cells[0]['pointer_byte_addresses'][0]=float(self.cells[0]['pointer_byte_addresses'][0]);self.reject()
    def test_boolean_index_refuses(self):self.cells[0]['x']=False;self.reject()
    def test_nonzero_hidden_b_refuses(self):self.cells[0]['hidden_b']=1;self.reject()
    def test_boolean_hidden_b_refuses(self):self.cells[0]['hidden_b']=False;self.reject()
    def test_float_command_refuses(self):self.cells[0]['command']=128.0;self.reject()
    def test_reachability_promotion_refuses(self):self.cells[0]['command_reachability_proved']=True;self.reject()
    def test_occupied_successor_is_not_added(self):self.cells[-1]['command']=0xFA;self.reject()
    def test_target_bank_substitution_refuses(self):self.cells[0]['target']='CE4000';self.reject()
    def test_wrong_near_call_kind_refuses(self):self.rows[0]['kind']='long';self.reject()
    def test_wrong_entry_width_refuses(self):self.rows[0]['entry_x8']=True;self.reject()
    def test_boolean_type_is_exact(self):self.rows[0]['entry_m8']=1;self.reject()
    def test_return_width_change_refuses(self):self.rows[0]['return_width_states'][0]['x8']=True;self.reject()
    def test_stack_arithmetic_change_refuses(self):self.rows[0]['maximum_counted_bytes_including_root_call_frame']=3;self.reject()
    def test_float_depth_refuses(self):self.rows[0]['maximum_additional_bytes_below_callee_entry']=0.0;self.reject()
    def test_float_frame_inclusive_depth_refuses(self):self.rows[0]['maximum_counted_bytes_including_root_call_frame']=2.0;self.reject()
    def test_alias_or_register_promotion_refuses(self):
        for key in ('nonstack_alias_closure','callee_register_value_preservation','termination_proved'):
            old=self.rows[0][key];self.rows[0][key]=True;self.reject();self.rows[0][key]=old
    def test_prior_closed_contract_cannot_drift(self):self.rows[0]['instruction_contexts']+=1;self.reject()
    def test_open_contract_cannot_acquire_bound(self):
        self.rows[0]=a.walk_direct(reader(bytes([0x6C,0x40,0x00])),0xCD4000,'near')
        self.old[0]=copy.deepcopy(self.rows[0]);self.rows[0]['maximum_additional_bytes_below_callee_entry']=0;self.reject()
    def test_open_peak_is_not_a_bound(self):
        self.rows[0]=a.walk_direct(reader(bytes([0x48,0x6C,0x40,0x00])),0xCD4000,'near')
        self.old[0]=copy.deepcopy(self.rows[0]);result=self.result()
        self.assertEqual(result['summary']['open_targets'],1)
        self.assertEqual(result['open_frontiers'][0]['exploratory_observed_local_peak_not_a_bound'],1)
        self.assertIsNone(result['open_frontiers'][0]['full_bound'])
        self.assertIsNone(result['whole_nmi_stack_bound'])
    def test_canonical_identity_is_checked_before_walking(self):
        with mock.patch.object(a,'walk_direct',side_effect=AssertionError('must not walk')):
            for blob in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(blob,{})


if __name__=='__main__':unittest.main()
