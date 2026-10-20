"""New v2 code only. Reuses frozen v1 CPU interpreter; no native timing claim."""
import copy
import shutil
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_pc07_status_portrait_v1 import Cpu,nz
import native_pc07_status_portrait_helpers_v2 as helpers
import pc07_status_portrait_write_contract_v2 as contract
import validate_rom_write_intents as guard
ROOT=Path(__file__).resolve().parents[1]

class PortraitHelperV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components = helpers.encode((ROOT/'asm/pc07_status_portrait_v2.asm').read_text())
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
        tile, preload = role == 'Tiles', role == 'Preload'
        hook = 0xC2EC3E if tile else 0xC29751 if preload else 0xC2EC8B
        name = 'Pc07StatusPortrait'+role+'V2'
        item = self.components[name]
        a = (0xA55A if tile else 0xFFFF if preload else 31) if a is None else a
        x = (identity if tile else 0xFCA7 if preload else 0xCE50) if x is None else x
        y = (0x73 if tile else 0x0C18 if preload else 0x94E0) if y is None else y
        p = (0x7D if tile else 0x4D) if p is None else p
        memory = {0x7E0061:0xDE,0x7E0062:0x2E,0x7E0001:0x0E if tile else 0x0D,
                  0x7E0D46:identity,0x7E9A90:identity,0x7E0D11:queue,0x7E0D12:0x93,
                  0x7E0D15:0xFF,0x7E0D16:0x12}
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
        original = bytes.fromhex('bf70ceff' if tile else 'e220a918' if preload else '547effee150d')
        reference = Cpu({hook+i:v for i,v in enumerate(original)},hook,memory,a,x,y,p,d,dbr).run(hook+len(original))
        code = {item['cpu_start']+i:v for i,v in enumerate(item['data'])}
        code.update({hook+i:v for i,v in enumerate(b'\x22'+item['cpu_start'].to_bytes(3,'little'))})
        cpu = Cpu(code,hook,memory,a,x,y,p,d,dbr).run(hook+4)
        coverage = self.coverage[name]
        coverage['cases'] += 1
        coverage['instructions'].update(pc for pc in cpu.instructions if item['cpu_start'] <= pc < item['cpu_start']+len(item['data']))
        coverage['branches'].update(cpu.branches)
        common = d==0 and dbr==0x7E and memory[0x7E0061]==0xDE and memory[0x7E0062]==0x2E
        tile_ok = tile and common and memory[0x7E0001]==0x0E and identity<=7 and memory[0x7E9A90]==identity and memory[0x7E0D46]==identity and x==identity
        palette_ok = not tile and not preload and common and memory[0x7E0001]==0x0D and a==31 and x==0xCE50 and y==0x94E0 and memory[0x7E9A90]==7 and memory[0x7E0D46]==7
        preload_ok = preload and a==0xFFFF and x==0xFCA7 and y==0x0C18 and d==0 and dbr==0x7E
        expected_a,expected_p = reference.a,reference.p
        if tile_ok and identity==7:
            expected_a=(a&0xFF00)|0xB0; expected_p=nz(p,0xB0,8)
        if preload_ok:
            expected_a=(a&0xFF00)|0x20; expected_p=nz(p|0x20,0x20,8)
        self.assertEqual((cpu.a,cpu.x,cpu.y,cpu.p,cpu.s,cpu.d,cpu.dbr),
                         (expected_a,reference.x,reference.y,expected_p,reference.s,reference.d,reference.dbr))
        expected = [(at,v) for at,v,k in reference.writes if k=='data']
        if tile_ok:
            destinations=[0x7E2FAC] if identity==7 else []
            expected=[] if identity==7 else [(0x7E2FB6,0)]
            scroll=memory[0x7E0413]
            if scroll<=5:
                destinations += [base for row,base in enumerate((0x7E2EC6,0x7E3046,0x7E31C6)) if memory[0x7E0D5F+scroll+row]==7]
            expected += [(base+2*i,v) for base in destinations for i,v in enumerate(bytes.fromhex('B2BCC1BAC5BA'))]
            if identity==7: expected += [(0x7E0001,0x0D)]
        elif palette_ok:
            expected=[(0x7E0001,0x0E)]+[(0x7E94E0+i,memory[0x4A1480+i]) for i in range(32)]+[(at,v) for at,v,k in reference.writes if at in (0x7E0D15,0x7E0D16)]
        elif preload_ok:
            expected=[(0x7E0C18+i,v) for i,v in enumerate(bytes.fromhex('001b00104a800400'))]
        self.assertEqual([(at,v) for at,v,k in cpu.writes if k=='data'],expected)
        self.assertGreaterEqual(cpu.min_sp,0x6D8-11)
        allowed={at for at,v,k in cpu.writes if k=='stack'}|{at for at,v in expected}
        self.assertTrue(all(value==memory.get(at,0) for at,value in cpu.mem.items() if at not in allowed))
        self.assertEqual(cpu.read(0x7E0D11),queue) # preload publication remains original STA, no redraw queue write
        return cpu

    def test_flags_and_all_three_helpers(self):
        flags=[sum(bit for n,bit in enumerate((1,2,4,8,64,128)) if mask>>n&1) for mask in range(64)]
        for p in flags:
            for identity in (0,7): self.execute('Tiles',identity=identity,p=p|0x30)
            self.execute('Palette',p=p)
            self.execute('Preload',p=p)

    def test_character_scroll_and_context_boundaries(self):
        for identity in range(256): self.execute('Tiles',identity=identity)
        for scroll in range(256): self.execute('Tiles',changes={0x7E0413:scroll})
        for queue in (0,1,8,24,112,240,255):
            self.execute('Tiles',queue=queue)
            self.execute('Preload',queue=queue)
        for x in (0,6,8): self.execute('Tiles',x=x)
        for role in ('Tiles','Palette'):
            for at,values in ((0x7E0061,(0,0x96,0xDF)),(0x7E0062,(0,0x2F)),(0x7E0001,(0,0x16)),
                              (0x7E9A90,(0,1,6,8)),(0x7E0D46,(0,1,6,8))):
                for value in values:self.execute(role,changes={at:value})
        for role in ('Tiles','Palette','Preload'):
            for d in (1,0x1234,0xFFFF):self.execute(role,d=d)
            for dbr in (0,0x7F,0xFF):self.execute(role,dbr=dbr)

    def test_exact_preload_and_palette_qualifiers(self):
        for a in (0,1,30,32):self.execute('Palette',a=a)
        for x in (0x1FE0,0xCE4F,0xCE51):self.execute('Palette',x=x)
        for y in (0x9480,0x94C0,0x9500):self.execute('Palette',y=y)
        for a in (0,1,0xFFFE):self.execute('Preload',a=a)
        for x in (0,0xFCA6,0xFCA8):self.execute('Preload',x=x)
        for y in (0,0x0C17,0x0C19):self.execute('Preload',y=y)
        for role in ('Tiles','Palette'):self.execute(role,changes={0x7E0061:0x96,0x7E0001:0x16})

    def test_tile_word_mapping_and_temporary_attribute_restore(self):
        tile=self.execute('Tiles')
        first=(tile.read(0x7E0001)<<8)|(tile.a&255)
        self.assertEqual(first,0x0DB0)
        self.assertEqual((first&0x3FF)*16,0x1B00)
        self.assertEqual(((first+35)&0x3FF)*16+16,0x1D40)
        self.assertEqual((first>>10)&7,3)
        palette=self.execute('Palette',changes={0x7E0001:tile.read(0x7E0001)})
        self.assertEqual(palette.read(0x7E0001),0x0E)
        for identity in range(7):
            restored=self.execute('Tiles',identity=identity,changes={0x7E2FB6:0xBA,0x7E2FB7:0x10})
            self.assertEqual(restored.read(0x7E2FB6),0)
            self.assertEqual(restored.read(0x7E2FB7),0x10)


