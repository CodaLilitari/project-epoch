"""Original synthetic refusal metadata and adversarial changes; no trace inputs."""
from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import package_natural_refusal_validation_v1 as v


def fixture():
 w={k:0 for k in v.WRAM_KEYS};w.update({'2980':0,'2981':1,'2982':2,'A62D':2,'9EE3':12,'95D5':1,'0006':0xF5,'0007':0x93,'B18B':1,'B18C':12,'B2EA':4,'B2EB':0,'B2EC':255,'AF22':1})
 reg={k:bytearray(n) for k,(_,n) in v.REGIONS.items()}
 reg['queue'][:]=bytes([0x81,0,0,0,0,255,0]*2+[0,0,0,0,0,255,0])
 reg['participant_map'][:]=bytes([0,1,2,255,255,255,255]);reg['saved_rates'][1]=84
 reg['atb_rates'][1]=37;reg['atb_status'][1]=3;reg['menu_ready'][1]=255
 for i in range(11):
  reg['battle_records'][i*128+3:i*128+5]=([739,600,187][i] if i<3 else 1000).to_bytes(2,'little')
  reg['battle_records'][i*128+7:i*128+9]=([93,97,99][i] if i<3 else 0).to_bytes(2,'little')
 reg['hp_pending_terms'][8:10]=(192).to_bytes(2,'little')
 rows=[];poll=0;pre=False;active=False;rid=0
 frame=[0xE9,0x85,0x35,0x83]+[0]*12
 def emit(kind,*,address=None,value=-1,buspc=None,stack=None,**changes):
  c={'a':0,'x':0,'y':0,'d':0,'dbr':126,'sp':0x6EA,'ps':0x20,'k':0,'pc':0,'emulationMode':False};c.update(changes)
  if pre and (kind.startswith('target-') or (buspc is not None and 0xC1EC00<=buspc<=0xC1EDFF)):
   c['sp']=0x6E3
   if stack is None:stack=[0x87,0xAC,0x5C,0xAC]+[0]*12
  a=v.SITES.get(kind,0) if address is None else address
  pc=buspc if buspc is not None else a if kind not in v.EVENTS|v.MEMORY else 0xC10000
  c['k'],c['pc']=pc>>16,pc&65535
  i=len(rows);clock=100000+i*10
  r={'kind':kind,'address':a,'value':value,'frame':poll,'cpu':c,'stack':list(frame if stack is None else stack),
   'wram':dict(w),'regions':{k:b.hex() for k,b in reg.items()},'transaction_id':rid,'transaction_active':active,
   'prelude_active':pre,'resolver_active':False,'selector_word':w['9877'],'branch_word':w['A0B3'],'mask0_word':w['0080'],'mask1_word':w['0082'],'root_word':0,
   'timing':{'masterClock':clock&0xFFFFFFFF,'memoryManager.masterClock':clock,'cpu.cycleCount':i*2,'frameCount':poll,'ppu.frameCount':poll,'ppu.scanline':0,'memoryManager.hClock':0,'clockRate':21477270}}
  rows.append(r);return r
 def write(address,value,pc,**changes):
  emit('prelude-memory-write' if pre else 'transaction-memory-write',address=address,value=value,buspc=pc,**changes)
  low=address&65535
  if f'{low:04X}' in w:w[f'{low:04X}']=value
  for name,(start,size) in v.REGIONS.items():
   if start<=low<start+size:reg[name][low-start]=value
 emit('baseline')
 for poll in (2320,2390,2410):emit('menu-observation')
 poll=2435;pre=True;emit('preselection-living-target')
 poll=2443;emit('menu-commit-entry')
 for a,z,pc in [(0x7E93F5,65,0xC116F5),(0x7E93F6,32,0xC116FD),(0x7E93F7,1,0xC11703),(0x7E93F8,2,0xC11709),(0x7E93FA,255,0xC1170E),(0x7E93FB,12,0xC11713)]:write(a,z,pc,x=7)
 emit('menu-queue-fields-written');emit('menu-commit-complete')
 poll=2524;emit('target-hp-before-subtraction',ps=0,x=256,y=8)
 emit('target-hp-subtraction-store',ps=0,x=256,y=8,a=65531)
 write(0x7E5F30,251,0xC1ECA3,ps=0,x=256,y=8,a=65531);write(0x7E5F31,255,0xC1ECA3,ps=0,x=256,y=8,a=65531)
 emit('target-hp-subtraction-readback',ps=0,x=256,y=8)
 emit('target-status-before-death',x=256,y=8);write(0x7E5F4A,128,0xC1ED0C,x=256,y=8,a=128);emit('target-status-death-readback',x=256,y=8)
 emit('target-hp-clamp-store',ps=0,x=256,y=8)
 write(0x7E5F30,0,0xC1ED12,ps=0,x=256,y=8);write(0x7E5F31,0,0xC1ED12,ps=0,x=256,y=8)
 emit('target-hp-clamp-readback',ps=0,x=256,y=8)
 poll=2560;write(0x7E93F5,1,0xC1B9A1)
 pre=False;active=True;rid=1;emit('queued-tech-entry',x=0x93F5)
 target_frame=[0x8A,0xBB]+frame[:14];final_frame=[0x5C,0xBC]+frame[:14]
 emit('target-validation-entry',sp=0x6E8,stack=target_frame)
 write(0x7EAF23,0,0xC1C1E1,sp=0x6E8,stack=target_frame)
 w.update({'B2EA':1,'B2EB':255})
 emit('selected-target-status-read',x=256,sp=0x6E8,stack=target_frame)
 emit('selected-target-dead-jump',a=128,x=256,ps=0xA0,sp=0x6E8,stack=target_frame)
 emit('target-validation-failure',sp=0x6E8,stack=target_frame)
 write(0x7EAF23,1,0xC1C730,sp=0x6E8,stack=target_frame)
 emit('target-validation-return',a=1);emit('target-failure-jump');emit('shared-finalizer-call')
 emit('shared-finalizer-entry',sp=0x6E8,stack=final_frame)
 for a,z,pc in [(0x7E93F5,0,0xC1BDCA),(0x7E93F6,0,0xC1BDCD),(0x7E93F7,0,0xC1BDD0),(0x7E93F8,0,0xC1BDD3),(0x7E93FB,0,0xC1BDD6),(0x7EB189,1,0xC1BDE3),(0x7EB189,0,0xC1BDE6),(0x7EAFAC,84,0xC1BDEC)]:write(a,z,pc,sp=0x6E8,stack=final_frame)
 write(0x7E9F23,84,0xC1BDB2,sp=0x6E6,stack=[0xEE,0xBD]+final_frame[:14])
 poll=2561
 for a,z,pc in [(0x7EAFAC,84,0xC1BE2A),(0x7E9F23,84,0xC1BE2D),(0x7EB03B,1,0xC1BE37),(0x7EB189,0,0xC1BE3B),(0x7E93F5,0,0xC1BE4B)]:write(a,z,pc,sp=0x6E8,stack=final_frame)
 emit('shared-finalizer-return');emit('queue-release-entry')
 for a,z,pc in [(0x7E93F6,0,0xC1BD0E),(0x7E93F7,0,0xC1BD11),(0x7E93F8,0,0xC1BD14),(0x7E93FB,0,0xC1BD17),(0x7E93FA,255,0xC1BD6B),(0x7EAF22,0,0xC1BD6E)]:write(a,z,pc)
 emit('queue-release-rts',x=0x93F5);emit('transaction-caller-resume',address=0xC185EA,x=0x93F5,sp=0x6EC,stack=frame[2:]+[0,0])
 active=False;poll=2600;emit('menu-observation')
 poll=2773;reg['atb_status'][1]=0x81
 emit('post-refusal-ready-write',address=0x7EA6DA,value=1,buspc=0xC11B83,x=1,a=1)
 reg['menu_ready'][1]=1
 emit('post-refusal-ready-readback',x=1,a=1)
 poll=3000;emit('menu-observation');poll=4000;emit('terminal')
 return {'schema':v.SCHEMA,'error':None,'records':rows}


