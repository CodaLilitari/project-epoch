"""Pure bounded append to the accepted112-tile/30-record PC07 provider.

The first30 records include physical left mirrors that can extend outside the
48px authoring canvas. Compare those in physical coordinates rather than
clipping or moving them. No file/ROM access, binding, or allocation authority.
"""
import struct
import native_pc07_pose_codec_v1 as base
from native_pc07_pose_mirror_v1 import decode_physical_pixels


def append_frames(graphics, assembly, candidates):
    base.need(type(graphics) is bytes and len(graphics) == 112*32, "exact112tile source prefix")
    base.need(type(assembly) is bytes and len(assembly) == 30*40, "exact30record source prefix")
    pool = [base.decode_tile(graphics[i:i+32]) for i in range(0,len(graphics),32)]
    records = [assembly[i:i+40] for i in range(0,len(assembly),40)]
    baseline = [decode_physical_pixels(graphics,r) for r in records]
    report = []
    for candidate in candidates:
        rows = candidate["rows"]
        base.need(type(rows) is list and len(rows) == 48 and all(type(r) is list and len(r) == 48 for r in rows)
                  and all(type(v) is int and 0 <= v <= 12 for r in rows for v in r), "indexed48x48 palette13")
        expected = {(x-16,y-40):v for y,row in enumerate(rows) for x,v in enumerate(row) if v}
        same = [i for i,pixels in enumerate(baseline) if pixels == expected]
        if same:
            report.append({"role":candidate["role"],"frame_id":same[0],"reused_existing_record":True})
            continue
        options = []
        for record in records[:30]:
            pieces = [(x+16,y+40) for x,y in base.xy(record)]
            if base.covers(rows,pieces): options.append(pieces)
        preferred = candidate.get("preferred_cover")
        if preferred and base.covers(rows,preferred): options.append(preferred)
        cover = base.four_piece_cover(rows)
        base.need(cover is not None,"not coverable by four16x16 pieces")
        options.append(cover)
        def cost(pieces):
            available = set(pool); extra = set()
            for tile in base.piece_tiles(rows,pieces):
                if tile not in available: extra.add(tile)
            return len(extra),len(pieces),tuple(tuple(p) for p in pieces)
        pieces = min(options,key=cost); tile_before = len(pool); words = [0]*16; coords = []
        for p in range(4):
            point = pieces[p:p+1] if p < len(pieces) else [(0,0)]
            tiles = base.piece_tiles(rows,point) if p < len(pieces) else [(0,)*64]*4
            coords.extend((point[0][0]-16,point[0][1]-40))
            for tile,at in zip(tiles,(2*p,2*p+1,8+2*p,9+2*p)):
                if tile in pool: index = pool.index(tile)
                else: index = len(pool); pool.append(tile)
                base.need(index < 128,"graphics append reaches occupied assembly at421000")
                words[at] = index
        record = struct.pack('<16H8b',*words,*coords)
        encoded = b''.join(base.encode_tile(tile) for tile in pool)
        base.need(decode_physical_pixels(encoded,record) == expected,"native physical pixel roundtrip")
        frame_id = len(records); records.append(record)
        report.append({"role":candidate["role"],"frame_id":frame_id,"reused_existing_record":False,
                       "piece_top_left_on_canvas":pieces,"tile_words":words,"record_hex":record.hex(),
                       "appended_tile_ids":list(range(tile_before,len(pool))),"native_pixel_equality":True,
                       "indices_sha256":base.sha(bytes(v for row in rows for v in row))})
    newgfx = b''.join(base.encode_tile(tile) for tile in pool); newasm = b''.join(records)
    base.need(newgfx[:len(graphics)] == graphics and newasm[:len(assembly)] == assembly,"existing prefix changed")
    return newgfx,newasm,report
