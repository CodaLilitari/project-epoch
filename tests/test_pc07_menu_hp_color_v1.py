"""Focused native instruction-model check of HP-color qualification/comparison.
No original portrait or historical helper suites are executed.
"""
from pathlib import Path
import sys,unittest,tempfile,json,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import pc07_menu_hp_color_write_contract_v1 as contract
import native_pc07_menu_hp_color_helper_v1 as helper
import validate_rom_write_intents as guard
ROOT=Path(__file__).resolve().parents[1]
def physical(address):
    address &= 0xFFFFFF
    return 0x7E0000+(address & 0xFFFF) if address >> 16 == 0 and address & 0xFFFF < 0x2000 else address


def nz(p, value, width):
    return (p & ~0x82) | (0x80 if value & (1 << (width-1)) else 0) | (2 if not value else 0)


class Cpu:
    def __init__(self, code, pc, memory, a, x, y, p, d=0, dbr=0x7E):
        self.code, self.pc, self.mem = code, pc, dict(memory)
        self.a, self.x, self.y, self.p, self.d, self.dbr, self.s = a, x, y, p, d, dbr, 0x6D8
        self.writes, self.instructions, self.branches = [], set(), set()
        self.min_sp = self.s

    def fetch(self, count):
        result = sum(self.code[self.pc+i] << (8*i) for i in range(count))
        self.pc += count
        return result

    def read(self, address, width=1):
        return sum(self.mem.get(physical(address+i), 0) << (8*i) for i in range(width))

    def write(self, address, value, width=1, kind='data'):
        for i in range(width):
            at, byte = physical(address+i), (value >> (8*i)) & 255
            self.mem[at] = byte
            self.writes.append((at, byte, kind))

    def push(self, value, width):
        for i in reversed(range(width)):
            self.write(self.s, value >> (8*i), kind='stack')
            self.s = (self.s-1) & 0xFFFF
            self.min_sp = min(self.min_sp, self.s)

    def pop(self, width):
        value = 0
        for i in range(width):
            self.s = (self.s+1) & 0xFFFF
            value |= self.read(self.s) << (8*i)
        return value

    def set_p(self, value):
        self.p = value
        if value & 0x10:
            self.x &= 255
            self.y &= 255

    def lda(self, value, width):
        mask = (1 << (8*width))-1
        self.a = (self.a & ~mask) | (value & mask)
        self.p = nz(self.p, value & mask, 8*width)

    def run(self, stop):
        for _ in range(220):
            if self.pc == stop:
                return self
            at, op = self.pc, self.fetch(1)
            self.instructions.add(at)
            m, xw = (1 if self.p & 0x20 else 2), (1 if self.p & 0x10 else 2)
            mask = (1 << (m*8))-1
            if op == 0x22:
                target = self.fetch(3)
                ret = self.pc-1
                self.push(ret >> 16, 1)
                self.push(ret & 0xFFFF, 2)
                self.pc = target
            elif op == 0x6B:
                ret, bank = self.pop(2), self.pop(1)
                self.pc = bank << 16 | ((ret+1) & 0xFFFF)
            elif op == 0x08:
                self.push(self.p, 1)
            elif op == 0x28:
                self.set_p(self.pop(1))
            elif op in (0xC2, 0xE2):
                value = self.fetch(1)
                self.set_p(self.p & ~value if op == 0xC2 else self.p | value)
            elif op in (0x48, 0xDA, 0x5A, 0x8B):
                value, width = {0x48: (self.a, m), 0xDA: (self.x, xw), 0x5A: (self.y, xw), 0x8B: (self.dbr, 1)}[op]
                self.push(value, width)
            elif op == 0x68:
                self.lda(self.pop(m), m)
            elif op in (0xFA, 0x7A):
                value = self.pop(xw)
                if op == 0xFA:
                    self.x = value
                else:
                    self.y = value
                self.p = nz(self.p, value, xw*8)
            elif op == 0x7B:
                self.a, self.p = self.d, nz(self.p, self.d, 16)
            elif op == 0x8A:
                self.lda(self.x, m)
            elif op == 0xAA:
                self.x = self.a & ((1 << (xw*8))-1)
                self.p = nz(self.p, self.x, xw*8)
            elif op == 0xE8:
                self.x = (self.x+1) & ((1 << (xw*8))-1)
                self.p = nz(self.p,self.x,xw*8)
            elif op in (0xA9, 0xA2):
                value = self.fetch(m if op == 0xA9 else xw)
                if op == 0xA9:
                    self.lda(value, m)
                else:
                    self.x, self.p = value, nz(self.p, value, xw*8)
            elif op in (0xAF, 0xBF):
                address = self.fetch(3) + (self.x if op == 0xBF else 0)
                self.lda(self.read(address, m), m)
            elif op in (0xC9, 0xE0, 0xC0, 0xCF):
                width = xw if op in (0xE0, 0xC0) else m
                left = self.x if op == 0xE0 else self.y if op == 0xC0 else self.a & mask
                right = self.read(self.fetch(3), m) if op == 0xCF else self.fetch(width)
                self.p = nz((self.p & ~1) | int(left >= right), (left-right) & ((1 << (8*width))-1), width*8)
            elif op == 0x29:
                self.lda((self.a & mask) & self.fetch(m), m)
            elif op in (0xF0, 0xD0, 0x90, 0xB0, 0x80, 0x82):
                width = 2 if op == 0x82 else 1
                relative = self.fetch(width)
                if relative & (1 << (8*width-1)):
                    relative -= 1 << (8*width)
                take = {0xF0: bool(self.p & 2), 0xD0: not self.p & 2, 0x90: not self.p & 1,
                        0xB0: bool(self.p & 1), 0x80: True, 0x82: True}[op]
                self.branches.add((at, bool(take)))
                if take:
                    self.pc += relative
            elif op in (0x8F, 0x9F):
                self.write(self.fetch(3) + (self.x if op == 0x9F else 0), self.a, m)
            elif op == 0xD8:
                self.p &= ~8
            elif op == 0x18:
                self.p &= ~1
            elif op == 0x69:
                if self.p & 8:
                    raise AssertionError('unmodeled decimal ADC')
                operand, old = self.fetch(m), self.a & mask
                value = old + operand + (self.p & 1)
                overflow = bool((~(old ^ operand) & (old ^ value)) & (1 << (m*8-1)))
                self.p = (self.p & ~0x41) | int(value > mask) | (0x40 if overflow else 0)
                self.lda(value & mask, m)
            elif op == 0xEA:
                self.nops_after_div += 1
            elif op == 0x5C:
                self.pc = self.fetch(3)
            elif op == 0x54:
                destination, source = self.fetch(1), self.fetch(1)
                self.dbr = destination
                count = self.a+1
                for _ in range(count):
                    self.write(destination << 16 | self.y, self.read(source << 16 | self.x))
                    self.x = (self.x+1) & 0xFFFF
                    self.y = (self.y+1) & 0xFFFF
                self.a = 0xFFFF
            elif op == 0xEE:
                address = self.dbr << 16 | self.fetch(2)
                value = (self.read(address, m)+1) & mask
                self.write(address, value, m)
                self.p = nz(self.p, value, m*8)
            else:
                raise AssertionError(f'unsupported {op:02X} at {at:06X}')
        raise AssertionError('helper instruction budget exceeded')


