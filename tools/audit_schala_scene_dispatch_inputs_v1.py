"""Read-only scene-dispatch byte/index provenance, with explicit open domains.

The finite prefix model proves accumulator-byte facts only. It stops before
the first indexed command call and does not infer a complete legal table,
script corpus, physical stack ownership, or whole-NMI bound.
"""
from __future__ import annotations
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_package_normal_nmi_closure_v2 as closure

ROOT=Path(__file__).resolve().parents[1]
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
REFERENCE=ROOT/'references/schala_package_normal_nmi_closure_v2.json'
REFERENCE_SHA='413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242'
SPANS=(
 ('initializer',0xCD0D33,0xCD0D62,'f5085c158bc23c516f51bb1d701866e19bd18b865c4a959e96550ced924a58a7'),
 ('background-config-reader',0xCD0F42,0xCD0F62,'e771998b50334fd023ef2c90de2cf16b94d1fd026bc4d078c42ba555cae3d415'),
 ('script-start',0xCD15D5,0xCD1609,'fecf987a80dc0592e83272d9be251a0d9f9f2db979feb90bf7c064428b412efd'),
 ('tick',0xCD1609,0xCD1654,'dce62d3d48a939537e1f9976e6177b9fda6f39e9076b72c4f4fc0e2af798fca9'),
 ('slot',0xCD1654,0xCD16A6,'c3f95e5fe6d77458c2fcb7b274031a9bda66a20121a5c88e7284d60fdf34f1b7'),
 ('dispatch',0xCD16A6,0xCD16B5,'de006cb5ff3d9e1303b29063bd54b1ff51cc794b038b1da68a285a8aa9efd28f'),
 ('reviewed-cell-prefix',0xCD16B5,0xCD17A9,'e1fe07cd81ca47f6e02ba61b565b22bacf33967482bb4970e43147c9631cc4da'),
 ('f9-target-body',0xCD17A9,0xCD17BE,'0904f1f58ecb736c0e605f6c428d54cff806de5ec7d11923a87546b0857e30be'),
 ('all-b-zero-syntax-cells',0xCD16B5,0xCD17B3,'6c9db81caca8b682feb44a305785deafafdd29b651065def9028fff663834073'),
 ('non-ff-script-id-read-cells',0xD1646C,0xD1666A,'b43241f863c1e35ce6ccf83407ddbe86621951fff0191656078ee7eaaa27e2aa'),
)


def require(condition,message):
    if not condition:raise ValueError(message)


def byte(value,name):require(type(value) is int and 0<=value<=255,'exact byte '+name)


def classify(value:int)->str:
    byte(value,'stream value')
    return 'tilemap' if value<0x7F else 'yield' if value==0x7F else 'stop' if value==0xFF else 'indexed-command'


def index_contract(command:int,hidden_b:int)->dict:
    byte(command,'command');byte(hidden_b,'hidden B')
    require(classify(command)=='indexed-command','not an indexed scene command')
    # ASL A in M8 preserves B; TAX in X16 copies both accumulator bytes.
    index=(hidden_b<<8)|((command<<1)&255)
    low=(0x16B5+index)&65535
    return {'command':command,'hidden_b':hidden_b,'x':index,
        'pointer_byte_addresses':[0xCD0000|low,0xCD0000|((low+1)&65535)]}


def script_start_contract(script_id:int,hidden_b:int=0)->dict:
    byte(script_id,'script ID');byte(hidden_b,'hidden B')
    require(script_id!=255,'initializer skips the FF sentinel')
    # StartScript widens A before ASL. A caller with nonzero B therefore
    # changes the pointer-table index even though the visible ID is one byte.
    index=(((hidden_b<<8)|script_id)<<1)&65535
    return {'script_id':script_id,'hidden_b':hidden_b,'x':index,
        'pointer_byte_addresses':[0xD1646C+index,0xD1646D+index],
        'selected_source_bank':0xD1,'complete_legal_id_domain_proved':False}


