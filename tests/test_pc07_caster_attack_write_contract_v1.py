"""Focused new caster boundaries; no historical builds or broad old suites."""
import copy,shutil,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_pc07_caster_pose_codec_v1 as codec
import native_pc07_pose_codec_v1 as base
import pc07_caster_attack_write_contract_v1 as contract
import validate_rom_write_intents as guard

class CasterPoseCodecTests(unittest.TestCase):
    def setUp(self):
        tile=[0]*64;tile[0]=3
        self.graphics=b'\0'*32+base.encode_tile(tile)+b'\0'*(110*32)
        blank=struct.pack('<16H8b',*([0]*16),*([0]*8))
        # Existing left-facing assembly may render outside the author canvas.
        outside=struct.pack('<16H8b',*([1]+[0]*15),-40,-40,0,0,0,0,0,0)
        self.assembly=blank*29+outside
        self.rows=[[0]*48 for _ in range(48)];self.rows[24][16]=3

    def test_unclipped_existing_physical_mirror_and_exact_prefix(self):
        gfx,assembly,report=codec.append_frames(self.graphics,self.assembly,[{'role':'front','rows':self.rows}])
        self.assertEqual(gfx[:len(self.graphics)],self.graphics)
        self.assertEqual(assembly[:len(self.assembly)],self.assembly)
        self.assertEqual(report[0]['frame_id'],30)
        self.assertTrue(report[0]['native_pixel_equality'])

    def test_invalid_palette_and_shape_refuse(self):
        for rows in ([row[:]for row in self.rows[:-1]],[[0]*47 for _ in range(48)]):
            with self.assertRaises(ValueError):codec.append_frames(self.graphics,self.assembly,[{'role':'bad','rows':rows}])
        rows=copy.deepcopy(self.rows);rows[24][16]=13
        with self.assertRaises(ValueError):codec.append_frames(self.graphics,self.assembly,[{'role':'bad','rows':rows}])

    def test_wrong_baseline_extent_refuses(self):
        with self.assertRaises(ValueError):codec.append_frames(self.graphics[:-32],self.assembly,[])
        with self.assertRaises(ValueError):codec.append_frames(self.graphics,self.assembly[:-40],[])

class CasterAttackContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not(contract.ROOT/contract.SOURCE['path']).is_file():
            raise unittest.SkipTest('private current image is not distributed')
        parent=(contract.ROOT/'private/test_runs').resolve()
        cls.temporary=Path(tempfile.mkdtemp(prefix='pc07_caster_attack_unit_',dir=parent)).resolve()
        if cls.temporary.parent!=parent:raise ValueError('private test directory required')
        def cleanup():
            target=cls.temporary.resolve()
            if target.parent!=parent or not target.name.startswith('pc07_caster_attack_unit_'):raise ValueError('unsafe cleanup target')
            shutil.rmtree(target)
        cls.addClassCleanup(cleanup)
        cls.context=contract.source_snapshot(cls.temporary/'assembly');cls.snap=cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__,None,None,None)
        cls.manifest=contract.template('private/test_runs/pc07_caster_attack_test/diagnostic.sfc')

    def test_guarded_exact_append_and_preserved_consumers(self):
        result=guard.audit_pc07_caster_attack_images(self.manifest,self.snap['source'],self.snap['target'])
        self.assertTrue(result['inverse_restores_parent']);self.assertTrue(result['inherited_KO_helpers_unchanged'])
        self.assertEqual(result['original_frame_prefix_preserved'],30)
        self.assertEqual(self.snap['streams']['entrypoints_checked'],1024)
        self.assertEqual(self.snap['streams']['changed_directional_entries'],5)
        self.assertTrue(self.snap['streams']['timing_unchanged'])
        self.assertFalse(self.manifest['impact_sound_hook'])
        for facing in range(4):
            start=contract.PRIMARY+facing*contract.STRIDE
            for selector in (0,1,3,5,6,7,8,0x0E,0x17,0x26,0xF0):
                self.assertEqual(contract.tokens(self.snap['source'][start:start+contract.STRIDE],selector,255),
                                 contract.tokens(self.snap['target'][start:start+contract.STRIDE],selector,255))

    def test_extra_worldmap_NPC_legacy_art_KO_and_unneeded_sound_hook_changes_refuse(self):
        for at in (0x19E2CE,0x240C00,0x420000,0x421000,0x421498,0x4251C4,0x480400,0x490000,0x490170,0x161F9,0x500000):
            with self.subTest(at=hex(at)):
                target=bytearray(self.snap['target']);target[at]^=1
                with self.assertRaises(ValueError):guard.audit_pc07_caster_attack_images(self.manifest,self.snap['source'],bytes(target))

    def test_forged_scope_and_source_refuse(self):
        for key,value in (('production_approval',True),('native_execution',True),('impact_sound_hook',True),
                          ('qualified_normal_path_package',0),('sections',self.manifest['sections']+[{'id':'extra'}])):
            manifest=copy.deepcopy(self.manifest);manifest[key]=value
            with self.assertRaises(ValueError):guard.validate_pc07_caster_attack_manifest(manifest)
        source=bytearray(self.snap['source']);source[0x480400]^=1
        with self.assertRaises(ValueError):guard.audit_pc07_caster_attack_images(self.manifest,bytes(source),self.snap['target'])

    def test_reached_stream_or_timing_mutation_refuses(self):
        for at in (contract.PRIMARY+7*4,contract.PRIMARY+9*4,contract.TIMING+0x31*4):
            target=bytearray(self.snap['target']);target[at]^=1
            with self.assertRaises(ValueError):contract.stream_audit(self.snap['source'],bytes(target))

    def test_output_escape_refuses(self):
        for path in ('diagnostic.sfc','private/test_runs/pc07_caster_attack_test/../diagnostic.sfc',
                     'private/test_runs/pc07_caster_attack_test/link/diagnostic.sfc'):
            with self.assertRaises(ValueError):contract.output_path(path)

if __name__=='__main__':unittest.main()
