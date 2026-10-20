"""Focused original synthetic checks; no game/art/ROM inputs."""
import struct
import unittest
from tools import native_pc07_pose_codec_v1 as codec

class NativePoseCodecTests(unittest.TestCase):
    def setUp(self):
        self.graphics=bytes(codec.GFX_SIZE)
        self.assembly=bytes(codec.ASM_SIZE)

    def candidate(self,rows):
        return {'author':'synthetic','source_index':0,'role':'test','rows':rows}

    def test_pixels_preserve_prefix_and_use_unflipped_append(self):
        rows=[[0]*48 for _ in range(48)]
        for y in range(11,38):
            for x in range(9,25):rows[y][x]=(x+2*y)%12+1
        g,a,r=codec.append_frames(self.graphics,self.assembly,[self.candidate(rows)])
        self.assertEqual(g[:codec.GFX_SIZE],self.graphics)
        self.assertEqual(a[:codec.ASM_SIZE],self.assembly)
        self.assertEqual(codec.decode_record(g,a[-40:]),rows)
        self.assertTrue(all(w<128 for w in r[0]['tile_words']))

    def test_exact_existing_pixels_reuse_record(self):
        rows=[[0]*48 for _ in range(48)]
        g,a,r=codec.append_frames(self.graphics,self.assembly,[self.candidate(rows)])
        self.assertEqual((g,a),(self.graphics,self.assembly))
        self.assertTrue(r[0]['reused_existing_record'])

    def test_flags_and_tile_bounds_fail_closed(self):
        for word in (0x0800,0x8000,79):
            record=struct.pack('<16H8b',word,*([0]*15),*([0]*8))
            with self.assertRaises(ValueError):codec.decode_record(self.graphics,record)

    def test_wrong_installed_prefix_size_refuses(self):
        with self.assertRaises(ValueError):codec.append_frames(self.graphics[:-1],self.assembly,[])

    def test_geometry_tall_accepts_dense_refuses(self):
        tall=[[1]+[0]*47 for _ in range(48)]
        self.assertLessEqual(len(codec.four_piece_cover(tall)),4)
        with self.assertRaises(ValueError):codec.append_frames(self.graphics,self.assembly,[self.candidate([[1]*48 for _ in range(48)])])

if __name__=='__main__':unittest.main()
