"""Pure source-safe native sprite reflection; no file access or embedded art.

Reflect physical pixels around x=-0.5 relative to the existing native origin.
Each 16x16 piece moves from ox to -16-ox; each tile row swaps left/right
words and toggles native horizontal-flip bit4000. No graphics bytes change.
"""
import struct

def require(test, message):
    if not test:
        raise ValueError(message)

def mirror_record(record):
    require(isinstance(record, bytes) and len(record)==40, 'exact40byte assembly record required')
    words=list(struct.unpack('<16H',record[:32]))
    require(all(w&0xB800==0 for w in words), 'unsupported native tile flags')
    coords=list(struct.unpack('<8b',record[32:]))
    transformed=words.copy()
    for piece in range(4):
        ox=coords[piece*2]
        reflected=-16-ox
        require(-(1<<31)<=reflected<(1<<31), 'intermediate signed32 range')
        require(-128<=reflected<=127, 'reflected native signed-byte offset out of range')
        coords[piece*2]=reflected
        for left,right in ((piece*2,piece*2+1),(8+piece*2,9+piece*2)):
            transformed[left]=words[right]^0x4000
            transformed[right]=words[left]^0x4000
    return struct.pack('<16H8b',*transformed,*coords)

def decode_physical_pixels(graphics,record):
    """Literal independent native decoder returning unbounded physical XY map.

    Origin/canvas are deliberately absent; transparent pixels don't overwrite.
    Source-over ordering follows the four physical pieces, then four tile words.
    """
    require(len(graphics)%32==0 and len(record)==40,'native component geometry')
    words=struct.unpack('<16H',record[:32])
    coords=struct.unpack('<8b',record[32:])
    pixels={}
    for p in range(4):
        ox,oy=coords[p*2:p*2+2]
        for word_index,dx,dy in ((2*p,0,0),(2*p+1,8,0),(8+2*p,0,8),(9+2*p,8,8)):
            word=words[word_index]
            require(word&0xB800==0,'unsupported native tile flag')
            start=(word&0x7FF)*32
            require(start+32<=len(graphics),'tile index exceeds graphics payload')
            for y in range(8):
                for x in range(8):
                    source_x=7-x if word&0x4000 else x
                    index=sum(((graphics[start+(plane//2)*16+y*2+plane%2]>>(7-source_x))&1)<<plane for plane in range(4))
                    if index:
                        pixels[ox+dx+x,oy+dy+y]=index
    return pixels

def physical_to_canvas(pixels, size=(64,64), origin=(32,40)):
    """Diagnostic canvas only: refuse clipping instead of moving the sprite."""
    width,height=size
    require(width>0 and height>0,'positive diagnostic dimensions')
    rows=[[0]*width for _ in range(height)]
    for (x,y),index in pixels.items():
        cx,cy=x+origin[0],y+origin[1]
        require(0<=cx<width and 0<=cy<height,'physical pixel outside diagnostic canvas')
        rows[cy][cx]=index
    return rows

def append_mirrored_records(graphics,assembly,source_ids=(23,24,25)):
    """Append exact reflections only; caller supplies unchanged graphics bytes."""
    require(isinstance(graphics,bytes) and isinstance(assembly,bytes),'immutable component bytes required')
    require(len(assembly)%40==0 and len(graphics)%32==0,'native component lengths')
    count=len(assembly)//40
    require(all(type(i)is int and 0<=i<count for i in source_ids),'valid existing frame IDs required')
    require(len(set(source_ids))==len(source_ids),'duplicate source frame IDs refused')
    output=bytearray(assembly);report=[]
    for source_id in source_ids:
        record=assembly[source_id*40:(source_id+1)*40]
        reflected=mirror_record(record)
        source_pixels=decode_physical_pixels(graphics,record)
        actual_pixels=decode_physical_pixels(graphics,reflected)
        expected_pixels={(-1-x,y):value for (x,y),value in source_pixels.items()}
        require(actual_pixels==expected_pixels,'physical reflection mismatch')
        require(mirror_record(reflected)==record,'reflection involution mismatch')
        # Both renders fit the explicit larger diagnostic canvas, never re-center.
        physical_to_canvas(source_pixels);physical_to_canvas(actual_pixels)
        new_id=len(output)//40;output.extend(reflected)
        report.append({'source_frame':source_id,'new_frame':new_id,'record_hex':reflected.hex(),
                       'native_piece_offsets':list(zip(*[iter(struct.unpack('<8b',reflected[32:]))]*2)),
                       'tile_words':list(struct.unpack('<16H',reflected[:32])),
                       'opaque_pixels':len(actual_pixels),'physical_reflection_equal':True,
                       'double_reflection_record_equal':True})
    require(bytes(output[:len(assembly)])==assembly,'assembly prefix changed')
    return bytes(output),report
