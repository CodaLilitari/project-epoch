-- Original read-only observer. After the single pinned checkpoint load,
-- no CPU/memory/ROM state is written; only the retained controller schedule is set.
local SCHEMA='project-epoch-normal-nmi-stack-observation-v1'
assert(os.getenv('PE_NMI_STACK_PROTOCOL')==SCHEMA)
local function read_file(path)
    local f=assert(io.open(path,'rb'));local value=f:read('*a');f:close();return value
end
local state_bytes=read_file(assert(os.getenv('PE_NMI_STACK_STATE')))
local trace_path=assert(os.getenv('PE_NMI_STACK_TRACE'))
local pilot=os.getenv('PE_NMI_STACK_PILOT')=='1'
local CPU,MEM,WRAM=emu.cpuType.snes,emu.memType.snesMemory,emu.memType.snesWorkRam
local wanted=pilot and {[379]=true} or {[379]=true,[500]=true,[700]=true,[927]=true,[928]=true}
local terminal_poll=pilot and 381 or 930
local loaded,seen,ready=false,false,false
local phase='capturing'
local poll,active,interval_count,baseline,resolver=0,nil,0,nil,nil
local trace_file,trace_bytes=nil,0
local completed={}
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
    trace_bytes=trace_bytes+#value
    assert(trace_bytes<=128*1024*1024,'total trace byte bound')
    assert(trace_file:write(value))
end
local function fail_stop(message)
    -- Do not call finish here: a failure while finalizing must still stop.
    phase='failed'
    if trace_file then pcall(function() trace_file:flush();trace_file:close() end);trace_file=nil end
    pcall(function()
        local f=assert(io.open(trace_path..'.error.txt','wb'))
        f:write(tostring(message)..'\n');f:close()
    end)
    emu.stop(93)
end
local function finish()
    assert(phase=='capturing' and active==nil and trace_file,'closed finalization state')
    phase='finalizing'
    write_chunk('],"error":null,"terminal_poll":'..tostring(poll)..'}\n')
    assert(trace_file:flush());assert(trace_file:close());trace_file=nil
    phase='stopped';emu.stop(52)
