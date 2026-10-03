-- Original read-only phase observer. The only game-state changes requested by
-- this script are one checkpoint load and the retained controller input schedule.
local SCHEMA='project-epoch-package-resolver-phase-v1'
assert(os.getenv('PE_RESOLVER_PHASE_PROTOCOL')==SCHEMA)
local trace_path=assert(os.getenv('PE_RESOLVER_PHASE_TRACE'))
local sf=assert(io.open(assert(os.getenv('PE_RESOLVER_PHASE_STATE')),'rb'))
local state_bytes=assert(sf:read('*a'));assert(sf:close())
local CPU,MEM,WRAM=emu.cpuType.snes,emu.memType.snesMemory,emu.memType.snesWorkRam
local loaded,seen,ready=false,false,false
local phase,poll,record_count,trace_bytes='capturing',0,0,0
local trace_file=nil
local window,resolver,nmi_complete=false,false,false
local contexts,context_serial={},0
local captured={}
local entries={[0xD1E77C]='normal-nmi',[0xD1FE97]='battle-irq',[0xD1F4C0]='alternate-nmi'}
local exits={[0xD1E898]='normal-nmi',[0xD1FEF3]='battle-irq',[0xD1F558]='alternate-nmi'}
local sites={[0xC1BBD4]='pre-effect',[0xC14612]='resolver-entry',
    [0xC1467F]='resolver-tail',[0xC14833]='common-loader-entry',
    [0xCD1609]='scene-gate',[0xCD160E]='scene-effect-gate'}
local gates={0x007C,0x007D,0x007E,0x007F,0x0080,0x0081,0x0082,0x0083,
    0x00A0,0x5D9B,0x9876,0x9877,0x9878,0x9879,0x987A,0x987B,
    0xA0B3,0xA0B4,0xA012,0xA013,0xA028,0xAE91,0xAE92,0xAE93,0xAE94,
    0xCCEA,0xCD01,0xCD02,0xCD2E}
local gate_set={};for _,a in ipairs(gates) do gate_set[a]=true end
local bool_fields={'cpu.irqLock','cpu.needNmi','ppu.overscanMode','ppu.screenInterlace','ppu.objInterlace',
    'internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
    'internalRegisters.enableVerticalIrq','internalRegisters.irqFlag',
    'internalRegisters.irqLevel','internalRegisters.nmiFlag','internalRegisters.enableFastRom',
    'dmaController.dmaPending','dmaController.dmaStartDelay','dmaController.needToProcess',
    'dmaController.hdmaPending','dmaController.hdmaInitPending'}
local int_fields={'cpu.irqSource','cpu.prevIrqSource','cpu.nmiFlagCounter',
    'internalRegisters.horizontalTimer','internalRegisters.verticalTimer','internalRegisters.needIrq',
    'dmaController.hdmaChannels','dmaController.dmaClockCounter'}
local channel_bools={'decrement','dmaActive','doTransfer','fixedTransfer','hdmaFinished',
    'hdmaIndirectAddressing','invertDirection','unusedControlFlag'}
local channel_ints={'destAddress','hdmaBank','hdmaLineCounterAndRepeat','hdmaTableAddress',
    'srcAddress','srcBank','transferMode','transferSize','unusedRegister'}
