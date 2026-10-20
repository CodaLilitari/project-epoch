"""Original source-safe pure native PC07 pose codec. No paths, files, ROMs or art.
Four-piece coverage algorithm copied from Coda engineering validator v1.
Exact original prefixes are inputs and remain byte-identical; new records use
no horizontal-flip flag. Capacity128 is a caller's bounded region ceiling.
"""
from functools import lru_cache
import hashlib
import struct
SIZE=48
GFX_SIZE=79*32
ASM_SIZE=23*40
GFX_START=0x420000
ASM_START=0x421000

def four_piece_cover(rows: list[list[int]]) -> list[tuple[int, int]] | None:
    """Exact <=4 axis-aligned 16x16 cover of opaque pixels on a 48x48 cell.

    Pick the topmost/leftmost uncovered pixel. A square covering it can be
    slid down to that row (clamped to y=32) without losing any uncovered pixel
    above it, because none exists. Enumerate all at-most-16 legal x origins.
    Repeating this yields a complete search, not a bbox heuristic. Squares may
    overlap; identical underlying pixel colors make reconstruction unambiguous.
    """
    occupied = sum(1 << (y * SIZE + x) for y, row in enumerate(rows)
                   for x, value in enumerate(row) if value)

    @lru_cache(maxsize=None)
    def mask(x: int, y: int) -> int:
        return sum(((1 << 16) - 1) << ((y + dy) * SIZE + x)
                   for dy in range(16))

    @lru_cache(maxsize=None)
    def search(left: int, budget: int):
        if not left:
            return ()
        if not budget or left.bit_count() > 256 * budget:
            return None
        first = (left & -left).bit_length() - 1
        y, x = divmod(first, SIZE)
        oy = min(y, SIZE - 16)
        choices = [(ox, mask(ox, oy))
                   for ox in range(max(0, x - 15), min(x, SIZE - 16) + 1)]
        choices.sort(key=lambda pair: -(left & pair[1]).bit_count())
        seen = set()
        for ox, square in choices:
            remaining = left & ~square
            if remaining in seen:
                continue
            seen.add(remaining)
            tail = search(remaining, budget - 1)
            if tail is not None:
                return ((ox, oy),) + tail
        return None

    found = search(occupied, 4)
    return None if found is None else list(found)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def need(test,message):
    if not test: raise ValueError(message)

