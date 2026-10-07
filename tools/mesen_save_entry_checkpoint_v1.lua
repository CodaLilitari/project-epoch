-- Original clean-ROM save-entry acquisition. Only an exact disposable SRAM
-- initialization and enumerated controller inputs change emulated state.
-- Captures at its caller's JSL, then observes the native entry. A state saved
-- inside an exec callback resumes instruction execution without redispatching
-- that callback, so saving at FFF9FB itself would skip our entry observer.
local W,S,M,C=emu.memType.snesWorkRam,emu.memType.snesSaveRam,emu.memType.snesMemory,emu.cpuType.snes
local function readfile(p) local f=assert(io.open(p,'rb')); local b=f:read('*a');f:close();return b end
local function writefile(p,b) local f=assert(io.open(p,'wb'));assert(f:write(b));f:close() end
local out=assert(os.getenv('PE_SAVE_ENTRY_OUTPUT'))
local sram=readfile(assert(os.getenv('PE_SRAM_PATH')))
assert(#sram==8192 and emu.getMemorySize(S)==8192,'SRAM shape')
for i=1,#sram do emu.write(i-1,sram:byte(i),S) end
local state_path=os.getenv('PE_SAVE_ENTRY_STATE')
local state_bytes=state_path and readfile(state_path) or nil
local expected_wram=state_path and readfile(assert(os.getenv('PE_SAVE_ENTRY_EXPECT_WRAM'))) or nil
local expected_cpu=state_path and readfile(assert(os.getenv('PE_SAVE_ENTRY_EXPECT_CPU'))) or nil
local frame,anchor,done=0,state_path and -1 or nil,false
local checkpoint_captured=state_path~=nil
local rows={}
local function bytes(a,n,t) local b={};for i=0,n-1 do b[#b+1]=string.char(emu.read(a+i,t)) end;return table.concat(b) end
local function hex(b) return (b:gsub('.',function(c)return string.format('%02x',c:byte())end)) end
local function snap(kind)
  local st=emu.getState();local fields={kind,tostring(frame)}
  for _,key in ipairs({'cpu.k','cpu.pc','cpu.sp','cpu.ps','cpu.d','cpu.dbr','cpu.a','cpu.x','cpu.y','memoryManager.masterClock'}) do
    assert(type(st[key])=='number','missing '..key);fields[#fields+1]=key..'='..tostring(st[key])
  end
  fields[#fields+1]='location='..hex(bytes(0x100,2,W))
  fields[#fields+1]='roster='..hex(bytes(0x2980,9,W))
  fields[#fields+1]='slot='..tostring(emu.read(0x79,W))
  rows[#rows+1]=table.concat(fields,'\t')
end
local function finish(err)
  if done then return end;done=true
  snap(err and ('failure:'..err) or 'success')
  writefile(out..'/checkpoint.tsv',table.concat(rows,'\n')..'\n')
  writefile(out..'/endpoint.png',emu.takeScreenshot())
  emu.stop(err and 91 or 49)
end
emu.addMemoryCallback(function()
  if done or state_bytes then return end
  local ok,err=pcall(function()
    assert(not checkpoint_captured,'duplicate save caller')
    assert(anchor~=nil,'save caller before loaded-location anchor')
    local st=emu.getState()
    assert(st['cpu.k']==0xC2 and st['cpu.pc']==0xCF51,'save caller PC')
    snap('save-caller')
    writefile(out..'/save_entry.mss',emu.createSavestate())
    checkpoint_captured=true
  end)
  if not ok then finish(tostring(err)) end
end,emu.callbackType.exec,0xC2CF51,0xC2CF51,C,M)
if state_bytes then
  local loaded=false
  emu.addMemoryCallback(function()
    if not loaded then assert(emu.loadSavestate(state_bytes),'checkpoint load refused');loaded=true end
  end,emu.callbackType.exec,0,0xFFFFFF,C,M)
end
emu.addMemoryCallback(function()
  if done then return end
  local ok,err=pcall(function()
    assert(anchor~=nil,'save before expected field anchor')
    assert(checkpoint_captured,'missing prior save caller')
    local st=emu.getState()
    assert(st['cpu.k']==0xFF and st['cpu.pc']==0xF9FB,'save-entry PC')
    assert(st['cpu.d']==0 and st['cpu.dbr']==0x7E,'save-entry D/DBR')
    assert(st['cpu.emulationMode']==false,'native CPU required')
    assert(bytes((st['cpu.sp']+1)&0xFFFF,3,M)==string.char(0x54,0xCF,0xC2),'caller return frame')
    assert(emu.read(0x79,W)==0,'not slot1')
    assert(emu.read16(0x100,W)==0x1DA,'not Lavos Tunnel')
    assert(bytes(0x2980,9,W)==string.char(0,1,2,0x82,0x80,4,3,6,5),'roster drift')
    assert(bytes(0,8192,S)==sram,'save ran before capture')
    assert(bytes(0x2C9C,0x64,W)==string.rep('\0',0x64),'candidate or guards occupied')
    if expected_wram then assert(bytes(0,0x20000,W)==expected_wram,'fresh-state WRAM differs') end
    local cpu_lines={}
    for _,key in ipairs({'k','pc','sp','ps','d','dbr','a','x','y'}) do
      cpu_lines[#cpu_lines+1]=key..'='..tostring(st['cpu.'..key])
    end
    cpu_lines[#cpu_lines+1]='emulationMode='..tostring(st['cpu.emulationMode'])
    local cpu_text=table.concat(cpu_lines,'\n')..'\n'
    if expected_cpu then assert(cpu_text==expected_cpu,'fresh-state CPU tuple differs') end
    snap('save-entry')
    if state_bytes then writefile(out..'/save_entry.mss',state_bytes) end
    writefile(out..'/entry_wram.bin',bytes(0,0x20000,W))
    writefile(out..'/entry_sram.bin',bytes(0,8192,S))
    writefile(out..'/entry_cpu.txt',cpu_text)
    finish(nil)
  end)
  if not ok then finish(tostring(err)) end
end,emu.callbackType.exec,0xFFF9FB,0xFFF9FB,C,M)
local function pulse(n,start,width) return n>=start and n<start+width end
emu.addEventCallback(function()
  if done then return end
  local ok,err=pcall(function()
    frame=frame+1
    local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
    if not anchor then
      input.left=pulse(frame,1800,2);input.a=pulse(frame,2450,4)
      if emu.read16(0x100,W)==0x1DA and emu.read(0x11F,W)==1 and emu.read(0x162,W)==0 then
        assert(bytes(0x2980,9,W)==string.char(0,1,2,0x82,0x80,4,3,6,5),'field roster')
        anchor=frame;snap('loaded-location-anchor')
      end
    elseif not state_bytes then
      local r=frame-anchor
      -- The recovered save starts at a save point. A opens its menu,
      -- selects slot1, and confirms. Fixed released intervals avoid repeats.
      input.a=pulse(r,60,2) or pulse(r,700,2) or pulse(r,1100,2)
    end
    emu.setInput(input,0)
    if frame%600==0 then snap('probe') end
    if frame>=6500 then finish('save-entry timeout') end
  end)
  if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