for i=0,7 do
    for _,k in ipairs(channel_bools) do bool_fields[#bool_fields+1]='dmaController.channel['..i..'].'..k end
    for _,k in ipairs(channel_ints) do int_fields[#int_fields+1]='dmaController.channel['..i..'].'..k end
end
local function encode(v)
    if type(v)=='string' then return '"'..v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')..'"' end
    if type(v)=='boolean' or type(v)=='number' then return tostring(v) end
    if v==nil then return 'null' end
    local parts={}
    if #v>0 then
        for _,x in ipairs(v) do parts[#parts+1]=encode(x) end
        return '['..table.concat(parts,',')..']'
    end
    local keys={};for k,_ in pairs(v) do keys[#keys+1]=k end;table.sort(keys)
    for _,k in ipairs(keys) do parts[#parts+1]=encode(k)..':'..encode(v[k]) end
    return '{'..table.concat(parts,',')..'}'
end
local function write_chunk(value)
    trace_bytes=trace_bytes+#value;assert(trace_bytes<=64*1024*1024,'total trace byte bound')
    assert(trace_file:write(value))
end
local function fail_stop(message)
    phase='failed'
    if trace_file then pcall(function() trace_file:flush();trace_file:close() end);trace_file=nil end
    pcall(function()
        local f=assert(io.open(trace_path..'.error.txt','wb'))
        f:write(tostring(message)..'\n');f:close()
    end)
    emu.stop(93)
end
local function protect(f)
    return function(...)
        if phase~='capturing' then return end
        local ok,err=pcall(f,...);if not ok then fail_stop(tostring(err)) end
    end
end
local function snapshot(kind,address,value)
    assert(record_count<8192,'record bound')
    local s=emu.getState();local cpu,timing,engine={},{},{}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k);cpu[k]=s['cpu.'..k]
    end
    assert(cpu.emulationMode==false and cpu.sp+12<0x2000,'native low WRAM stack required')
    for _,k in ipairs({'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount',
        'ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}) do
        assert(type(s[k])=='number','missing timing field '..k);timing[k]=s[k]
    end
    for _,k in ipairs(bool_fields) do
        assert(type(s[k])=='boolean','missing/nonboolean engine field '..k);engine[k]=s[k]
    end
    for _,k in ipairs(int_fields) do
        assert(type(s[k])=='number' and s[k]%1==0,'missing/noninteger engine field '..k);engine[k]=s[k]
    end
    local stack,trampolines,w={},{},{}
    for i=1,12 do stack[i]=emu.read(cpu.sp+i,MEM) end
    for i=0,7 do trampolines[i+1]=emu.read(0x500+i,MEM) end
    for _,a in ipairs(gates) do w[string.format('%04X',a)]=emu.read(a,WRAM) end
    local ctx=contexts[#contexts]
    local r={kind=kind,address=address,value=value,poll=poll,cpu=cpu,timing=timing,
        engine=engine,stack=stack,trampolines=trampolines,gates=w,
        context_id=ctx and ctx.id or 0,context_kind=ctx and ctx.kind or 'main',context_depth=#contexts}
    if record_count>0 then write_chunk(',') end
    write_chunk(encode(r));record_count=record_count+1
end
local function finish()
    assert(phase=='capturing' and trace_file and not window and #contexts==0,'closed finalization state')
    assert(resolver and nmi_complete,'incomplete selected replay')
    phase='finalizing'
    write_chunk('],"error":null,"terminal_poll":'..poll..'}\n')
    assert(trace_file:flush());assert(trace_file:close());trace_file=nil
    phase='stopped';emu.stop(52)
end
emu.addMemoryCallback(protect(function(address)
    if not loaded then loaded=true;emu.loadSavestate(state_bytes);return end
    seen=true;if not ready then return end
    if entries[address] then
        context_serial=context_serial+1
        contexts[#contexts+1]={id=context_serial,kind=entries[address]}
        if window then snapshot('interrupt-entry',address,-1) end
        return
    end
    if exits[address] then
        assert(#contexts>0 and contexts[#contexts].kind==exits[address],'unpaired interrupt return')
        if window then snapshot('interrupt-rti',address,-1) end
        contexts[#contexts]=nil
        if window and resolver and exits[address]=='normal-nmi' then
            assert(#contexts==0,'nested selected NMI exit');window=false;nmi_complete=true
        end
        return
    end
    local kind=sites[address]
    if not kind then return end
    if kind=='scene-gate' or kind=='scene-effect-gate' then
        if window and resolver then snapshot(kind,address,-1) end
        return
    end
    assert(not captured[kind],'repeated selected resolver phase')
    if kind=='pre-effect' then
        assert(not resolver and #contexts==0,'pre-effect ordering/context');window=true
    elseif kind=='resolver-entry' then
        assert(not resolver and #contexts==0,'resolver ordering/context');window=true;resolver=true
    else assert(resolver and window and #contexts==0,'resolver continuation context') end
    captured[kind]=true;snapshot(kind,address,-1)
end),emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
local function physical_wram(address)
    local bank=(address>>16)&0xFF;local offset=address&0xFFFF
    if bank==0x7E then return offset end
    if (bank<0x40 or (bank>=0x80 and bank<0xC0)) and offset<0x2000 then return offset end
    return nil
end
local function watched_bus(address)
    local p=physical_wram(address);if p and gate_set[p] then return true end
    local bank=(address>>16)&0xFF;local offset=address&0xFFFF
    return (bank<0x40 or (bank>=0x80 and bank<0xC0)) and
        (offset==0x4200 or (offset>=0x4207 and offset<=0x420D) or
        (offset>=0x4300 and offset<=0x437F))
end
for _,operation in ipairs({'read','write'}) do
    emu.addMemoryCallback(protect(function(address,value)
        if ready and window and watched_bus(address) then snapshot('bus-'..operation,address,value) end
        -- No return value: never replace a bus byte. Mesen includes DMA/dummy
        -- operations in these callback families; these are not CPU-only rows.
    end),emu.callbackType[operation],0,0xFFFFFF,CPU,MEM)
end
emu.addEventCallback(protect(function()
    local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,
        left=false,right=false,start=false,select=false}
    if seen and not ready then
        assert(emu.read16(0x0100,WRAM)==0x01DB,'wrong checkpoint location')
        assert(emu.read(0x2980,WRAM)==0 and emu.read(0x2981,WRAM)==1 and emu.read(0x2982,WRAM)==2,'wrong checkpoint party')
        ready=true;trace_file=assert(io.open(trace_path,'wb'))
        write_chunk('{"schema":'..encode(SCHEMA)..',"records":[');snapshot('baseline',0,-1)
    elseif ready then poll=poll+1 end
    input.down=poll>=20 and poll<=23
    input.a=(poll>=60 and poll<=63) or (poll>=100 and poll<=103) or (poll>=140 and poll<=143)
    emu.setInput(input,0)
end),emu.eventType.inputPolled)
emu.addEventCallback(protect(function()
    if ready and poll>=381 then snapshot('terminal',0,-1);finish() end
end),emu.eventType.endFrame)
