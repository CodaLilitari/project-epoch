-- Clean-ROM native field-entry observer. No ROM, WRAM, or CPU writes.
-- The approved checkpoint is replayed; this is not a direct coldboot run.
local W,S,M,C=emu.memType.snesWorkRam,emu.memType.snesSaveRam,emu.memType.snesMemory,emu.cpuType.snes
local out=assert(os.getenv('PE_FIELD_ENTRY_OUTPUT'))
local function readfile(p) local f=assert(io.open(p,'rb'));local b=f:read('*a');f:close();return b end
local function writefile(p,b) local f=assert(io.open(p,'wb'));assert(f:write(b));assert(f:close()) end
local state=readfile(assert(os.getenv('PE_FIELD_ENTRY_STATE')))
local expected_sram=readfile(assert(os.getenv('PE_FIELD_ENTRY_SRAM')))
local packet=readfile(assert(os.getenv('PE_FIELD_ENTRY_PACKET')))
local builtins=readfile(assert(os.getenv('PE_FIELD_ENTRY_BUILTINS')))
assert(#packet==2361 and #builtins==134 and #expected_sram==8192,'comparison input sizes')
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
local count,polls,exec_index=0,0,0
local preceding_exec_pc=nil
local function emit(row)
  count=count+1;if not done then assert(count<=300000,'field observation record budget') end
  row.n=count;row.poll=polls;assert(f:write(encode(row)..'\n'))
end
local function snapshot(label)
  writefile(out..'/'..label..'.wram.bin',bytes(0,0x20000,W))
  writefile(out..'/'..label..'.sram.bin',bytes(0,8192,S))
  writefile(out..'/'..label..'.png',emu.takeScreenshot())
  local row=context();row.kind='snapshot';row.label=label;emit(row)
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
emit({kind='header',schema='project-epoch-pc07-field-entry-v1',
  source_bundle=assert(os.getenv('PE_FIELD_ENTRY_BUNDLE')),rom_unmodified=true,
  debugger_state_writes=false,checkpoint_replay=true,playable_pc07=false})
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
  local c=cpu();assert(not c.emulationMode and c.d==0x100 and c.dbr==0 and (c.ps&0x30)==0x20,'field entry ABI')
  assert(emu.read16(0x100,W)==0x1DA,'selected location')
  field=true;snapshot('scene_entry')
end),emu.callbackType.exec,0xC00085,0xC00085,C,M)
emu.addMemoryCallback(checked(function()
  if not field then return end
  assert(not ready,'one canonical decompression return required')
  local c=cpu();assert(not c.emulationMode and c.d==0x100 and c.dbr==0 and (c.ps&0x30)==0x20,'event return ABI')
  local st=stack(c);assert(st:byte(1)+256*st:byte(2)==0x0111,'native stored return word')
  assert(emu.read16(0x100,W)==0x1DA,'event location')
  assert(bytes(0x12000,#packet,W)==packet,'canonical event packet mismatch')
  assert(bytes(0x13700,#builtins,W)==builtins,'canonical fixed builtins mismatch')
  ready=true;snapshot('canonical_event_ready')
  emit({kind='canonical-equality',packet_bytes=#packet,builtin_bytes=#builtins,stored_return=0x0111})
end),emu.callbackType.exec,0xC05D36,0xC05D36,C,M)
emu.addMemoryCallback(checked(function()
  if not field then return end
  assert(ready and not returned,'native decompression caller return')
  returned=true;emit({kind='decompression-caller-return',context=context()})
end),emu.callbackType.exec,0xC00112,0xC00112,C,M)

-- Dedicated loaders in this canonical packet reach the same active-role path.
-- Generic80 entry is observed if reached; its absence is not fabricated.
local sites={0xC0008E,0xC056C5,0xC05709,0xC0595C,
  0xC041E4,0xC041EC,0xC041F4,0xC041FC,0xC04204,0xC0420C,0xC04214,
  0xC0421E,0xC0426A,0xC04281,0xC0429C,0xC04310,0xC043C3,0xC043C5,
  0xC043D7,0xC043DA,0xC043DC,0xC043EC,0xC0448D,
  0xC0607E,0xC06109,0xC061E9,0xC061FE,0xC06214,0xC06225,0xC06229,
  0xC0623B,0xC06122,0xC061AF,0xC0616D,0xC06186,0xC0618C,0xC0618F,0xC06193,0xC06196}
for _,pc in ipairs(sites) do
  emu.addMemoryCallback(checked(function()
    if not field then return end
    local row=context();row.kind='exec';row.site=pc;row.exec_index=exec_index;emit(row)
  end),emu.callbackType.exec,pc,pc,C,M)
end
local function watch(op,a,b,t,phase)
  emu.addMemoryCallback(checked(function(address,value)
    if not field or (phase=='ready' and not ready) then return end
    local p=assert(emu.convertAddress(address,M,C),'bus conversion')
    assert(p.memType==t and p.address>=a and p.address<=b,'bus physical range')
    emit({kind='bus',operation=op,address=address,physical=p.address,memory=t==S and 'SRAM' or 'WRAM',
      value=value,cpu_observed=cpu(),preceding_exec_pc=preceding_exec_pc,exec_index=exec_index})
    if t==S then error('SRAM write outside field scope') end
  end),op=='read' and emu.callbackType.read or emu.callbackType.write,a,b,C,t)
end
for _,r in ipairs({{0x18D,0x19C},{0xA00,0xAFF},{0xB87,0xB8C},{0x1000,0x107F},
  {0x1100,0x15FF},{0x1800,0x18FF},{0x1C00,0x1C7F},{0x2600,0x287F},
  {0x2980,0x2989},{0x29AF,0x29AF},{0x10580,0x109FF}}) do watch('write',r[1],r[2],W,'field') end
for _,op in ipairs({'read','write'}) do
  watch(op,0x12000,0x12000+#packet-1,W,'ready')
  watch(op,0x13700,0x13700+#builtins-1,W,'ready')
end
watch('write',0,8191,S,'field')
for _,pc in ipairs({0xC10000,0xC28000,0xC20000,0xFFF9FB,0xFFFAA3,0xFFFB3B}) do
  emu.addMemoryCallback(checked(function() if field then error('engine path outside selected field scope') end end),emu.callbackType.exec,pc,pc,C,M)
end
emu.addEventCallback(checked(function()
  if loaded and not load_hook_removed then
    emu.removeMemoryCallback(load_hook,emu.callbackType.exec,0,0xFFFFFF,C,M);load_hook_removed=true
  end
  if not started then return end;polls=polls+1
  assert(bytes(0,8192,S)==expected_sram,'SRAM snapshot drift')
  if field then assert(emu.read16(0x100,W)==0x1DA,'location transition outside scope') end
  local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
  input.left=polls>=120 and polls<=131;input.right=polls>=180 and polls<=191
  emu.setInput(input,0)
  if polls==90 or polls==150 or polls==210 or polls==300 then
    assert(returned,'entry sequence not complete before movement snapshots');snapshot('poll_'..polls)
  end
  if polls==300 then finish(nil) end
end),emu.eventType.inputPolled)
