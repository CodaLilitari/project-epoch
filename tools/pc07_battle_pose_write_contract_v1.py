"""Fixed private battle-art append, with one current-image pin and full diff.

No historical builders run. Original NPC/vehicle bytes and frames0..22 remain
unchanged. These private hooks do not enter either production catalog.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import re
import subprocess

from pc07_run_pose_write_contract_v1 import ROOT, SIZE, NPC_SPANS, need, sha, encoded, resolve, read_pin, tokens
import native_pc07_pose_codec_v1 as codec
import native_pc07_pose_mirror_v1 as mirror

SCHEMA = "project-epoch-private-pc07-battle-pose-intents-v1"
SOURCE = {"path": "private/test_runs/pc07_run_pose_v1/diagnostic.sfc", "bytes": SIZE,
          "sha256": "00e3440c2927834554c7e3f872a5b995b76e53e1e6775ddd76abe9bac0b8f18f"}
PARENT = {"path": "private/test_runs/pc07_run_pose_v1/receipt.json", "bytes": 4996,
          "sha256": "3bbd059c6c213d33739b421c9d8c572ae4b279414868a6fc3a4005e458fcb8b1"}
ART = (
    {"path": "private/research/pc07_main_sprite_art_20261018/collaboration/lily/returned_v2/extracted/schala_pc07_sixpose_study_v2_indexed.json",
     "bytes": 34142, "sha256": "54148907a4257116fe572beb2e537ab112131018ea83078e5d48c0c2b15abd79"},
    {"path": "private/research/pc07_main_sprite_art_20261018/collaboration/red/returned_v1/extracted/schala_six_pose_red_20261018/out/schala_six_pose_red_frames.json",
     "bytes": 21879, "sha256": "1fb5a1b558112487561b08439308ec89a6c9acab86438a3d4be8c13cd47ae004"},
)
CENSUS = {"path": "private/research/pc07_battle_pose_20261020/engineering/allocation_census_v1.json",
          "bytes": 19929, "sha256": "bbb17c2644b585329290965ffd4f8dc63b353bf47c116eb8e80574840a0487f9"}
ASAR = {"path": "private/tools/asar-1.91/asar.exe", "bytes": 501248,
        "sha256": "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"}
PRIMARY, TIMING, STRIDE = 0x424000, 0x425100, 0x404
GFX, ASSEMBLY = 0x420000, 0x421000
NEW_ALLOCATIONS = (("pc07-battle-pose-graphics-append", 0x4209E0, 0x420E00),
                   ("pc07-battle-pose-assembly-append", 0x421398, 0x4214B0),
                   ("pc07-battle-pose-ko-helpers", 0x490000, 0x490100))
HOOKS = (("status-ko-producer", 0x1300D, bytes.fromhex("8584A494"), bytes.fromhex("22800049")),
         ("direct-ko-frame", 0x141A5, bytes.fromhex("BF425FD1"), bytes.fromhex("22000049")))
CHANGED_SELECTORS = (5, 0x31, 0x32, 0xF0)
_ACTIVE = None


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r"private/test_runs/pc07_battle_pose_[A-Za-z0-9_-]+/diagnostic\.sfc", relative),
         "fresh private battle-pose destination required")
    return resolve(relative)


def source_identity(relative, raw):
    return {"path": relative, "bytes": len(raw), "sha256": sha(raw)}


def candidate_rows(documents):
    lily, red = documents
    palette = lily["palette_indices_0_12"]
    need(type(palette) is list and len(palette) == 13 and all(type(r) is list and len(r) == 3
         and all(type(v) is int and 0 <= v <= 255 for v in r) for r in palette)
         and [r["rgb8"] for r in red["palette"]] == palette, "pinned returned palette13 correspondence")
    need(lily["transparent_index"] == 0 and lily["frame_size"] == [48,48]
         and lily["native_origin"] == [16,40] and red["canvas"] == [48,48]
         and red["origin"] == [16,40], "fixed authoring geometry")
    candidates = []
    for author, doc, indices, roles in (("Lily", lily, (2,3), ("cast_windup_right", "cast_release_right")),
                                        ("Red", red, (4,5), ("hurt_recoil_right", "KO_head_left"))):
        for index, role in zip(indices, roles):
            frame = doc["frames"][index]
            need(frame.get("name", frame.get("label")) == role, "exact selected art role")
            rows = ([list(bytes.fromhex(row)) for row in frame["rows"]] if author == "Lily"
                    else [[int(c,16) for c in row] for row in frame["pixel_rows_hex"]])
            need(len(rows) == 48 and all(len(r) == 48 for r in rows)
                 and all(type(v) is int and 0 <= v <= 12 for r in rows for v in r), "indexed48x48 palette13")
            candidates.append({"author": author, "source_index": index, "role": role, "rows": rows,
                               "preferred_cover": frame.get("cover_16x16_top_left")})
    return candidates


def encode_art(source, documents):
    graphics = source[GFX:GFX + 79*32]
    assembly = source[ASSEMBLY:ASSEMBLY + 23*40]
    newgfx, newasm, frames = codec.append_frames(graphics, assembly, candidate_rows(documents))
    need([r["frame_id"] for r in frames] == [23,24,25,26], "four exact append roles")
    newasm, mirrors = mirror.append_mirrored_records(newgfx, newasm, (23,24,25))
    need(len(newgfx) == 3584 and sha(newgfx) == "742d9dc34d4cb80482d25b50c4b38bdff5e70be3823c4fed6932c8ff4ab398cc",
         "deterministic reviewed112tile component")
    need(len(newasm) == 1200 and sha(newasm) == "eec00f69cb58127732f5f3096c8107877522dfcd3ddeabe4946f88c4ab6ba25b",
         "deterministic reviewed30frame component")
    need(newgfx[:len(graphics)] == graphics and newasm[:len(assembly)] == assembly, "installed prefix preserved")
    return newgfx, newasm, {"frames": frames, "mirrors": mirrors, "graphics_tiles": 112, "assembly_frames": 30}


def encode_helpers(source):
    """Narrow independent opcode encoder; Asar must reproduce these bytes."""
    roots = {"Pc07DirectKoFrameV1": 0x490000, "Pc07StatusKoSelectorV1": 0x490080}
    single = {"php":8,"pha":0x48,"phx":0xDA,"plx":0xFA,"pla":0x68,"plp":0x28,"rtl":0x6B}
    branches = {"bcc":0x90,"bcs":0xB0,"bne":0xD0}
    operands = {"cpx.w #":(0xE0,2),"cmp.b #":(0xC9,1),"lda.b #":(0xA9,1),
                "lda.l ":(0xAF,3),"ldx.b ":(0xA6,1),"sta.b ":(0x85,1),"ldy.b ":(0xA4,1)}
    result = {}; current = None
    for raw in source.splitlines():
        line = raw.split(";",1)[0].strip()
        if not line: continue
        if line.endswith(":"):
            label = line[:-1]
            if label in roots:
                need(label not in result, "duplicate helper root")
                current = {"data":bytearray(),"labels":{},"branches":[],"instructions":[],"cpu_start":roots[label]}
                result[label] = current
            elif label.endswith("End"):
                need(current is not None, "unexpected end label")
                current["labels"][label] = len(current["data"]); current = None
            else:
                need(current is not None and label not in current["labels"], "unscoped/duplicate label")
                current["labels"][label] = len(current["data"])
            continue
        need(current is not None, "instruction outside helper")
        at = len(current["data"])
        if line in single: chunk = bytes([single[line]])
        elif line.split()[0] in branches:
            mnemonic,label = line.split(); current["branches"].append((at,label))
            chunk = bytes([branches[mnemonic],0])
        elif re.fullmatch(r"lda\.l \$[0-9A-Fa-f]{6},x",line):
            chunk = b"\xBF" + int(line[7:-2],16).to_bytes(3,"little")
        else:
            matches = [(p,v) for p,v in operands.items() if line.startswith(p)]
            need(len(matches) == 1, "unsupported helper instruction")
            prefix,(opcode,size) = matches[0]; value = line[len(prefix):]
            need(re.fullmatch(r"\$[0-9A-Fa-f]+",value), "literal helper operand")
            chunk = bytes([opcode]) + int(value[1:],16).to_bytes(size,"little")
        current["data"].extend(chunk)
        current["instructions"].append({"cpu":current["cpu_start"]+at,"bytes":len(chunk),"source":line})
    need(set(result) == set(roots), "exact two helper roots")
    for name,row in result.items():
        for at,label in row.pop("branches"):
            relative = row["labels"][label] - at - 2
            need(-128 <= relative <= 127, "helper branch outside rel8")
            row["data"][at+1] = relative & 255
        row["data"] = bytes(row["data"])
        need(len(row["data"]) == (74 if name == "Pc07DirectKoFrameV1" else 82), "fixed helper extent")
        expected = ("9da0bb3218bf7e03d795c070b4273fbbb3ac12af39cbc71f93ba18608ea5f27b" if name == "Pc07DirectKoFrameV1"
                    else "9a959feacec315f499322ab05b397ae7fb381ab13c44d6b5a7186cac5301500d")
        need(sha(row["data"]) == expected, "fixed independently reviewed helper semantics")
    return result


def assemble_components(directory):
    """Asar sees only new original-source .bin components, never a game image."""
    directory = resolve(directory.relative_to(ROOT).as_posix())
    need(not directory.exists(), "fresh assembly directory")
    read_pin(ASAR)
    ko_path, tile_path = "asm/pc07_battle_pose_ko_v1.asm", "asm/pc07_schala_tile_bank_v3.asm"
    ko_raw, tile_raw = resolve(ko_path).read_bytes(), resolve(tile_path).read_bytes()
    ko_source = ko_raw.decode("utf-8"); helpers = encode_helpers(ko_source)
    items = []
    for name,row in helpers.items():
        body = ko_source.split(name+":",1)[1].split(name+"End:",1)[0]
        items.append((name,row["cpu_start"],name+":"+body+name+"End:\n",row["data"]))
    items.append(("Pc07SchalaTileBankV3",0x413000,tile_raw.decode("utf-8"),None))
    directory.mkdir(parents=True,exist_ok=False)
    components = {}; evidence = []
    for name,cpu,body,expected in items:
        wrapper = f"arch 65816\nnorom\norg $000000\nbase ${cpu:06X}\n" + body
        asm = directory/(name+".asm"); binary = directory/(name+".bin")
        asm.write_text(wrapper,encoding="utf-8",newline="\n"); binary.write_bytes(b"")
        command = [str(resolve(ASAR["path"])),"--no-title-check","--fix-checksum=off",str(asm),str(binary)]
        run = subprocess.run(command,cwd=directory,capture_output=True,timeout=30,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        (directory/(name+".stdout.txt")).write_bytes(run.stdout)
        (directory/(name+".stderr.txt")).write_bytes(run.stderr)
        need(run.returncode == 0, "Asar component failure: "+name)
        data = binary.read_bytes(); need(0 < len(data) <= 256, "bounded original component")
        if expected is not None: need(data == expected, "Asar/opcode-encoder mismatch")
        components[name] = data
        evidence.append({"name":name,"cpu_start":cpu,"bytes":len(data),"sha256":sha(data),
                         "wrapper_sha256":sha(wrapper.encode()),"returncode":run.returncode,
                         "stdout_sha256":sha(run.stdout),"stderr_sha256":sha(run.stderr)})
    labels = {name:{"cpu_start":r["cpu_start"],"bytes":len(r["data"]),"hex":r["data"].hex(),
                   "labels":{k:r["cpu_start"]+v for k,v in r["labels"].items()},"instructions":r["instructions"]}
              for name,r in helpers.items()}
    return components, {"assembler":ASAR,"components":evidence,"helpers":labels,
                        "source_inputs":[source_identity(ko_path,ko_raw),source_identity(tile_path,tile_raw)]}


def expected_role(facing, selector, before, delays):
    if selector == 5: return (bytes([29 if facing == 2 else 25]) if facing in (2,3) else before), delays
    if selector == 0x31: return bytes(([27,28] if facing == 2 else [23,24]) if facing in (2,3) else [facing,facing]), bytes([2,3])
    if selector == 0x32: return (bytes([28 if facing == 2 else 24]) if facing in (2,3) else before), delays
    if selector == 0xF0: return bytes([26]), bytes([25])
    return before, delays


def stream_audit(source, target):
    records = []
    oldtiming, newtiming = source[TIMING:TIMING+STRIDE], target[TIMING:TIMING+STRIDE]
    for facing in range(4):
        start = PRIMARY+facing*STRIDE
        old, new = source[start:start+STRIDE], target[start:start+STRIDE]
        for selector in range(256):
            before, after = tokens(old,selector,255), tokens(new,selector,255)
            olddelays, delays = tokens(oldtiming,selector,0), tokens(newtiming,selector,0)
            expected, expected_delays = expected_role(facing,selector,before,olddelays)
            need(after == expected and delays == expected_delays, "selector ownership violation")
            need(len(after) == len(delays) and all(v < 30 for v in after), "frame/timing validity")
            if selector in CHANGED_SELECTORS:
                records.append({"facing":facing,"selector":selector,"before_frames":list(before),
                                "frames":list(after),"before_delays":list(olddelays),"delays":list(delays)})
    return {"entrypoints_checked":1024,"changed_selectors":list(CHANGED_SELECTORS),
            "unchanged_selectors_per_facing":252,"assembly_frame_count":30,"bindings":records,
            "selector07_08_unchanged":True,"run06_alternate17_and_preparation26_unchanged":True,
            "attack31_original_total":5,"attack31_new_total":5,"attack32_total":5,
            "evidence_level":"static-stream-reachability-not-native-consumer-proof"}


def derive(source, graphics, assembly, components):
    need(type(source) is bytes and len(source) == SIZE, "eight-MiB current source")
    need(source[:0x10000] == source[0x400000:0x410000], "inherited boot mirror")
    target = bytearray(source); sections = []
    def put(name,start,data):
        need(type(data) is bytes and data and 0 <= start < start+len(data) <= SIZE, "bounded immutable payload")
        target[start:start+len(data)] = data; sections.append((name,start,len(data)))
    for name,start,end in NEW_ALLOCATIONS:
        need(source[start:end] == b"\xFF"*(end-start), "new named allocation preimage: "+name)
    need(graphics[:79*32] == source[GFX:GFX+79*32] and assembly[:23*40] == source[ASSEMBLY:ASSEMBLY+23*40],
         "original component prefixes changed")
    put("pc07-battle-pose-graphics-append",GFX+79*32,graphics[79*32:])
    put("pc07-battle-pose-assembly-append",ASSEMBLY+23*40,assembly[23*40:])
    for name,start,preimage,payload in HOOKS:
        need(source[start:start+4] == preimage, "exact whole-instruction hook preimage")
        put(name,start,payload)
    put("pc07-direct-ko-helper",0x490000,components["Pc07DirectKoFrameV1"])
    put("pc07-status-ko-helper",0x490080,components["Pc07StatusKoSelectorV1"])
    tile = components["Pc07SchalaTileBankV3"]
    need(tile.count(bytes.fromhex("E0E10D")) == 1, "single new tile-bound instruction")
    oldtile = tile.replace(bytes.fromhex("E0E10D"),bytes.fromhex("E0C109"),1)
    need(source[0x413000:0x413000+len(tile)] == oldtile, "entire inherited tile adapter identity")
    bound = tile.index(bytes.fromhex("E0E10D"))+1
    put("pc07-tile-bank-payload-bound",0x413000+bound,tile[bound:bound+2])
    for facing in range(4):
        base = PRIMARY+facing*STRIDE
        for selector in CHANGED_SELECTORS:
            old = tokens(source[base:base+STRIDE],selector,255)
            delays = tokens(source[TIMING:TIMING+STRIDE],selector,0)
            need(old == (bytes([18]) if selector == 5 else bytes([facing])) and delays == bytes([5]),
                 "fixed existing battle selector preimage")
            frames,_ = expected_role(facing,selector,old,delays)
            if frames != old:
                put(f"pc07-primary-{selector:02x}-facing{facing}",base+selector*4,frames+b"\xFF")
    put("pc07-timing-31",TIMING+0x31*4,bytes([2,3,0]))
    put("pc07-timing-f0",TIMING+0xF0*4,bytes([25,0]))
    checksum = sum(target)&0xFFFF
    pair = (checksum^0xFFFF).to_bytes(2,"little")+checksum.to_bytes(2,"little")
    for name,start in (("checksum-primary",0xFFDC),("checksum-mirror",0x40FFDC)): put(name,start,pair)
    need(sum(target)&0xFFFF == checksum and target[:0x10000] == target[0x400000:0x410000], "checksum/mirror")
    return bytes(target), sorted(sections,key=lambda r:r[1])


@contextmanager
def source_snapshot(assembly_directory):
    global _ACTIVE
    need(_ACTIVE is None, "nested snapshot refused")
    source = read_pin(SOURCE); parent = json.loads(read_pin(PARENT))
    need(parent["emitted"] is True and parent["target"] == {k:SOURCE[k] for k in ("bytes","sha256")}
         and parent["manifest"]["output"] == SOURCE["path"], "immediate parent binding")
    need(parent["current_shared_intent"]["status"] == "metadata-valid"
         and parent["current_shared_diff"]["status"] == "images-valid"
         and parent["current_shared_diff"]["complete_diff_coverage"] is True, "accepted immediate parent")
    allocation = qualify_allocations()
    graphics, assembly, art_report = encode_art(source,[json.loads(read_pin(r)) for r in ART])
    components, assembly_report = assemble_components(assembly_directory)
    target, sections = derive(source,graphics,assembly,components)
    _ACTIVE = {"source":source,"target":target,"target_sha256":sha(target),"sections":sections,
               "streams":stream_audit(source,target),"allocation":allocation,"art":art_report,"assembly":assembly_report}
    try: yield _ACTIVE
    finally: _ACTIVE = None


def inputs():
    need(_ACTIVE is not None, "one active current-operation snapshot required")
    return _ACTIVE


def qualify_allocations():
    census = json.loads(read_pin(CENSUS))
    need(census["schema"] == "epoch-private-battle-pose-allocation-census-v1"
         and census["current_parent"] == SOURCE and census["new_allocations_disjoint"] is True
         and census["FF_alone_is_authority"] is False, "accepted allocation provenance")
    fill = census["inherited_expanded_fill"]
    need(fill == {"start":0x410000,"end":0x7E0000,"fill":255}, "inherited scaffold extent")
    need(len(census["occupied_spans"]) == 117, "complete accepted occupied census")
    expected = [(start,end) for _,start,end in NEW_ALLOCATIONS]
    actual = [(r["file_start"],r["file_end_exclusive"]) for r in census["new_allocations"]]
    need(actual == expected, "exact private new allocations")
    rows = []
    for name,start,end in NEW_ALLOCATIONS:
        need(fill["start"] <= start < end <= fill["end"], "expanded allocation outside inherited fill")
        for old in census["occupied_spans"]:
            need(old["file_end_exclusive"] == old["file_start"] + old["bytes"], "occupied span extent")
            need(max(start,old["file_start"]) >= min(end,old["file_end_exclusive"]), "occupied allocation overlap")
        rows.append({"id":name,"file_start":start,"bytes":end-start,"file_end_exclusive":end})
    return {"accepted_census":CENSUS,"inherited_expanded_fill":fill,"new_allocations":rows,
            "occupied_spans_checked":117,"all_disjoint":True,"production_approval":False}


def template(output):
    output_path(output); snap = inputs()
    rows = [{"id":name,"file_start":start,"bytes":size,
             "preimage_sha256":sha(snap["source"][start:start+size]),
             "target_sha256":sha(snap["target"][start:start+size])} for name,start,size in snap["sections"]]
    return {"schema":SCHEMA,"source":SOURCE,"accepted_parent_receipt":PARENT,"art_inputs":list(ART),
            "target":{"bytes":SIZE,"sha256":snap["target_sha256"]},"output":output,"sections":rows,
            "named_allocation_provenance":snap["allocation"],"stream_audit":snap["streams"],
            "new_frames":[23,24,25,26,27,28,29],"original_frame_prefix_preserved":23,
            "original_tile_prefix_preserved":79,"production_approval":False,"native_execution":False,
            "evidence_level":"guarded-private-static-battle-pose-append"}


def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest) == encoded(template(manifest.get("output"))), "fixed battle-pose manifest")
    return {"status":"metadata-valid","schema":SCHEMA,"manifest_sha256":sha(encoded(manifest)),"production_approval":False}


def audit_images(manifest, source, target):
    validate_manifest(manifest); snap = inputs()
    need(type(source) is bytes and source == snap["source"], "exact pinned current source")
    need(type(target) is bytes and target == snap["target"], "exact fixed battle-pose target")
    cursor = changed = 0; inverse = bytearray(target)
    for row in manifest["sections"]:
        start,end = row["file_start"],row["file_start"]+row["bytes"]
        need(start >= cursor and source[cursor:start] == target[cursor:start], "undeclared image change or overlap")
        changed += sum(a != b for a,b in zip(source[start:end],target[start:end]))
        inverse[start:end] = source[start:end]; cursor = end
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, "complete diff and inverse")
    for name,start,end in NPC_SPANS: need(source[start:end] == target[start:end], "original NPC changed: "+name)
    need(source[GFX:GFX+79*32] == target[GFX:GFX+79*32] and source[ASSEMBLY:ASSEMBLY+23*40] == target[ASSEMBLY:ASSEMBLY+23*40],
         "original art prefix changed")
    need(source[0x115F42:0x115F62] == target[0x115F42:0x115F62], "canonical direct KO table changed")
    return {"status":"images-valid","schema":SCHEMA,"declared_sections":len(manifest["sections"]),
            "changed_bytes":changed,"complete_diff_coverage":True,"inverse_restores_parent":True,
            "npc_protected_spans_unchanged":len(NPC_SPANS),"shared_palette_unchanged":True,
            "original_frame_prefix_preserved":23,"original_tile_prefix_preserved":79,
            "worldmap_unchanged":True,"canonical_direct_KO_table_unchanged":True,
            "production_approval":False,"native_execution":False}
