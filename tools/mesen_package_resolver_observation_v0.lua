-- Original read-only CPU/memory observer for one ordinary player-Tech action.
-- Only savestate loading and an enumerated joypad sequence affect emulation.
local SCHEMA = "project-epoch-package-resolver-observation-v0"
assert(os.getenv("PE_RESOLVER_PROTOCOL") == SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,"rb")); local b=f:read("*a"); f:close(); return b
end
local state_bytes=read_file(assert(os.getenv("PE_RESOLVER_STATE")))
local trace_path=assert(os.getenv("PE_RESOLVER_TRACE"))
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
    assert(#records<4096,"observation bound")
    local s=emu.getState(); local cpu={}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k); cpu[k]=s['cpu.'..k]
    end
    local stack={}
    for i=1,8 do stack[i]=emu.read((cpu.sp+i)&0xFFFF,MEM) end
    local w={}
    for _,a in ipairs({0x0080,0x0082,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
                      0x95D5,0x95DC,0x06E2,0x06E6,0x06E7,0xA43F,0x2980,0x2981,0x2982}) do
        w[string.format('%04X',a)]=emu.read(a,WRAM)
    end
    records[#records+1]={kind=kind,address=address,value=value or -1,frame=frame,cpu=cpu,stack=stack,wram=w,
        selector_word=emu.read16(0x9877,WRAM),branch_word=emu.read16(0xA0B3,WRAM),
        mask0_word=emu.read16(0x0080,WRAM),mask1_word=emu.read16(0x0082,WRAM),root_word=emu.read16(0x9878,WRAM)}
end
local watched={
    [0xC1409C]='branch-producer-complete',[0xC14612]='resolver-entry',
    [0xC1467F]='resolver-tail',[0xC14833]='common-loader-entry',
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
for _,address in ipairs({0x7E9876,0x7E5D9B}) do
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
            assert(emu.read16(0x0100,WRAM)==0x01DB,'wrong checkpoint location')
            assert(emu.read(0x2980,WRAM)==0 and emu.read(0x2981,WRAM)==1 and emu.read(0x2982,WRAM)==2,'wrong checkpoint party')
            ready=true; snapshot('baseline',0,-1)
        elseif ready then frame=frame+1 end
        input.down=frame>=20 and frame<=23
        input.a=(frame>=60 and frame<=63) or (frame>=100 and frame<=103) or (frame>=140 and frame<=143)
        emu.setInput(input,0)
        if ready and (frame==40 or frame==80 or frame==120 or frame==160) then snapshot('menu-observation',0,-1) end
    end)
    if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
    if ready and not done and frame>=1200 then
        local ok,err=pcall(snapshot,'terminal',0,-1)
        if ok then finish(nil) else finish(tostring(err)) end
    end
end,emu.eventType.endFrame)