def decode_tile(raw):
    need(len(raw)==32,'32-byte 4bpp tile required')
    return tuple(sum(((raw[(p//2)*16+y*2+p%2]>>(7-x))&1)<<p for p in range(4))
                 for y in range(8) for x in range(8))

def encode_tile(pixels):
    need(len(pixels)==64 and all(type(v)is int and 0<=v<16 for v in pixels),'64 valid indices required')
    raw=bytearray(32)
    for y in range(8):
        for x in range(8):
            for p in range(4): raw[(p//2)*16+y*2+p%2] |= ((pixels[y*8+x]>>p)&1)<<(7-x)
    return bytes(raw)

def hflip(tile): return tuple(tile[y*8+7-x] for y in range(8) for x in range(8))

def xy(record): return list(zip(*[iter(struct.unpack('<8b',record[32:40]))]*2))

def decode_record(graphics,record):
    """Literal native tile/coordinate layout, rendered onto fixed author canvas."""
    need(len(record)==40 and len(graphics)%32==0,'native component geometry')
    rows=[[0]*48 for _ in range(48)]
    words=struct.unpack('<16H',record[:32])
    for p,(ox,oy) in enumerate(xy(record)):
        for at,dx,dy in ((2*p,0,0),(2*p+1,8,0),(8+2*p,0,8),(9+2*p,8,8)):
            w=words[at];need(w&0xB800==0,'unsupported native tile flag')
            index=w&0x7FF;need((index+1)*32<=len(graphics),'tile outside payload')
            tile=decode_tile(graphics[index*32:(index+1)*32])
            if w&0x4000:tile=hflip(tile)
            for y in range(8):
                for x in range(8):
                    v=tile[y*8+x]
                    if v:
                        ax,ay=ox+16+dx+x,oy+40+dy+y
                        need(0<=ax<48 and 0<=ay<48,'opaque pixel outside fixed author canvas')
                        rows[ay][ax]=v
    return rows

def covers(rows,pieces):
    return len(pieces)<=4 and all(any(ox<=x<ox+16 and oy<=y<oy+16 for ox,oy in pieces)
                                for y,row in enumerate(rows)for x,v in enumerate(row)if v)

def piece_tiles(rows,pieces):
    out=[]
    for ox,oy in pieces:
        need(-128<=ox-16<=127 and -128<=oy-40<=127,'signed native coordinate')
        for dx,dy in ((0,0),(8,0),(0,8),(8,8)):
            out.append(tuple(rows[y][x]if 0<=x<48 and 0<=y<48 else 0
                             for y in range(oy+dy,oy+dy+8) for x in range(ox+dx,ox+dx+8)))
    return out

def append_frames(graphics,assembly,candidates):
    """Pure function returning preserved-prefix components and exact report.

    Bounded allocation ceiling128 comes from next occupied assembly at421000,
    not a general engine tile capacity or approval to consume the gap.
    """
    need(len(graphics)==GFX_SIZE and len(assembly)==ASM_SIZE,'exact installed23frame79tile prefixes')
    pool=[decode_tile(graphics[i:i+32])for i in range(0,len(graphics),32)]
    records=[assembly[i:i+40]for i in range(0,len(assembly),40)]
    baseline=[decode_record(graphics,r)for r in records]
    report=[]
    for c in candidates:
        rows=c['rows'];same=[i for i,r in enumerate(baseline)if r==rows]
        if same:
            report.append({k:c[k]for k in ('author','source_index','role')}|{'frame_id':same[0],'reused_existing_record':True})
            continue
        options=[]
        for r in records[:23]:
            pieces=[(x+16,y+40)for x,y in xy(r)]
            if covers(rows,pieces):options.append(pieces)
        if c.get('preferred_cover') and covers(rows,c['preferred_cover']):options.append(c['preferred_cover'])
        found=four_piece_cover(rows)
        need(found is not None,'not representable by four native16x16pieces')
        options.append(found)
        def cost(pieces):
            extra=set();available=set(pool)
            for t in piece_tiles(rows,pieces):
                if t not in available and t not in extra:extra.add(t)
            return len(extra),len(pieces),tuple(tuple(p)for p in pieces)
        pieces=min(options,key=cost)
        tile_before=len(pool);words=[0]*16;coords=[]
        # Empty padded pieces use transparent pixels; coordinates are explicit.
        for p in range(4):
            pts=pieces[p:p+1] if p<len(pieces) else [(0,0)]
            tiles=piece_tiles(rows,pts)if p<len(pieces)else [(0,)*64]*4
            coords.extend([pts[0][0]-16,pts[0][1]-40])
            for t,at in zip(tiles,(2*p,2*p+1,8+2*p,9+2*p)):
                if t in pool:word=pool.index(t)
                else:word=len(pool);pool.append(t)
                need(word&0x7FF<128,'named graphics region reaches next assembly allocation')
                words[at]=word
        record=struct.pack('<16H8b',*words,*coords)
        new_graphics=b''.join(encode_tile(t)for t in pool)
        need(decode_record(new_graphics,record)==rows,'actual native4bpp/record roundtrip mismatch')
        frame_id=len(records);records.append(record)
        distances=sorted((sum(a!=b for old,new in zip(frame,rows)for a,b in zip(old,new)),i)for i,frame in enumerate(baseline))
        report.append({k:c[k]for k in ('author','source_index','role')}|{
            'frame_id':frame_id,'reused_existing_record':False,'piece_top_left_on_canvas':pieces,
            'piece_offsets_from_origin':list(xy(record)),'tile_words':words,'record_hex':record.hex(),
            'assembly_file_start':ASM_START+frame_id*40,'assembly_file_end_exclusive':ASM_START+(frame_id+1)*40,
            'appended_tile_ids':list(range(tile_before,len(pool))),'minimum_installed_pixel_difference':distances[0][0],
            'nearest_installed_frame':distances[0][1],'native_pixel_equality':True,
            'candidate_index_sha256':sha(bytes(v for row in rows for v in row))})
    output_graphics=b''.join(encode_tile(t)for t in pool);output_assembly=b''.join(records)
    need(output_graphics[:GFX_SIZE]==graphics and output_assembly[:ASM_SIZE]==assembly,'old bytes not preserved')
    return output_graphics,output_assembly,report