class ColorCpu(Cpu):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.nops_after_div=0;self.quotient=None
    def write(self,address,value,width=1,kind='data'):
        super().write(address,value,width,kind)
        if address==0x4206:
            divisor=value&255
            self.quotient=self.read(0x4204,2)//divisor if divisor else 65535
            self.nops_after_div=0
    def read(self,address,width=1):
        if address==0x4214:
            if self.quotient is None or self.nops_after_div<8:raise AssertionError('division latency not respected')
            return self.quotient
        return super().read(address,width)

class ColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.item=helper.encode((ROOT/contract.ASM['path']).read_text(encoding='utf-8'))['Pc07MenuHpColorV1']
        cls.hits=set();cls.edges=set();cls.cases=0
    def run_case(self,maximum=969,hp=608,p=4,**change):
        code={self.item['cpu_start']+i:b for i,b in enumerate(self.item['data'])}
        code.update({0xC2A200+i:b for i,b in enumerate(bytes.fromhex('2240044A'))})
        vals={'x':14,'d':0,'dbr':0x7E,'layout':255,'record':7,'live':7,'pointer':0x2830};vals.update(change)
        memory={0x7E0D36:vals['layout'],0x7E9A90:vals['record'],0x7E2830:vals['live'],
                0x7E006F:vals['pointer']&255,0x7E0070:vals['pointer']>>8,
                0x7E9ACF:maximum&255,0x7E9AD0:maximum>>8,0x7E9A93:hp&255,0x7E9A94:hp>>8}
        eligible=not change
        cpu=ColorCpu(code,0xC2A200,memory,0x000E,vals['x'],0x9AE6,p,d=vals['d'],dbr=vals['dbr'])
        cpu.run(0xC2A204 if eligible else 0x470205)
        self.assertEqual((cpu.x,cpu.y,cpu.d,cpu.dbr),(vals['x'],0x9AE6,vals['d'],vals['dbr']))
        if eligible:
            threshold=maximum//10
            expected=nz((p&~1)|int(threshold>=hp),(threshold-hp)&65535,16)
            self.assertEqual((cpu.a,cpu.p,cpu.s),(threshold,expected,0x6D8))
            self.assertEqual([(a,b) for a,b,k in cpu.writes if k=='data'],[(0x4204,maximum&255),(0x4205,maximum>>8),(0x4206,10)])
        else:
            self.assertEqual((cpu.a,cpu.p,cpu.s),(14,p,0x6D5));self.assertEqual([r for r in cpu.writes if r[2]=='data'],[])
            self.assertEqual([cpu.read(0x7E06D6+i) for i in range(3)],[3,0xA2,0xC2])
        self.assertGreaterEqual(cpu.min_sp,0x6CF)
        self.hits.update(cpu.instructions);self.edges.update(cpu.branches);type(self).cases+=1
    def test_division_threshold_boundaries_and_flags(self):
        for maximum in (0,1,9,10,11,99,100,969,999,65535):
            q=maximum//10
            for hp in sorted({0,max(0,q-1),q,q+1,65535}):
                for p in (0,4,0x40,0xC7):self.run_case(maximum,hp,p)
    def test_rejected_context_taildelegates_exactly(self):
        for key,values in {'d':(1,0x100),'dbr':(0,0x7F),'x':(0,2,12,16),'layout':(0,1,5),
                           'record':(0,1,6,8,0x80,0xFF),'live':(0,1,6,8,0x80,0xFF),'pointer':(0x2600,0x27E0,0x287F)}.items():
            for value in values:
                for p in (0,4,0x40,0xC7):self.run_case(p=p,**{key:value})
    def test_current_normal_HP(self):self.run_case()
    @classmethod
    def tearDownClass(cls):
        expected={r['cpu'] for r in cls.item['instructions']}
        if cls.hits-{0xC2A200}!=expected:raise AssertionError('new code coverage')
        for r in cls.item['instructions']:
            if r['source'].split()[0] in ('bne','beq','bcc','bcs'):
                if not {(r['cpu'],False),(r['cpu'],True)}<=cls.edges:raise AssertionError('new branch coverage')
        print(json.dumps({'color_cases':cls.cases,'helper_bytes':len(cls.item['data']),'all_new_instructions_and_edges':True,'critical_equality_preserved':True}))

