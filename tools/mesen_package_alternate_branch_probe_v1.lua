-- Original read-only CPU/memory observer for one ordinary player-Tech action.
-- Only savestate loading and an enumerated joypad sequence affect emulation.
local SCHEMA = "project-epoch-package-alternate-branch-probe-v1"
assert(os.getenv("PE_RESOLVER_PROTOCOL") == SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,"rb")); local b=f:read("*a"); f:close(); return b
end
local state_bytes=read_file(assert(os.getenv("PE_RESOLVER_STATE")))
local trace_path=assert(os.getenv("PE_RESOLVER_TRACE"))
local output_path=assert(os.getenv("PE_ALTERNATE_OUTPUT"))
local route=assert(os.getenv("PE_ALTERNATE_ROUTE"))
assert(route=="baseline-menu" or route=="marle-menu" or route=="marle-provoke" or route=="lucca-hypnowave" or route=="crono-spincut" or route=="crono-spincut-left" or route=="crono-spincut-right" or route=="spekkio-talk" or route=="spekkio-robo-menu" or route=="spekkio-robo-rocket" or route=="spekkio-magus-black-hole")
local spekkio=route:find("spekkio-",1,true)==1
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
    local s=emu.getState(); local cpu={}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k); cpu[k]=s['cpu.'..k]
    end
    local stack={}
    for i=1,8 do stack[i]=emu.read((cpu.sp+i)&0xFFFF,MEM) end
    local w={}
    for _,a in ipairs({0x5e67,0x5e68,0x5ee7,0x5ee8,0x5f67,0x5f68,0x5fe7,0x5fe8,0x6067,0x6068,0x60e7,0x60e8,0x6167,0x6168,0x61e7,0x61e8,0x6267,0x6268,0x62e7,0x62e8,0x6367,0x6368,0x0016,0x0018,0x001A,0x001C,0xB1F4,0xB1F5,0xB1F6,0xB1F7,0xB1FD,0xAD8D,0xAD8E,0xAD8F,0xAD90,0xAECC,0xAECD,0xAECE,0x0080,0x0082,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
                      0xA6D9,0xA6DA,0xA6DB,0x95D5,0x95DB,0x95DC,0x95E0,0x95E1,0x95E2,0x95E3,0x95E4,0x95E5,0x95E6,0x95E7,0x95E8,0x95E9,0x95EA,0x95EB,0x95EC,0xA6DD,0x06E2,0x06E6,0x06E7,0xA43F,0x2980,0x2981,0x2982}) do
        w[string.format('%04X',a)]=emu.read(a,WRAM)
    end
    for _,a in ipairs({0x0100,0x0101,0x011F,0x0162}) do w[string.format('%04X',a)]=emu.read(a,WRAM) end
    records[#records+1]={kind=kind,address=address,value=value or -1,frame=frame,cpu=cpu,stack=stack,wram=w,
        selector_word=emu.read16(0x9877,WRAM),branch_word=emu.read16(0xA0B3,WRAM),
        mask0_word=emu.read16(0x0080,WRAM),mask1_word=emu.read16(0x0082,WRAM),root_word=emu.read16(0x9878,WRAM)}
