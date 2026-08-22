local output_dir = "private/test_runs/smoke"
local frame = 0

local function write_binary(path, data)
    local file = assert(io.open(path, "wb"))
    file:write(data)
    file:close()
end

local function capture(name)
    write_binary(output_dir .. "/" .. name, emu.takeScreenshot())
end

emu.addEventCallback(function()
    frame = frame + 1

    if frame == 1 then
        capture("frame_0001.png")
    elseif frame == 60 then
        capture("frame_0060.png")
    elseif frame == 180 then
        capture("frame_0180.png")
    elseif frame == 360 then
        capture("frame_0360.png")
    elseif frame == 600 then
        capture("frame_0600.png")
        local status = assert(io.open(output_dir .. "/smoke_status.txt", "w"))
        status:write("frames=600\n")
        status:close()
        emu.stop(0)
    end
end, emu.eventType.endFrame)