end
local function cpu_timing()
    local s=emu.getState();local c,t={},{}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU key '..k);c[k]=s['cpu.'..k]
    end
    for _,k in ipairs({'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount',
        'ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}) do
        assert(type(s[k])=='number','missing timing key '..k);t[k]=s[k]
    end
    return c,t
end
local function wram_snapshot()
    local out={};for address=0,0x1FFFF do out[#out+1]=emu.read(address,WRAM) end;return out
end
local function marker(c)
    local hardware,trampolines,gates={},{},{}
    for i=1,4 do hardware[#hardware+1]=emu.read((c.sp+i)&0xFFFF,MEM) end
    for i=0,7 do trampolines[#trampolines+1]=emu.read(0x500+i,MEM) end
    for _,address in ipairs({0x7F,0xCD02,0xA013,0xA028,0xCCEA,0x5D9B,0x9876,0x9877,0xA0B3,0xA0,0xA012,0xCD2E}) do
        gates[#gates+1]=emu.read(address,WRAM)
    end
    return {hardware=hardware,trampolines=trampolines,gate_bytes=gates}
end
local function append(event)
    assert(active,'event outside interval')
    assert(event.cpu.emulationMode==false,'native mode changed')
    assert(event.cpu.sp<0x2000,'stack leaves low WRAM')
    assert(event.timing['memoryManager.masterClock']-active.start_clock<=715000,'interval clock bound')
    assert(event.timing['ppu.frameCount']-active.start_frame<=2,'interval frame bound')
    -- Encode one bounded event per existing emulator callback. Encoding the
    -- complete run in one endFrame callback can exceed Mesen's Lua watchdog.
    if active.event_count>0 then write_chunk(',') end
    write_chunk(encode(event));active.event_count=active.event_count+1
end
local function protect(f)
    return function(...)
        if phase~='capturing' then return end
        local ok,err=pcall(f,...);if not ok then fail_stop(tostring(err)) end
    end
end
-- This single execution callback remains installed throughout the ordinary
-- replay. Outside the five intervals it returns without a full state snapshot.
emu.addMemoryCallback(protect(function(address,value)
    if not loaded then loaded=true;emu.loadSavestate(state_bytes);return end
    seen=true;if not ready then return end
    if address==0xC14612 then
        assert(resolver==nil,'unexpected second resolver')
        local c=cpu_timing();resolver={poll=poll,cpu=c,selector=emu.read16(0x9877,WRAM),branch=emu.read16(0xA0B3,WRAM)}
    end
    if address==0xD1E77C and wanted[poll] then
        assert(active==nil and not completed[poll],'nested or duplicate selected NMI')
        local c,t=cpu_timing()
        assert(baseline and resolver,'missing pre-interval checkpoint or resolver')
        if not trace_file then
            trace_file=assert(io.open(trace_path,'wb'))
            write_chunk('{"schema":'..encode(SCHEMA)..',"pilot":'..encode(pilot)..
                ',"baseline":'..encode(baseline)..',"resolver":'..encode(resolver)..',"intervals":[')
        end
        if interval_count>0 then write_chunk(',') end
        write_chunk('{"poll":'..tostring(poll)..',"entry_marker":'..encode(marker(c))..
            ',"wram_before":'..encode(wram_snapshot())..',"events":[')
        active={ordinal=0,bus_count=0,event_count=0,poll=poll,
            start_clock=t['memoryManager.masterClock'],start_frame=t['ppu.frameCount']}
    end
    if not active then return end
    assert(address~=0xD1FE97 and address~=0xD1F4C0,'nested/alternate interrupt')
    assert(address~=0xD1E77C or active.ordinal==0,'nested normal NMI')
    active.ordinal=active.ordinal+1;assert(active.ordinal<=50000,'instruction observation bound')
    local c,t=cpu_timing();local code,stack={},{}
    assert(address==(c.k<<16|c.pc),'exec callback PC relation')
    for i=0,3 do code[#code+1]=emu.read(address+i,MEM) end
    assert(code[1]==value,'pre-execution debugger opcode peek relation')
    for i=1,12 do stack[#stack+1]=emu.read((c.sp+i)&0xFFFF,MEM) end
    append({kind='exec',ordinal=active.ordinal,cpu=c,timing=t,code=code,stack=stack})
    if address==0xD1E898 then
        write_chunk('],"exit_marker":'..encode(marker(c))..',"wram_after":'..encode(wram_snapshot())..'}')
        assert(trace_file:flush())
        completed[active.poll]=true;interval_count=interval_count+1;active=nil
    end
end),emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
-- Standard Lua read/write callbacks include DMA/dummy operations. The host
-- labels these as bus events and attributes only exact implicit stack cycles.
for _,kind in ipairs({'read','write'}) do
    emu.addMemoryCallback(protect(function(address,value)
        if not ready or not active then return end
        active.bus_count=active.bus_count+1;assert(active.bus_count<=250000,'bus event bound')
        local c,t=cpu_timing()
        append({kind=kind,ordinal=active.ordinal,cpu=c,timing=t,address=address,value=value})
    end),emu.callbackType[kind],0,0xFFFFFF,CPU,MEM)
end
emu.addEventCallback(protect(function()
    local input={a=false,b=false,x=false,y=false,l=false,r=false,up=false,down=false,left=false,right=false,start=false,select=false}
    if seen and not ready then
        baseline={location=emu.read16(0x100,WRAM),party={emu.read(0x2980,WRAM),emu.read(0x2981,WRAM),emu.read(0x2982,WRAM)}}
        assert(baseline.location==0x01DB and baseline.party[1]==0 and baseline.party[2]==1 and baseline.party[3]==2,'wrong checkpoint')
        ready=true
    elseif ready then poll=poll+1 end
    input.down=poll>=20 and poll<=23
    input.a=(poll>=60 and poll<=63) or (poll>=100 and poll<=103) or (poll>=140 and poll<=143)
    emu.setInput(input,0)
end),emu.eventType.inputPolled)
emu.addEventCallback(protect(function()
    if ready and poll>=terminal_poll then
        assert(poll==terminal_poll and active==nil,'closed terminal boundary')
        for wanted_poll,_ in pairs(wanted) do assert(completed[wanted_poll],'missing selected NMI') end
        finish()
    end
end),emu.eventType.endFrame)
