-- Original synthetic CPU conformance collector, Mesen 2.1.1 API only.
-- Launcher stages an immutable original boot image and isolated zero SRAM.
-- Every mutation below is original WRAM test setup, never cartridge data.
local SCHEMA = "project-epoch-package-helper-v4-timing-calibration"
assert(os.getenv("PE_PACKAGE_PROTOCOL") == SCHEMA, "launcher protocol required")
local input = assert(loadfile(assert(os.getenv("PE_PACKAGE_INPUT"))))()
assert(input.schema == SCHEMA, "input schema")
assert(input.entry_bridge == 0x008060, "exact original entry bridge required")
local output = assert(os.getenv("PE_PACKAGE_TRACE"))
local progress_path=assert(os.getenv("PE_PACKAGE_PROGRESS"))
local WRAM, MEM, CPU = emu.memType.snesWorkRam, emu.memType.snesMemory, emu.cpuType.snes
local writes, baseline, rom_reads = {}, {}, {}
local record_count=0
local trace_file=assert(io.open(output,"wb"))
trace_file:write('{"schema":"'..SCHEMA..'","records":[')
local index, instructions, started, active, stopped = 0, 0, false, false, false
local exec_sample = {}
local input_fixture_before_hex = ""
local descriptor_fixture_before_hex=""
local exec_opcode_peeks={}
local preparation,last_false,latch_rise,fixture_baseline=nil,nil,nil,nil
local execution_samples={}
local wait_start_clock=0
local reads_total = 0
local exec_addresses = {}
local stack_accesses,minimum_sp={},0
local retired_scratch_before_hex=""
local previous_opcode=nil
local sp_observations={}
local code_bytes={}
for p=1,#input.code_hex,2 do code_bytes[#code_bytes+1]=tonumber(input.code_hex:sub(p,p+1),16) end
local changes_sp={[0x08]=true,[0x48]=true,[0xDA]=true,[0x5A]=true,[0x8B]=true,
    [0xAB]=true,[0x7A]=true,[0xFA]=true,[0x68]=true,[0x28]=true,[0x20]=true,
    [0x60]=true,[0x1B]=true}
local stack_relative={[0xA3]=0,[0x83]=1,[0x63]=0,[0xC3]=0}
local stack_implicit={[0x08]=1,[0x48]=1,[0xDA]=1,[0x5A]=1,[0x8B]=1,
    [0xAB]=0,[0x7A]=0,[0xFA]=0,[0x68]=0,[0x28]=0,[0x20]=1,[0x60]=0}
local cpu_keys = {"a","x","y","d","dbr","sp","ps","emulationMode"}

