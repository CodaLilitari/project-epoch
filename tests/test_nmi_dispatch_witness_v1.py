"""Original abbreviated selected-record specimens, not accepted native traces."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_nmi_dispatch_witness_v1 as a


def specimen():
    mode_cells=[dict(a.mode.index_contract(i),target='CD088D' if i in (1,2) else 'CD09F1') for i in range(256)]
    scene_cells=[dict(a.scene.index_contract(i,0),target='CD2000') for i in range(128,255)]
    cpu={'a':0xABCD,'x':0x1234,'y':0x5678,'d':0x4321,'dbr':0x7E,'sp':0x0700,'ps':0x04,'k':0xD1,'pc':0xE77C,'emulationMode':False}
    def row(kind,address,clock):
        return {'kind':kind,'address':address,'context_id':1,'context_depth':1,'context_kind':'normal-nmi',
            'cpu':dict(cpu,k=address>>16,pc=address&65535),'stack':[4,0x11,0x22,0xC1]+[0]*8,
            'wram':{'007E':1,'007F':0},'timing':{'memoryManager.masterClock':clock*8,'cpu.cycleCount':clock,'ppu.frameCount':1}}
    e=row('interrupt-entry',0xD1E77C,100)
    m=row('nmi-mode-dispatch',0xCD0C99,200)
    m['cpu'].update(a=2,x=2,y=0xCC90,d=0,dbr=0,sp=0x06F4,ps=0x24)
    m['stack']=[0xDD,0xE7,0xD1,0x21,0x43,0x7E,0x78,0x56,0x34,0x12,0xCD,0xAB];m['wram']['007F']=1
    s=row('nmi-scene-dispatch',0xCD16AF,300)
    s['cpu'].update(a=8,x=8,d=0,dbr=0x7E,sp=0x06E8,ps=0x24);s['wram']['007F']=1
    z=row('interrupt-rti',0xD1E898,400)
    return [e,m,s,z],mode_cells,scene_cells


class Projection(unittest.TestCase):
    def reject(self,fn):
        args=specimen();fn(*args)
        with self.assertRaises(ValueError):a.project_validated_records(*args)

    def test_selected_specimen_and_scope_flags(self):
        r=a.project_validated_records(*specimen())
        self.assertEqual((r['normal_nmi_pairs'],r['mode_observations'],r['scene_observations']),(1,1,1))
        self.assertEqual(r['scene_derived_commands'],[{'command':'84','count':1}])
        self.assertEqual(r['mode_entry_stack_deltas'],[12]);self.assertEqual(r['scene_entry_stack_deltas'],[24])
        self.assertEqual(r['mode_static_target'],'CD088D')
        for key in ('target_pointer_bus_reads_observed','scene_command_fetch_bytes_observed','complete_legal_input_domains_proved','full_stack_low_water_proved','production_approval'):
            self.assertIs(r[key],False)

    def test_later_scene_records_are_retained_without_global_b_claim(self):
        rows,modes,scenes=specimen();later=copy.deepcopy(rows[2]);later['cpu'].update(a=10,x=10)
        later['timing'].update({'memoryManager.masterClock':2800,'cpu.cycleCount':350});rows.insert(3,later)
        r=a.project_validated_records(rows,modes,scenes)
        self.assertEqual(r['scene_observations'],2);self.assertEqual(r['scene_derived_command_count'],2)

    def test_nmi_without_scene_is_valid_subset(self):
        args=specimen();args[0].pop(2);r=a.project_validated_records(*args)
        self.assertEqual(r['scene_observations'],0);self.assertIsNone(r['scene_minimum_observed_sp'])

    def test_exact_context_scalar_types(self):
        for key,value in [('context_id',1.0),('context_depth',True)]:
            with self.subTest(key=key):self.reject(lambda rs,*_,k=key,v=value:rs[1].__setitem__(k,v))

    def test_exact_cpu_scalar_types(self):
        for key,value in [('a',2.0),('d',False),('emulationMode',0)]:
            with self.subTest(key=key):self.reject(lambda rs,*_,k=key,v=value:rs[1]['cpu'].__setitem__(k,v))

    def test_exact_wram_timing_stack_scalar_types(self):
        self.reject(lambda rs,*_:rs[1]['wram'].__setitem__('007E',True))
        self.reject(lambda rs,*_:rs[1]['timing'].__setitem__('cpu.cycleCount',200.0))
        self.reject(lambda rs,*_:rs[1]['stack'].__setitem__(0,221.0))

    def test_missing_or_duplicate_mode_refuses(self):
        self.reject(lambda rs,*_:rs.pop(1))
        self.reject(lambda rs,*_:rs.insert(2,copy.deepcopy(rs[1])))

    def test_cross_context_scene_refuses(self):self.reject(lambda rs,*_:rs[2].__setitem__('context_id',2))
    def test_wrong_context_kind_cannot_borrow_entry(self):self.reject(lambda rs,*_:rs[0].__setitem__('context_kind','battle-irq'))
    def test_unmatched_rti_refuses(self):self.reject(lambda rs,*_:rs.pop())
    def test_rti_register_and_frame_preservation(self):
        self.reject(lambda rs,*_:rs[-1]['cpu'].__setitem__('a',0))
        self.reject(lambda rs,*_:rs[-1]['stack'].__setitem__(0,0))

    def test_each_saved_byte_and_jsl_byte_is_bound(self):
        for i in range(12):
            with self.subTest(i=i):self.reject(lambda rs,*_,j=i:rs[1]['stack'].__setitem__(j,rs[1]['stack'][j]^1))

    def test_mode_stack_delta_and_hidden_byte(self):
        self.reject(lambda rs,*_:rs[1]['cpu'].__setitem__('sp',0x06F3))
        self.reject(lambda rs,*_:rs[1]['cpu'].__setitem__('a',0x0102))
        self.reject(lambda rs,*_:rs[1]['cpu'].__setitem__('x',4))

    def test_mode_y_dbr_and_d_are_bound(self):
        for key,value in [('y',0xCC91),('d',0x100),('dbr',0x7E)]:
            with self.subTest(key=key):self.reject(lambda rs,*_,k=key,v=value:rs[1]['cpu'].__setitem__(k,v))

    def test_width_and_irq_mask_are_bound(self):
        for ps in (0x04,0x34,0x20):self.reject(lambda rs,*_,p=ps:rs[1]['cpu'].__setitem__('ps',p))

    def test_busy_prefix_inputs_are_bound(self):
        self.reject(lambda rs,*_:rs[0]['wram'].__setitem__('007F',1))
        self.reject(lambda rs,*_:rs[1]['wram'].__setitem__('007F',0))
        self.reject(lambda rs,*_:rs[1]['wram'].__setitem__('007E',2))

    def test_scene_index_must_be_zero_b_even_and_in_classifier_domain(self):
        for index in (7,254,0x108):
            self.reject(lambda rs,*_,i=index:rs[2]['cpu'].update(a=i,x=i))

    def test_scene_a_x_and_stack_must_agree(self):
        self.reject(lambda rs,*_:rs[2]['cpu'].__setitem__('a',10))
        self.reject(lambda rs,*_:rs[2]['cpu'].__setitem__('sp',0x06E7))

    def test_mode_or_scene_clock_cannot_be_borrowed(self):
        self.reject(lambda rs,*_:rs[1]['timing'].__setitem__('cpu.cycleCount',100))
        self.reject(lambda rs,*_:rs[2]['timing'].__setitem__('memoryManager.masterClock',4000))

    def test_static_cell_cannot_be_substituted(self):
        self.reject(lambda rs,ms,*_:ms[1].__setitem__('x',4))
        self.reject(lambda rs,ms,ss:ss[4].__setitem__('pointer_byte_addresses',[0xC00000,0xC00001]))

    def test_projection_hash_binds_entry_and_record_ordinals(self):
        args=specimen();r=a.project_validated_records(*args)
        args[0].insert(0,{'kind':'unrelated'})
        other=a.project_validated_records(*args)
        self.assertNotEqual(r['selected_record_ordinals_sha256'],other['selected_record_ordinals_sha256'])
        self.assertNotEqual(r['mode_projection_sha256'],other['mode_projection_sha256'])

    def test_empty_selected_evidence_refuses(self):
        _,m,s=specimen()
        with self.assertRaises(ValueError):a.project_validated_records([],m,s)


if __name__=='__main__':unittest.main()
