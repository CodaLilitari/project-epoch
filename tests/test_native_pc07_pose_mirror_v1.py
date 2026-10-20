"""Original synthetic mirror checks, no ROM or art inputs."""
import struct
import unittest
from tools import native_pc07_pose_mirror_v1 as mirror

class MirrorTests(unittest.TestCase):
    def record(self,coords,words=None):return struct.pack('<16H8b',*(words or list(range(16))),*coords)
    def test_swaps_each_tile_row_and_inverts_flip_once(self):
        words=[n|(0x4000 if n%3==0 else 0)for n in range(16)]
        raw=self.record([0,-32,-16,-32,0,-16,-16,-16],words)
        other=mirror.mirror_record(raw)
        actual=struct.unpack('<16H8b',other)
        self.assertEqual(list(actual[:16]),[words[n^1]^0x4000 for n in range(16)])
        self.assertEqual(actual[16:],(-16,-32,0,-32,-16,-16,0,-16))
        self.assertEqual(mirror.mirror_record(other),raw)
    def test_native_signed_coordinate_boundaries(self):
        raw=self.record([-128,-128,112,127,0,0,-1,1])
        self.assertEqual(struct.unpack('<8b',mirror.mirror_record(raw)[32:]),(112,-128,-128,127,-16,0,-15,1))
        with self.assertRaises(ValueError):mirror.mirror_record(self.record([113,0,0,0,0,0,0,0]))
    def test_physical_pixels_reflect_without_recentering(self):
        # Tile0 has left-edge plane0 pixel; tile1 has right-edge plane1 pixel.
        graphics=bytearray(64);graphics[0]=0x80;graphics[33]=1
        words=[0]*16;words[0]=1
        record=self.record([0,-20,-16,-20,0,-4,-16,-4],words)
        before=mirror.decode_physical_pixels(graphics,record)
        after=mirror.decode_physical_pixels(graphics,mirror.mirror_record(record))
        self.assertEqual(after,{(-1-x,y):v for (x,y),v in before.items()})
    def test_canvas_never_silently_clips(self):
        self.assertEqual(mirror.physical_to_canvas({(-32,-40):7})[0][0],7)
        with self.assertRaises(ValueError):mirror.physical_to_canvas({(-33,-40):7})
    def test_unknown_flags_refuse(self):
        words=[0]*16;words[3]=0x8000
        with self.assertRaises(ValueError):mirror.mirror_record(self.record([0]*8,words))

if __name__=='__main__':unittest.main()
