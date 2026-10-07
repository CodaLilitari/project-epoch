-- Private instrumented native ten-region loop experiment. No ROM/SRAM writes
-- are performed by Lua. Successful runs restore the opaque marker before the
-- remaining native epilogue; failed runs remain quarantined. emu.stop is
-- deferred, so successful restoration occurs synchronously at copy completion.
-- The entry checkpoint must resume at the actual JSL routine entry. No CPU
-- register, stack, interrupt-enable, PC, input, or timing injection is allowed.
local SCHEMA = 'project-epoch-save-layout-native-v1'
assert(os.getenv('PE_SAVE_LAYOUT_PROTOCOL') == SCHEMA)
local mode = assert(os.getenv('PE_SAVE_LAYOUT_MODE'))
assert(mode == 'save' or mode == 'load')
local slot = assert(tonumber(os.getenv('PE_SAVE_LAYOUT_SLOT')))
assert(slot >= 0 and slot <= 2 and slot % 1 == 0)
local prefix = assert(os.getenv('PE_SAVE_LAYOUT_PREFIX'))
local state_path = assert(os.getenv('PE_SAVE_LAYOUT_STATE'))
local table_path = assert(os.getenv('PE_SAVE_LAYOUT_TABLE'))
local entry_pin = assert(os.getenv('PE_SAVE_LAYOUT_ENTRY_PIN'))
local bundle_pin = assert(os.getenv('PE_SAVE_LAYOUT_BUNDLE_PIN'))
local CPU, MEM = emu.cpuType.snes, emu.memType.snesMemory
local WRAM, SRAM = emu.memType.snesWorkRam, emu.memType.snesSaveRam
local mode_sites = {
    save = {entry=0xFFF9FB, inject=0xFFFA26, loop=0xFFFA2D, cmp=0xFFFA4F,
            complete=0xFFFA54, terminal=0xFFFA7A, caller=0xC2CF54},
    load = {entry=0xFFFAA3, inject=0xFFFABE, loop=0xFFFAC4, cmp=0xFFFAE6,
            complete=0xFFFAEB, terminal=0xFFFAEC, caller=0xC2E65A},
}
local sites = mode_sites[mode]
local function read_file(path)
    local f=assert(io.open(path,'rb')); local b=assert(f:read('*a')); assert(f:close()); return b
end
local function write_file(path, bytes)
    local f=assert(io.open(path,'wb')); assert(f:write(bytes)); assert(f:close())
