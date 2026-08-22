-- Project Epoch private Mesen 2.1.1 Spekkio checkpoint collector.
--
-- This script loads a disposable SRAM image, follows the already calibrated
-- slot-3/End-of-Time route with controller input, and emits a native Mesen
-- checkpoint only after reaching the bounded talkable state in location $1D1.
-- ROMs, SRAM, screenshots, savestates, and logs must remain under private/.

local WRAM = emu.memType.snesWorkRam
local SRAM = emu.memType.snesSaveRam

local LOCATION = 0x0100
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local LEADER_OBJECT = 0x0197
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
local CANDIDATE_START = 0x2CA0
local CANDIDATE_LENGTH = 0x50
local FRONT_GUARD_START = 0x2C9C
local FRONT_GUARD_LENGTH = 4
local REAR_GUARD_START = 0x2CF0
local REAR_GUARD_LENGTH = 0x10
local EPOCH_NAME_START = 0x2C4D
local EPOCH_NAME = { 0xA4, 0xC9, 0xC8, 0xBC, 0xC1, 0x00 }

local sram_path = assert(os.getenv("PE_SRAM_PATH"), "PE_SRAM_PATH is required")
local log_path = assert(os.getenv("PE_CHECKPOINT_LOG"), "PE_CHECKPOINT_LOG is required")
local state_path = assert(os.getenv("PE_CHECKPOINT_STATE"), "PE_CHECKPOINT_STATE is required")
local screenshot_path = assert(
	os.getenv("PE_CHECKPOINT_SCREENSHOT"),
	"PE_CHECKPOINT_SCREENSHOT is required"
)

local function read_file(path)
	local file = assert(io.open(path, "rb"))
	local data = assert(file:read("*a"))
	file:close()
	return data
end

local function write_file(path, data)
	local file = assert(io.open(path, "wb"))
	assert(file:write(data))
	file:close()
end

local function read8(offset)
	return emu.read(offset, WRAM)
end

local function read16(offset)
	return emu.read16(offset, WRAM)
end

local function location()
	return read16(LOCATION)
end

local function leader_position()
	local object = read8(LEADER_OBJECT)
	return read16(OBJECT_X + object), read16(OBJECT_Y + object)
end

local function range_is_zero(start_offset, length)
	for offset = start_offset, start_offset + length - 1 do
		if read8(offset) ~= 0 then
			return false
		end
	end
	return true
end

local function epoch_name_is_exact()
	for index, value in ipairs(EPOCH_NAME) do
		if read8(EPOCH_NAME_START + index - 1) ~= value then
			return false
		end
	end
	return true
end

local log_lines = {}

local function append_snapshot(label, frame)
	local x, y = leader_position()
	table.insert(
		log_lines,
		string.format(
			"%s\tframe=%d\tlocation=%04x\tx=%d\ty=%d\texplore=%02x\tdialog=%02x",
			label,
			frame,
			location(),
			x,
			y,
			read8(EXPLORE_MODE),
			read8(DIALOG_STATE)
		)
	)
end

local function flush_log(status, frame)
	append_snapshot(status, frame)
	write_file(log_path, table.concat(log_lines, "\n") .. "\n")
end

local sram = read_file(sram_path)
assert(#sram == emu.getMemorySize(SRAM), "disposable SRAM length mismatch")
for index = 1, #sram do
	emu.write(index - 1, sram:byte(index), SRAM)
end

local frame = 0
local stage = "boot"
local stage_start = 0
local state_hook = nil
local capture_pending = false

local function begin_stage(name)
	stage = name
	stage_start = frame
	append_snapshot("stage-" .. name, frame)
end

local function exact_talkable_state()
	if location() ~= 0x01D1 then
		return false
	end
	local x, y = leader_position()
	return x == 1568
		and y == 2623
		and read8(EXPLORE_MODE) == 1
		and read8(DIALOG_STATE) == 0
end

local function queue_checkpoint_capture()
	if capture_pending then
		return
	end
	capture_pending = true

	assert(range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH), "candidate is not zero")
	assert(range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH), "front guard is not zero")
	assert(range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH), "rear guard is not zero")
	assert(epoch_name_is_exact(), "Epoch name changed")

	write_file(screenshot_path, emu.takeScreenshot())
	flush_log("success", frame)

	state_hook = emu.addMemoryCallback(
		function()
			local state = emu.createSavestate()
			write_file(state_path, state)
			emu.removeMemoryCallback(
				state_hook,
				emu.callbackType.exec,
				0x000000,
				0xFFFFFF,
				emu.cpuType.snes,
				emu.memType.snesMemory
			)
			emu.stop(39)
		end,
		emu.callbackType.exec,
		0x000000,
		0xFFFFFF,
		emu.cpuType.snes,
		emu.memType.snesMemory
	)
end

local function pulse(active, first, last)
	return active >= first and active <= last
end

local function on_input_polled()
	frame = frame + 1
	local input = {
		a = false,
		b = false,
		x = false,
		y = false,
		l = false,
		r = false,
		up = false,
		down = false,
		left = false,
		right = false,
		start = false,
		select = false,
	}

	if stage == "boot" then
		input.left = pulse(frame, 1800, 1801)
		-- On the title screen, Left exposes the Continue/save list directly.
		-- Confirming immediately selects slot 1, so move twice before A.
		input.down = pulse(frame, 2200, 2201) or pulse(frame, 2300, 2301)
		input.a = pulse(frame, 2450, 2453)

		if location() == 0x01D0 then
			local x, y = leader_position()
			if x == 6272 and y == 5887 then
				begin_stage("end-time-diagonal")
			end
		end
	elseif stage == "end-time-diagonal" then
		local relative = frame - stage_start
		input.up = pulse(relative, 60, 359)
		input.right = pulse(relative, 60, 359)
		if relative >= 420 then
			local x, y = leader_position()
			if location() == 0x01D0 and x == 7888 and y == 4271 then
				begin_stage("door")
			end
		end
	elseif stage == "door" then
		local relative = frame - stage_start
		input.right = pulse(relative, 60, 67)
		input.up = pulse(relative, 80, 129)
		if location() == 0x01D1 then
			local x, y = leader_position()
			if x == 1536 and y == 3583 then
				begin_stage("approach")
			end
		end
	elseif stage == "approach" then
		local relative = frame - stage_start
		input.up = pulse(relative, 60, 119)
		input.right = pulse(relative, 140, 141)
		if relative >= 170 and exact_talkable_state() then
			begin_stage("capture")
			queue_checkpoint_capture()
		end
	end

	emu.setInput(input, 0)

	if frame == 2000
		or frame == 2500
		or frame == 3190
		or frame == 3250
		or frame == 3350
		or frame == 3490
		or frame == 3550
		or frame == 3500
		or frame == 4200
	then
		append_snapshot("probe", frame)
		write_file(
			screenshot_path .. "." .. tostring(frame) .. ".png",
			emu.takeScreenshot()
		)
	end

	if frame >= 12000 and not capture_pending then
		write_file(screenshot_path, emu.takeScreenshot())
		flush_log("failure-timeout", frame)
		emu.stop(90)
	end
end

append_snapshot("start", frame)
emu.addEventCallback(on_input_polled, emu.eventType.inputPolled)
