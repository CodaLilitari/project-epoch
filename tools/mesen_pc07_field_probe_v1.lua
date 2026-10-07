-- Separate emulator-assisted diagnostic, derived from frozen field-entry v1.
-- Replays the same checkpoint; explicit WRAM edits and one A-low substitution
-- are assistance, not an installed native graphics adapter or coldboot proof.
local W,S,M,C=emu.memType.snesWorkRam,emu.memType.snesSaveRam,emu.memType.snesMemory,emu.cpuType.snes
local out=assert(os.getenv('PE_FIELD_PROBE_OUTPUT'))
local function readfile(p) local f=assert(io.open(p,'rb'));local b=f:read('*a');f:close();return b end
local function writefile(p,b) local f=assert(io.open(p,'wb'));assert(f:write(b));assert(f:close()) end
local state=readfile(assert(os.getenv('PE_FIELD_PROBE_STATE')))
local expected_sram=readfile(assert(os.getenv('PE_FIELD_PROBE_SRAM')))
local packet=readfile(assert(os.getenv('PE_FIELD_PROBE_PACKET')))
local builtins=readfile(assert(os.getenv('PE_FIELD_PROBE_BUILTINS')))
local transformed=readfile(assert(os.getenv('PE_FIELD_PROBE_TRANSFORMED')))
local baseline_entry=readfile(assert(os.getenv('PE_FIELD_PROBE_ENTRY_PREIMAGE')))
local baseline_ready=readfile(assert(os.getenv('PE_FIELD_PROBE_READY_PREIMAGE')))
local new_record=readfile(assert(os.getenv('PE_FIELD_PROBE_RECORD')))
assert(#packet==2361 and #transformed==2553 and #builtins==134 and #expected_sram==8192,'comparison input sizes')
assert(#baseline_entry==0x20000 and #baseline_ready==0x20000 and #new_record==80,'stage input sizes')
local function slice(b,a,n) return b:sub(a+1,a+n) end
local function bytes(a,n,t) local b={};for i=0,n-1 do b[#b+1]=string.char(emu.read(a+i,t)) end;return table.concat(b) end
local function hex(b) return (b:gsub('.',function(c) return string.format('%02X',c:byte()) end)) end
local function encode(v)
  if type(v)=='string' then return '"'..v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')..'"' end
  if type(v)=='boolean' or type(v)=='number' then return tostring(v) end
  if v==nil then return 'null' end
  local keys,parts={},{};for k in pairs(v) do keys[#keys+1]=k end;table.sort(keys)
  for _,k in ipairs(keys) do parts[#parts+1]=encode(k)..':'..encode(v[k]) end
  return '{'..table.concat(parts,',')..'}'
end
local function cpu()
  local s=emu.getState();local c={}
  for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do c[k]=assert(s['cpu.'..k]~=nil) and s['cpu.'..k] end
  c.clock=assert(s['memoryManager.masterClock']);return c
end
local function stack(c)
  local b={};for i=1,16 do b[i]=string.char(emu.read((c.sp+i)&0xFFFF,M)) end
  return table.concat(b)
end
local function context()
  local c=cpu();local st=stack(c);local self=emu.read16((c.d+0x6D)&0xFFFF,M)
  local r={cpu=c,stack_after_sp_hex=hex(st),stored_near_return=st:byte(1)+256*st:byte(2),
    location=emu.read16(0x100,W),decompressed_size_0306=emu.read16(0x306,W),
    self_object_offset=self,roles_hex=hex(bytes(0x197,6,W)),
    roster_hex=hex(bytes(0x2980,9,W)),joined=emu.read(0x29AF,W),
    dp_d9_e6_hex=hex(bytes((c.d+0xD9)&0xFFFF,14,M))}
  if self<=0x7E and (self&1)==0 then
    r.self_role=emu.read(0x1100+self,W);r.self_logical_id=emu.read(0x1101+self,W)
    r.self_script_pointer=emu.read16(0x1180+self,W);r.self_call_wait=emu.read(0x10980+self,W)
  end
  -- At C0618C/C0618F and C06193/C06196 X is the call target, which
  -- can differ from DP6D (the caller). Keep its publication readback separate.
  if c.x<=0x7E and (c.x&1)==0 then
    r.x_indexed_script_pointer=emu.read16(0x1180+c.x,W)
    r.x_indexed_priority=emu.read(0x1C00+c.x,W)
    r.x_indexed_role=emu.read(0x1100+c.x,W);r.x_indexed_logical_id=emu.read(0x1101+c.x,W)
  end
  if c.y<=0x1780 then r.script_window_address=0x7F2001+c.y;r.script_window_hex=hex(bytes(0x12001+c.y,6,W)) end
  return r
end
local f=assert(io.open(out..'/events.jsonl','wb'))
local loaded,started,field,ready,returned,done=false,false,false,false,false,false
local injecting=false
local edit_count,control_count,window_count=0,0,0
local graphics_window=nil
local post_entry_expected={}
local count,polls,exec_index=0,0,0
local preceding_exec_pc=nil
local function emit(row)
  count=count+1;if not done then assert(count<=500000,'field probe record budget') end
  row.n=count;row.poll=polls;assert(f:write(encode(row)..'\n'))
end
local function snapshot(label)
  writefile(out..'/'..label..'.wram.bin',bytes(0,0x20000,W))
  writefile(out..'/'..label..'.sram.bin',bytes(0,8192,S))
  writefile(out..'/'..label..'.png',emu.takeScreenshot())
  local row=context();row.kind='snapshot';row.label=label;row.actors={}
  for role=0,2 do
    local o=emu.read16(0x197+2*role,W)
    if o<=0x7E and (o&1)==0 then row.actors['role'..role]={object_offset=o,
      logical_id=emu.read(0x1101+o,W),role=emu.read(0x1100+o,W),
      x=emu.read16(0x1800+o,W),y=emu.read16(0x1880+o,W)} end
  end
  emit(row)
end
local function same_cpu(before,after,allowed_a)
  for k,v in pairs(before) do
    if k:sub(1,4)=='cpu.' then
      assert(after[k]~=nil,'CPU field disappeared')
      assert(after[k]==((k=='cpu.a' and allowed_a~=nil) and allowed_a or v),'undeclared CPU change '..k)
    end
  end
  for k in pairs(after) do if k:sub(1,4)=='cpu.' then assert(before[k]~=nil,'CPU field appeared') end end
  assert(before['memoryManager.masterClock']==after['memoryManager.masterClock'],'debugger edit advanced clock')
end
local function cpu_map(state)
  local r={};for k,v in pairs(state) do if k:sub(1,4)=='cpu.' then r[k]=v end end
  r['memoryManager.masterClock']=state['memoryManager.masterClock'];return r
end
local function inject(label,address,preimage,replacement)
  assert(#preimage==#replacement and bytes(address,#preimage,W)==preimage,'injection preimage '..label)
  injecting=true
  for i=1,#replacement do
    local a=address+i-1;local old=preimage:byte(i);local new=replacement:byte(i)
    emit({kind='injection',label=label,physical=a,before=old,after=new,memory='WRAM',cpu=cpu()})
    emu.write(a,new,W)
    assert(emu.read(a,W)==new,'injection readback '..label)
    emit({kind='injection-readback',label=label,physical=a,value=emu.read(a,W)})
  end
  injecting=false
end
local function preserved()
  assert(bytes(0x2600,560,W)==slice(baseline_entry,0x2600,560),'original seven records changed')
  for _,r in ipairs(post_entry_expected) do assert(bytes(r.a,#r.data,W)==r.data,'protected range '..r.name) end
  assert(bytes(0,8192,S)==expected_sram,'SRAM changed')
end
local function finish(err)
  if done then return end;done=true
  if err then writefile(out..'/failure.txt',tostring(err)..'\n') end
  -- No cleanup mutation. Every later deferred-stop instruction is excluded.
  emit({kind=err and 'failure' or 'success',error=err,cpu=cpu()})
  f:flush();f:close();emu.stop(err and 91 or 63)
end
local function checked(fn)
  return function(...) if done then return end;local ok,err=pcall(fn,...);if not ok then finish(tostring(err)) end end
end
emit({kind='header',schema='project-epoch-pc07-field-probe-v1',
  source_bundle=assert(os.getenv('PE_FIELD_PROBE_BUNDLE')),rom_unmodified=true,
  emulator_assisted=true,debugger_wram_writes=true,debugger_A_low_edit=true,
  installed_native_adapter=false,checkpoint_replay=true,playable_pc07=false,
  write_coverage='declared ranges only; no global WRAM reconciliation'})
local load_hook,load_hook_removed
load_hook=emu.addMemoryCallback(checked(function()
  if loaded then return end
  assert(emu.loadSavestate(state),'checkpoint replay refused')
  local c=cpu();assert(c.k==0xC2 and c.pc==0xE657,'checkpoint caller PC')
  loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,C,M)
emu.addMemoryCallback(checked(function(address)
  if not field then return end
  preceding_exec_pc=address;exec_index=exec_index+1
end),emu.callbackType.exec,0,0xFFFFFF,C,M)
emu.addMemoryCallback(checked(function()
  assert(loaded and not started,'native-load return sequencing')
  assert(bytes(0,8192,S)==expected_sram,'SRAM at load return')
  started=true;emit({kind='native-load-return',context=context()})
end),emu.callbackType.exec,0xC2E65B,0xC2E65B,C,M)
emu.addMemoryCallback(checked(function()
  assert(started and not field,'one fresh field entry required')
  local c=cpu();assert(not c.emulationMode and c.d==0x100 and c.dbr==0 and (c.ps&0x30)==0x20 and c.sp==0x6FF,'field entry ABI')
  assert(emu.read16(0x100,W)==0x1DA,'selected location')
  field=true;snapshot('scene_entry')
  local before=emu.getState()
  assert(bytes(0x2600,560,W)==slice(baseline_entry,0x2600,560),'original-record entry preimage')
  local donor=bytes(0x2600,80,W);local hp=donor:byte(4)+256*donor:byte(5)
  assert(donor:byte(1)==0 and hp>1 and new_record:byte(1)==7,'candidate record identity/HP')
  assert(new_record:byte(4)+256*new_record:byte(5)==hp-1,'distinct candidate HP')
  for i=2,80 do if i~=4 and i~=5 then assert(new_record:byte(i)==donor:byte(i),'candidate donor equality') end end
  assert(bytes(0x2C80,0x90,W)==slice(baseline_entry,0x2C80,0x90),'candidate and guard entry preimage')
  inject('compatibility-copy',0x2CA0,slice(baseline_entry,0x2CA0,80),slice(baseline_entry,0x2830,80))
  inject('separate-PC07-record',0x2830,slice(baseline_entry,0x2830,80),new_record)
  inject('roster',0x2980,string.char(0,1,2,0x82,0x80,4,3,6,5),string.char(0,1,7,2,0x80,4,3,6,5))
  inject('joined',0x29AF,string.char(0xFE),string.char(0xFF))
  post_entry_expected={{name='PC07',a=0x2830,data=new_record},
    {name='compatibility',a=0x2CA0,data=slice(baseline_entry,0x2830,80)},
    {name='low-guard',a=0x2C80,data=slice(baseline_entry,0x2C80,32)},
    {name='high-guard',a=0x2CF0,data=slice(baseline_entry,0x2CF0,32)},
    {name='roster',a=0x2980,data=string.char(0,1,7,2,0x80,4,3,6,5)},
    {name='joined',a=0x29AF,data=string.char(0xFF)}}
  same_cpu(before,emu.getState());preserved();snapshot('entry_staged')
end),emu.callbackType.exec,0xC00085,0xC00085,C,M)
emu.addMemoryCallback(checked(function()
  if not field then return end
  assert(not ready,'one canonical decompression return required')
  local c=cpu();assert(not c.emulationMode and c.d==0x100 and c.dbr==0 and c.ps==0x27 and c.sp==0x6FB and c.a==0xFFFF and c.x==0x5D6E and c.y==0x3786,'event return ABI')
  local st=stack(c);assert(st:byte(1)+256*st:byte(2)==0x0111,'native stored return word')
  assert(emu.read16(0x100,W)==0x1DA,'event location')
  assert(bytes(0x12000,#packet,W)==packet,'canonical event packet mismatch')
  assert(bytes(0x13700,#builtins,W)==builtins,'canonical fixed builtins mismatch')
  assert(emu.read16(0x306,W)==2361,'canonical decompressed length')
  assert(bytes(0x12000,0x1700,W)==slice(baseline_ready,0x12000,0x1700),'complete event arena preimage')
  snapshot('canonical_event_ready')
  emit({kind='canonical-equality',packet_bytes=#packet,builtin_bytes=#builtins,stored_return=0x0111})
  local before=emu.getState()
  inject('transformed-event',0x12000,slice(baseline_ready,0x12000,#transformed),transformed)
  inject('decompressed-length',0x306,string.char(0x39,0x09),string.char(0xF9,0x09))
  assert(bytes(0x13700,#builtins,W)==builtins,'event injection changed builtins')
  same_cpu(before,emu.getState());ready=true;preserved();snapshot('event_staged')
end),emu.callbackType.exec,0xC05D36,0xC05D36,C,M)
emu.addMemoryCallback(checked(function()
  if not field then return end
  assert(ready and not returned,'native decompression caller return')
  assert(cpu().sp==0x6FD,'actual caller SP');returned=true;emit({kind='decompression-caller-return',context=context()})
end),emu.callbackType.exec,0xC00112,0xC00112,C,M)

-- Dedicated loaders in this canonical packet reach the same active-role path.
-- Generic80 entry is observed if reached; its absence is not fabricated.
local sites={0xC0008E,0xC056C5,0xC05709,0xC0595C,
  0xC041E4,0xC041EC,0xC041F4,0xC041FC,0xC04204,0xC0420C,0xC04214,
  0xC0421E,0xC0426A,0xC04281,0xC0429C,0xC042B8,0xC04310,0xC043C3,0xC043C5,
  0xC043D7,0xC043DA,0xC043DC,0xC043DF,0xC043EC,0xC0448D,0xC04556,
  0xC0607E,0xC06109,0xC061E9,0xC061FE,0xC06214,0xC06225,0xC06229,
  0xC0623B,0xC06122,0xC061AF,0xC0616D,0xC06186,0xC0618C,0xC0618F,0xC06193,0xC06196}
for _,pc in ipairs(sites) do
  emu.addMemoryCallback(checked(function()
    if not field then return end
    local row=context();row.kind='exec';row.site=pc;row.exec_index=exec_index;emit(row)
  end),emu.callbackType.exec,pc,pc,C,M)
end
emu.addMemoryCallback(checked(function()
  if not field then return end
  assert(ready and returned,'graphics before event staging/return')
  local c=cpu();local self=emu.read16(0x16D,W)
  local logical=emu.read(0x1101+self,W);local role=emu.read(0x1100+self,W)
  local candidate=(c.a&0xFF)==7
  local control=self==2 and logical==0 and role==0
  if not candidate and not control then return end
  assert(graphics_window==nil,'nested graphics window')
  assert(not c.emulationMode and c.d==0x100 and c.dbr==0 and (c.ps&0x30)==0x20 and c.sp==0x6F7,'graphics native ABI')
  for _,root in ipairs({{0x1AF,0xE42000},{0x1B2,0xE42300},{0x1B5,0xE42600},{0x1B8,0xE42800}}) do
    assert(emu.read16(root[1],W)+0x10000*emu.read(root[1]+2,W)==root[2],'canonical donor pointer root')
  end
  local st=stack(c)
  assert(st:byte(1)+256*st:byte(2)==(candidate and 0x43DE or 0x42B7),'graphics actual caller frame')
  if candidate then
    assert(edit_count==0 and self==0x10 and c.x==0x10 and c.y==0x734,'candidate graphics context')
    assert(logical==7 and role==2 and emu.read16(0x19B,W)==0x10 and emu.read(0x2982,W)==7,'candidate identity/role')
    local before=emu.getState();local replacement=before['cpu.a']&0xFF00
    emu.setState({['cpu.a']=replacement})
    local after=emu.getState();same_cpu(before,after,replacement)
    edit_count=edit_count+1
    emit({kind='cpu-edit',field='cpu.a',before=cpu_map(before),after=cpu_map(after),
      reason='qualified logical07 graphics donor0 diagnostic; hidden B preserved'})
  else
    assert(control_count==0 and c.x==2 and c.y==0x2E2 and (c.a&0xFF)==0,'original00 negative control')
    control_count=control_count+1
    emit({kind='graphics-negative-control',context=context(),cpu_edit=false})
  end
  window_count=window_count+1
  graphics_window={id=window_count,kind=candidate and 'candidate07' or 'original00',self=self,
    return_pc=candidate and 0xC043DF or 0xC042B8,
    y_exit=candidate and 0x735 or 0x2E3,entry_sp=c.sp,descriptor_count=0,pointer_read_count=0,first_store=false,pre_rts=false}
  emit({kind='graphics-window-start',window=graphics_window.id,which=graphics_window.kind,context=context()})
end),emu.callbackType.exec,0xC0448D,0xC0448D,C,M)
emu.addMemoryCallback(checked(function()
  if not graphics_window then return end
  local w=graphics_window;local c=cpu()
  assert(w.first_store and w.descriptor_count==5 and w.pointer_read_count==14,'graphics hardware/descriptor/pointer coverage')
  assert(c.a==0x2001 and c.x==w.y_exit and c.y==w.y_exit and c.sp==w.entry_sp,'graphics native result')
  assert(c.d==0x100 and c.dbr==0 and (c.ps&0x31)==0x21,'graphics native result ABI')
  assert(emu.read(0x1101+w.self,W)==(w.kind=='candidate07' and 7 or 0),'graphics changed logical identity')
  assert(emu.read(0x1100+w.self,W)==(w.kind=='candidate07' and 2 or 0),'graphics changed active role')
  w.pre_rts=true;emit({kind='graphics-pre-rts',window=w.id,which=w.kind,context=context()})
end),emu.callbackType.exec,0xC04556,0xC04556,C,M)
for _,return_pc in ipairs({0xC042B8,0xC043DF}) do
  emu.addMemoryCallback(checked(function()
    if not graphics_window then return end
    local w=graphics_window;local c=cpu()
    assert(return_pc==w.return_pc,'wrong graphics caller return')
    assert(w.pre_rts and c.sp==w.entry_sp+2 and c.a==0x2001 and c.x==w.y_exit and c.y==w.y_exit,'actual graphics caller return')
    emit({kind='graphics-return',window=w.id,which=w.kind,context=context()});graphics_window=nil
  end),emu.callbackType.exec,return_pc,return_pc,C,M)
end
local descriptor_order={0xE4F001,0xE4F002,0xE4F003,0xE4F004,0xE4F000}
local descriptor_pc={0xC044A0,0xC044C3,0xC044E4,0xC0450D,0xC04518}
local pointer_order={0xE42300,0xE42301,0xE42302,0xE42602,0xE42603,0xE42600,0xE42601,
  0xE42600,0xE42601,0xE42800,0xE42801,0xE42000,0xE42001,0xE42002}
local pointer_pc={0xC044B1,0xC044B1,0xC044BC,0xC044F1,0xC044F1,0xC044F6,0xC044F6,
  0xC044FF,0xC044FF,0xC04504,0xC04504,0xC04529,0xC04529,0xC04534}
emu.addMemoryCallback(checked(function(address,value)
  if not graphics_window then return end
  local w=graphics_window
  emit({kind='graphics-hardware-write',window=w.id,which=w.kind,address=address,value=value,
    preceding_exec_pc=preceding_exec_pc,cpu=cpu()})
  if preceding_exec_pc==0xC0448D then
    assert(address==0x4202 and value==0 and not w.first_store,'native selector store after diagnostic edit')
    w.first_store=true
  end
end),emu.callbackType.write,0x4202,0x4203,C,M)
for _,range in ipairs({{0xE4F000,0xE4F027},{0xE42000,0xE42002},{0xE42300,0xE42302},
                       {0xE42600,0xE42603},{0xE42800,0xE42801}}) do
  emu.addMemoryCallback(checked(function(address,value)
    if not graphics_window then return end
    local w=graphics_window
    emit({kind='graphics-rom-read',window=w.id,which=w.kind,address=address,value=value,
      preceding_exec_pc=preceding_exec_pc,cpu=cpu()})
    if address>=0xE4F000 and address<=0xE4F027 then
      w.descriptor_count=w.descriptor_count+1;local i=w.descriptor_count
      assert(address==descriptor_order[i] and preceding_exec_pc==descriptor_pc[i],'canonical donor0 descriptor route')
    else
      w.pointer_read_count=w.pointer_read_count+1;local i=w.pointer_read_count
      assert(address==pointer_order[i] and preceding_exec_pc==pointer_pc[i],'canonical donor0 pointer-table route')
    end
  end),emu.callbackType.read,range[1],range[2],C,M)
end
local function watch(op,a,b,t,phase)
  emu.addMemoryCallback(checked(function(address,value)
    if not field or (phase=='ready' and not ready) then return end
    local p=assert(emu.convertAddress(address,M,C),'bus conversion')
    assert(p.memType==t and type(p.address)=='number' and p.address>=a and p.address<=b,'bus physical range')
    emit({kind='bus',operation=op,address=address,physical=p.address,memory=t==S and 'SRAM' or 'WRAM',
      value=value,origin=injecting and 'debugger-injection-callback' or 'observed-game-bus',
      cpu_observed=cpu(),preceding_exec_pc=preceding_exec_pc,exec_index=exec_index})
    if t==S then error('SRAM write outside field scope') end
    if op=='write' and not injecting then
      if p.address>=0x2600 and p.address<0x2830 then
        assert(value==baseline_entry:byte(p.address+1),'game write changes an original record')
      end
      for _,r in ipairs(post_entry_expected) do
        if p.address>=r.a and p.address<r.a+#r.data then
          assert(value==r.data:byte(p.address-r.a+1),'game write changes protected '..r.name)
        end
      end
    end
  end),op=='read' and emu.callbackType.read or emu.callbackType.write,a,b,C,t)
end
for _,r in ipairs({{0x18D,0x19C},{0x306,0x307},{0xA00,0xAFF},{0xB87,0xB8C},
  {0xC00,0xC7F},{0x1000,0x107F},{0x1100,0x16FF},{0x1800,0x18FF},{0x1C00,0x1C7F},
  {0x2600,0x287F},{0x2980,0x2989},{0x29AF,0x29AF},{0x2C80,0x2D0F},
  {0x10580,0x109FF},{0x12000,0x13785}}) do watch('write',r[1],r[2],W,'field') end
for _,op in ipairs({'read','write'}) do
  -- Writes are registered once above; reads here stay inside declared ranges.
  if op=='read' then
    for _,r in ipairs({{0x2600,0x287F},{0x2C80,0x2D0F},{0x12000,0x13785}}) do
      watch(op,r[1],r[2],W,'ready')
    end
  end
end
watch('write',0,8191,S,'field')
for _,pc in ipairs({0xC00000,0xC001A5,0xC10000,0xC28000,0xC20000,0xFFF9FB,0xFFFAA3,0xFFFB3B}) do
  emu.addMemoryCallback(checked(function() if field then error('engine path outside selected field scope') end end),emu.callbackType.exec,pc,pc,C,M)
end
emu.addEventCallback(checked(function()
  if loaded and not load_hook_removed then
    emu.removeMemoryCallback(load_hook,emu.callbackType.exec,0,0xFFFFFF,C,M);load_hook_removed=true
  end
  if not started then return end;polls=polls+1
  assert(bytes(0,8192,S)==expected_sram,'SRAM snapshot drift')
  if field then assert(emu.read16(0x100,W)==0x1DA,'location transition outside scope');preserved() end
  local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
  input.left=polls>=120 and polls<=167;input.right=polls>=220 and polls<=267
  emu.setInput(input,0)
  if polls==90 or polls==180 or polls==280 or polls==400 then
    assert(returned and edit_count==1 and control_count==1 and graphics_window==nil,'native graphics sequence incomplete')
    assert(bytes(0x197,6,W)==string.char(2,0,4,0,16,0),'persistent active-role pointers')
    snapshot('poll_'..polls)
  end
  if polls==400 then finish(nil) end
end),emu.eventType.inputPolled)
