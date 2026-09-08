"""Original synthetic transaction metadata, independent of private game traces."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import package_transaction_validation_v1 as v


def fixture():
    w={k:0 for k in v.WRAM_KEYS}
    w.update({'0006':0xEE,'0007':0x93,'9877':8,'AF22':1,'B18C':8,'B2EA':0,'B2EB':255,'B2EC':255,
              'AE91':0,'AE92':2,'AE93':8,'2980':0,'2981':1,'2982':2})
    regions={name:bytearray(size) for name,(_,size) in v.REGIONS.items()}
    regions['queue'][:]=bytes([1,0x20,1,3,0,255,8]+[0,0,0,0,0,255,0]*2)
    regions['participant_map'][:]=bytes([0,1,2,255,255,255,255])
    regions['target_result_work'][18]=1
    for slot in range(11):
        regions['battle_records'][slot*128+3:slot*128+5]=(1000+slot).to_bytes(2,'little')
        regions['battle_records'][slot*128+7:slot*128+9]=([93,97,99][slot] if slot<3 else 0).to_bytes(2,'little')
        regions['hp_pending_terms'][slot*4:slot*4+2]=(10 if slot==3 else 0).to_bytes(2,'little')
    frame=[0xD0,0x85,0x35,0x83]+[0]*12
    cpu={'a':0,'x':0,'y':0,'d':0,'dbr':0x7E,'sp':0x06EA,'ps':0x23,'k':0xC1,'pc':0,'emulationMode':False}
    rows=[]; poll=0; active=False; rid=0; resolving=False
    def emit(kind,*,address=None,value=-1,stack=None,**changes):
        nonlocal cpu
        c=dict(cpu);c.update(changes)
        a=v.SITES.get(kind,0) if address is None else address
        pc=a if kind not in v.EVENTS|v.MEMORY else 0xC10000
        if kind in v.MEMORY: pc=changes.pop('buspc',0xC10000);c.pop('buspc',None)
        c['k'],c['pc']=pc>>16,pc&65535
        i=len(rows);clock=100000+i*10
        r={'kind':kind,'address':a,'value':value,'frame':poll,'cpu':c,'stack':list(frame if stack is None else stack),
           'wram':dict(w),'regions':{k:b.hex() for k,b in regions.items()},'transaction_id':rid,
           'transaction_active':active,'resolver_active':resolving,'selector_word':w['9877'],'branch_word':w['A0B3'],
           'mask0_word':w['0080'],'mask1_word':w['0082'],'root_word':0,
           'timing':{'masterClock':clock&0xFFFFFFFF,'memoryManager.masterClock':clock,'cpu.cycleCount':i*2,
                     'frameCount':poll,'ppu.frameCount':poll,'ppu.scanline':0,'memoryManager.hClock':0,'clockRate':21477270}}
        rows.append(r);return r
    def write(address,value,pc,**changes):
        emit('latch-write' if address in (0x7E9876,0x7E5D9B) else 'transaction-memory-write',address=address,value=value,buspc=pc,**changes)
        low=address&65535
        if f'{low:04X}' in w:w[f'{low:04X}']=value
        for name,(start,size) in v.REGIONS.items():
            if start<=low<start+size:regions[name][low-start]=value
    emit('baseline')
    for poll in (40,80,120,160):emit('menu-observation')
    poll=373;active=True;rid=1;emit('queued-tech-entry',x=0x93EE,ps=0x20)
    poll=374;emit('target-validation-return');emit('pre-effect-boundary',a=0,x=0,y=3,ps=0x22)
    poll=376;emit('effect-preparation-return');emit('preparation-af23-branch');emit('preparation-b3c8-branch')
    for pos in range(3):
        call=f'mp-participant{pos}-call'; ret=f'mp-participant{pos}-return' if pos<2 else 'animation-result-call'
        arg=0 if pos==0 else 255;cost=20 if pos==0 else 0
        emit(call,a=arg,y=cost)
        inner=list((v.SITES[ret]-1).to_bytes(3,'little')[:2])+frame[:14]
        emit('mp-deduction-entry',a=arg,y=cost,sp=0x6E8,stack=inner)
        if pos==0:
            write(0x7E5E34,73,0xC1CC8F,a=73,ps=0,sp=0x6E8,stack=inner)
            write(0x7E5E35,0,0xC1CC8F,a=73,ps=0,sp=0x6E8,stack=inner)
        emit('mp-deduction-rts',a=arg,y=cost,sp=0x6E8,stack=inner)
        emit(ret,a=arg,y=cost)
    emit('animation-wrapper-entry',sp=0x6E8,stack=[0x20,0xBC]+frame[:14])
    animation_frame=[0]*12+[0x20,0xBC]+frame[:2]
    poll=377;emit('branch-producer-complete',sp=0x6DC,stack=animation_frame)
    poll=378;root=[0x2A,0x43,0xAF,0x40]+animation_frame[:12]
    resolving=True;emit('resolver-entry',sp=0x6D8,ps=0,stack=root)
    emit('resolver-tail',sp=0x6D8,stack=root);resolving=False
    emit('common-loader-entry',sp=0x6D8,stack=root)
    poll=413;emit('common-loader-rts',sp=0x6D8,stack=root)
    emit('dispatcher-rts',sp=0x6DA,stack=root[2:]+[0]*2)
    emit('caller-resume',sp=0x6DC,stack=animation_frame)
    poll=992;write(0x7E9876,1,0xC14D03);emit('caller-package-latch',sp=0x6DC,stack=animation_frame);emit('caller-effect-latch',sp=0x6DC,stack=animation_frame)
    wrapper=[0x20,0xBC]+frame[:14]; result_frame=[0x87,0xAC,0x5C,0xAC]+wrapper[:12]
    poll=993;emit('result-wrapper-entry',sp=0x6E8,stack=wrapper);emit('result-application-entry',sp=0x6E4,stack=result_frame)
    for slot in range(11):
        before=int.from_bytes(regions['battle_records'][slot*128+3:slot*128+5],'little')
        after=before-(10 if slot==3 else 0)
        c={'a':after,'x':slot*128,'y':slot*4,'sp':0x6E4,'ps':1,'stack':result_frame}
        emit('hp-result-store',**c)
        write(0x7E5E30+slot*128,after&255,0xC1ECA3,**c)
        write(0x7E5E31+slot*128,after>>8,0xC1ECA3,**c)
        emit('hp-result-store-readback',**c)
    poll=994;emit('animation-result-return');emit('successful-table-clear')
    regions['target_result_work'][18:]=bytes(len(regions['target_result_work'])-18)
    emit('shared-finalizer-call');emit('shared-finalizer-entry',sp=0x6E8,stack=[0x5C,0xBC]+frame[:14])
    for offset in (0,1,2,3,6):write(0x7E93EE+offset,0,0xC1BDCA)
    emit('shared-finalizer-return');emit('queue-release-entry')
    write(0x7EAF22,0,0xC1BD6E)
    emit('queue-release-rts',a=255,x=0x93EE,y=0,ps=0xA0)
    emit('transaction-caller-resume',address=0xC185D1,a=255,x=0x93EE,y=0,ps=0xA0,sp=0x6EC,stack=frame[2:]+[0]*2)
    active=False;poll=1200;emit('terminal')
    return {'schema':v.SCHEMA,'error':None,'records':rows}


class TransactionEvidenceTests(unittest.TestCase):
    def setUp(self):self.t=fixture()
    def get(self,kind):return next(r for r in self.t['records'] if r['kind']==kind)
    def reject(self,pattern=None):
        with self.assertRaisesRegex(v.ObservationError,pattern or '.'):v.summarize(self.t)
    def test_original_transaction_fixture_passes(self):
        result=v.summarize(self.t);self.assertEqual(result['pc_mp_before'],[93,97,99]);self.assertEqual(result['pc_mp_after'],[73,97,99]);self.assertEqual(len(result['hp_first_pass_witnesses']),11)
    def test_wrong_transaction_id_refuses(self):self.get('pre-effect-boundary')['transaction_id']=2;self.reject('identity')
    def test_false_active_window_refuses(self):self.get('queue-release-rts')['transaction_active']=False;self.reject('window')
    def test_duplicate_entry_refuses(self):self.t['records'].insert(6,copy.deepcopy(self.get('queued-tech-entry')));self.reject()
    def test_unknown_kind_refuses(self):self.get('pre-effect-boundary')['kind']='looks-right';self.reject('unknown')
    def test_boolean_cpu_integer_refuses(self):self.get('pre-effect-boundary')['cpu']['a']=False;self.reject('integer')
    def test_wrong_native_mode_refuses(self):self.get('pre-effect-boundary')['cpu']['emulationMode']=True;self.reject('native')
    def test_wrong_exact_region_shape_refuses(self):self.get('hp-result-store')['regions']['hp_pending_terms']='00';self.reject('region')
    def test_cpu_pc_cannot_claim_another_boundary(self):self.get('pre-effect-boundary')['cpu']['pc']+=1;self.reject('PC')
    def test_queue_pointer_drift_refuses(self):self.get('pre-effect-boundary')['wram']['0006']+=7;self.reject('pointer')
    def test_pre_effect_width_refuses(self):self.get('pre-effect-boundary')['cpu']['ps']=0;self.reject('ABI')
    def test_participant_ff_not_real_pc_refuses(self):self.get('pre-effect-boundary')['wram']['B2EB']=1;self.reject('participant')
    def test_other_namespace_is_not_participant_proof(self):self.get('pre-effect-boundary')['wram']['B3BB']=1;v.summarize(self.t)
    def test_outer_frame_damage_refuses(self):self.get('animation-result-return')['stack'][0]^=1;self.reject('frame')
    def test_mp_return_cannot_use_other_call_frame(self):self.get('mp-deduction-rts')['stack'][0]=0x10;self.reject('MP near')
    def test_missing_actual_mp_write_refuses(self):
        self.t['records']=[r for r in self.t['records'] if not(r['kind']=='transaction-memory-write' and r['address']==0x7E5E34)];self.reject('actual write')
    def test_wrong_mp_write_owner_refuses(self):
        r=next(r for r in self.t['records'] if r['kind']=='transaction-memory-write' and r['address']==0x7E5E34);r['cpu']['pc']=0xCCAC;self.reject('MP write')
    def test_absent_participant_wrong_argument_refuses(self):
        self.get('mp-participant1-call')['cpu']['a']=1;self.reject('continuity|participant argument')
    def test_unexplained_other_pc_mp_change_refuses(self):
        r=self.get('animation-result-call');b=bytearray.fromhex(r['regions']['battle_records']);b[128+7]-=1;r['regions']['battle_records']=b.hex();self.reject('actual write')
    def test_wrong_hp_pending_term_refuses(self):
        r=self.get('hp-result-store');b=bytearray.fromhex(r['regions']['hp_pending_terms']);b[0]=1;r['regions']['hp_pending_terms']=b.hex();self.reject('subtraction')
    def test_hp_execution_watchpoint_is_not_write_proof(self):
        self.t['records']=[r for r in self.t['records'] if not(r['kind']=='transaction-memory-write' and r['address']==0x7E5E30)];self.reject('witness')
    def test_missing_hp_readback_refuses(self):self.t['records'].remove(self.get('hp-result-store-readback'));self.reject('readbacks')
    def test_wrong_hp_battler_index_refuses(self):self.get('hp-result-store')['cpu']['x']=128;self.reject('index')
    def test_wrong_hp_write_owner_refuses(self):
        r=next(r for r in self.t['records'] if r['kind']=='transaction-memory-write' and r['address']==0x7E5E30);r['cpu']['pc']=0xECB5;self.reject('wrong instruction')
    def test_readback_from_next_action_cannot_be_borrowed(self):self.get('hp-result-store-readback')['transaction_id']=2;self.reject('identity')
    def test_missing_latch_completion_refuses(self):self.get('caller-package-latch')['wram']['9876']=0;self.reject()
    def test_wrong_dynamic_caller_refuses(self):
        r=self.get('transaction-caller-resume');r['address']+=1;r['cpu']['pc']+=1;self.reject('caller')
    def test_finalizer_cannot_claim_success_without_queue_release(self):
        self.t['records']=[r for r in self.t['records'] if not(r['kind']=='transaction-memory-write' and r['address']==0x7E93EE)];self.reject('actual write')
    def test_wrong_caller_pop_size_refuses(self):self.get('transaction-caller-resume')['cpu']['sp']-=1;self.reject('caller/frame')
    def test_generic_clock_rollover_valid(self):
        for i,r in enumerate(self.t['records']):
            r['timing']['memoryManager.masterClock']=2**32-100+i*10;r['timing']['masterClock']=r['timing']['memoryManager.masterClock']&0xFFFFFFFF
        v.summarize(self.t)
    def test_full_clock_reversal_refuses(self):
        r=self.get('pre-effect-boundary');r['timing']['memoryManager.masterClock']=r['timing']['masterClock']=1;self.reject('reversal')
    def test_generic_clock_must_match_full(self):self.get('pre-effect-boundary')['timing']['masterClock']+=1;self.reject('low 32')
    def test_missing_success_boundary_refuses(self):self.t['records'].remove(self.get('animation-result-return'));self.reject('exactly one')
    def test_result_wrapper_frame_refuses(self):self.get('result-wrapper-entry')['stack'][0]^=1;self.reject('wrapper frame')
    def test_result_application_frame_refuses(self):self.get('result-application-entry')['stack'][0]^=1;self.reject('wrapper frame')
    def test_hp_store_frame_refuses(self):self.get('hp-result-store')['stack'][0]^=1;self.reject('HP result frame')
    def test_resolver_drifted_dbr_refuses(self):self.get('resolver-entry')['cpu']['dbr']=0x41;self.reject('addressing')
    def test_animation_latch_drifted_stack_refuses(self):self.get('caller-effect-latch')['cpu']['sp']+=2;self.reject('caller context')
    def test_mp_rts_register_drift_refuses(self):self.get('mp-participant0-return')['cpu']['y']+=1;self.reject('continuity')
    def test_full_target_table_tail_is_checked(self):
        r=self.get('shared-finalizer-call');b=bytearray.fromhex(r['regions']['target_result_work']);b[-1]=1;r['regions']['target_result_work']=b.hex();self.reject('clear snapshot')
    def test_target_header_byte_16_is_preserved_not_cleared(self):
        for r in self.t['records']:
            b=bytearray.fromhex(r['regions']['target_result_work']);b[16]=255;r['regions']['target_result_work']=b.hex()
        v.summarize(self.t)


if __name__=='__main__':unittest.main()