def first_indexed_b(read,*,entry=0xCD161D,hidden_b=None,direct_page=0,
                    spans=((0xCD161D,0xCD16B5),),frontier=0xCD16AF,
                    calls=((0xCD1631,0xCD1654),(0xCD1695,0xCD16A6)),budget=2000):
    """Finite overapproximation ending before the first indexed call.

    Both outcomes of every conditional branch are explored. Bytes are exact
    constants or unknown; no branch/value feasibility or loop termination is
    claimed. The artificial call continuation is not a physical stack model.
    """
    require(type(direct_page) is int and direct_page==0,'D=0 prefix contract')
    require(hidden_b is None or type(hidden_b) is int and 0<=hidden_b<=255,'hidden B domain')
    require(type(budget) is int and budget>0,'positive finite state budget')
    State=tuple
    todo=deque([State((entry,True,False,None,hidden_b,()))]);seen=set();observed=set();decoded={};owners={};exits=set()
    allowed_calls=dict(calls)
    preserve={0x18,0x38,0x48,0x5A,0x7A,0x84,0x85,0x86,0x8D,0x9C,0x9D,0x9E,
              0xA4,0xA8,0xAA,0xBC,0xC0,0xC8,0xC9,0xDA,0xDE,0xE0,0xEE,0xFA}
    while todo:
        state=todo.popleft()
        if state in seen:continue
        seen.add(state);require(len(seen)<=budget,'prefix state budget exceeded')
        pc,m8,x8,lo,hi,frames=state
        require(any(a<=pc<b for a,b in spans),'prefix control flow left declared code')
        opcode_bytes=read(pc,1);require(len(opcode_bytes)==1,'short prefix opcode read');op=opcode_bytes[0]
        if op in closure.prior.irq.M_IMMEDIATES:length=2 if m8 else 3
        elif op in closure.prior.irq.X_IMMEDIATES:length=2 if x8 else 3
        elif op in closure.prior.irq.BRANCHES or op==0x80:length=2
        else:
            require(op in closure.FIXED,'unsupported prefix opcode')
            length=closure.FIXED[op][1]
        require((pc&65535)+length<=65536,'prefix instruction bank boundary')
        raw=read(pc,length);require(len(raw)==length and any(a<=pc and pc+length<=b for a,b in spans),'prefix instruction extent')
        for address in range(pc,pc+length):
            require(address not in owners or owners[address]==pc,'prefix overlapping decode');owners[address]=pc
        require(pc not in decoded or decoded[pc]['length']==length,'prefix incompatible width length')
        decoded[pc]={'address':f'{pc:06X}','length':length,'sha256':hashlib.sha256(raw).hexdigest()}
        if pc==frontier:
            require(op==0xFC and not x8 and m8,'indexed frontier width/opcode contract')
            observed.add(hi);continue
        next_pc=(pc&0xFF0000)|((pc+length)&65535);dest=[next_pc]
        if op==0x7B:lo=hi=0
        elif op in (0xC2,0xE2):
            require(raw[1]==0x20,'prefix changes unmodeled status bits');m8=op==0xE2
        elif op in (0xAD,0xBD,0xA7,0xA5,0x8A,0x98,0x69,0x7D):
            lo=None
            if not m8:hi=None
        elif op==0xEB:lo,hi=hi,lo
        elif op in (0x0A,0x1A):
            if m8:lo=None if lo is None else ((lo<<1) if op==0x0A else lo+1)&255
            elif lo is None or hi is None:lo=hi=None
            else:
                value=((hi<<8)|lo);value=((value<<1) if op==0x0A else value+1)&65535;lo,hi=value&255,value>>8
        elif op==0x20:
            target=(pc&0xFF0000)|int.from_bytes(raw[1:],'little')
            require(allowed_calls.get(pc)==target,'unreviewed prefix direct call')
            frames=frames+(next_pc,);dest=[target]
        elif op==0x60:
            if not frames:exits.add(pc);continue
            dest=[frames[-1]];frames=frames[:-1]
        elif op in closure.prior.irq.BRANCHES or op==0x80:
            target=(pc&0xFF0000)|((next_pc+int.from_bytes(raw[1:],'little',signed=True))&65535)
            dest=[target] if op==0x80 else [next_pc,target]
        else:require(op in preserve,'unmodeled prefix accumulator effect')
        require(not x8,'prefix X16 premise lost')
        todo.extend((target,m8,x8,lo,hi,frames) for target in dest)
    return {'entry':f'{entry:06X}','initial_hidden_b':hidden_b,'initial_d':0,
        'frontier':f'{frontier:06X}','frontier_hidden_b_values':sorted(v for v in observed if v is not None),
        'frontier_hidden_b_can_be_unknown':None in observed,'frontier_reached':bool(observed),
        'all_frontier_hidden_b_zero':observed=={0},'abstract_states':len(seen),
        'decoded_instructions':list(decoded[k] for k in sorted(decoded)),
        'root_return_sites':[f'{x:06X}' for x in sorted(exits)],
        'termination_proved':False,'physical_stack_model':False,
        'branch_value_feasibility_proved':False,'command_handler_executed_or_summarized':False}


