"""Native48x48 portrait encoding from honestly attributed indexed art.

No image generation, resizing, palette selection or ROM mutation occurs here.
The imported indexed source remains the separately reviewed creative artifact.
"""
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encode(document):
    require(type(document) is dict and document.get('schema') in
            ('epoch-private-schala-portrait-native-candidate-v1',
             'epoch-private-portrait-semantic-palette-candidate-v1'), 'native candidate schema')
    require(document.get('dimensions') == [48, 48] and document.get('tiles') == [6, 6]
            and document.get('tile_count') == 36 and document.get('packed_bytes') == 1152
            and document.get('palette_bytes') == 32 and document.get('palette_entries') == 16,
            'exact native full-portrait geometry')
    require(document.get('transparent_index') == 0, 'native transparent index zero')
    rows = document.get('pixel_rows_hex')
    require(type(rows) is list and len(rows) == 48 and all(type(row) is str and len(row) == 48
            and all(value in '0123456789abcdefABCDEF' for value in row) for row in rows), '48 indexed rows')
    pixels = [[int(value, 16) for value in row] for row in rows]
    palette = document.get('palette_bgr555')
    require(type(palette) is list and len(palette) == 16 and all(type(value) is int and
            0 <= value < 0x8000 for value in palette), '16 BGR555 palette words')
    require(palette[0] == 0, 'reserved index0 is black')
    tiles = bytearray()
    for ty in range(6):
        for tx in range(6):
            tile = bytearray(32)
            for y in range(8):
                for x in range(8):
                    value = pixels[ty*8+y][tx*8+x]
                    for bit in range(4):
                        offset = (bit//2)*16 + y*2 + bit%2
                        tile[offset] |= ((value >> bit) & 1) << (7-x)
            tiles.extend(tile)
    packed_palette = struct.pack('<16H', *palette)
    require(decode(bytes(tiles)) == pixels, 'native planar roundtrip')
    return bytes(tiles), packed_palette


def decode(tiles):
    require(type(tiles) is bytes and len(tiles) == 1152, '36 complete4bpp tiles')
    rows = [[0]*48 for _ in range(48)]
    for tile_id in range(36):
        tile = tiles[tile_id*32:(tile_id+1)*32]
        tx, ty = tile_id % 6, tile_id // 6
        for y in range(8):
            for x in range(8):
                rows[ty*8+y][tx*8+x] = sum(((tile[(bit//2)*16+y*2+bit%2] >> (7-x)) & 1) << bit
                                            for bit in range(4))
    return rows