class RefusalTests(unittest.TestCase):
 def setUp(self):self.t=fixture()
 def row(self,kind):return next(r for r in self.t['records'] if r['kind']==kind)
 def reject(self):
  with self.assertRaises(v.ObservationError):v.summarize(self.t)
 def test_complete_synthetic_refusal(self):
  r=v.summarize(self.t);self.assertEqual(r['pc_mp_after'],[93,97,99]);self.assertEqual(r['transaction_actual_write_count'],22)
 def test_empty_trace(self):self.t['records']=[];self.reject()
 def test_collector_error(self):self.t['error']='failure';self.reject()
 def test_schema(self):self.t['schema']='success';self.reject()
 def test_extra_field(self):self.row('queued-tech-entry')['extra']=1;self.reject()
 def test_bool_cpu_integer(self):self.row('queued-tech-entry')['cpu']['x']=True;self.reject()
 def test_byte_bound(self):self.row('queued-tech-entry')['wram']['AF23']=256;self.reject()
 def test_wrong_pc(self):self.row('target-validation-failure')['cpu']['pc']+=1;self.reject()
 def test_wrong_bank(self):self.row('target-validation-failure')['cpu']['k']=0;self.reject()
 def test_wrong_dbr(self):self.row('target-hp-subtraction-store')['cpu']['dbr']=0x41;self.reject()
 def test_wrong_d(self):self.row('selected-target-status-read')['cpu']['d']=1;self.reject()
 def test_wrong_width(self):self.row('target-hp-clamp-store')['cpu']['ps']=0x20;self.reject()
 def test_decimal_arithmetic(self):self.row('target-hp-subtraction-store')['cpu']['ps']|=8;self.reject()
 def test_wrong_x(self):self.row('target-hp-subtraction-store')['cpu']['x']=128;self.reject()
 def test_wrong_y(self):self.row('target-hp-subtraction-store')['cpu']['y']=4;self.reject()
 def test_clock_reversal(self):self.row('queued-tech-entry')['timing']['memoryManager.masterClock']=0;self.row('queued-tech-entry')['timing']['masterClock']=0;self.reject()
 def test_cycle_reversal(self):self.row('queued-tech-entry')['timing']['cpu.cycleCount']=0;self.reject()
 def test_clock_low32(self):self.row('queued-tech-entry')['timing']['masterClock']+=1;self.reject()
 def test_legitimate_clock_rollover(self):
  for i,r in enumerate(self.t['records']):
   t=0xFFFFFFF0+i*10;r['timing']['memoryManager.masterClock']=t;r['timing']['masterClock']=t&0xFFFFFFFF
  v.summarize(self.t)
 def test_missing_store(self):self.t['records'].remove(next(r for r in self.t['records'] if r['kind']=='transaction-memory-write'));self.reject()
 def test_duplicate_boundary(self):r=self.row('target-validation-return');self.t['records'].insert(self.t['records'].index(r),copy.deepcopy(r));self.reject()
 def test_wrong_transaction(self):self.row('target-validation-return')['transaction_id']=2;self.reject()
 def test_false_window(self):self.row('target-validation-return')['transaction_active']=False;self.reject()
 def test_false_prelude(self):self.row('menu-commit-entry')['prelude_active']=False;self.reject()
 def test_resolver_hidden(self):self.row('target-validation-return')['resolver_active']=True;self.reject()
 def test_wrong_target(self):self.row('preselection-living-target')['wram']['A62D']=0;self.reject()
 def test_wrong_tech(self):self.row('preselection-living-target')['wram']['9EE3']=16;self.reject()
 def test_wrong_queue_store(self):r=next(r for r in self.t['records'] if r['kind']=='prelude-memory-write' and r['address']==0x7E93F8);r['value']=0;self.reject()
 def test_forged_death_without_store(self):self.t['records'].remove(next(r for r in self.t['records'] if r['kind']=='prelude-memory-write' and r['address']==0x7E5F4A));self.reject()
 def test_wrong_subtraction_accumulator(self):self.row('target-hp-subtraction-store')['cpu']['a']=1;self.reject()
 def test_wrong_frame(self):self.row('target-validation-failure')['stack'][0]^=1;self.reject()
 def test_damage_frame_mismatch(self):self.row('target-hp-subtraction-store')['stack'][7]^=1;self.reject()
 def test_menu_frame_mismatch(self):self.row('menu-queue-fields-written')['cpu']['sp']+=1;self.reject()
 def test_wrong_caller(self):r=self.row('transaction-caller-resume');r['address']=0xC185D1;r['cpu']['pc']=0x85D1;self.reject()
 def test_wrong_return_register(self):self.row('transaction-caller-resume')['cpu']['a']=1;self.reject()
 def test_final_unexplained_queue_change(self):r=self.row('transaction-caller-resume');a=bytearray.fromhex(r['regions']['queue']);a[0]=0;r['regions']['queue']=a.hex();self.reject()
 def test_missing_ready(self):self.t['records'].remove(self.row('post-refusal-ready-write'));self.reject()
 def test_wrong_ready_source(self):self.row('post-refusal-ready-write')['cpu']['pc']+=1;self.reject()
 def test_ready_without_readback(self):self.t['records'].remove(self.row('post-refusal-ready-readback'));self.reject()

