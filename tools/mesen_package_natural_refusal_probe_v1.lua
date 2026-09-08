-- Original read-only CPU/memory observer for one ordinary player-Tech action.
-- Only savestate loading and an enumerated joypad sequence affect emulation.
local SCHEMA = "project-epoch-package-natural-refusal-probe-v1"
assert(os.getenv("PE_RESOLVER_PROTOCOL") == SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,"rb")); local b=f:read("*a"); f:close(); return b
end
local state_bytes=read_file(assert(os.getenv("PE_RESOLVER_STATE")))
local trace_path=assert(os.getenv("PE_RESOLVER_TRACE"))
local output_path=assert(os.getenv('PE_REFUSAL_OUTPUT'))
local route=assert(os.getenv('PE_NATURAL_REFUSAL_ROUTE'))
assert(route=='lavos-idle' or route=='lavos-cure-before-ko' or route=='lavos-cure-lucca-before-ko')
local CPU,MEM,WRAM=emu.cpuType.snes,emu.memType.snesMemory,emu.memType.snesWorkRam
local records,loaded,seen,ready,done,frame={},false,false,false,false,0
local resolver_active=false
local transaction_active,transaction_id=false,0
local return_hook=nil
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
    for i=1,16 do stack[i]=emu.read((cpu.sp+i)&0xFFFF,MEM) end
    local w={}
    for _,a in ipairs({0x0080,0x0082,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
                      0x95D5,0x95DC,0x06E2,0x06E6,0x06E7,0xA43F,0x2980,0x2981,0x2982}) do
        w[string.format('%04X',a)]=emu.read(a,WRAM)
    end
    for _,a in ipairs({0x0006,0x0007,0xAF22,0xAF23,0xB18B,0xB18C,0xB2EA,0xB2EB,0xB2EC,0xB3C8,0xB3F4,0xB3BA,0xB3BB,0xB3BC}) do
        w[string.format('%04X',a)]=emu.read(a,WRAM)
    end
    local regions={}
    for _,r in ipairs({{'battle_records',0x5E2D,0x580},{'queue',0x93EE,21},{'participant_map',0xB1BE,7},
        {'pending_results',0xB18E,0x30},{'target_result_work',0xAD89,0xC3},
        {'hp_pending_terms',0xB328,0x84},
        {'atb_rates',0xAFAB,11},{'atb_status',0xB03A,11},{'saved_rates',0xB158,11}}) do
        local bytes={}; for a=r[2],r[2]+r[3]-1 do bytes[#bytes+1]=string.format('%02x',emu.read(a,WRAM)) end
        regions[r[1]]=table.concat(bytes)
    end
    records[#records+1]={kind=kind,address=address,value=value or -1,frame=frame,cpu=cpu,stack=stack,wram=w,timing=timing,regions=regions,transaction_id=transaction_id,transaction_active=transaction_active,resolver_active=resolver_active,
        selector_word=emu.read16(0x9877,WRAM),branch_word=emu.read16(0xA0B3,WRAM),
        mask0_word=emu.read16(0x0080,WRAM),mask1_word=emu.read16(0x0082,WRAM),root_word=emu.read16(0x9878,WRAM)}
end
local watched={
    [0xC1D7C4]='enemy-effect-preparation',[0xC1C72B]='target-validation-failure',[0xC1D7B8]='participant-mp-failure',
    [0xC1B421]='disabled-pending-command-clear',[0xC1BB49]='queued-tech-entry',[0xC1BB8B]='target-validation-return',[0xC1BB90]='target-failure-jump',
    [0xC1BBD4]='pre-effect-boundary',[0xC1BBD7]='effect-preparation-return',
    [0xC1BBDA]='preparation-af23-branch',[0xC1BBDF]='preparation-b3c8-branch',
    [0xC1BC01]='mp-participant0-call',[0xC1BC04]='mp-participant0-return',
    [0xC1BC0E]='mp-participant1-call',[0xC1BC11]='mp-participant1-return',
    [0xC1BC1B]='mp-participant2-call',[0xC1BC1E]='animation-result-call',
    [0xC1CC71]='mp-deduction-entry',[0xC1CCCA]='mp-deduction-rts',
    [0xC1AC57]='animation-wrapper-entry',[0xC1AC5A]='result-wrapper-entry',
    [0xC1EC7F]='result-application-entry',[0xC1ECA0]='hp-result-store',[0xC1ECA3]='hp-result-store-readback',
    [0xC1BC21]='animation-result-return',[0xC1BC56]='successful-table-clear',
    [0xC1BC5A]='shared-finalizer-call',[0xC1BDB3]='shared-finalizer-entry',
    [0xC1BC5D]='shared-finalizer-return',[0xC1BCF8]='queue-release-entry',[0xC1BD6E]='queue-release-rts',
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
        if ready and not done and (transaction_active or kind=='queued-tech-entry' or kind=='target-validation-failure' or kind=='participant-mp-failure' or kind=='disabled-pending-command-clear' or kind=='enemy-effect-preparation') then
            local ok,err=pcall(function()
                if kind=='queued-tech-entry' then
                    assert(not transaction_active,'overlapping queued-Tech transaction')
                    transaction_id=transaction_id+1; transaction_active=true
                end
                if kind=='resolver-entry' then resolver_active=true end
                snapshot(kind,address,-1)
                if kind=='resolver-tail' then resolver_active=false end
                if kind=='queue-release-rts' then
                    assert(transaction_active and not resolver_active,'unscoped queue return')
                    local st=emu.getState(); local sp=st['cpu.sp']
                    local target=0xC10000|((emu.read16((sp+1)&0xFFFF,MEM)+1)&0xFFFF)
                    assert(return_hook==nil,'return callback already pending')
                    return_hook=emu.addMemoryCallback(function()
                        if ready and not done then
                            assert(transaction_active and not resolver_active,'unscoped transaction caller')
                            local good,problem=pcall(snapshot,'transaction-caller-resume',target,-1)
                            emu.removeMemoryCallback(return_hook,emu.callbackType.exec,target,target,CPU,MEM)
                            return_hook=nil; transaction_active=false
                            if not good then finish(tostring(problem)) end
                        end
                    end,emu.callbackType.exec,target,target,CPU,MEM)
                end
            end)
            if not ok then finish(tostring(err)) end
        end
    end,emu.callbackType.exec,address,address,CPU,MEM)
end
local write_ranges={{0x93EE,0x9402},{0xB18E,0xB1BD},{0xAFAB,0xAFB5},{0xB03A,0xB044},{0xAF22,0xAF23}}
for i=0,10 do write_ranges[#write_ranges+1]={0x5E30+i*0x80,0x5E37+i*0x80} end
for _,range in ipairs(write_ranges) do
    emu.addMemoryCallback(function(a,value)
        if ready and not done and transaction_active then
            local ok,err=pcall(snapshot,'transaction-memory-write',a,value)
            if not ok then finish(tostring(err)) end
        end
    end,emu.callbackType.write,range[1],range[2],CPU,WRAM)
end
for i=0,2 do
    local base=0x5E30+i*0x80
    emu.addMemoryCallback(function(a,value)
        if ready and not done and not transaction_active then
            local ok,err=pcall(snapshot,'ordinary-hp-write',a,value)
            if not ok then finish(tostring(err)) end
        end
    end,emu.callbackType.write,base,base+1,CPU,WRAM)
end
emu.addMemoryCallback(function(address,value)
    if ready and not done and resolver_active then
        local ok,err=pcall(snapshot,'publication-write',address,value)
        if not ok then finish(tostring(err)) end
    end
end,emu.callbackType.write,0x7E5DAC,0x7E5DFC,CPU,MEM)
for _,address in ipairs({0x7E9876,0x7E5D9B}) do
    emu.addMemoryCallback(function(a,value)
        if ready and not done and transaction_active then
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
        if route=='lavos-cure-before-ko' or route=='lavos-cure-lucca-before-ko' then
            input.right=frame>=2180 and frame<=2183
            input.down=(frame>=2200 and frame<=2203) or (frame>=2340 and frame<=2343) or (frame>=2360 and frame<=2363) or (frame>=2380 and frame<=2383) or (frame>=2420 and frame<=2423)
            if route=='lavos-cure-lucca-before-ko' then input.down=input.down or (frame>=2430 and frame<=2433) end
            input.up=frame>=2240 and frame<=2319
            input.a=(frame>=2220 and frame<=2223) or (frame>=2400 and frame<=2403) or (frame>=2440 and frame<=2443)
        end
        emu.setInput(input,0)
        if ready and (frame%120==0) then snapshot('menu-observation',0,-1) end
    end)
    if not ok then finish(tostring(err)) end
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
    if ready and not done and (frame==2180 or frame==2320 or frame==2390 or frame==2410 or frame==2435 or frame==2600 or frame==3600) then
        local f=assert(io.open(output_path..'/menu_'..frame..'.png','wb'));f:write(emu.takeScreenshot());f:close()
    end
    if ready and not done and frame>=4000 then
        local ok,err=pcall(snapshot,'terminal',0,-1)
        if ok then finish(nil) else finish(tostring(err)) end
    end
end,emu.eventType.endFrame)