end
local state_bytes = read_file(state_path)
local translated = read_file(table_path)
assert(#translated == 50)
local function encode(v)
    if type(v)=='string' then return '"'..v:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r')..'"' end
    if type(v)=='boolean' or type(v)=='number' then return tostring(v) end
    if v==nil then return 'null' end
    local keys, parts = {}, {}
    for k,_ in pairs(v) do keys[#keys+1]=k end; table.sort(keys)
    for _,k in ipairs(keys) do parts[#parts+1]=encode(k)..':'..encode(v[k]) end
    return '{'..table.concat(parts,',')..'}'
end
local function read_span(start, size, kind)
    local chunks={}
    for i=0,size-1 do chunks[#chunks+1]=string.char(emu.read(start+i,kind)) end
    return table.concat(chunks)
end
local function hex(bytes)
    return (bytes:gsub('.', function(c) return string.format('%02x',string.byte(c)) end))
end
local function cpu()
    local s=emu.getState(); local c={}
    for _,k in ipairs({'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}) do
        assert(s['cpu.'..k]~=nil,'missing CPU field '..k); c[k]=s['cpu.'..k]
    end
    c.pc24=(c.k<<16)|c.pc
    c.clock=assert(s['memoryManager.masterClock'])
    return c
end
local f=assert(io.open(prefix..'.jsonl','wb'))
local loaded, active, stopped, injected, copied = false,false,false,false,false
local last_pc, count, byte_count, loops, cmps = 0,0,0,0,0
local original_candidate, original_table, original_natural = nil,nil,nil
local entry_sp, entry_ps, start_clock = nil,nil,nil
local pending_failure=nil
local function record(r)
    count=count+1; assert(count<=250000,'record bound exceeded')
    local raw=encode(r)..'\n'; byte_count=byte_count+#raw
    assert(byte_count<=64*1024*1024,'trace byte bound exceeded')
    assert(f:write(raw))
end
local function snapshot(name)
    write_file(prefix..'.'..name..'.wram.bin', read_span(0,0x20000,WRAM))
    write_file(prefix..'.'..name..'.sram.bin', read_span(0,0x2000,SRAM))
    record({kind='snapshot',name=name,cpu=cpu()})
end
local function write_span(start, bytes, purpose)
    -- The sole explicit write API. The host validator checks exact bytes and
    -- timing, including restoration. Never callable outside these fixed spans.
    local permitted=(start==0x2830 and #bytes==80) or
                    (start==0x2CA0 and #bytes==80) or
                    (start==0x9890 and #bytes==50)
    assert(permitted,'explicit write outside fixed diagnostic spans')
    record({kind='inject',purpose=purpose,address=start,hex=hex(bytes),pc=last_pc})
    for i=1,#bytes do emu.write(start+i-1,bytes:byte(i),WRAM) end
    assert(read_span(start,#bytes,WRAM)==bytes,'explicit write readback failed')
end
local function restore()
    if not original_candidate then return end
    -- Before complete copy, load must recover entry natural compatibility;
    -- after complete copy, normal semantics require the loaded compatibility.
    local compatibility = (mode=='load' and copied) and read_span(0x2CA0,80,WRAM)
                          or original_natural
    write_span(0x2830,compatibility,'restore-natural')
    write_span(0x2CA0,original_candidate,'restore-candidate')
    if original_table then write_span(0x9890,original_table,'restore-table') end
    original_candidate=nil
end
local function fail(message)
    if stopped then return end
    active=false
    pending_failure=tostring(message)
    -- Best effort only: a failed mid-loop run stays quarantined. Instructions
    -- may resume after this snapshot and alter restored bytes before shutdown.
    local ok,err=pcall(restore)
    if not ok then pending_failure=pending_failure..'; restore failed: '..tostring(err) end
    pcall(function() record({kind='failure',message=pending_failure}); f:flush(); f:close() end)
    write_file(prefix..'.error.txt',pending_failure..'\n')
    stopped=true; emu.stop(93)
end
local function protect(fn)
    return function(...)
        if stopped then return end
        local ok,err=pcall(fn,...); if not ok then fail(err) end
    end
end
local function begin()
    local c=cpu()
    assert(c.pc24==sites.entry and c.emulationMode==false,'checkpoint is not native routine entry')
    assert(c.d==0 and c.dbr==0x7E and c.sp>=0x0100 and c.sp+3<0x2000,'entry CPU contract')
    assert(emu.read(0x79,WRAM)==slot and emu.read16(0x51,WRAM)==0,'slot/zero-word contract')
    local ret=emu.read(c.sp+1,MEM)|(emu.read(c.sp+2,MEM)<<8)|(emu.read(c.sp+3,MEM)<<16)
    assert(ret==sites.caller,'actual JSL return frame mismatch')
    assert(emu.read(0x0D01,WRAM)>=0x80,'menu task negative flag required')
    assert(hex(read_span(0x500,8,WRAM))=='5c0e84c25c7284c2','menu interrupt trampoline mismatch')
    record({kind='header',schema=SCHEMA,mode=mode,slot=slot,
            entry_pin=entry_pin,bundle_pin=bundle_pin,stop_is_deferred=true})
    snapshot('entry')
    original_candidate=read_span(0x2CA0,80,WRAM)
    original_natural=read_span(0x2830,80,WRAM)
    assert(read_span(0x2C9C,100,WRAM)==string.rep('\0',100),'candidate/guards preimage is not zero')
    local marker,poison={},{}
    for i=0,79 do marker[#marker+1]=string.char((19+73*i)%256); poison[#poison+1]=string.char((167+91*i)%256) end
    marker=table.concat(marker); poison=table.concat(poison)
    assert(marker~=original_natural,'marker is not distinguishable')
    write_span(0x2CA0,mode=='save' and original_natural or poison,'prepare-candidate')
    write_span(0x2830,marker,'prepare-marker')
    snapshot('prepared')
    entry_sp,entry_ps,start_clock=c.sp,c.ps,c.clock
    active=true
end
emu.addMemoryCallback(protect(function(address)
    if not loaded then loaded=true; assert(emu.loadSavestate(state_bytes)==true,'savestate load failed'); return end
    last_pc=address
    if not active and not copied then begin() end
    if not active then return end
    local c=cpu()
    assert(c.clock-start_clock<=1000000,'native interval clock bound')
    assert(emu.read(0x0D01,WRAM)>=0x80,'negative menu task flag lost')
    local code_mapping=assert(emu.convertAddress(address,MEM,CPU))
    if code_mapping.memType==WRAM then
        local a=code_mapping.address
        assert(not ((a>=0x2830 and a<0x2880) or (a>=0x2CA0 and a<0x2CF0) or
                    (a>=0x9890 and a<0x98C2)),'execution entered diagnostic data span')
    end
    -- Record before any boundary action; following bus rows always have an
    -- explicit latest CPU exec witness. DMA still has no separate CPU PC.
    record({kind='exec',pc=address,cpu=c})
    if address==sites.inject then
        assert(not injected and c.a==0xFFFF and c.x==0xFAA3 and c.y==0x98B8 and
               c.d==0 and c.dbr==0x7E and (c.ps&0x30)==0,'post-MVN CPU contract')
        original_table=read_span(0x9890,50,WRAM)
        assert(original_table:sub(1,40)==read_span(0xFFFA7B,40,MEM),'vanilla staging copy mismatch')
        snapshot('table')
        write_span(0x9890,translated,'translated-table')
        injected=true
    elseif address==sites.loop then
        assert(injected and not copied,'loop phase mismatch')
        local index=mode=='save' and c.x or c.y
        assert(index==loops*5 and loops<10,'region loop index mismatch')
        loops=loops+1
    elseif address==sites.cmp then
        assert(c.a==(cmps+1)*5 and cmps<10,'region CMP accumulator mismatch')
        cmps=cmps+1
    elseif address==sites.complete then
        assert(injected and not copied and loops==10 and cmps==10,'incomplete ten-region loop')
        copied=true
        snapshot('copy_complete')
        restore()
        snapshot('restored')
    elseif address==sites.terminal then
        assert(copied and c.sp==entry_sp and c.ps==entry_ps,'pre-RTL context mismatch')
        snapshot('terminal')
        record({kind='success',loops=loops,comparisons=cmps,terminal_before_rtl=true,
                post_stop_execution_excluded=true})
        active=false; stopped=true
        assert(f:flush()); assert(f:close()); emu.stop(62); return
    end
end),emu.callbackType.exec,0,0xFFFFFF,CPU,MEM)
for _,space in ipairs({{name='wram',kind=WRAM,size=0x20000},{name='sram',kind=SRAM,size=0x2000}}) do
    for _,op in ipairs({'read','write'}) do
        emu.addMemoryCallback(protect(function(bus_address,value)
            if not active then return end
            local mapped=assert(emu.convertAddress(bus_address,MEM,CPU))
            assert(mapped.memType==space.kind and type(mapped.address)=='number' and
                   mapped.address>=0 and mapped.address<space.size,'memory callback mapping')
            local address=mapped.address
            -- Lua debug writes do not generate CPU memory callbacks in the
            -- pinned API. If this changes, the independent replay rejects it.
            record({kind='bus',space=space.name,op=op,address=address,value=value,
                    bus_address=bus_address,pc=last_pc})
            if space.name=='wram' and not copied and address>=0x2830 and address<0x2880 then
                error('native access to opaque PC07 marker')
            end
        end),emu.callbackType[op],0,space.size-1,CPU,space.kind)
    end
end
emu.addMemoryCallback(protect(function(address,value)
    if active then
        record({kind='bus',space='table_rom',op='read',address=address-0xFFFA7B,
                value=value,bus_address=address,pc=last_pc})
    end
end),emu.callbackType.read,0xFFFA7B,0xFFFAA2,CPU,MEM)
emu.addEventCallback(protect(function()
    if active and cpu().clock-start_clock>1000000 then error('interval timeout') end
end),emu.eventType.endFrame)
