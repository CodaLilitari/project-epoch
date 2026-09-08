-- Original, separately scoped NMI conformance fixture. No cartridge writes.
-- A real 4200 enable edge requests native interrupt entry; no NMI/PPU/frame edits.
local SCHEMA="project-epoch-package-helper-v4-rom-nmi-calibrated-v3"
assert(os.getenv("PE_PACKAGE_PROTOCOL")==SCHEMA)
local input=assert(loadfile(assert(os.getenv("PE_PACKAGE_INPUT"))))()
assert(input.schema==SCHEMA and input.code==0x410000 and input.entry_bridge==0x008060)
local WRAM,MEM,CPU=emu.memType.snesWorkRam,emu.memType.snesMemory,emu.cpuType.snes
local output=assert(io.open(assert(os.getenv("PE_PACKAGE_TRACE")),"wb"))
output:write('{"schema":"'..SCHEMA..'","records":[')
local phase,index,count="boot",0,0
local events,baseline,execs={}, {},0
local requested,entered,resumed=false,false,false
local start_clock=0
local before_inputs,before_scratch,before_descriptor="","",""
local initial=nil
local preparation,last_false,latch_rise=nil,nil,nil
local CPU_KEYS={"a","x","y","d","dbr","sp","ps","k","pc","emulationMode"}
local TIME_KEYS={"masterClock","memoryManager.masterClock","cpu.cycleCount","frameCount","ppu.frameCount","ppu.scanline","memoryManager.hClock","clockRate"}
local FLAG_KEYS={"internalRegisters.nmiFlag","internalRegisters.enableNmi","internalRegisters.enableHorizontalIrq",
    "internalRegisters.enableVerticalIrq","internalRegisters.enableAutoJoypadRead","cpu.nmiFlagCounter","cpu.needNmi",
    "cpu.irqLock","cpu.irqSource","cpu.prevIrqSource","dmaController.needToProcess","dmaController.hdmaChannels",
    "dmaController.hdmaPending","dmaController.hdmaInitPending","dmaController.dmaStartDelay","dmaController.dmaPending"}