def identity(path,expected=None):
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    require(expected is None or digest==expected,'source identity drift: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':digest}


def audit(rom:bytes):
    require(type(rom) is bytes and len(rom)==0x400000 and hashlib.sha256(rom).hexdigest()==ROM_SHA,'canonical ROM identity')
    def read(address,length):
        require(0xC00000<=address and address+length<=0x1000000,'canonical high-ROM read bound')
        return rom[address&0x3FFFFF:(address&0x3FFFFF)+length]
    observations=[]
    for name,start,end,pin in SPANS:
        digest=hashlib.sha256(read(start,end-start)).hexdigest();require(digest==pin,'canonical span drift')
        observations.append({'name':name,'start':f'{start:06X}','end_exclusive':f'{end:06X}','size':end-start,'sha256':digest})
    prefixes={
        'first-indexed-call-from-tick':first_indexed_b(read),
        'standalone-slot-with-unknown-b':first_indexed_b(read,entry=0xCD1654),
        'next-command-after-unmodeled-return':first_indexed_b(read,entry=0xCD1698),
    }
    require(prefixes['first-indexed-call-from-tick']['all_frontier_hidden_b_zero'],'first indexed call B proof drift')
    require(all(prefixes[k]['frontier_hidden_b_can_be_unknown'] for k in prefixes if k!='first-indexed-call-from-tick'),'unknown return B accidentally discharged')
    cells=[]
    for command in range(0x80,0xFF):
        cell=index_contract(command,0);addresses=cell['pointer_byte_addresses'];raw=b''.join(read(a,1) for a in addresses)
        cell.update(target=f'{0xCD0000|int.from_bytes(raw,"little"):06X}',pointer_bytes_sha256=hashlib.sha256(raw).hexdigest(),
            in_reviewed_122_cell_prefix=command<=0xF9,command_reachability_proved=False)
        cells.append(cell)
    require(cells[0xF9-0x80]['target']=='CD17A9','reviewed prefix last target drift')
    # Decode the exact following target body in its declared entry widths.
    # This records code occupancy, not an asserted scene grammar or execution.
    body_spec=((0xCD17A9,2,0xA7),(0xCD17AB,1,0x48),(0xCD17AC,3,0xA0),
        (0xCD17AF,2,0xC2),(0xCD17B1,2,0xB7),(0xCD17B3,1,0xAA),
        (0xCD17B4,2,0xE6),(0xCD17B6,1,0x7B),(0xCD17B7,2,0xE2),
        (0xCD17B9,1,0x68),(0xCD17BA,3,0x9D),(0xCD17BD,1,0x60))
    body=[]
    for address,length,opcode in body_spec:
        raw=read(address,length);require(raw[0]==opcode,'F9 target decode drift')
        body.append({'address':f'{address:06X}','length':length,'sha256':hashlib.sha256(raw).hexdigest()})
    require(read(0xCD17AF,2)[1]==0x20 and read(0xCD17B7,2)[1]==0x20,'F9 target width transitions')
    pair_count=0;wrapped=0
    for b in range(256):
        for command in range(256):
            if classify(command)=='indexed-command':
                c=index_contract(command,b);pair_count+=1;wrapped+=c['pointer_byte_addresses'][1]<c['pointer_byte_addresses'][0]
    starts=[]
    for script_id in range(255):
        c=script_start_contract(script_id);addresses=c['pointer_byte_addresses'];raw=b''.join(read(a,1) for a in addresses)
        root=int.from_bytes(raw,'little')
        starts.append({'script_id':script_id,'table_cpu_address':f'{addresses[0]:06X}',
            'root_cpu_address':f'{0xD10000|root:06X}','initial_cursor_cpu_address':f'{0xD10000|((root+1)&65535):06X}',
            'pointer_bytes_sha256':hashlib.sha256(raw).hexdigest(),'reachability_proved':False})
    return {'schema':'project-epoch-scene-dispatch-input-contract-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},'spans':observations,'prefix_b_proofs':prefixes,
        'syntax_command_counts':{'tilemap':127,'yield':1,'indexed-command':127,'stop':1},
        'exhaustive_hidden_b_command_pairs':pair_count,'pointer_word_bank_wrap_pairs':wrapped,
        'b_zero_syntax_cells':cells,'reviewed_prefix_cells':122,'reviewed_prefix_distinct_targets':len({c['target'] for c in cells[:122]}),
        'following_f9_target_instructions':body,'fa_through_fe_cells_overlap_f9_code':True,
        'possible_non_ff_script_id_reads':starts,'possible_id_distinct_roots':len({c['root_cpu_address'] for c in starts}),
        'complete_legal_command_domain_proved':False,'complete_legal_script_id_domain_proved':False,
        'script_token_grammar_proved':False,'script_reachability_or_lifetime_proved':False,
        'helper_frame_ownership_proved':False,'whole_nmi_stack_bound':None,'production_approval':False,
        'limits':['Native M1/X0 and D0 are explicit prefix entry premises; DBR7E is required to name the WRAM fields.',
            'Prefix branch outcomes overapproximate inputs and stop before the first indexed call; no command handler is assigned an opaque return.',
            'The 122-cell prefix is a reviewed physical prefix, not a certified complete legal table; canonical code/data dual use is not forbidden.',
            'FA-FE syntax values and arbitrary incoming B remain possible at the local consumer without a source-domain proof.',
            '255 non-FF script IDs are hypothetical local-consumer inputs, not 255 certified scripts.',
            'No new command execution, original cartridge run, game hook, allocation, or interrupt ownership is approved.']}


