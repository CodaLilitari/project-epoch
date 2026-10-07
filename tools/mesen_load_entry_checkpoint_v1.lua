-- Original clean-ROM, selected-slot load-entry observer. All binaries private.
-- Cold boot initializes exact disposable SRAM and supplies controller input.
-- Replay restores the caller checkpoint, not a second cold boot. Restoring
-- inside an exec callback continues execution without redispatching that callback.
local W,S,M,C=emu.memType.snesWorkRam,emu.memType.snesSaveRam,emu.memType.snesMemory,emu.cpuType.snes
local function readfile(p) local f=assert(io.open(p,'rb'));local b=f:read('*a');f:close();return b end
local function writefile(p,b) local f=assert(io.open(p,'wb'));assert(f:write(b));assert(f:close()) end
local out=assert(os.getenv('PE_LOAD_ENTRY_OUTPUT'))
local sram=readfile(assert(os.getenv('PE_LOAD_ENTRY_SRAM')))
assert(#sram==8192 and emu.getMemorySize(S)==8192,'SRAM shape')
for i=1,#sram do emu.write(i-1,sram:byte(i),S) end
local state_path=os.getenv('PE_LOAD_ENTRY_STATE')
local state_bytes=state_path and readfile(state_path) or nil
local expected_wram=state_path and readfile(assert(os.getenv('PE_LOAD_ENTRY_EXPECT_WRAM'))) or nil
local expected_cpu=state_path and readfile(assert(os.getenv('PE_LOAD_ENTRY_EXPECT_CPU'))) or nil
local polls,done,captured,loaded=0,false,false,false
local active,validated=nil,false
local rows={}
local function bytes(a,n,t) local b={};for i=0,n-1 do b[#b+1]=string.char(emu.read(a+i,t)) end;return table.concat(b) end
local function hex(b) return (b:gsub('.',function(c)return string.format('%02x',c:byte())end)) end
local function source_unchanged() assert(bytes(0,8192,S)==sram,'SRAM differs before load entry') end
local function native(st)
  assert(st['cpu.emulationMode']==false and st['cpu.d']==0,'native D0 required')
end
local function frame(st)
  assert(st['cpu.sp']>=0 and st['cpu.sp']<=0x1FFC,'caller frame outside proved low-WRAM mirror')
  return bytes(st['cpu.sp']+1,3,M)
end
local function snap(kind,extra)
  local st=emu.getState();local fields={kind,tostring(polls)}
  for _,key in ipairs({'cpu.k','cpu.pc','cpu.sp','cpu.ps','cpu.d','cpu.dbr','cpu.a','cpu.x','cpu.y','memoryManager.masterClock'}) do
    assert(type(st[key])=='number','missing '..key);fields[#fields+1]=key..'='..tostring(st[key])
  end
  -- Absolute $0079 is the selected slot only inside the native D0 contract.
  -- Boot also calls this validator with D=$0400, where DP $79 means $0479.
  if st['cpu.d']==0 and st['cpu.emulationMode']==false then
    fields[#fields+1]='slot='..tostring(emu.read(0x79,W))
  else
    fields[#fields+1]='absolute_0079='..tostring(emu.read(0x79,W))
  end
  if extra then for _,item in ipairs(extra) do fields[#fields+1]=item end end
  rows[#rows+1]=table.concat(fields,'\t')
end
local function finish(err)
  if done then return end;done=true
  snap(err and ('failure:'..err) or 'success')
  writefile(out..'/checkpoint.tsv',table.concat(rows,'\n')..'\n')
  -- A replay can reach the entry before a rendered frame; an empty PNG is OK.
  writefile(out..'/endpoint.png',emu.takeScreenshot())
  emu.stop(err and 91 or 49)
end
local function callback(address,fn)
  emu.addMemoryCallback(function()
    if done then return end
    local ok,err=pcall(fn)
    if not ok then finish(tostring(err)) end
  end,emu.callbackType.exec,address,address,C,M)
end

-- Observe only slot 0. Other preview slots are outside this bounded witness.
callback(0xFFF9C4,function()
  if state_bytes then return end
  local st=emu.getState()
  if st['cpu.d']~=0 then
    assert(not active and not validated,'outside-D0 validation after selected-slot witness began')
    local extra={'scope=outside-D0','emulationMode='..tostring(st['cpu.emulationMode'])}
    -- These optional observations do not extend the selected-slot contract.
    if st['cpu.emulationMode']==false then
      local address=(st['cpu.d']+0x79)&0xFFFF
      extra[#extra+1]='dp79_address='..address
      if address<=0x1FFF then extra[#extra+1]='dp79_value='..emu.read(address,W) end
      if st['cpu.sp']>=0 and st['cpu.sp']<=0x1FFC then extra[#extra+1]='return_frame='..hex(frame(st)) end
    end
    snap('outside-scope-validation',extra)
    return
  end
  native(st)
  if emu.read(0x79,W)~=0 then assert(not active,'nested validation');return end
  assert(not active,'nested selected-slot validation')
  source_unchanged()
  active={sp=st['cpu.sp'],dbr=st['cpu.dbr'],return_frame=frame(st),compared=false}
  validated=false
  snap('validation-entry',{'return_frame='..hex(active.return_frame)})
end)
callback(0xFFF9E3,function()
  if state_bytes or not active then return end
  local st=emu.getState();native(st);source_unchanged()
  assert(emu.read(0x79,W)==0 and st['cpu.x']==0,'checksum slot/index')
  assert(st['cpu.dbr']==0x30 and (st['cpu.ps']&0x30)==0,'checksum CPU context')
  assert(not active.compared,'duplicate checksum comparison')
  local stored=sram:byte(0x1FF1)+256*sram:byte(0x1FF2)
  local magic=sram:byte(0x1FF9)+256*sram:byte(0x1FFA)
  assert(magic==0xE41B,'selected-slot magic')
  assert(st['cpu.a']==stored,'native selected-slot checksum mismatch')
  active.compared=true
  snap('validation-compare',{'stored_checksum='..stored,'magic='..magic})
end)
callback(0xFFF9FA,function()
  if state_bytes or not active then return end
  local st=emu.getState();native(st);source_unchanged()
  assert(emu.read(0x79,W)==0,'validation slot changed')
  assert(active.compared and emu.read16(0,W)==0,'selected-slot validation refused')
  assert(st['cpu.sp']==active.sp and st['cpu.dbr']==active.dbr and frame(st)==active.return_frame,'validation return context')
  snap('validation-return',{'result=0','return_frame='..hex(frame(st))})
  active=nil;validated=true
end)
callback(0xC2E657,function()
  if state_bytes then return end
  assert(not captured and not active and validated,'missing completed native selected-slot validation')
  local st=emu.getState();native(st);source_unchanged()
  assert(st['cpu.k']==0xC2 and st['cpu.pc']==0xE657,'load caller PC')
  assert(emu.read(0x79,W)==0,'load caller slot')
  snap('load-caller')
  writefile(out..'/load_entry.mss',emu.createSavestate())
  captured=true
end)
if state_bytes then
  emu.addMemoryCallback(function()
    if done or loaded then return end
    local ok,err=pcall(function()
      assert(emu.loadSavestate(state_bytes),'checkpoint load refused')
      local st=emu.getState();native(st)
      assert(st['cpu.k']==0xC2 and st['cpu.pc']==0xE657,'restored caller PC')
      loaded=true;captured=true
      snap('checkpoint-restored')
    end)
    if not ok then finish(tostring(err)) end
  end,emu.callbackType.exec,0,0xFFFFFF,C,M)
end
callback(0xFFFAA3,function()
  assert(captured and (not state_bytes or loaded),'missing caller checkpoint')
  local st=emu.getState();native(st);source_unchanged()
  assert(st['cpu.k']==0xFF and st['cpu.pc']==0xFAA3,'load-entry PC')
  assert(st['cpu.dbr']==0x7E and (st['cpu.ps']&0x30)==0x30,'load-entry DBR/widths')
  assert(frame(st)==string.char(0x5A,0xE6,0xC2),'load caller return frame')
  assert(emu.read(0x79,W)==0,'load-entry slot')
  local cpu_lines={}
  for _,key in ipairs({'k','pc','sp','ps','d','dbr','a','x','y'}) do
    assert(type(st['cpu.'..key])=='number','missing CPU '..key)
    cpu_lines[#cpu_lines+1]=key..'='..tostring(st['cpu.'..key])
  end
  cpu_lines[#cpu_lines+1]='emulationMode=false'
  local cpu_text=table.concat(cpu_lines,'\n')..'\n'
  local wram=bytes(0,0x20000,W)
  if expected_wram then assert(wram==expected_wram,'fresh-state WRAM differs') end
  if expected_cpu then assert(cpu_text==expected_cpu,'fresh-state CPU tuple differs') end
  snap('load-entry',{'return_frame='..hex(frame(st))})
  if state_bytes then writefile(out..'/load_entry.mss',state_bytes) end
  writefile(out..'/entry_wram.bin',wram)
  writefile(out..'/entry_sram.bin',bytes(0,8192,S))
  writefile(out..'/entry_cpu.txt',cpu_text)
  finish(nil)
end)
local function pulse(n,start,width) return n>=start and n<start+width end
emu.addEventCallback(function()
  if done then return end
  local ok,err=pcall(function()
    polls=polls+1
    local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
    if not state_bytes then input.left=pulse(polls,1800,2);input.a=pulse(polls,2450,4) end
    emu.setInput(input,0)
    if polls%600==0 then snap('probe') end
    if polls>=6500 then finish('load-entry timeout') end
  end)
  if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
