-- V2 copied from frozen v1: only the residue observation boundary is extended.
-- Bounded menu relocation probe. Captured observations, not global ownership.
-- Private RAM preparation after the actual native load return; no CPU edits.
local W,S,M,C=emu.memType.snesWorkRam,emu.memType.snesSaveRam,emu.memType.snesMemory,emu.cpuType.snes
local mode=assert(os.getenv('PE_COMPAT_MENU_MODE'))
assert(mode=='control' or mode=='relocated')
local out=assert(os.getenv('PE_COMPAT_MENU_OUTPUT'))
local function readfile(p) local f=assert(io.open(p,'rb'));local b=f:read('*a');f:close();return b end
local function writefile(p,b) local f=assert(io.open(p,'wb'));assert(f:write(b));assert(f:close()) end
local state=readfile(assert(os.getenv('PE_COMPAT_MENU_STATE')))
local expected_sram=readfile(assert(os.getenv('PE_COMPAT_MENU_SRAM')))
local function bytes(a,n,t) local b={};for i=0,n-1 do b[#b+1]=string.char(emu.read(a+i,t)) end;return table.concat(b) end
local function put(a,b) for i=1,#b do emu.write(a+i-1,b:byte(i),W) end end
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
local f=assert(io.open(out..'/events.jsonl','wb'))
local active,done,injecting,loaded=false,false,false,false
local polls,count=0,0
local preceding_exec_pc,exec_index=nil,0
local original,marker=nil,nil
local function emit(row)
  count=count+1;assert(count<=200000,'record budget');row.n=count;row.poll=polls
  assert(f:write(encode(row)..'\n'))
end
local function snapshot(label)
  writefile(out..'/'..label..'.wram.bin',bytes(0,0x20000,W))
  writefile(out..'/'..label..'.sram.bin',bytes(0,8192,S))
  writefile(out..'/'..label..'.png',emu.takeScreenshot())
  emit({kind='snapshot',label=label,cpu=cpu(),menu=emu.read(0xA00,W),cursor=emu.read(0x411,W),location=emu.read16(0x100,W)})
end
local function restore()
  if active and mode=='relocated' then
    local compatibility=bytes(0x2CA0,80,W)
    injecting=true
    put(0x2830,compatibility);put(0x2CA0,string.rep('\0',80))
    injecting=false
    assert(bytes(0x2830,80,W)==compatibility and bytes(0x2CA0,80,W)==string.rep('\0',80),'cleanup readback')
  end
end
local function finish(err)
  if done then return end
  done=true
  if err then writefile(out..'/failure.txt',tostring(err)..'\n') end
  -- This is a cleanup boundary only: the relocated ROM remains active and
  -- all subsequent deferred-stop execution is excluded from the evidence.
  restore()
  if active then snapshot('cleanup') end
  emit({kind=err and 'failure' or 'success',error=err,cpu=cpu()})
  f:flush();f:close();emu.stop(err and 91 or 63)
end
local function checked(fn)
  return function(...)
    if done then return end
    local ok,err=pcall(fn,...);if not ok then finish(tostring(err)) end
  end
end
emit({kind='header',schema='project-epoch-compat-menu-v2',mode=mode,
      source_bundle=assert(os.getenv('PE_COMPAT_MENU_BUNDLE')),
      evidence='bounded-runtime-observation',full_wram_reconciliation=false,
      residue_scope='four physical bytes; preceding exec is not interrupt/DMA ownership'})
local load_hook
local load_hook_removed=false
load_hook=emu.addMemoryCallback(checked(function()
  if loaded then return end
  assert(emu.loadSavestate(state),'load refused')
  local c=cpu();assert(c.k==0xC2 and c.pc==0xE657,'restored caller PC')
  loaded=true
end),emu.callbackType.exec,0,0xFFFFFF,C,M)

-- Keep an actual preceding-exec identity, including instructions outside the
-- five witnesses. Hardware interrupt entry or DMA can intervene: this is a
-- context witness, never an assertion that this instruction owns a bus event.
emu.addMemoryCallback(checked(function(address)
  if not active then return end
  preceding_exec_pc=address;exec_index=exec_index+1
end),emu.callbackType.exec,0,0xFFFFFF,C,M)

emu.addMemoryCallback(checked(function()
  assert(loaded and not active,'post-load sequencing')
  local c=cpu();assert(c.k==0xC2 and c.pc==0xE65B and c.d==0 and not c.emulationMode,'native return context')
  assert(bytes(0,8192,S)==expected_sram,'SRAM changed before post-load')
  assert(bytes(0x2C9C,100,W)==string.rep('\0',100),'candidate/guards not zero')
  assert(bytes(0x2980,9,W)==string.char(0,1,2,0x82,0x80,4,3,6,5),'seven-PC roster premise')
  snapshot('post_load')
  original=bytes(0x2830,80,W)
  local m={};for i=0,79 do m[#m+1]=string.char((19+73*i)&255) end;marker=table.concat(m)
  if mode=='relocated' then
    injecting=true;put(0x2CA0,original);put(0x2830,marker);injecting=false
    emit({kind='diagnostic-preparation',natural_start=0x2830,candidate_start=0x2CA0,size=80})
  end
  active=true;snapshot('prepared')
end),emu.callbackType.exec,0xC2E65B,0xC2E65B,C,M)

local function watch(kind,start,stop,t)
  emu.addMemoryCallback(checked(function(address,value)
    if not active or injecting then return end
    local converted=assert(emu.convertAddress(address,M,C),'address conversion missing')
    assert(converted.memType==t and type(converted.address)=='number','physical callback type mismatch')
    local a=converted.address
    assert(a>=start and a<=stop,'physical callback range mismatch')
    local c=cpu()
    emit({kind='bus',operation=kind,address=address,physical=a,value=value,cpu_observed=c})
    if t==S and kind=='write' then error('SRAM write outside selected menu scope') end
    if a>=0x2C9C and a<=0x2C9F or a>=0x2CF0 and a<=0x2CFF then error('guard access') end
    if mode=='relocated' and a>=0x2830 and a<=0x287F then error('unadapted natural compatibility access') end
    if mode=='control' and a>=0x2CA0 and a<=0x2CEF then error('unexpected control candidate access') end
  end),kind=='read' and emu.callbackType.read or emu.callbackType.write,start,stop,C,t)
end
for _,kind in ipairs({'read','write'}) do
  watch(kind,0x2830,0x287F,W);watch(kind,0x2C9C,0x2CFF,W)
end
watch('write',0x2600,0x282F,W);watch('write',0x2980,0x2989,W)
watch('write',0,8191,S)
-- These callbacks do not enter the frozen v1 bus projection or its guards.
-- All read/write values are retained, including unexpected source contexts.
local function watch_residue(kind,start,stop)
  emu.addMemoryCallback(checked(function(address,value)
    if not active or injecting then return end
    local converted=assert(emu.convertAddress(address,M,C),'residue conversion missing')
    assert(converted.memType==W and type(converted.address)=='number','residue callback type mismatch')
    local a=converted.address
    assert(a>=start and a<=stop,'residue callback range mismatch')
    assert(preceding_exec_pc~=nil and exec_index>0,'residue exec context missing')
    emit({kind='residue-bus',operation=kind,address=address,physical=a,value=value,
          cpu_observed=cpu(),preceding_exec_pc=preceding_exec_pc,exec_index=exec_index})
  end),kind=='read' and emu.callbackType.read or emu.callbackType.write,start,stop,C,W)
end
for _,kind in ipairs({'read','write'}) do
  watch_residue(kind,0x0A78,0x0A79)
  watch_residue(kind,0x12158,0x12159)
end
-- All are PRE-execution callbacks. The successor rows observe the prior
-- instruction's result before the successor executes; MVN successors occur
-- only when the whole block copy has completed.
local residue_sites={
  {0xC2821F,0x5A,'phy','before'},
  {0xC28220,0x08,'phy','successor'},
  {0xC28213,0x7A,'ply','before'},
  {0xC28214,0xFA,'ply','successor'},
  {0xC28403,0x4C,'terminal-sleep-jump','before'},
  {0xC00911,0x54,'restore-field-work','before'},
  {0xC00914,0xAB,'restore-field-work','successor'},
  {0xC00924,0x54,'save-field-work','before'},
  {0xC00927,0xAB,'save-field-work','successor'},
}
for _,site in ipairs(residue_sites) do
  local pc,opcode,role,phase=table.unpack(site)
  emu.addMemoryCallback(checked(function()
    if not active then return end
    assert(emu.read(pc,M)==opcode,'residue witness opcode drift')
    assert(preceding_exec_pc==pc,'residue exec callback ordering')
    emit({kind='residue-exec',site=pc,opcode=opcode,role=role,phase=phase,cpu=cpu(),
          exec_index=exec_index,stack_word=emu.read16(0x0A78,W),backup_word=emu.read16(0x12158,W)})
  end),emu.callbackType.exec,pc,pc,C,M)
end
for _,pc in ipairs({0xFFF86D,0xFFF9A2,0xC282E4,0xC282E7,0xC282EA,0xC2830E,0xC2B9AF}) do
  emu.addMemoryCallback(checked(function()
    if active then emit({kind='consumer',site=pc,cpu=cpu()}) end
  end),emu.callbackType.exec,pc,pc,C,M)
end
for _,pc in ipairs({0xFFF9FB,0xFFFAA3,0xFFFB3B}) do
  emu.addMemoryCallback(checked(function() if active then error('lifecycle outside selected scope') end end),emu.callbackType.exec,pc,pc,C,M)
end
emu.addMemoryCallback(checked(function() if active then error('execution in record/candidate') end end),emu.callbackType.exec,0x7E2830,0x7E287F,C,M)
emu.addMemoryCallback(checked(function() if active then error('execution in record/candidate') end end),emu.callbackType.exec,0x7E2C9C,0x7E2CFF,C,M)
local function pulse(p,n) return p==n or p==n+1 end
emu.addEventCallback(checked(function()
  -- This is outside memory callback-vector iteration. Never erase the active
  -- exec callback from inside itself in the pinned Mesen implementation.
  if loaded and not load_hook_removed then
    emu.removeMemoryCallback(load_hook,emu.callbackType.exec,0,0xFFFFFF,C,M)
    load_hook_removed=true
  end
  if not active then return end
  polls=polls+1
  if mode=='relocated' then assert(bytes(0x2830,80,W)==marker,'marker changed') end
  assert(bytes(0,8192,S)==expected_sram,'SRAM snapshot differs')
  local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
  input.x=pulse(polls,180)
  input.right=pulse(polls,420) or pulse(polls,510)
  input.a=pulse(polls,660)
  input.b=pulse(polls,960) or pulse(polls,1260)
  emu.setInput(input,0)
  if polls==150 or polls==390 or polls==630 or polls==900 or polls==1200 or polls==1500 then snapshot('poll_'..polls) end
  if polls==1500 then finish(nil) end
end),emu.eventType.inputPolled)
