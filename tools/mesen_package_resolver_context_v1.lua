-- Original read-only observer: bounded ordinary game replay and ISR context.
-- Memory callbacks return no value. No emu.write or CPU-state edit is used.
local SCHEMA="project-epoch-package-resolver-context-v1"
assert(os.getenv("PE_RESOLVER_PROTOCOL")==SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,"rb")); local b=f:read("*a"); f:close(); return b
end
local state_bytes=read_file(assert(os.getenv("PE_RESOLVER_STATE")))
local trace_path=assert(os.getenv("PE_RESOLVER_TRACE"))
local CPU,MEM,WRAM=emu.cpuType.snes,emu.memType.snesMemory,emu.memType.snesWorkRam
local records,loaded,seen,ready,done,poll={},false,false,false,false,0
local resolver_active,action_active=false,false
local contexts,next_context={},0
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
    f:close(); emu.stop(message==nil and 52 or 93)
end
local function snapshot(kind,address,value)
    assert(#records<32768,"observation bound")
    local s=emu.getState(); local cpu,timing={},{}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k); cpu[k]=s['cpu.'..k]
    end
    -- These exact numeric keys were observed in the pinned Mesen 2.1.1 runtime.
    for _,k in ipairs({'masterClock','memoryManager.masterClock','cpu.cycleCount',
        'frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}) do
        assert(type(s[k])=='number','missing timing field '..k); timing[k]=s[k]
    end
    local stack,trampolines,w={},{},{}
    for i=1,12 do stack[i]=emu.read((cpu.sp+i)&0xFFFF,MEM) end
    for i=0,7 do trampolines[i+1]=emu.read(0x500+i,MEM) end
    for _,a in ipairs({0x007C,0x007D,0x007E,0x007F,0x0080,0x0082,0x5D9B,0x9876,0x9877,
        0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,0x95D5,0x95DC,0x06E2,0x06E6,0x06E7,
        0xA43F,0x2980,0x2981,0x2982,0xCD01,0xCD02}) do w[string.format('%04X',a)]=emu.read(a,WRAM) end
    local ctx=contexts[#contexts]
    records[#records+1]={kind=kind,address=address,value=value or -1,poll=poll,cpu=cpu,stack=stack,
        wram=w,timing=timing,trampolines=trampolines,context_id=ctx and ctx.id or 0,
        context_kind=ctx and ctx.kind or 'main',context_depth=#contexts,
        resolver_active=resolver_active,action_active=action_active,
        selector_word=emu.read16(0x9877,WRAM),branch_word=emu.read16(0xA0B3,WRAM),
        mask0_word=emu.read16(0x0080,WRAM),mask1_word=emu.read16(0x0082,WRAM),root_word=emu.read16(0x9878,WRAM)}
end
local watched={
    [0xC1409C]='branch-producer-complete',[0xC14612]='resolver-entry',
    [0xC14616]='canonical-continuation',[0xC1467F]='resolver-tail',
    [0xC14833]='common-loader-entry',[0xC148EB]='common-loader-rts',
    [0xC1432B]='dispatcher-rts',[0xC140B0]='caller-resume',
    [0xC140CE]='caller-package-latch',[0xC140E7]='caller-effect-latch',
    [0xC14CF3]='terminal-command-clear',[0xC14D00]='sync-command-increment',
    [0xCD160E]='nmi-effect-latch-read',[0xCD164D]='nmi-effect-latch-clear',
    [0xCD0C99]='nmi-mode-dispatch',[0xCD16AF]='nmi-scene-dispatch',
    [0xCEEEAE]='irq-display-stack-lowpoint',
    [0xC1E922]='special-result-alternate-store',[0xC1E951]='special-result-alternate-store',
    [0xC1F1C0]='exhausted-mask-alternate-store'
}
local entries={[0xD1E77C]='normal-nmi',[0xD1FE97]='battle-irq',[0xD1F4C0]='alternate-nmi'}
local exits={[0xD1E898]='normal-nmi',[0xD1FEF3]='battle-irq',[0xD1F558]='alternate-nmi'}
local load_hook
load_hook=emu.addMemoryCallback(function()
    local ok,err=pcall(function()
        if not loaded then loaded=true; emu.loadSavestate(state_bytes); return end
        seen=true
    end)
    if not ok then finish(tostring(err)) end
end,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
local function protect(f)
    return function(...)
        if ready and not done then
            local ok,err=pcall(f,...); if not ok then finish(tostring(err)) end
        end
    end
end
for address,kind in pairs(entries) do
    emu.addMemoryCallback(protect(function()
        next_context=next_context+1
        contexts[#contexts+1]={id=next_context,kind=kind}
        snapshot('interrupt-entry',address,-1)
    end),emu.callbackType.exec,address,address,CPU,MEM)
end
for address,kind in pairs(exits) do
    emu.addMemoryCallback(protect(function()
        assert(#contexts>0 and contexts[#contexts].kind==kind,'unpaired interrupt return')
        snapshot('interrupt-rti',address,-1); contexts[#contexts]=nil
    end),emu.callbackType.exec,address,address,CPU,MEM)
end
for address,kind in pairs(watched) do
    emu.addMemoryCallback(protect(function()
        if kind=='branch-producer-complete' then action_active=false end
        if kind=='resolver-entry' then resolver_active=true; action_active=true end
        snapshot(kind,address,-1)
        if kind=='resolver-tail' then resolver_active=false end
    end),emu.callbackType.exec,address,address,CPU,MEM)
end
emu.addMemoryCallback(protect(function(a,v)
    if resolver_active then snapshot('publication-write',a,v) end
end),emu.callbackType.write,0x7E5DAC,0x7E5DFC,CPU,MEM)
for _,address in ipairs({0x7E9876,0x7E5D9B,0x7EAE94}) do
    emu.addMemoryCallback(protect(function(a,v) snapshot('latch-or-flag-write',a,v) end),emu.callbackType.write,address,address,CPU,MEM)
end
-- WRAM physical callbacks include low-bank direct-page mirrors.
for _,range in ipairs({{0x80,0x83},{0x4000,0x407F}}) do
    for _,op in ipairs({'read','write'}) do
        emu.addMemoryCallback(protect(function(a,v)
            if resolver_active or (action_active and #contexts>0) then snapshot('temporary-'..op,a,v) end
        end),emu.callbackType[op],range[1],range[2],CPU,WRAM)
    end
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
        elseif ready then poll=poll+1 end
        input.down=poll>=20 and poll<=23
        input.a=(poll>=60 and poll<=63) or (poll>=100 and poll<=103) or (poll>=140 and poll<=143)
        emu.setInput(input,0)
        if ready and (poll==40 or poll==80 or poll==120 or poll==160) then snapshot('menu-observation',0,-1) end
    end)
    if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
    if ready and not done and poll>=1200 then
        local ok,err=pcall(snapshot,'terminal',0,-1)
        if ok then finish(nil) else finish(tostring(err)) end
    end
end,emu.eventType.endFrame)