end
local watched={
    [0xC1DC64]='hit-percentage-entry',[0xC1DC99]='hit-roll-compare',[0xC1DCA8]='hit-roll-result',[0xC1E922]='special-result-alternate-store',[0xC1E951]='special-result-alternate-store',
    [0xC1F1C0]='exhausted-mask-alternate-store',[0xC1409C]='branch-producer-complete',[0xC14612]='resolver-entry',
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
            assert(emu.read16(0x0100,WRAM)==(spekkio and 0x01D1 or 0x01DB),'wrong checkpoint location')
            if spekkio then
                assert(emu.read(0x2980,WRAM)==6 and emu.read(0x2981,WRAM)==4 and emu.read(0x2982,WRAM)==3,'wrong Spekkio checkpoint party')
            else
                assert(emu.read(0x2980,WRAM)==0 and emu.read(0x2981,WRAM)==1 and emu.read(0x2982,WRAM)==2,'wrong checkpoint party')
            end
            ready=true; snapshot('baseline',0,-1)
        elseif ready then frame=frame+1 end
        local crono=route:find("crono-spincut",1,true)==1
        local delay=route=="lucca-hypnowave" and 540 or ((route=="marle-menu" or route=="marle-provoke") and 500 or 0)
        input.right=((route=="marle-menu" or route=="marle-provoke" or route=="lucca-hypnowave") and frame>=500 and frame<=503) or (route=="lucca-hypnowave" and frame>=540 and frame<=543)
        input.down=frame>=delay+20 and frame<=delay+23
        input.a=frame>=delay+60 and frame<=delay+63
        if route=="marle-provoke" or route=="lucca-hypnowave" then
            local shift=route=="lucca-hypnowave" and 40 or 0
            input.up=frame>=600+shift and frame<=879+shift
            input.down=input.down or (frame>=900+shift and frame<=903+shift)
            input.a=input.a or (frame>=980+shift and frame<=983+shift) or (frame>=1020+shift and frame<=1023+shift)
        end
        if crono then
            input.up=frame>=100 and frame<=379
            input.down=input.down or (frame>=400 and frame<=403) or (frame>=440 and frame<=443) or (frame>=480 and frame<=483)
            input.a=input.a or (frame>=520 and frame<=523) or (frame>=560 and frame<=563)
            input.left=route=="crono-spincut-left" and frame>=540 and frame<=543
            input.right=route=="crono-spincut-right" and frame>=540 and frame<=543
        end
        if spekkio then
            for k,_ in pairs(input) do input[k]=false end
            input.a=frame>=60 and frame<=(route=="spekkio-talk" and 1863 or 1143) and ((frame-60)%120)<=3
            if route~="spekkio-talk" then
                input.right=(frame>=2000 and frame<=2003) or (frame>=2020 and frame<=2023)
                input.down=frame>=2040 and frame<=2043
                input.a=input.a or (frame>=2080 and frame<=2083)
                if route=="spekkio-robo-rocket" then
                    input.up=frame>=2120 and frame<=2399
                    input.a=input.a or (frame>=2440 and frame<=2443) or (frame>=2480 and frame<=2483)
                end
            end
        end
        if route=="spekkio-magus-black-hole" then
            input.right=false
            input.up=frame>=2120 and frame<=2399
            for i=0,5 do input.down=input.down or (frame>=2440+i*40 and frame<=2443+i*40) end
            input.a=input.a or (frame>=2720 and frame<=2723) or (frame>=2760 and frame<=2763)
        end
        emu.setInput(input,0)
        if ready and (frame==40 or frame==80 or frame==400 or frame==500 or frame==540 or frame==580 or frame==880 or frame==960 or frame==1000 or frame==1040 or frame==1100 or frame==1800 or frame==2040 or frame==2100 or frame==2400 or frame==2440 or frame==2520 or frame==3000) then snapshot('menu-observation',0,-1) end
    end)
    if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
    if ready and not done and (frame==0 or frame==40 or frame==80 or frame==400 or frame==500 or frame==540 or frame==580 or frame==880 or frame==960 or frame==1000 or frame==1040 or frame==1100 or frame==1800 or frame==2040 or frame==2100 or frame==2400 or frame==2440 or frame==2520 or frame==3000) then
        local f=assert(io.open(output_path..'/menu_'..frame..'.png','wb')); f:write(emu.takeScreenshot()); f:close()
    end
    if ready and not done and frame>=(route=="spekkio-magus-black-hole" and 4400 or route=="spekkio-robo-rocket" and 4000 or ((spekkio or route=="marle-provoke" or route=="lucca-hypnowave" or route=="crono-spincut" or route=="crono-spincut-left" or route=="crono-spincut-right") and 2400 or (route=="marle-menu" and 600 or 90))) then
        local f=assert(io.open(output_path..'/menu_terminal.png','wb')); f:write(emu.takeScreenshot()); f:close()
        local ok,err=pcall(snapshot,'terminal',0,-1)
        if ok then finish(nil) else finish(tostring(err)) end
    end
end,emu.eventType.endFrame)