def collect():
    prior=identity(REFERENCE,REFERENCE_SHA)
    report=audit(ROM.read_bytes())
    report['sources']={'auditor':identity(Path(__file__).resolve()),'tests':identity(ROOT/'tests/test_schala_scene_dispatch_inputs_v1.py'),
        'closure_reference':prior,'closure_auditor':identity(Path(closure.__file__),'c346e0db11dc35a4ecd4e756dcc951ca7a760d3bd52849da55b1f7fe7e7b7e13'),
        'cd_annotation':identity(ROOT/'private/research/ct_disassembly_eeae27a/bank_CD.asm','0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb'),
        'd1_annotation':identity(ROOT/'private/research/ct_disassembly_eeae27a/bank_D1.asm','020f6df9efd22cc12a35608da6523b5d2e5d76d965d94567e0b74d50ab9eacea')}
    report['preserved_closure_dependency_identities']=[identity(ROOT/item['path'],item['sha256'])
        for item in json.loads(REFERENCE.read_text(encoding='utf-8'))['source_identities']]
    for relative,pin,_ in closure.PRIMARY_SOURCES:
        report['sources'][Path(relative).name]=identity(ROOT/relative,pin)
    report['reproduce']=['python','-B','tools/audit_schala_scene_dispatch_inputs_v1.py']
    return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode('utf-8'))
