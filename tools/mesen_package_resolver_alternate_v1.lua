-- Original read-only CPU/memory observer for one ordinary player-Tech action.
-- Only savestate loading and an enumerated joypad sequence affect emulation.
local SCHEMA = "project-epoch-package-resolver-alternate-v1"
assert(os.getenv("PE_RESOLVER_PROTOCOL") == SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,"rb")); local b=f:read("*a"); f:close(); return b
end
local state_bytes=read_file(assert(os.getenv("PE_RESOLVER_STATE")))
local trace_path=assert(os.getenv("PE_RESOLVER_TRACE"))
local output_path=assert(os.getenv("PE_ALTERNATE_OUTPUT"))
local CPU,MEM,WRAM=emu.cpuType.snes,emu.memType.snesMemory,emu.memType.snesWorkRam
local records,loaded,seen,ready,done,frame={},false,false,false,false,0
local resolver_active=false
local function encode(v)
    if type(v)=="string" then return '"'..v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')..'"' end
    if type(v)=="boolean" or type(v)=="number" then return tostring(v) end
    if v==nil then return "null" end
    local parts={}
    if #v>0 then
        for _,x in ipairs(v) do parts[#parts+1]=encode(x) end
        return '['..table.concat(parts,',')..']'
    end
    local keys={}; for k,_ in pairs(v) do keys[#keys+1]=k end; table.sort(keys)
    for _,k in ipairs(keys) do parts[#parts+1]=encode(k)..':'..encode(v[k]) end
    return '{'..table.concat(parts,',')..'}'
end
local function finish(message)
    if done then return end
    done=true
    local f=assert(io.open(trace_path,"wb"))
    f:write('{"schema":'..encode(SCHEMA)..',"error":'..encode(message)..',"records":'..(#records==0 and '[]' or encode(records))..'}\n')
    f:close(); emu.stop(message==nil and 51 or 92)
end
local function snapshot(kind,address,value)
    assert(#records<16384,"observation bound")
    local s=emu.getState(); local cpu,timing={},{}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k); cpu[k]=s['cpu.'..k]
    end
    for _,k in ipairs({'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}) do
        assert(type(s[k])=='number','missing timing field '..k); timing[k]=s[k]
    end
    local stack={}
    for i=1,12 do stack[i]=emu.read((cpu.sp+i)&0xFFFF,MEM) end
    local w={}
    for _,a in ipairs({0x001A,0x001C,0x007E,0x007F,0x0080,0x0082,
        0x0100,0x0101,0x011F,0x0162,0x2980,0x2981,0x2982,
        0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
        0xAE95,0xAE96,0xAE99,0xAE9A,0xAEFF,0xAF00,0xAF01,
        0xB1F6,0xB1F7,0xB1FD,0xA6D9,0xA6DA,0xA6DB,0x95D5,0x95DC}) do
        w[string.format('%04X',a)]=emu.read(a,WRAM)
    end
    local target_base=emu.read16(0xB1F6,WRAM)
    local target_type=-1
    if target_base<=0x500 and target_base%0x80==0 then target_type=emu.read(0x5E46+target_base,WRAM) end
    records[#records+1]={kind=kind,address=address,value=value or -1,frame=frame,cpu=cpu,stack=stack,wram=w,timing=timing,target_type=target_type,
        selector_word=emu.read16(0x9877,WRAM),branch_word=emu.read16(0xA0B3,WRAM),
        mask0_word=emu.read16(0x0080,WRAM),mask1_word=emu.read16(0x0082,WRAM),root_word=emu.read16(0x9878,WRAM)}
end
local watched={
    [0xC1F132]='black-hole-entry',[0xC1F139]='black-hole-type-test',
    [0xC1F13F]='black-hole-rng-path',[0xC1F156]='black-hole-survivor',
    [0xC1F18B]='black-hole-mask-advance',[0xC1F1C0]='exhausted-mask-alternate-store',
    [0xC1409C]='branch-producer-complete',[0xC14612]='resolver-entry',
    [0xC14616]='canonical-continuation',[0xC1467F]='resolver-tail',[0xC14833]='common-loader-entry',
    [0xC148EB]='common-loader-rts',[0xC1432B]='dispatcher-rts',
    [0xC140B0]='caller-resume',[0xC140CE]='caller-package-latch',
    [0xC140E7]='caller-effect-latch',[0xC14CF3]='terminal-command-clear',
    [0xC14D00]='sync-command-increment'
}
local load_hook
load_hook=emu.addMemoryCallback(function()
    local ok,err=pcall(function()
        if not loaded then loaded=true; emu.loadSavestate(state_bytes); return end
        seen=true
    end)
    if not ok then finish(tostring(err)) end
end,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
for address,kind in pairs(watched) do
    emu.addMemoryCallback(function()
        if ready and not done then
            if kind=='resolver-entry' then resolver_active=true end
            local ok,err=pcall(snapshot,kind,address,-1)
            if kind=='resolver-tail' then resolver_active=false end
            if not ok then finish(tostring(err)) end
        end
    end,emu.callbackType.exec,address,address,CPU,MEM)
end
emu.addMemoryCallback(function(address,value)
    if ready and not done and resolver_active then
        local ok,err=pcall(snapshot,'publication-write',address,value)
        if not ok then finish(tostring(err)) end
    end
end,emu.callbackType.write,0x7E5DAC,0x7E5DFC,CPU,MEM)
for _,address in ipairs({0x7E9876,0x7E5D9B,0x7EAE94}) do
    emu.addMemoryCallback(function(a,value)
        if ready and not done then
            local ok,err=pcall(snapshot,'latch-write',a,value)
            if not ok then finish(tostring(err)) end
        end
    end,emu.callbackType.write,address,address,CPU,MEM)
end
emu.addEventCallback(function()
    if done then return end
    local ok,err=pcall(function()
        local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
        if seen and not ready then
            emu.removeMemoryCallback(load_hook,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
            assert(emu.read16(0x0100,WRAM)==0x01D1,'wrong checkpoint location')
            assert(emu.read(0x2980,WRAM)==6 and emu.read(0x2981,WRAM)==4 and emu.read(0x2982,WRAM)==3,'wrong checkpoint party')
            ready=true; snapshot('baseline',0,-1)
        elseif ready then frame=frame+1 end
        input.a=frame>=60 and frame<=1143 and ((frame-60)%120)<=3
        input.down=frame>=2040 and frame<=2043
        input.a=input.a or (frame>=2080 and frame<=2083)
        input.up=frame>=2120 and frame<=2399
        for i=0,5 do input.down=input.down or (frame>=2440+i*40 and frame<=2443+i*40) end
        input.a=input.a or (frame>=2720 and frame<=2723) or (frame>=2760 and frame<=2763)
        emu.setInput(input,0)
        if ready and (frame==2100 or frame==2680 or frame==3000) then snapshot('menu-observation',0,-1) end
    end)
    if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
local saved_screens={}
emu.addEventCallback(function()
    if ready and not done and (frame==2100 or frame==2680 or frame==3000) and not saved_screens[frame] then
        saved_screens[frame]=true
        local f=assert(io.open(output_path..'/menu_'..frame..'.png','wb')); f:write(emu.takeScreenshot()); f:close()
    end
    if ready and not done and frame>=4400 then
        local ok,err=pcall(snapshot,'terminal',0,-1)
        if ok then finish(nil) else finish(tostring(err)) end
    end
end,emu.eventType.endFrame)
