-- Original synthetic CPU conformance collector, Mesen 2.1.1 API only.
-- Launcher stages an immutable original boot image and isolated zero SRAM.
-- Every mutation below is original WRAM test setup, never cartridge data.
local SCHEMA = "project-epoch-original-package-helper-conformance-v0"
assert(os.getenv("PE_PACKAGE_PROTOCOL") == SCHEMA, "launcher protocol required")
local input = assert(loadfile(assert(os.getenv("PE_PACKAGE_INPUT"))))()
assert(input.schema == SCHEMA, "input schema")
local output = assert(os.getenv("PE_PACKAGE_TRACE"))
local WRAM, MEM, CPU = emu.memType.snesWorkRam, emu.memType.snesMemory, emu.cpuType.snes
local records, writes, baseline = {}, {}, {}
local index, instructions, started, active, stopped = 0, 0, false, false, false
local exec_sample = {}
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
        if (k == "writes" or k == "changes") and #x == 0 then encoded="[]" end
        parts[#parts+1] = json(k) .. ":" .. encoded
    end
    return "{" .. table.concat(parts,",") .. "}"
end
local function array_json(v)
    if #v == 0 then return "[]" end
    return json(v)
end
local function finish(message)
    if stopped then return end
    stopped, active = true, false
    local f = assert(io.open(output,"wb"))
    f:write('{"schema":' .. json(SCHEMA) .. ',"error":' .. json(message) .. ',"records":' .. array_json(records) .. ',"exec_sample":' .. array_json(exec_sample) .. '}\n')
    f:close()
    emu.stop(message == nil and 41 or 42)
end
local function snapshot_cpu()
    local state, result = emu.getState(), {}
    for _,k in ipairs(cpu_keys) do
        assert(state["cpu." .. k] ~= nil, "missing CPU field " .. k)
        result[k] = state["cpu." .. k]
    end
    return result
end
local function patch(address,value)
    assert(address >= 0x7E0000 and address < 0x800000, "setup outside WRAM")
    emu.write(address - 0x7E0000,value,WRAM)
end
local function prepare()
    active = false
    index = index + 1
    if index > #input.cases then finish(nil); return end
    local c = input.cases[index]
    -- A complete deterministic fixture; native stack return sentinel remains A5.
    for a = 0,0x1FFFF do emu.write(a,0xA5,WRAM) end
    for a = 0x3000,0x305F do emu.write(a,0,WRAM) end
    for p = 1,#input.code_hex,2 do
        patch(input.code + (p-1)/2,tonumber(input.code_hex:sub(p,p+1),16))
    end
    for _,address in pairs(input.tails) do patch(address,0xDB) end
    for _,p in ipairs(c.patches) do patch(p[1],p[2]) end
    -- Original synthetic peripheral policy, outside the observed helper interval.
    emu.write(0x004200,0,MEM)
    emu.write(0x00420B,0,MEM)
    emu.write(0x00420C,0,MEM)
    for a = 0,0x1FFFC,4 do baseline[a] = emu.read32(a,WRAM) end
    local state,changed = emu.getState(),{}
    for k,v in pairs(c.cpu) do
        assert(state["cpu." .. k] ~= nil,"missing setState CPU field " .. k)
        changed["cpu." .. k] = v
    end
    assert(state["cpu.k"] ~= nil and state["cpu.pc"] ~= nil,"missing PC fields")
    changed["cpu.k"],changed["cpu.pc"] = input.code >> 16,input.code & 0xFFFF
    emu.setState(changed)
    instructions,writes = 0,{}
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
emu.addMemoryCallback(function(address,value)
    if active then
        if #writes >= 8192 then finish("write bound exceeded"); return end
        writes[#writes+1] = {physical(address),value}
    end
end,emu.callbackType.write,0,0xFFFFFF,CPU,MEM)
emu.addMemoryCallback(function(address)
    if stopped then return end
    local ok,message = pcall(function()
        if not started then started = true; prepare(); return end
        if not active then return end
        if #exec_sample < 24 then exec_sample[#exec_sample+1] = address end
        instructions = instructions + 1
        assert(instructions <= 10000,"instruction bound exceeded")
        local route = nil
        for name,tail in pairs(input.tails) do if tail == address then route=name end end
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
                writes=writes,changes=changes}
            -- Explicit arrays even when empty are enforced by the writer below.
            records[#records+1]=row
            prepare()
        end
    end)
    if not ok then finish(tostring(message)) end
end,emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