local ARRAY_KEYS={events=true,changes=true,stack=true}
local function json(v,key)
    if type(v)=="string" then return '"'..v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')..'"' end
    if type(v)=="boolean" or type(v)=="number" then return tostring(v) end
    if v==nil then return 'null' end
    local parts={}
    if #v>0 or ARRAY_KEYS[key] then
        for _,x in ipairs(v) do parts[#parts+1]=json(x) end
        return '['..table.concat(parts,',')..']'
    end
    local keys={};for k,_ in pairs(v) do keys[#keys+1]=k end;table.sort(keys)
    for _,k in ipairs(keys) do parts[#parts+1]=json(k)..':'..json(v[k],k) end
    return '{'..table.concat(parts,',')..'}'
end
local function finish(error)
    if phase=="stopped" then return end
    phase="stopped"
    output:write('],"error":'..json(error)..',"partial_events":'..json(events,"events")..'}\n');output:close()
    emu.stop(error==nil and 61 or 62)
end
local function cpu(state)
    local c={};for _,k in ipairs(CPU_KEYS) do assert(state['cpu.'..k]~=nil,'missing CPU '..k);c[k]=state['cpu.'..k] end
    return c
end
local function snapshot(kind,address,value)
    assert(#events<20000,"event bound")
    local s=emu.getState();local t,f={},{}
    for _,k in ipairs(TIME_KEYS) do assert(s[k]~=nil,'missing timing '..k);t[k]=s[k] end
    for _,k in ipairs(FLAG_KEYS) do assert(s[k]~=nil,'missing flag '..k);f[k]=s[k] end
    local c=cpu(s);local stack={}
    for i=1,16 do stack[i]=emu.read((c.sp+i)&0xFFFF,MEM) end
    local row={kind=kind,address=address,value=value,exec_index=execs,cpu=c,timing=t,flags=f,stack=stack,
        nmi_counter=emu.read16(0x5EF0,WRAM),latch_peek=emu.read(0x004210,MEM)}
    events[#events+1]=row;return row
end
local function patch(a,v)
    assert(a>=0x7E0000 and a<0x800000,'setup outside WRAM');emu.write(a-0x7E0000,v,WRAM)
end
local function hex(start,length,memory_type)
    local b={};for a=start,start+length-1 do b[#b+1]=string.format('%02x',emu.read(a,memory_type or WRAM)) end
    return table.concat(b)
end
local function pending_clear(s)
    return s['cpu.nmiFlagCounter']==0 and s['cpu.needNmi']==false and s['cpu.irqLock']==false
        and s['cpu.irqSource']==0 and s['cpu.prevIrqSource']==0 and s['dmaController.needToProcess']==false
        and s['dmaController.hdmaChannels']==0
end
local function begin_wait()
    phase="wait";index=index+1
    if index>#input.cases then finish(nil);return end
    emu.write(0x004200,0,MEM);emu.write(0x00420B,0,MEM);emu.write(0x00420C,0,MEM)
    emu.setState({['cpu.k']=0,['cpu.pc']=0x8040})
    start_clock=emu.getState()['memoryManager.masterClock']
    preparation={wait_start_clock=start_clock};last_false=nil;latch_rise=nil
end
local function prepare_case()
    local c=input.cases[index]
    for a=0,0x1FFFF do emu.write(a,0xA5,WRAM) end
    -- All code, registry and package data remain in the immutable original ROM.
    for _,p in ipairs(c.patches) do patch(p[1],p[2]) end
    for a=0,0x1FFFC,4 do baseline[a]=emu.read32(a,WRAM) end
    before_inputs=hex(0x430000,0x500,MEM);before_descriptor=hex(0x420000,#input.descriptor_hex/2,MEM);before_scratch=hex(0x4000,0x80)
    local changed={};for k,v in pairs(c.cpu) do changed['cpu.'..k]=v end
    changed['cpu.k']=input.entry_bridge>>16;changed['cpu.pc']=input.entry_bridge&65535
    emu.setState(changed)
    events,execs,requested,entered,resumed={},0,false,false,false
    initial=snapshot('fixture-baseline',input.entry_bridge,-1)
    phase="active"
end
local function physical(a)
    if a>=0x7E0000 and a<0x800000 then return a end
    local b,o=a>>16,a&65535
    if (b<=0x3F or (b>=0x80 and b<=0xBF)) and o<0x2000 then return 0x7E0000+o end
    return a
end
local function memory(a,value,mode)
    if phase~="active" then return end
    local c=input.cases[index];local p=physical(a)
    local stack=p>=0x7E0000+c.cpu.sp-c.nmi_max_depth+1 and p<=0x7E0000+c.cpu.sp
    local counter=p>=0x7E5EF0 and p<0x7E5EF2
    if mode=='read' then
        local normal=(a>=0x420000 and a<0x420000+#input.descriptor_hex/2) or (a>=0x430000 and a<0x430500)
            or (p>=0x7E9877 and p<0x7E9879) or (p>=0x7EA0B3 and p<0x7EA0B5)
        local hardware=requested and not entered and (a==0x00FFEA or a==0x00FFEB or a==c.nmi_resume)
        assert(normal or stack or (entered and counter) or hardware,string.format('undeclared data read %06X',a))
    else
        local publication=(p>=0x7E5DAC and p<0x7E5DFD) or (p>=0x7E0080 and p<0x7E0084)
            or (p>=0x7E9878 and p<0x7E987A)
            or (p>=0x7EA0B3 and p<0x7EA0B5)
        assert(stack or publication or (entered and counter),string.format('undeclared CPU write %06X',a))
    end
    local r=snapshot(mode,p,value);r.bus_address=a
end
for _,mode in ipairs({'read','write'}) do
    emu.addMemoryCallback(function(a,v)
        local ok,err=pcall(memory,a,v,mode);if not ok then finish(tostring(err)) end
    end,mode=='read' and emu.callbackType.read or emu.callbackType.write,0,0xFFFFFF,CPU,MEM)
end
emu.addMemoryCallback(function(address,peek)
    if phase=="stopped" then return end
    local ok,err=pcall(function()
        if phase=="boot" then
            -- Match calibration: the original cold boot reaches its native idle.
            if address==0x008040 then begin_wait() end
            return
        end
        if phase=="wait" then
            assert(address==0x008040,'natural NMI preparation left original idle')
            local s=emu.getState()
            assert(s['memoryManager.masterClock']-start_clock<2*400000,'natural VBlank preparation bound')
            local sample={clock=s['memoryManager.masterClock'],cycles=s['cpu.cycleCount'],frame=s['ppu.frameCount'],scanline=s['ppu.scanline'],hclock=s['memoryManager.hClock'],latch=s['internalRegisters.nmiFlag'],peek=emu.read(0x004210,MEM)}
            if sample.latch==false then last_false=sample
            elseif latch_rise==nil and last_false~=nil then latch_rise={before=last_false,after=sample};preparation.latch_rise=latch_rise end
            local c=input.cases[index]
            if latch_rise~=nil and s['ppu.scanline']==c.nmi_start_scanline and s['ppu.frameCount']==latch_rise.after.frame
                and s['internalRegisters.nmiFlag']==(c.nmi_start_scanline>=latch_rise.after.scanline)
                and s['internalRegisters.enableNmi']==false and pending_clear(s) then
                assert(latch_rise.after.scanline==c.nmi_rise_scanline,'calibrated natural rise changed')
                prepare_case()
            end
            return
        end
        assert(phase=="active")
        local c=input.cases[index];local route=nil
        for name,a in pairs(input.tails) do if address==a then route=name end end
        local helper=address>=input.code and address<input.code+#input.code_hex/2
        local handler=address>=0x008080 and address<0x008090
        assert(helper or handler or route~=nil,string.format('undeclared execution %06X',address))
        execs=execs+1;assert(execs<=10000,'execution bound')
        snapshot('exec',address,peek)
        if address==c.nmi_trigger and not requested then
            local s=emu.getState()
            assert(s['internalRegisters.nmiFlag']==true and s['internalRegisters.enableNmi']==false and pending_clear(s),'NMI trigger precondition')
            assert(s['ppu.scanline']>=latch_rise.after.scanline and s['ppu.scanline']<c.nmi_phase_limit,'NMI trigger phase')
            snapshot('request-before',0x004200,0x80)
            emu.write(0x004200,0x80,MEM);requested=true
            snapshot('request-after',0x004200,0x80)
        end
        if address==0x008080 then
            assert(requested and not entered,'unexpected or repeated NMI');entered=true
            snapshot('handler-entry',address,-1)
            snapshot('disable-before',0x004200,0);emu.write(0x004200,0,MEM);snapshot('disable-after',0x004200,0)
        elseif handler then assert(entered and not resumed,'unscoped handler instruction') end
        if address==c.nmi_resume and entered and not resumed then
            resumed=true;snapshot('post-rti',address,-1)
        end
        if handler and peek==0x40 then snapshot('pre-rti',address,-1) end
        if route~=nil then
            assert(requested and entered and resumed,'missing NMI lifecycle')
            phase="finishing"
            local changes={}
            for a=0,0x1FFFC,4 do
                local value=emu.read32(a,WRAM)
                if value~=baseline[a] then
                    for b=0,3 do local v=(value>>(b*8))&255
                        if v~=((baseline[a]>>(b*8))&255) then changes[#changes+1]={0x7E0000+a+b,v} end
                    end
                end
            end
            local row={name=c.name,route=route,events=events,changes=changes,preparation=preparation,
                input_fixture_before_hex=before_inputs,input_fixture_after_hex=hex(0x430000,0x500,MEM),
                descriptor_fixture_before_hex=before_descriptor,descriptor_fixture_after_hex=hex(0x420000,#input.descriptor_hex/2,MEM),
                retired_scratch_before_hex=before_scratch,retired_scratch_after_hex=hex(0x4000,0x80)}
            if count>0 then output:write(',') end;output:write(json(row));output:flush();count=count+1
            events={};begin_wait()
        end
    end)
    if not ok then finish(tostring(err)) end
end,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
