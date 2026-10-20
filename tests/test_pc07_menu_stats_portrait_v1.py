"""Scoped gate CPU oracle, independent assembler and fail-closed image guards."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_pc07_menu_stats_helper_v1 as helper
import pc07_menu_stats_portrait_write_contract_v1 as contract
import validate_rom_write_intents as guard
ROOT=Path(__file__).resolve().parents[1]

def nz(p,value,bits):
    return (p&~0x82)|(0x80 if value&(1<<(bits-1)) else 0)|(2 if value==0 else 0)

def canonical(counter,p):
    return nz((p&~1)|int(counter>=7),(counter-7)&65535,16)

class GateCpu:
    """Direct instruction execution of the 30-byte helper, including its JSL frame."""
    def __init__(self,blob,counter,identity,p):
        self.code={helper.BASE+i:b for i,b in enumerate(blob)}
        self.code.update({0xC299C1+i:b for i,b in enumerate(bytes.fromhex('2200044A'))})
        self.pc=0xC299C1; self.p=p; self.a=0x937A; self.x=0x5342; self.y=0xB7D0; self.d=0; self.dbr=0x7E; self.s=0x6D8
        self.mem={0x7E0002:counter&255,0x7E0003:counter>>8,0x7E2830:identity}
        self.reads=[]; self.writes=[]; self.instructions=set(); self.branches=set(); self.min_s=self.s
    def fetch(self,n):
        value=sum(self.code[self.pc+i]<<(8*i) for i in range(n)); self.pc+=n; return value
    def read(self,at,n):
        self.reads.append((at,n)); return sum(self.mem.get(at+i,0)<<(8*i) for i in range(n))
    def push(self,value,n):
        for i in reversed(range(n)):
            self.mem[0x7E0000+self.s]=(value>>(8*i))&255
            self.writes.append((0x7E0000+self.s,(value>>(8*i))&255)); self.s-=1; self.min_s=min(self.s,self.min_s)
    def pop(self,n):
        value=0
        for i in range(n): self.s+=1; value|=self.read(0x7E0000+self.s,1)<<(8*i)
        return value
    def run(self):
        for _ in range(40):
            if self.pc==0xC299C5:return self
            at=self.pc; op=self.fetch(1); self.instructions.add(at); width=1 if self.p&32 else 2; mask=(1<<(width*8))-1
            if op==0x22:
                target=self.fetch(3); ret=self.pc-1; self.push(ret>>16,1); self.push(ret&65535,2); self.pc=target
            elif op==0x6B:
                lo=self.pop(2); bank=self.pop(1); self.pc=(bank<<16)|((lo+1)&65535)
            elif op in (0xA5,0xAF):
                address=0x7E0000+self.d+self.fetch(1) if op==0xA5 else self.fetch(3)
                value=self.read(address,width); self.a=(self.a&~mask)|value; self.p=nz(self.p,value,width*8)
            elif op==0xC9:
                left=self.a&mask; right=self.fetch(width)
                self.p=nz((self.p&~1)|int(left>=right),(left-right)&mask,width*8)
            elif op==0xD0:
                rel=self.fetch(1); rel=rel-256 if rel&128 else rel; take=not(self.p&2)
                self.branches.add((at,take)); self.pc+=rel if take else 0
            elif op==0x08:self.push(self.p,1)
            elif op==0x48:self.push(self.a,width)
            elif op==0x68:
                value=self.pop(width); self.a=(self.a&~mask)|value; self.p=nz(self.p,value,width*8)
            elif op==0x28:self.p=self.pop(1)
            elif op==0xC2:self.p&=~self.fetch(1)
            elif op==0xE2:self.p|=self.fetch(1)
            elif op==0x18:self.p&=~1
            else:raise AssertionError(f'unknown opcode {op:02X} at {at:06X}')
        raise AssertionError('instruction budget')

class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/contract.ASM['path']).read_bytes(); cls.item=helper.encode(cls.source.decode('utf-8'))
        cls.hits=set(); cls.branches=set(); cls.cases=0
    def run_case(self,counter,identity,p=4):
        cpu=GateCpu(self.item['data'],counter,identity,p).run(); admitted=counter==7 and identity==7
        self.assertEqual(cpu.a,counter)
        self.assertEqual(cpu.p,canonical(counter,p)&~1 if admitted else canonical(counter,p))
        self.assertEqual((cpu.x,cpu.y,cpu.d,cpu.dbr,cpu.s),(0x5342,0xB7D0,0,0x7E,0x6D8))
        self.assertEqual(cpu.min_s,0x6D2 if counter==7 else 0x6D5)
        self.assertTrue(all(0x7E06D3<=address<=0x7E06D8 for address,_ in cpu.writes))
        self.assertEqual([r for r in cpu.reads if r[0]==0x7E2830],[(0x7E2830,1)] if counter==7 else [])
        self.hits.update(cpu.instructions); self.branches.update(cpu.branches); type(self).cases+=1
        return cpu
    def test_all_identity_bytes_at_last_iteration_and_exit(self):
        for ident in range(256):
            self.run_case(7,ident); self.run_case(8,ident)
    def test_canonical_counter_and_flags(self):
        for p in (0,1,2,0x43,0x84,0xC7):
            for counter in (0,1,2,3,4,5,6,7,8,9,0x7FFF,0x8000,0xFFFF):self.run_case(counter,7,p)
    def test_loop_runs_seven_or_eight_and_terminates(self):
        for ident in (0,1,6,7,8,0x80,0x87,0xFF):
            executed=[]; counter=0
            while True:
                executed.append(counter); counter+=1
                if self.run_case(counter,ident).p&1:break
                self.assertLess(counter,9)
            self.assertEqual(executed,list(range(8 if ident==7 else 7)))
    def test_source_pin_and_independent_assembler(self):
        self.assertEqual(len(self.source),contract.ASM['bytes']); self.assertEqual(contract.sha(self.source),contract.ASM['sha256'])
        base=ROOT/'private/research/pc07_menu_stats_20261020/engineering'
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='gate_test_',dir=base) as tmp:
            actual,receipt=contract.assemble(Path(tmp)/'assembly',self.source)
            self.assertEqual(actual['data'],self.item['data']); self.assertTrue(receipt['independent_opcode_equality'])
    @classmethod
    def tearDownClass(cls):
        expected={r['cpu'] for r in cls.item['instructions']}
        if cls.hits-{0xC299C1}!=expected:raise AssertionError('new helper instruction coverage')
        for row in cls.item['instructions']:
            if row['source'].startswith('bne '):
                if not {(row['cpu'],False),(row['cpu'],True)}<=cls.branches:raise AssertionError('conditional edge coverage')
        print(json.dumps({'gate_cases':cls.cases,'all_new_instructions_and_conditional_edges':True,
                          'helper_bytes':len(cls.item['data']),'local_stack_including_jsl':6}))

class GuardTests(unittest.TestCase):
    def test_sealed_guard_and_mutations(self):
        if contract.ART is None or contract.SOURCE_QUALIFICATION is None:
            with self.assertRaises(ValueError):
                with contract.source_snapshot(ROOT/'private/test_runs/pc07_menu_stats_portrait_UNSEALED/assembly'):pass
            return
        base=ROOT/'private/research/pc07_menu_stats_20261020/engineering'; base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='guard_test_',dir=base) as tmp:
            with contract.source_snapshot(Path(tmp)/'assembly') as snap:
                manifest=contract.template('private/test_runs/pc07_menu_stats_portrait_TEST/diagnostic.sfc')
                self.assertEqual(guard.validate_pc07_menu_stats_portrait_v1_manifest(manifest)['status'],'metadata-valid')
                self.assertTrue(guard.audit_pc07_menu_stats_portrait_v1_images(manifest,snap['source'],snap['target'])['complete_diff_coverage'])
                for field,value in (('production_approval',True),('per_redraw_portrait_dma_bytes',1152),('source',{})):
                    bad=copy.deepcopy(manifest); bad[field]=value
                    with self.assertRaises(ValueError):guard.validate_pc07_menu_stats_portrait_v1_manifest(bad)
                for offset in (0x0C0000,0x3F0000,0x4A0000,0x4A0450,0x4A14A0,0x0299C6):
                    bad=bytearray(snap['target']); bad[offset]^=1
                    with self.assertRaises(ValueError):guard.audit_pc07_menu_stats_portrait_v1_images(manifest,snap['source'],bytes(bad))
                bad=bytearray(snap['source']); bad[0]^=1
                with self.assertRaises(ValueError):guard.audit_pc07_menu_stats_portrait_v1_images(manifest,bytes(bad),snap['target'])
if __name__=='__main__':unittest.main()