class GuardTests(unittest.TestCase):
    def test_independent_assembly_and_complete_guard(self):
        base=ROOT/'private/research/pc07_menu_stats_20261020/engineering';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='hp_color_',dir=base) as temp:
            with contract.source_snapshot(Path(temp)/'assembly') as snap:
                m=contract.template('private/test_runs/pc07_menu_stats_portrait_COLOR_TEST/diagnostic.sfc')
                self.assertEqual(guard.validate_pc07_menu_hp_color_v1_manifest(m)['status'],'metadata-valid')
                self.assertTrue(guard.audit_pc07_menu_hp_color_v1_images(m,snap['source'],snap['target'])['complete_diff_coverage'])
                self.assertTrue(snap['assembly']['independent_opcode_equality'])
                for field,value in (('fallback_tail','bad'),('threshold','maxHP/2'),('production_approval',True)):
                    bad=copy.deepcopy(m);bad[field]=value
                    with self.assertRaises(ValueError):guard.validate_pc07_menu_hp_color_v1_manifest(bad)
                for offset in (0x470205,0x4A0400,0x4A1000,0x0C0000,0x02A206):
                    bad=bytearray(snap['target']);bad[offset]^=1
                    with self.assertRaises(ValueError):guard.audit_pc07_menu_hp_color_v1_images(m,snap['source'],bytes(bad))
if __name__=='__main__':unittest.main()