class ArchiveTests(unittest.TestCase):
 def test_exact_archive_and_post_run_drift(self):
  import tempfile
  import run_package_natural_refusal_observation_v1 as runner
  with tempfile.TemporaryDirectory() as d:
   directory=Path(d); sources={}
   for key in runner.ARCHIVE_KEYS:
    p=directory/(key+'.original.txt');p.write_text('original synthetic '+key);sources[key]=p
   before={k:runner.safe.sha256_file(p) for k,p in sources.items()}
   archived,hashes=runner.archive_sources(directory/'archive',sources,before)
   self.assertEqual(hashes,before)
   runner.safe.require_file_hashes_unchanged(archived,hashes,'archive')
   archived['collector'].write_text('changed synthetic source')
   with self.assertRaises(runner.safe.ProbeError):
    runner.safe.require_file_hashes_unchanged(archived,hashes,'archive')
 def test_archive_copy_must_match_guarded_hash(self):
  import tempfile
  import run_package_natural_refusal_observation_v1 as runner
  with tempfile.TemporaryDirectory() as d:
   directory=Path(d); sources={}
   for key in runner.ARCHIVE_KEYS:
    p=directory/(key+'.original.txt');p.write_text('original synthetic '+key);sources[key]=p
   before={k:runner.safe.sha256_file(p) for k,p in sources.items()};before['collector']='0'*64
   with self.assertRaises(runner.ObservationError):runner.archive_sources(directory/'archive',sources,before)

if __name__=='__main__':unittest.main()
