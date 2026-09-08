"""Read-only, conditional normal-NMI prefix and mode-index input audit.

This is a bounded symbolic register-byte model of one reviewed prefix. It
does not execute a selected mode body or certify a complete legal mode domain.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_package_normal_nmi_closure_v2 as closure

ROOT=Path(__file__).resolve().parents[1]
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
PRIOR_SHA='413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242'
SPANS=(
    ('normal-prefix',0xD1E77C,0xD1E7DE,'6f17d51f6f079348d1ead69e09bc1bb9170276964404822dcf4b60fdaac04173'),
    ('reviewed-mode-cells',0xCD0C83,0xCD0C89,'08b70c44234ab89a1d4d433cd397c304224d9b463dbe59be9ccdf257e21e8726'),
    ('occupied-following-wrapper',0xCD0C89,0xCD0C95,'659a8a28fd2a6955a6d2c7f84e919a344f34990dd81ecf7214059e0434fcf89f'),
    ('mode-dispatcher',0xCD0C95,0xCD0C9D,'ef7128b199049373d36aac5b3e2aeb852edbf0e0e04eea2f5ef7b1c1b3c69a0d'),
)


def require(condition,message):
    if not condition:raise ValueError(message)


def byte(value,name):require(type(value) is int and 0<=value<=255,'exact byte '+name)


def index_contract(mode:int,hidden_b:int=0):
    byte(mode,'mode');byte(hidden_b,'hidden B')
    index=(hidden_b<<8)|((mode<<1)&255)
    low=(0x0C83+index)&65535
    return {'mode':mode,'hidden_b':hidden_b,'x':index,
        'pointer_byte_addresses':[0xCD0000|low,0xCD0000|((low+1)&65535)],
        'mode_reachability_proved':False}


def prefix(read,*,entry=0xD1E77C,end=0xD1E7DE,call=0xD1E7DA,
           target=0xCD0C95,busy_site=0xD1E798,busy_value=0,
           entry_m8=False,entry_x8=False,budget=100):
    """One busy-zero path, from arbitrary initial register-byte symbols.

    Stores are recorded but memory aliases are not solved. Software-stack
    push/pop semantics presume ordinary writable native stack RAM and no
    intervening corruption or asynchronous entry. MVN is summarized using
    the pinned CPU's exact X16 count and register effects, not its timing.
    """
    require(type(entry_m8) is bool and type(entry_x8) is bool,'exact entry widths')
    byte(busy_value,'busy input');require(busy_value==0,'normal prefix requires busy zero')
    require(type(budget) is int and budget>0,'positive prefix budget')
    regs={k:(k+'.lo',k+'.hi') for k in ('a','x','y','d')}
    if entry_x8:
        for k in ('x','y'):regs[k]=(k+'.lo',0)
    regs['dbr']=('dbr',)
    stack=[];m8=entry_m8;x8=entry_x8;pc=entry;zero=None
    decoded=[];writes=[];reads=[];moves=[];peak=4;busy_seen=False;busy_mutated=False
    push={0x48:'a',0xDA:'x',0x5A:'y',0x8B:'dbr',0x0B:'d'}
    def word(k):
        value=regs[k]
        require(len(value)==2 and all(type(v) is int for v in value),'symbolic word used as concrete '+k)
        return value[0]|value[1]<<8
    def set_word(k,value):regs[k]=(value&255,value>>8&255)
    def load_a(value,n):
        nonlocal zero
        regs['a']=tuple(value)+(regs['a'][1],) if n==1 else tuple(value)
        zero=all(v==0 for v in value) if all(type(v) is int for v in value) else None
    while len(decoded)<budget:
        require(entry<=pc<end,'normal prefix escaped declared span')
        op,name,raw=closure.prior.decode(read,pc,m8,x8)
        require(pc+len(raw)<=end,'normal prefix instruction extent')
        decoded.append({'address':f'{pc:06X}','length':len(raw),'name':name,
            'm8':m8,'x8':x8,'sha256':hashlib.sha256(raw).hexdigest()})
        operand=int.from_bytes(raw[1:],'little');nxt=pc+len(raw);n=1 if m8 else 2
        if op in (0xC2,0xE2):
            require(operand&~0x30==0,'unmodeled status change')
            if operand&0x20:m8=op==0xE2
            if operand&0x10:
                x8=op==0xE2
                if x8:
                    for k in ('x','y'):regs[k]=(regs[k][0],0)
        elif op in push:
            k=push[op];width=n if k=='a' else ((1 if x8 else 2) if k in ('x','y') else len(regs[k]))
            stack.extend(reversed(regs[k][:width]))
        elif op==0xAB:
            require(stack,'PLB consumes missing software value')
            regs['dbr']=(stack.pop(),)
            zero=regs['dbr'][0]==0 if type(regs['dbr'][0]) is int else None
        elif op==0xA9:load_a(tuple(raw[1:]),n)
        elif op in (0xA2,0xA0):
            k='x' if op==0xA2 else 'y';set_word(k,operand);zero=operand==0
        elif op==0x5B:
            regs['d']=regs['a']
            zero=all(v==0 for v in regs['d']) if all(type(v) is int for v in regs['d']) else None
        elif op==0x7B:
            regs['a']=regs['d'];zero=word('d')==0
        elif op in (0xAF,0xAD,0xA5):
            if op==0xAF:address=operand
            elif op==0xAD:
                require(type(regs['dbr'][0]) is int,'unknown absolute read bank')
                address=regs['dbr'][0]<<16|operand
            else:address=(word('d')+operand)&65535
            reads.append({'site':f'{pc:06X}','cpu_address':f'{address:06X}','width':n})
            if pc==busy_site:
                require(op==0xA5 and address==0x7F and n==1,'busy premise applied to wrong read')
                require(not busy_seen,'busy premise cannot be reused')
                load_a((busy_value,),1);busy_seen=True
            else:load_a(tuple(f'read.{pc:06X}.{i}' for i in range(n)),n)
        elif op in (0x8F,0x8D):
            if op==0x8F:address=operand
            else:
                require(type(regs['dbr'][0]) is int,'unknown absolute store bank')
                address=regs['dbr'][0]<<16|operand
            require(not (busy_seen and address<=0x7F<address+n),'store invalidates one-time busy premise')
            writes.append({'site':f'{pc:06X}','cpu_address':f'{address:06X}','width':n,
                'value_bytes':list(regs['a'][:n])})
        elif op==0xE6:
            address=(word('d')+operand)&65535
            require(address==0x7F and n==1 and busy_seen and not busy_mutated,'unreviewed or repeated direct-page mutation')
            busy_mutated=True
            writes.append({'site':f'{pc:06X}','cpu_address':'00007F','width':1,'value_bytes':[1]})
            zero=False
        elif op==0xF0:
            require(busy_seen and zero is True,'branch lacks exact busy-zero premise')
            nxt=(pc&0xFF0000)|((nxt+int.from_bytes(raw[1:],'little',signed=True))&65535)
        elif op==0x54:
            require(not x8 and not m8,'MVN summary requires M16/X16')
            count=word('a')+1;x=word('x');y=word('y');dest=raw[1];source=raw[2]
            require(count<=256 and x+count<=65536 and y+count<=65536,'MVN summary bound')
            moves.append({'site':f'{pc:06X}','count':count,'source_start':f'{source<<16|x:06X}',
                'source_end_exclusive':f'{(source<<16|x)+count:06X}',
                'destination_start':f'{dest<<16|y:06X}',
                'destination_end_exclusive':f'{(dest<<16|y)+count:06X}'})
            set_word('a',65535);set_word('x',x+count);set_word('y',y+count);regs['dbr']=(dest,)
        elif op==0x22:
            require(pc==call and operand==target,'unreviewed call before frontier')
            require(busy_seen,'call reached without busy-zero input')
            peak=max(peak,4+len(stack)+3)
            return {'entry_widths':{'m8':entry_m8,'x8':entry_x8},'entry':f'{entry:06X}',
                'frontier':f'{target:06X}','decoded_instructions':decoded,
                'frontier_register_bytes':{k:list(v) for k,v in regs.items()},
                'frontier_widths':{'m8':m8,'x8':x8,'irq_masked':True,'native':True},
                'software_saved_bytes':len(stack),'hardware_entry_bytes':4,'frontier_jsl_bytes':3,
                'conditional_bytes_below_interrupted_sp':4+len(stack)+3,'prefix_peak_stack_bytes':peak,
                'nonstack_reads':reads,'nonstack_stores':writes,'block_moves':moves,
                'memory_aliases_solved':False,'whole_nmi_bound_proved':False,
                'asynchronous_entry_or_physical_stack_ownership_proved':False}
        else:raise ValueError(f'unmodeled prefix effect at {pc:06X}: {op:02X}')
        peak=max(peak,4+len(stack));pc=nxt
    raise ValueError('normal prefix state budget exceeded')


def identity(path,expected=None):
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    require(expected is None or digest==expected,'source identity drift: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':digest}


def audit(rom):
    require(type(rom) is bytes and len(rom)==0x400000 and hashlib.sha256(rom).hexdigest()==ROM_SHA,'canonical ROM identity')
    def read(address,size):
        require(0xC00000<=address and address+size<=0x1000000,'canonical ROM read bounds')
        return rom[address&0x3FFFFF:(address&0x3FFFFF)+size]
    spans=[]
    for name,start,end,pin in SPANS:
        digest=hashlib.sha256(read(start,end-start)).hexdigest();require(digest==pin,'pinned span drift')
        spans.append({'name':name,'start':f'{start:06X}','end_exclusive':f'{end:06X}','size':end-start,'sha256':digest})
    runs=[]
    for m8 in (False,True):
        for x8 in (False,True):
            r=prefix(read,entry_m8=m8,entry_x8=x8)
            require(r['frontier_register_bytes']=={'a':[128,0],'x':[43,0],'y':[144,204],'d':[0,0],'dbr':[0]},'frontier register contract drift')
            require(r['frontier_widths']=={'m8':True,'x8':False,'irq_masked':True,'native':True},'frontier width drift')
            require(r['conditional_bytes_below_interrupted_sp']==16 and r['software_saved_bytes']==9,'prefix stack count drift')
            runs.append(r)
    # The local mode dispatcher is decoded separately; no callee is summarized.
    spec=((0xCD0C95,2,0xA5),(0xCD0C97,1,0x0A),(0xCD0C98,1,0xAA),(0xCD0C99,3,0xFC),(0xCD0C9C,1,0x6B))
    dispatcher=[]
    for address,size,opcode in spec:
        raw=read(address,size);require(raw[0]==opcode,'mode dispatcher opcode drift')
        dispatcher.append({'address':f'{address:06X}','length':size,'sha256':hashlib.sha256(raw).hexdigest()})
    require(read(0xCD0C96,1)[0]==0x7E and int.from_bytes(read(0xCD0C9A,2),'little')==0x0C83,'mode dispatcher operand drift')
    cells=[]
    for mode in range(256):
        c=index_contract(mode);raw=b''.join(read(p,1) for p in c['pointer_byte_addresses'])
        c.update(target=f'{0xCD0000|int.from_bytes(raw,"little"):06X}',
            pointer_bytes_sha256=hashlib.sha256(raw).hexdigest())
        cells.append(c)
    return {'schema':'project-epoch-nmi-mode-input-contract-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},'spans':spans,'normal_prefix_width_cases':runs,
        'dispatcher_instructions':dispatcher,'b_zero_mode_cells':cells,
        'b_zero_unique_cells':len({tuple(c['pointer_byte_addresses']) for c in cells}),
        'b_zero_modes_aliasing_reviewed_three_cells':[c['mode'] for c in cells if c['x'] in (0,2,4)],
        'all_hidden_b_mode_pairs':sum(1 for b in range(256) for mode in range(256) if index_contract(mode,b)),
        'reviewed_three_cell_targets':[c['target'] for c in cells[:3]],
        'mode_03_cell_overlaps_wrapper_code':cells[3]['pointer_byte_addresses']==[0xCD0C89,0xCD0C8A],
        'complete_legal_mode_domain_proved':False,'selected_mode_bodies_executed_or_closed':False,
        'whole_nmi_stack_bound':None,'production_approval':False,
        'limits':['Native entry and no intervening asynchronous handler/corruption are explicit prefix premises.',
            'Stack byte counts assume ordinary writable native stack RAM; nonstack aliasing and actual SP ownership remain open.',
            'The busy-zero input is read at D1E798; other busy values use the separately audited busy fast path.',
            'All four initial M/X combinations are modeled; symbolic initial register bytes are not concrete test seeds.',
            'The 43-byte MVN is an instruction-semantic summary, not a CPU-cycle or bus-event simulation.',
            'No bound check precedes indexed mode dispatch; the three reviewed cells are not a complete producer-domain proof.',
            'Hypothetical mode values are not asserted reachable, legal, illegal or unused; successor code remains occupied.',
            'No NMI callee, script lifetime, saved-frame alias, interrupt timing, high-package binding or PC07 proof is promoted.']}


def collect():
    prior_path=ROOT/'references/schala_package_normal_nmi_closure_v2.json'
    old=identity(prior_path,PRIOR_SHA)
    result=audit(ROM.read_bytes())
    result['sources']={'auditor':identity(Path(__file__).resolve()),'tests':identity(ROOT/'tests/test_schala_nmi_mode_inputs_v1.py'),
        'closure_reference':old,'closure_auditor':identity(Path(closure.__file__),'c346e0db11dc35a4ecd4e756dcc951ca7a760d3bd52849da55b1f7fe7e7b7e13'),
        'cd_annotation':identity(ROOT/'private/research/ct_disassembly_eeae27a/bank_CD.asm','0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb'),
        'd1_annotation':identity(ROOT/'private/research/ct_disassembly_eeae27a/bank_D1.asm','020f6df9efd22cc12a35608da6523b5d2e5d76d965d94567e0b74d50ab9eacea')}
    result['preserved_closure_dependencies']=[identity(ROOT/i['path'],i['sha256'])
        for i in json.loads(prior_path.read_text(encoding='utf-8'))['source_identities']]
    for relative,pin,_ in closure.PRIMARY_SOURCES:result['sources'][Path(relative).name]=identity(ROOT/relative,pin)
    result['reproduce']=['python','-B','tools/audit_schala_nmi_mode_inputs_v1.py']
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode('utf-8'))