class PortraitContractV2Tests(unittest.TestCase):
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
        result = guard.audit_pc07_status_portrait_v2_images(self.manifest,self.snap['source'],self.snap['target'])
        self.assertTrue(result['complete_diff_coverage'])
        self.assertTrue(result['inverse_restores_parent'])
        self.assertTrue(result['original_seven_portraits_palettes_and_tables_unchanged'])
        self.assertTrue(result['canonical_game_data_including_unused_unchanged'])
        self.assertEqual(result['canonical_instruction_hook_bytes'],14)
        self.assertEqual(result['declared_sections'],11)

    def test_every_other_asset_and_manifest_authority_refuse(self):
        for at in (0x3F0000,0x3F1F80,0x3FCE50,0x3FCE70,0x02E44D,0x02D1C1,0x19E2CE,0x240C00,
                   0x161EF,0x02EC42,0x02EC91,0x420000,0x423000,0x480400,0x490000,0x4A01FF,
                   0x4A1000,0x4A1480,0x4A14A0,0x4A14A6,0x500000):
            target = bytearray(self.snap['target']); target[at] ^= 1
            with self.subTest(at=hex(at)),self.assertRaises(ValueError):
                guard.audit_pc07_status_portrait_v2_images(self.manifest,self.snap['source'],bytes(target))
        for key,value in (('production_approval',True),('native_execution',True),('name_width',5),
                          ('dynamic_first_slot_ids',[7]),('save_preview_unchanged',False)):
            manifest = copy.deepcopy(self.manifest); manifest[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                guard.validate_pc07_status_portrait_v2_manifest(manifest)
        source = bytearray(self.snap['source']); source[0x490100] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_status_portrait_v2_images(self.manifest,bytes(source),self.snap['target'])
        for path in ('diagnostic.sfc','private/test_runs/pc07_status_portrait_test/../diagnostic.sfc',
                     'private/test_runs/pc07_status_portrait_test/subdir/diagnostic.sfc'):
            with self.assertRaises(ValueError): contract.output_path(path)


if __name__ == '__main__':
    unittest.main()
