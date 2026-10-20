"""Pure sparse-tile append for the accepted 122-tile/32-frame PC07 provider.

No file access or allocation authority. New tile IDs begin at 0x180, leaving
the occupied assembly and intervening bytes outside the tile pool entirely.
"""
import struct
import native_pc07_pose_codec_v1 as base
from native_pc07_pose_mirror_v1 import decode_physical_pixels

OLD_TILES = 122
OLD_FRAMES = 32
FIRST_NEW_TILE = 0x180
NEW_TILE_LIMIT = 0x200


def decode_sparse(old_graphics, new_graphics, record):
    """Validate all word ownership before using the independent native decoder."""
    base.need(len(old_graphics) == OLD_TILES * 32 and len(new_graphics) % 32 == 0,
              'exact old pool and complete new tiles')
    count = len(new_graphics) // 32
    base.need(FIRST_NEW_TILE + count <= NEW_TILE_LIMIT, 'sparse tile ceiling')
    for word in struct.unpack('<16H', record[:32]):
        index = word & 0x7FF
        base.need(word & 0xB800 == 0, 'unsupported native tile flags')
        base.need(index < OLD_TILES or FIRST_NEW_TILE <= index < FIRST_NEW_TILE + count,
                  'record references unowned sparse gap')
    # This ephemeral decode buffer is not an image or emission payload. Every
    # reference into its padding was refused above; only two owned pools exist.
    canvas = old_graphics + bytes(FIRST_NEW_TILE * 32 - len(old_graphics)) + new_graphics
    return decode_physical_pixels(canvas, record)


def append_frames(graphics, assembly, candidates):
    base.need(type(graphics) is bytes and len(graphics) == OLD_TILES * 32, 'exact122tile prefix')
    base.need(type(assembly) is bytes and len(assembly) == OLD_FRAMES * 40, 'exact32record prefix')
    pool = [base.decode_tile(graphics[i:i+32]) for i in range(0, len(graphics), 32)]
    lookup = {}
    for index, tile in enumerate(pool):
        lookup.setdefault(tile, index)
    new_tiles = []
    records = [assembly[i:i+40] for i in range(0, len(assembly), 40)]
    baseline = [decode_sparse(graphics, b'', record) for record in records]
    report = []
    for candidate in candidates:
        rows = candidate['rows']
        base.need(type(rows) is list and len(rows) == 48 and
                  all(type(row) is list and len(row) == 48 for row in rows) and
                  all(type(value) is int and 0 <= value <= 12 for row in rows for value in row),
                  'indexed48x48 palette13')
        expected = {(x-16, y-40): value for y, row in enumerate(rows) for x, value in enumerate(row) if value}
        same = [i for i, pixels in enumerate(baseline) if pixels == expected]
        if same:
            report.append({'role': candidate['role'], 'frame_id': same[0], 'reused_existing_record': True})
            continue
        options = []
        for record in records:
            pieces = [(x+16, y+40) for x, y in base.xy(record)]
            if base.covers(rows, pieces):
                options.append(pieces)
        preferred = candidate.get('preferred_cover')
        if preferred and base.covers(rows, preferred):
            options.append(preferred)
        cover = base.four_piece_cover(rows)
        base.need(cover is not None, 'not coverable by four16x16 pieces')
        options.append(cover)

        def cost(pieces):
            extra = {tile for tile in base.piece_tiles(rows, pieces) if tile not in lookup}
            return len(extra), len(pieces), tuple(tuple(point) for point in pieces)

        pieces = min(options, key=cost)
        before_count = len(new_tiles)
        words, coords = [0] * 16, []
        for piece in range(4):
            point = pieces[piece:piece+1] if piece < len(pieces) else [(0, 0)]
            tiles = base.piece_tiles(rows, point) if piece < len(pieces) else [(0,) * 64] * 4
            coords.extend((point[0][0]-16, point[0][1]-40))
            for tile, at in zip(tiles, (2*piece, 2*piece+1, 8+2*piece, 9+2*piece)):
                if tile not in lookup:
                    index = FIRST_NEW_TILE + len(new_tiles)
                    base.need(index < NEW_TILE_LIMIT, 'sparse tile island reaches primary stream')
                    lookup[tile] = index
                    new_tiles.append(tile)
                words[at] = lookup[tile]
        record = struct.pack('<16H8b', *words, *coords)
        added = b''.join(base.encode_tile(tile) for tile in new_tiles)
        base.need(decode_sparse(graphics, added, record) == expected, 'native sparse physical pixel roundtrip')
        frame_id = len(records)
        records.append(record)
        report.append({'role': candidate['role'], 'frame_id': frame_id, 'reused_existing_record': False,
                       'piece_top_left_on_canvas': pieces, 'tile_words': words, 'record_hex': record.hex(),
                       'appended_tile_ids': list(range(FIRST_NEW_TILE + before_count, FIRST_NEW_TILE + len(new_tiles))),
                       'native_pixel_equality': True, 'indices_sha256': base.sha(bytes(v for row in rows for v in row))})
    new_graphics = b''.join(base.encode_tile(tile) for tile in new_tiles)
    new_assembly = b''.join(records)
    base.need(new_assembly[:len(assembly)] == assembly, 'old assembly prefix changed')
    for record in records:
        decode_sparse(graphics, new_graphics, record)
    return new_graphics, new_assembly, report
