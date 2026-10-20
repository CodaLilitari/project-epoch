"""Independent fixed-grammar encoder for the menu-recompute gate only."""
import re
BASE = 0x4A0400
RESERVATION = 0x40
SIMPLE = {'php':0x08,'pha':0x48,'pla':0x68,'plp':0x28,'clc':0x18,'rtl':0x6B}
IMM = {'rep':(0xC2,1),'sep':(0xE2,1),'cmp.b':(0xC9,1),'cmp.w':(0xC9,2)}
def encode(source):
    labels, ops, offset = {}, [], 0
    root_seen = False
    for raw in source.splitlines():
        line = raw.split(';',1)[0].strip()
        if not line: continue
        if line == 'Pc07MenuRecomputeGateV1:':
            if root_seen: raise ValueError('duplicate root')
            root_seen = True
            continue
        if not root_seen: raise ValueError('source outside exact helper')
        if line.startswith('.') and ' ' not in line:
            if line in labels: raise ValueError('duplicate local label')
            labels[line] = offset
            continue
        op, _, arg = line.partition(' ')
        if op in SIMPLE and not arg: data = bytes([SIMPLE[op]])
        elif op == 'bne': data = bytes([0xD0,0])
        elif op == 'lda.b' and arg == '$02': data = bytes([0xA5,0x02])
        elif op == 'lda.l' and arg == '$7E2830': data = bytes.fromhex('AF30287E')
        elif op in IMM and re.fullmatch(r'#\$[0-9A-F]+',arg):
            opcode,width=IMM[op]
            data=bytes([opcode])+int(arg[2:],16).to_bytes(width,'little')
        else: raise ValueError('unknown authored instruction: '+line)
        ops.append((offset,op,arg,data,line)); offset += len(data)
    if not root_seen or not 0 < offset <= RESERVATION: raise ValueError('invalid extent')
    data,ins=bytearray(),[]
    for offset,op,arg,raw,line in ops:
        if op == 'bne': raw=raw[:1]+(labels[arg]-offset-2).to_bytes(1,'little',signed=True)
        data.extend(raw); ins.append({'cpu':BASE+offset,'bytes':raw.hex(),'source':line})
    return {'cpu_start':BASE,'data':bytes(data),'instructions':ins,'source':source}