local function json(v)
    local t = type(v)
    if t == "string" then return '"' .. v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r') .. '"' end
    if t == "boolean" or t == "number" then return tostring(v) end
    if t == "nil" then return "null" end
    local parts = {}
    if #v > 0 then
        for _,x in ipairs(v) do parts[#parts+1] = json(x) end
        return "[" .. table.concat(parts,",") .. "]"
    end
    local keys = {}
    for k,_ in pairs(v) do keys[#keys+1]=k end
    table.sort(keys)
    for _,k in ipairs(keys) do
        local x=v[k]
        local encoded=json(x)
        if (k == "writes" or k == "changes" or k == "rom_reads") and #x == 0 then encoded="[]" end
        parts[#parts+1] = json(k) .. ":" .. encoded
    end
    return "{" .. table.concat(parts,",") .. "}"
end
local function array_json(v)
    if #v == 0 then return "[]" end
    return json(v)
end
local function progress(status,message)
    local f=assert(io.open(progress_path,"wb"))
    f:write(json({schema=SCHEMA,status=status,completed_cases=record_count,
        total_cases=#input.cases,error=message}).."\n")
    f:close()
end
local function finish(message)
    if stopped then return end
    stopped, active = true, false
    trace_file:write('],"error":'..json(message)..',"exec_sample":'..array_json(exec_sample)..',"partial_execution_samples":'..array_json(execution_samples)..',"partial_preparation":'..json(preparation)..'}\n')
    trace_file:close()
    progress(message==nil and "completed" or "rejected",message)
    emu.stop(message == nil and 41 or 42)
end
local function append_record(row)
    if record_count>0 then trace_file:write(",") end
    trace_file:write(json(row))
    trace_file:flush()
    record_count=record_count+1
    if record_count%50==0 then progress("running",nil) end
end
local function snapshot_cpu()
    local state, result = emu.getState(), {}
    for _,k in ipairs(cpu_keys) do
        assert(state["cpu." .. k] ~= nil, "missing CPU field " .. k)
        result[k] = state["cpu." .. k]
    end
    return result
end
local TIME_KEYS={"masterClock","memoryManager.masterClock","cpu.cycleCount","frameCount","ppu.frameCount","ppu.scanline","memoryManager.hClock","clockRate"}
local FLAG_KEYS={"internalRegisters.nmiFlag","internalRegisters.enableNmi","internalRegisters.enableHorizontalIrq",
    "internalRegisters.enableVerticalIrq","internalRegisters.enableAutoJoypadRead","cpu.nmiFlagCounter","cpu.needNmi",
    "cpu.irqLock","cpu.irqSource","cpu.prevIrqSource","dmaController.needToProcess","dmaController.hdmaChannels",
    "dmaController.hdmaPending","dmaController.hdmaInitPending","dmaController.dmaStartDelay","dmaController.dmaPending"}
local INTEGER_FLAGS={["cpu.nmiFlagCounter"]=true,["cpu.irqSource"]=true,["cpu.prevIrqSource"]=true,["dmaController.hdmaChannels"]=true}
local function timing_snapshot(ordinal,address)
    local state=emu.getState();local result={exec_index=ordinal,pc=address,cpu={},timing={},flags={}}
    for _,key in ipairs(cpu_keys) do assert(state["cpu."..key]~=nil,"missing CPU "..key);result.cpu[key]=state["cpu."..key] end
    result.cpu.k=assert(state['cpu.k']);result.cpu.pc=assert(state['cpu.pc'])
    assert(((result.cpu.k<<16)|result.cpu.pc)==address,'timing CPU/PC mismatch')
    for _,key in ipairs(TIME_KEYS) do assert(state[key]~=nil,'missing timing '..key);result.timing[key]=state[key] end
    for _,key in ipairs(FLAG_KEYS) do
        assert(state[key]~=nil,'missing interrupt/DMA field '..key);result.flags[key]=state[key]
        if INTEGER_FLAGS[key] then assert(state[key]==0,'pending interrupt/DMA integer')
        elseif key~='internalRegisters.nmiFlag' then assert(state[key]==false,'interrupt/DMA enabled or pending') end
    end
    result.latch_peek=emu.read(0x004210,MEM)
    return result
end
local function begin_wait()
    active=false
    if index>=#input.cases then finish(nil);return end
    emu.write(0x004200,0,MEM);emu.write(0x00420B,0,MEM);emu.write(0x00420C,0,MEM)
    emu.setState({['cpu.k']=0,['cpu.pc']=0x8040})
    wait_start_clock=emu.getState()['memoryManager.masterClock']
    preparation={wait_start_clock=wait_start_clock};last_false=nil;latch_rise=nil
end
local function patch(address,value)
    assert(address >= 0x7E0000 and address < 0x800000, "setup outside WRAM")
    emu.write(address - 0x7E0000,value,WRAM)
end
local function retired_scratch_hex()
    local bytes={}
    for a=0x4000,0x407F do bytes[#bytes+1]=string.format("%02x",emu.read(a,WRAM)) end
    return table.concat(bytes)
end
local function input_fixture_hex()
    local bytes={}
    for address=0x430000,0x4304FF do bytes[#bytes+1]=string.format("%02x",emu.read(address,MEM)) end
    return table.concat(bytes)
end
local function descriptor_fixture_hex()
    local bytes={}
    for address=0x420000,0x420000+#input.descriptor_hex/2-1 do
        bytes[#bytes+1]=string.format("%02x",emu.read(address,MEM))
    end
    return table.concat(bytes)
end
local function prepare()
    active = false
    index = index + 1
    if index > #input.cases then finish(nil); return end
    local c = input.cases[index]
    -- A complete deterministic fixture; native stack return sentinel remains A5.
    for a = 0,0x1FFFF do emu.write(a,0xA5,WRAM) end
    -- Helper, registry, descriptors and entry/tail code remain in immutable ROM.
    -- setState's unobserved redirected instruction is the original ROM JML
    -- bridge, so the very first helper PHP receives its own exec callback.
    for _,p in ipairs(c.patches) do patch(p[1],p[2]) end
    -- Original synthetic peripheral policy, outside the observed helper interval.
    emu.write(0x004200,0,MEM)
    emu.write(0x00420B,0,MEM)
    emu.write(0x00420C,0,MEM)
    for a = 0,0x1FFFC,4 do baseline[a] = emu.read32(a,WRAM) end
    input_fixture_before_hex=input_fixture_hex()
    descriptor_fixture_before_hex=descriptor_fixture_hex()
    retired_scratch_before_hex=retired_scratch_hex()
    local state,changed = emu.getState(),{}
    for k,v in pairs(c.cpu) do
        assert(state["cpu." .. k] ~= nil,"missing setState CPU field " .. k)
        changed["cpu." .. k] = v
    end
    assert(state["cpu.k"] ~= nil and state["cpu.pc"] ~= nil,"missing PC fields")
    changed["cpu.k"],changed["cpu.pc"] = input.entry_bridge >> 16,input.entry_bridge & 0xFFFF
    emu.setState(changed)
    instructions,writes,rom_reads,reads_total,exec_addresses,stack_accesses = 0,{},{},0,{},{}
    minimum_sp=c.cpu.sp
    previous_opcode,sp_observations,exec_opcode_peeks=nil,{},{}
    execution_samples={}
    fixture_baseline=timing_snapshot(0,input.entry_bridge)
    active = true
end
local function physical(address)
    if address >= 0x7E0000 and address < 0x800000 then return address end
    local bank,offset = address >> 16,address & 0xFFFF
    if (bank <= 0x3F or (bank >= 0x80 and bank <= 0xBF)) and offset < 0x2000 then
        return 0x7E0000 + offset
    end
    return address
end
local function stack_access(address,value,mode)
    local c=input.cases[index]
    if address<c.stack_span[1] or address>=c.stack_span[2] then return false end
    local sp=emu.getState()["cpu.sp"]
    assert(sp~=nil,"missing live SP")
    minimum_sp=math.min(minimum_sp,sp)
    if sp<c.cpu.sp-c.stack_depth_limit or sp>c.cpu.sp or (address & 0xFFFF)<sp then
        finish(string.format("stack access outside live frame: %06X SP=%04X",address,sp));return true
    end
    local owner=exec_addresses[instructions]
    local offset=owner and owner-input.code+1 or 0
    local opcode=code_bytes[offset]
    local low=address & 0xFFFF
    if stack_relative[opcode]~=nil then
        local operand=code_bytes[offset+1]
        if mode~=stack_relative[opcode] or low<=sp or operand==nil or low<sp+operand or low>sp+operand+1 then
            finish("stack-relative access lacks live owning operand");return true
        end
    elseif stack_implicit[opcode]~=mode then
        finish("stack access lacks matching instruction semantics");return true
    end
    if #stack_accesses>=10000 then finish("stack access bound exceeded");return true end
    stack_accesses[#stack_accesses+1]={instructions,address,value,sp,mode}
    return true
end
-- CPU data reads are distinguished from execution callbacks and debugger reads.
-- All non-ROM reads must stay in the exact synthetic inputs/workspace/stack.
emu.addMemoryCallback(function(address,value)
    if not active then return end
    reads_total=reads_total+1
    if reads_total>10000 then finish("CPU read bound exceeded"); return end
    if (address>=0x420000 and address<0x420000+#input.descriptor_hex/2) or (address>=0x430000 and address<0x430500) then
        if #rom_reads >= 256 then finish("ROM read bound exceeded"); return end
        rom_reads[#rom_reads+1] = {address,value}
        return
    end
    local a=physical(address)
    if stack_access(a,value,0) then return end
    local allowed=(a>=0x7E9877 and a<0x7E9879)
        or (a>=0x7EA0B3 and a<0x7EA0B5)
    if not allowed then finish(string.format("undeclared CPU data read %06X",address)) end
end,emu.callbackType.read,0,0xFFFFFF,CPU,MEM)
emu.addMemoryCallback(function(address,value)
    if active then
        if #writes >= 8192 then finish("write bound exceeded"); return end
        local a=physical(address)
        writes[#writes+1] = {a,value}
        stack_access(a,value,1)
    end
end,emu.callbackType.write,0,0xFFFFFF,CPU,MEM)
emu.addMemoryCallback(function(address,opcode_peek)
    if stopped then return end
    local ok,message = pcall(function()
        if not started then
            -- Let the original boot establish its native idle state naturally.
            if address~=0x008040 then return end
            started=true;begin_wait();return
        end
        if not active then
            assert(address==0x008040,'natural calibration wait left original idle')
            local state=emu.getState()
            assert(state['memoryManager.masterClock']-wait_start_clock<800000,'natural VBlank wait bound')
            local sample={clock=state['memoryManager.masterClock'],cycles=state['cpu.cycleCount'],frame=state['ppu.frameCount'],
                scanline=state['ppu.scanline'],hclock=state['memoryManager.hClock'],latch=state['internalRegisters.nmiFlag'],peek=emu.read(0x004210,MEM)}
            if sample.latch==false then last_false=sample
            elseif latch_rise==nil and last_false~=nil then latch_rise={before=last_false,after=sample};preparation.latch_rise=latch_rise end
            if latch_rise~=nil and state['ppu.frameCount']==latch_rise.after.frame and state['ppu.scanline']==latch_rise.after.scanline+1 then
                assert(state['internalRegisters.enableNmi']==false and state['internalRegisters.nmiFlag']==true,'latched no-NMI preparation')
                prepare()
            end
            return
        end
        local route = nil
        for name,tail in pairs(input.tails) do if tail == address then route=name end end
        -- Check every observed execution PC before accepting any instruction.
        -- A terminal address is an observation point: its ROM BRA is not executed.
        assert(route ~= nil or (address >= input.code and address < input.code + #input.code_hex/2),
            string.format("undeclared execution address %06X",address))
        -- Mesen supplies a pre-execution debugger Peek, not an independent
        -- opcode bus-fetch observation. Keep that provenance explicit.
        local expected_peek=route~=nil and 0x80 or code_bytes[address-input.code+1]
        assert(opcode_peek==expected_peek,"pre-execution opcode peek differs from mapped ROM")
        exec_opcode_peeks[#exec_opcode_peeks+1]=opcode_peek
        if #exec_sample < 24 then exec_sample[#exec_sample+1] = address end
        if previous_opcode~=nil and changes_sp[previous_opcode] then
            local sp=emu.getState()["cpu.sp"]
            local c=input.cases[index]
            assert(sp>=c.cpu.sp-c.stack_depth_limit and sp<=c.cpu.sp,"executed SP outside exact stack floor")
            minimum_sp=math.min(minimum_sp,sp)
            sp_observations[#sp_observations+1]={instructions+1,address,sp}
        end
        if route==nil then previous_opcode=code_bytes[address-input.code+1] end
        exec_addresses[#exec_addresses+1]=address
        instructions = instructions + 1
        assert(instructions <= 10000,"instruction bound exceeded")
        execution_samples[#execution_samples+1]=timing_snapshot(instructions,address)
        if route ~= nil then
            active=false
            local changes={}
            for a=0,0x1FFFC,4 do
                local value=emu.read32(a,WRAM)
                if value ~= baseline[a] then
                    for b=0,3 do
                        local before=(baseline[a] >> (b*8)) & 255
                        local after=(value >> (b*8)) & 255
                        if before ~= after then changes[#changes+1]={0x7E0000+a+b,after} end
                    end
                end
            end
            local row={name=input.cases[index].name,route=route,cpu=snapshot_cpu(),instructions=instructions,
                writes=writes,changes=changes,rom_reads=rom_reads,reads_total=reads_total,exec_addresses=exec_addresses,exec_opcode_peeks=exec_opcode_peeks,
                input_fixture_before_hex=input_fixture_before_hex,input_fixture_after_hex=input_fixture_hex(),
                descriptor_fixture_before_hex=descriptor_fixture_before_hex,descriptor_fixture_after_hex=descriptor_fixture_hex(),
                retired_scratch_before_hex=retired_scratch_before_hex,retired_scratch_after_hex=retired_scratch_hex(),
                stack_accesses=stack_accesses,minimum_sp=minimum_sp,sp_observations=sp_observations,
                preparation=preparation,fixture_baseline=fixture_baseline,execution_samples=execution_samples}
            -- Explicit arrays even when empty are enforced by the writer below.
            append_record(row)
            execution_samples={}
            begin_wait()
        end
    end)
    if not ok then finish(tostring(message)) end
end,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
