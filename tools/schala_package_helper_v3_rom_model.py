"""Original immutable-ROM fixture model for separately scoped v3 conformance."""
from __future__ import annotations
import hashlib
import audit_schala_player_tech_package_bank_adapter_v0 as adapter
import original_snes_package_fixtures_v1 as fixtures
import run_schala_package_helper_v2_stack as v2

PAYLOAD_SHA256="2eaa608733618d79876b55e9bde43f4bf213f9556484b15216781a5df52dce70"
REGISTRY_SHA256="6cb7223449fca8f93771e37639cf0e9e28ac520ce5bb2b77d43154447e1ac965"
CODE=0x410000
REGISTRY=0x430000
TARGETS=0x430100
TAILS={"canonical":0x008100,"success":0x008110,"refusal":0x008120}
ENTRY_BRIDGE=0x008060
ENTRY_STACKS=(0x1FEF,0x06D8)


def require_components(payload:bytes,registry:bytes)->None:
    if type(payload) is not bytes or len(payload)!=897 or hashlib.sha256(payload).hexdigest()!=PAYLOAD_SHA256:
        raise ValueError("immutable original descriptor/terminal fixture differs")
    if type(registry) is not bytes or len(registry)!=0x500 or hashlib.sha256(registry).hexdigest()!=REGISTRY_SHA256:
        raise ValueError("immutable original registry/target fixture differs")


def original_components():
    payload,registry,certificate=fixtures.build()
    require_components(payload,registry)
    return payload,registry,certificate


def make_case(payload:bytes,registry:bytes,name:str,selector:int=0x80,flag:int=0,*,
              sp:int=0x1FEF,status:int=0,category:str="immutable-rom-binding")->dict:
    require_components(payload,registry)
    if type(selector) is not int or not 0<=selector<=65535 or type(flag) is not int or not 0<=flag<=65535:
        raise ValueError("native input words must be exact unsigned integers")
    if sp not in ENTRY_STACKS or type(status) is not int or not 0<=status<=255 or status&0x30:
        raise ValueError("synthetic entry SP or native M0/X0 status mismatch")
    cpu=v2.input_cpu(0);cpu.update(sp=sp,ps=status)
    expected=dict(cpu);reads=[];writes=[];route="refusal";countbits=False
    framed=0x80<=selector<=0x8F and flag<=255
    def registry_word(offset):
        for a in (offset,offset+1):reads.append([REGISTRY+a,registry[a]])
        return int.from_bytes(registry[offset:offset+2],"little")
    def source_word(offset):
        for a in (offset,offset+1):reads.append([0x420000+a,payload[a]])
        return int.from_bytes(payload[offset:offset+2],"little")
    if selector<0x80:
        route="canonical";expected.update(a=selector*2,ps=(status&0x7C)|(2 if selector==0 else 0))
    elif framed:
        index=(selector-0x80)*16
        valid=registry_word(index)
        if valid==1:
            # Fixed immutable registry preflight read order. Semantic fields are
            # separately bound to original_components' exact certified bytes.
            for offset in (0xC,0xE,0xA,6,8,4,2):registry_word(index+offset)
            root=int.from_bytes(registry[index+2:index+4],"little")
            m0=int.from_bytes(source_word(root).to_bytes(2,"little"),"big")
            m1=int.from_bytes(source_word(root+2).to_bytes(2,"little"),"big")
            countbits=True
            count=m0.bit_count()+m1.bit_count()
            target_count=int.from_bytes(registry[index+0xA:index+0xC],"little")
            target_base=0x100+(selector-0x80)*64
            for pointer_index in range(count):
                pointer=source_word(root+4+pointer_index*2)
                for target_index in range(target_count):
                    if registry_word(target_base+target_index*2)==pointer:break
                else:raise ValueError("certified immutable pointer lacks its target allowlist")
            source=adapter.make_package_source(selector=selector,bank=0x42,root_offset=root,
                allocation_name=f"ORIGINAL_TEST_PACKAGE_{selector:02X}_DESCRIPTOR",source_kind="synthetic-test")
            bank=payload+bytes([255])*(65536-len(payload))
            model=adapter.simulate_descriptor_install(bank,source,a0b3=flag)
            route="success";expected.update(a=0,x=model.x_final,y=16,ps=(status&0x4C)|0x23)
            writes+=v2.word_bytes(0x7E9878,root)+v2.word_bytes(0x7E0080,0)+v2.word_bytes(0x7E0082,m1)
            first=root+4+(2*m0.bit_count() if flag else 0)
            for i,pub in enumerate(model.publications):
                source_word(first+i*2)
                writes+=v2.word_bytes(0x7E0000+pub.activation_address,pub.activation_word)
                writes+=v2.word_bytes(0x7E0000+pub.script_address,pub.script_offset)
                writes+=v2.word_bytes(0x7E0000+pub.bank_address,pub.bank_word)
            writes.append([0x7EA0B3,0])
    depth=52 if framed else 8
    return {"name":name+f"-sp-{sp:04X}","category":category,"selector":selector,"flag":flag,
        "cpu":cpu,"patches":v2.word_bytes(0x7E9877,selector)+v2.word_bytes(0x7EA0B3,flag),
        "route":route,"expected_cpu":expected,"expected_writes":writes,"expected_rom_reads":reads,
        "frame_allocated":framed,"countbits_reached":countbits,"stack_depth_limit":depth,
        "stack_span":[0x7E0000+sp-depth+1,0x7E0000+sp+1]}


def build_cases(payload:bytes,registry:bytes)->list[dict]:
    require_components(payload,registry)
    result=[]
    statuses=(0,0xC3,0x4C,0x8F)
    for sp in ENTRY_STACKS:
        for selector in range(128):
            result.append(make_case(payload,registry,f"canonical-{selector:02X}",selector,0xA55A,
                sp=sp,status=statuses[selector%4],category="all-canonical-selectors"))
        for selector in range(0x80,0x84):
            for flag in range(256):
                result.append(make_case(payload,registry,f"bound-{selector:02X}-flag-{flag:02X}",selector,flag,
                    sp=sp,status=statuses[flag%4],category="all-four-bindings-all-flag-bytes"))
        for selector in range(0x84,0x90):
            for flag in (0,0x40,255):
                result.append(make_case(payload,registry,f"unbound-{selector:02X}-{flag:02X}",selector,flag,
                    sp=sp,status=statuses[selector%4],category="all-twelve-immutable-unbound-records"))
        for selector in (0x90,255,0x100,65535):
            for flag in (0,0x40,255):
                result.append(make_case(payload,registry,f"unsupported-{selector:04X}-{flag:02X}",selector,flag,
                    sp=sp,status=statuses[selector%4],category="unsupported-and-wide-selectors"))
        for selector in range(0x80,0x84):
            for flag in (0x100,65535):
                result.append(make_case(payload,registry,f"wide-flag-{selector:02X}-{flag:04X}",selector,flag,
                    sp=sp,status=0x8F,category="wide-flag-refusal"))
        for status in range(256):
            if status&0x30:continue
            for name,selector,flag in (("canonical",0x7F,0),("primary",0x80,0),("alternate",0x80,0x40),
                    ("empty-primary",0x83,0),("empty-alternate",0x82,0x40),("unbound",0x84,0)):
                result.append(make_case(payload,registry,f"status-{status:02X}-{name}",selector,flag,
                    sp=sp,status=status,category="all-native-status-bits"))
    return result
