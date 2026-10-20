"""Focused native-format and independent helper instruction-model checks.

The bounded CPU model proves no native timing, interrupt or physical stack ownership.
It checks new code only; no historical helper suite is replayed.
"""
import copy
import shutil
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import native_pc07_status_portrait_codec_v1 as codec
import native_pc07_status_portrait_helpers_v1 as helpers
import pc07_status_portrait_write_contract_v1 as contract
import validate_rom_write_intents as guard

ROOT = Path(__file__).resolve().parents[1]


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


class PortraitCodecTests(unittest.TestCase):
    def test_exact_geometry_bitplanes_and_palette(self):
        rows = [[(x+y*3) % 16 for x in range(48)] for y in range(48)]
        doc = {'schema': 'epoch-private-schala-portrait-native-candidate-v1', 'dimensions': [48,48],
               'tiles': [6,6], 'tile_count': 36, 'packed_bytes': 1152, 'palette_bytes': 32,
               'palette_entries': 16, 'transparent_index': 0, 'palette_bgr555': list(range(16)),
               'pixel_rows_hex': [''.join(f'{v:x}' for v in row) for row in rows]}
        packed, palette = codec.encode(doc)
        self.assertEqual(codec.decode(packed), rows)
        self.assertEqual(packed[:2], bytes([0x55,0x33]))
        self.assertEqual(packed[16:18], bytes([0x0F,0]))
        self.assertEqual(palette, b''.join(v.to_bytes(2,'little') for v in range(16)))
        for key, value in (('dimensions',[32,32]),('palette_bgr555',[0x8000]*16),('pixel_rows_hex',['0'*47]*48)):
            bad = copy.deepcopy(doc); bad[key] = value
            with self.assertRaises(ValueError): codec.encode(bad)


class PortraitHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components = helpers.encode((ROOT/'asm/pc07_status_portrait_v1.asm').read_text())
        cls.coverage = {name:{'cases':0,'instructions':set(),'branches':set()} for name in cls.components}

    @classmethod
    def tearDownClass(cls):
        for name,item in cls.components.items():
            covered = cls.coverage[name]
            expected = {row['cpu'] for row in item['instructions']}
            conditional = {row['cpu'] for row in item['instructions'] if row['source'].split()[0] in ('beq','bne','bcc','bcs')}
            if covered['instructions'] != expected:
                raise AssertionError((name,'unexecuted helper instruction',sorted(expected-covered['instructions'])))
            if not {(pc,take) for pc in conditional for take in (False,True)} <= covered['branches']:
                raise AssertionError((name,'unexecuted conditional branch outcome'))

    def execute(self, role, *, identity=7, queue=0, changes=None, a=None, x=None, y=None, p=None, d=0, dbr=0x7E):
        tile = role == 'Tiles'
        hook = 0xC2EC3E if tile else 0xC2EC8B
        name = 'Pc07StatusPortrait'+role+'V1'
        item = self.components[name]
        a = (0xA55A if tile else 31) if a is None else a
        x = (identity if tile else 0xCE50) if x is None else x
        y = (0x73 if tile else 0x94E0) if y is None else y
        p = (0x7D if tile else 0x4D) if p is None else p
        memory = {0x7E0061:0xDE,0x7E0062:0x2E,0x7E0001:0x0E,0x7E0D46:identity,
                  0x7E9A90:identity,0x7E0D11:queue,0x7E0D12:0x93,0x7E0D15:0xFF,0x7E0D16:0x12}
        memory.update({0xFFCE70+i:(i*36+1)&255 for i in range(256)})
        memory.update({0xFFCE50+i:(i*13+2)&255 for i in range(32)})
        memory.update({0x4A1480+i:(i*7+3)&255 for i in range(32)})
        memory.update({0x4A14A0+i:value for i,value in enumerate(bytes.fromhex('B2BCC1BAC5BA'))})
        memory.update({0x7E2FAC+i:(i*19+7)&255 for i in range(12)})
        memory.update({0x7E0D5F+i:v for i,v in enumerate([0,1,7,2,4,3,6,5])})
        memory[0x7E0413] = 0
        for base in (0x7E2EC6,0x7E3046,0x7E31C6):
            memory.update({base+i:(i*29+9)&255 for i in range(16)})
        memory.update({at:(at*11+4)&255 for at in range(0x7E0C00,0x7E0D00)})
        memory.update(changes or {})
        original = bytes.fromhex('bf70ceff') if tile else bytes.fromhex('547effee150d')
        reference_code = {hook+i:v for i,v in enumerate(original)}
        reference = Cpu(reference_code,hook,memory,a,x,y,p,d,dbr).run(hook+len(original))
        code = {item['cpu_start']+i:v for i,v in enumerate(item['data'])}
        code.update({hook+i:v for i,v in enumerate(b'\x22'+item['cpu_start'].to_bytes(3,'little'))})
        cpu = Cpu(code,hook,memory,a,x,y,p,d,dbr).run(hook+4)
        coverage = self.coverage[name]
        coverage['cases'] += 1
        coverage['instructions'].update(pc for pc in cpu.instructions if item['cpu_start'] <= pc < item['cpu_start']+len(item['data']))
        coverage['branches'].update(cpu.branches)
        self.assertEqual((cpu.a,cpu.x,cpu.y,cpu.p,cpu.s,cpu.d,cpu.dbr),
                         (reference.a,reference.x,reference.y,reference.p,reference.s,reference.d,reference.dbr))
        common = d == 0 and dbr == 0x7E and memory[0x7E0061] == 0xDE and memory[0x7E0062] == 0x2E and memory[0x7E0001] == 0x0E
        names_qualified = common and identity <= 7 and memory[0x7E9A90] == identity and memory[0x7E0D46] == identity and x == identity
        qualified = common and (identity in (0,7) and memory[0x7E9A90] == identity and memory[0x7E0D46] == identity and x == identity and queue <= 0xF0 and queue % 8 == 0 if tile else
                                a == 31 and x == 0xCE50 and y == 0x94E0 and memory[0x7E9A90] == 7 and memory[0x7E0D46] == 7)
        data = [(at,value) for at,value,kind in cpu.writes if kind == 'data']
        if tile and qualified:
            record = bytes.fromhex('10200010')+bytes([0x4A,0x80,4,0]) if identity == 7 else bytes.fromhex('10200000ff800400')
            expected = [(0x7E0C00+queue+i,value) for i,value in enumerate(record)]+[(0x7E0D11,queue+8)]
        elif not tile and qualified:
            expected = [(0x7E94E0+i,memory[0x4A1480+i]) for i in range(32)] + [(at,value) for at,value,kind in reference.writes if at in (0x7E0D15,0x7E0D16)]
        else:
            expected = [(at,value) for at,value,kind in reference.writes if kind == 'data']
        if tile and names_qualified:
            destinations = [0x7E2FAC] if identity == 7 else []
            scroll = memory[0x7E0413]
            if scroll <= 5:
                destinations += [base for row,base in enumerate((0x7E2EC6,0x7E3046,0x7E31C6))
                                 if memory[0x7E0D5F+scroll+row] == 7]
            expected = [(base+2*i,value) for base in destinations for i,value in enumerate(bytes.fromhex('B2BCC1BAC5BA'))]+expected
        self.assertEqual(data, expected)
        self.assertGreaterEqual(cpu.min_sp, 0x6D8-11)
        allowed = {at for at,value,kind in cpu.writes if kind == 'stack'} | {at for at,value in expected}
        self.assertTrue(all(value == memory.get(at,0) for at,value in cpu.mem.items() if at not in allowed))
        return cpu

    def test_new_helpers_flag_preservation_and_crono_restore(self):
        flags = [sum(bit for n,bit in enumerate((1,2,4,8,64,128)) if mask >> n & 1) for mask in range(64)]
        for p in flags:
            for identity in (0,7):
                self.execute('Tiles',identity=identity,p=p|0x30)
            self.execute('Palette',p=p)

    def test_every_queue_index_and_other_characters_fallback(self):
        for queue in range(256): self.execute('Tiles',queue=queue)
        for identity in range(256): self.execute('Tiles',identity=identity)
        for x in (0,6,8): self.execute('Tiles',x=x)
        for scroll in range(256): self.execute('Tiles',changes={0x7E0413:scroll})
        for role in ('Tiles','Palette'):
            for at, values in ((0x7E0061,(0,0x96,0xDF)),(0x7E0062,(0,0x2F)),(0x7E0001,(0,0x16)),
                               (0x7E9A90,(0,1,6,8)),(0x7E0D46,(0,1,6,8))):
                for value in values: self.execute(role,changes={at:value})
            for d in (1,0x1234,0xFFFF): self.execute(role,d=d)
            for dbr in (0,0x7F,0xFF): self.execute(role,dbr=dbr)

    def test_palette_pointer_count_and_epoch_context_fallback(self):
        for a in (0,1,30,32): self.execute('Palette',a=a)
        for x in (0x1FE0,0xCE4F,0xCE51): self.execute('Palette',x=x)
        for y in (0x9480,0x94C0,0x9500): self.execute('Palette',y=y)
        for role in ('Tiles','Palette'):
            self.execute(role,changes={0x7E0061:0x96,0x7E0001:0x16})


class PortraitContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/contract.SOURCE['path']).is_file():
            raise unittest.SkipTest('private current image is not distributed')
        parent = (ROOT/'private/test_runs').resolve()
        cls.folder = Path(tempfile.mkdtemp(prefix='pc07_status_portrait_unit_',dir=parent)).resolve()
        if cls.folder.parent != parent:
            raise ValueError('private test directory required')
        def cleanup():
            target = cls.folder.resolve()
            if target.parent != parent or not target.name.startswith('pc07_status_portrait_unit_'):
                raise ValueError('unsafe cleanup target')
            shutil.rmtree(target)
        cls.addClassCleanup(cleanup)
        cls.context = contract.source_snapshot(cls.folder/'assembly')
        cls.snap = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__,None,None,None)
        cls.manifest = contract.template('private/test_runs/pc07_status_portrait_test/diagnostic.sfc')

    def test_exact_guard_original_assets_and_complete_inverse(self):
        result = guard.audit_pc07_status_portrait_images(self.manifest,self.snap['source'],self.snap['target'])
        self.assertTrue(result['complete_diff_coverage'])
        self.assertTrue(result['inverse_restores_parent'])
        self.assertTrue(result['original_seven_portraits_palettes_and_tables_unchanged'])
        self.assertTrue(result['canonical_game_data_including_unused_unchanged'])
        self.assertEqual(result['canonical_instruction_hook_bytes'],10)
        self.assertEqual(result['declared_sections'],9)

    def test_every_other_asset_and_manifest_authority_refuse(self):
        for at in (0x3F0000,0x3F1F80,0x3FCE50,0x3FCE70,0x02E44D,0x02D1C1,0x19E2CE,0x240C00,
                   0x161EF,0x02EC42,0x02EC91,0x420000,0x423000,0x480400,0x490000,0x4A01FF,
                   0x4A1000,0x4A1480,0x4A14A0,0x4A14A6,0x500000):
            target = bytearray(self.snap['target']); target[at] ^= 1
            with self.subTest(at=hex(at)),self.assertRaises(ValueError):
                guard.audit_pc07_status_portrait_images(self.manifest,self.snap['source'],bytes(target))
        for key,value in (('production_approval',True),('native_execution',True),('name_width',5),
                          ('dynamic_first_slot_ids',[7]),('save_preview_unchanged',False)):
            manifest = copy.deepcopy(self.manifest); manifest[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                guard.validate_pc07_status_portrait_manifest(manifest)
        source = bytearray(self.snap['source']); source[0x490100] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_status_portrait_images(self.manifest,bytes(source),self.snap['target'])
        for path in ('diagnostic.sfc','private/test_runs/pc07_status_portrait_test/../diagnostic.sfc',
                     'private/test_runs/pc07_status_portrait_test/subdir/diagnostic.sfc'):
            with self.assertRaises(ValueError): contract.output_path(path)


if __name__ == '__main__':
    unittest.main()
