-- Project Epoch Mesen 2.1.1 instruction-level trace for event $11C.
--
-- This source-only collector loads a private native Mesen checkpoint,
-- prepares one bounded volatile diagnostic profile, observes the exact
-- vanilla absolute-read/absolute-write instructions used by the event, and
-- writes only a compact private JSON trace. It never writes a ROM or SRAM.

local WRAM = emu.memType.snesWorkRam
local CPU_MEMORY = emu.memType.snesMemory
local PRG_ROM = emu.memType.snesPrgRom
local CPU = emu.cpuType.snes

local LOCATION = 0x0100
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local LEADER_OBJECT = 0x0197
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
local STORYLINE = 0x10000
local MAGIC_FLAGS = 0x101E0
local ROBO_FLAGS = 0x101E2
local LAP_SCRATCH = 0x1021C
local ACTIVE_PARTY = 0x2980
local TECH_COUNTS = 0x2830
local LEARNED_MASKS = 0x2837
local EPOCH_NAME = 0x2C4D
local OLD_BLOCK_START = 0x2830
local OLD_BLOCK_END = 0x287F
local CANDIDATE_GUARDS_START = 0x2C9C
local CANDIDATE_GUARDS_END = 0x2CFF
local CANDIDATE_START = 0x2CA0
local CANDIDATE_LENGTH = 0x50
local FRONT_GUARD_START = 0x2C9C
local FRONT_GUARD_LENGTH = 4
local REAR_GUARD_START = 0x2CF0
local REAR_GUARD_LENGTH = 0x10
local CALLBACK_LIMIT = 64
local READ_ABS8_PC = 0xC06797
local WRITE_ABS_FROM_MEM8_PC = 0xC06822
local READ_ABS8_MAPPING = assert(
	emu.convertAddress(READ_ABS8_PC, CPU_MEMORY, CPU),
	"read handler is not mapped"
)
local WRITE_ABS_FROM_MEM8_MAPPING = assert(
	emu.convertAddress(WRITE_ABS_FROM_MEM8_PC, CPU_MEMORY, CPU),
	"write handler is not mapped"
)
local CHECKPOINT_DIRECT_PAGE = 0x0100
local CHECKPOINT_FRAME = 3237

local EXPECTED_EPOCH_NAME = { 0xA4, 0xC9, 0xC8, 0xBC, 0xC1, 0x00 }
local CANARY_HEX =
	"471eea9705fecea2040cc7e0d72b4a50a9a996d83f9cc34b46c753b1968f659b" ..
	"aaa47f0daf10c8d9074953390d34d25c5f631b7bbf6d1f08e1ff2387281084f7" ..
	"844c9cda36c941873207b6269ea72566"

local PROFILES = {
	["frog-robo"] = {
		active_party = { 0x06, 0x04, 0x03 },
		clear_magic_bits = 0x18,
		clear_robo_bits = 0x01,
		tech_count_offsets = { 0x2834 },
		learned_mask_offsets = { 0x283B },
		remaining_tp_offsets = { 0x276D },
		expected_callbacks = {
			{ access = "write", address = 0x7E2834 },
			{ access = "read", address = 0x7E283B },
			{ access = "write", address = 0x7E283B },
		},
		minimum_terminal_frame = 1500,
	},
	["crono-marle-lucca"] = {
		active_party = { 0x00, 0x01, 0x02 },
		clear_magic_bits = 0x47,
		clear_robo_bits = 0x00,
		tech_count_offsets = { 0x2830, 0x2831, 0x2832 },
		learned_mask_offsets = { 0x2837, 0x2838, 0x2839 },
		remaining_tp_offsets = { 0x262D, 0x267D, 0x26CD },
		expected_callbacks = {
			{ access = "write", address = 0x7E2830 },
			{ access = "read", address = 0x7E2837 },
			{ access = "write", address = 0x7E2837 },
			{ access = "write", address = 0x7E2831 },
			{ access = "read", address = 0x7E2838 },
			{ access = "write", address = 0x7E2838 },
			{ access = "write", address = 0x7E2832 },
			{ access = "read", address = 0x7E2839 },
			{ access = "write", address = 0x7E2839 },
		},
		minimum_terminal_frame = 2000,
	},
}

local state_path = assert(os.getenv("PE_STATE_PATH"), "PE_STATE_PATH is required")
local trace_path = assert(os.getenv("PE_TRACE_OUT"), "PE_TRACE_OUT is required")
local screenshot_path = assert(
	os.getenv("PE_TRACE_SCREENSHOT"),
	"PE_TRACE_SCREENSHOT is required"
)
local profile_name = assert(os.getenv("PE_PROFILE"), "PE_PROFILE is required")
local variant = assert(os.getenv("PE_VARIANT"), "PE_VARIANT is required")
local profile = assert(PROFILES[profile_name], "unknown PE_PROFILE")
assert(variant == "zero" or variant == "canary", "unknown PE_VARIANT")

local function require_private_path(path, label)
	local normalized = path:gsub("\\", "/"):lower()
	for part in normalized:gmatch("[^/]+") do
		assert(part ~= "..", label .. " contains parent traversal")
	end
	assert(
		("/" .. normalized):find("/private/", 1, true) ~= nil,
		label .. " must remain under private/"
	)
	return path
end

state_path = require_private_path(state_path, "PE_STATE_PATH")
trace_path = require_private_path(trace_path, "PE_TRACE_OUT")
screenshot_path = require_private_path(
	screenshot_path,
	"PE_TRACE_SCREENSHOT"
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

local function write8(offset, value)
	emu.write(offset, value & 0xFF, WRAM)
end

local function write16(offset, value)
	emu.write16(offset, value & 0xFFFF, WRAM)
end

local function bytes_from_hex(value)
	assert(#value % 2 == 0)
	local result = {}
	for index = 1, #value, 2 do
		table.insert(result, assert(tonumber(value:sub(index, index + 1), 16)))
	end
	return result
end

local CANARY = bytes_from_hex(CANARY_HEX)
assert(#CANARY == CANDIDATE_LENGTH)

local function range_hex(start_offset, length)
	local values = {}
	for offset = start_offset, start_offset + length - 1 do
		table.insert(values, string.format("%02x", read8(offset)))
	end
	return table.concat(values)
end

local function range_matches(start_offset, values)
	for index, value in ipairs(values) do
		if read8(start_offset + index - 1) ~= value then
			return false
		end
	end
	return true
end

local function range_is_zero(start_offset, length)
	for offset = start_offset, start_offset + length - 1 do
		if read8(offset) ~= 0 then
			return false
		end
	end
	return true
end

local function candidate_matches_variant()
	if variant == "zero" then
		return range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH)
	end
	return range_matches(CANDIDATE_START, CANARY)
end

local function json_string(value)
	value = value:gsub("\\", "\\\\")
	value = value:gsub('"', '\\"')
	value = value:gsub("\r", "\\r")
	value = value:gsub("\n", "\\n")
	value = value:gsub("\t", "\\t")
	return '"' .. value .. '"'
end

local function bool_json(value)
	return value and "true" or "false"
end

local function snapshot_json()
	local object = read8(LEADER_OBJECT)
	return table.concat({
		"{",
		'"location":', tostring(read16(LOCATION)), ",",
		'"storyline":', tostring(read8(STORYLINE)), ",",
		'"lap_scratch":', tostring(read8(LAP_SCRATCH)), ",",
		'"magic_flags":', tostring(read8(MAGIC_FLAGS)), ",",
		'"robo_flags":', tostring(read8(ROBO_FLAGS)), ",",
		'"explore_mode":', tostring(read8(EXPLORE_MODE)), ",",
		'"dialog_state":', tostring(read8(DIALOG_STATE)), ",",
		'"leader_x":', tostring(read16(OBJECT_X + object)), ",",
		'"leader_y":', tostring(read16(OBJECT_Y + object)), ",",
		'"active_party_hex":', json_string(range_hex(ACTIVE_PARTY, 3)), ",",
		'"tech_counts_hex":', json_string(range_hex(TECH_COUNTS, 7)), ",",
		'"learned_masks_hex":', json_string(range_hex(LEARNED_MASKS, 7)), ",",
		'"candidate_matches_variant":', bool_json(candidate_matches_variant()), ",",
		'"front_guard_hex":', json_string(range_hex(FRONT_GUARD_START, FRONT_GUARD_LENGTH)), ",",
		'"rear_guard_hex":', json_string(range_hex(REAR_GUARD_START, REAR_GUARD_LENGTH)), ",",
		'"epoch_name_hex":', json_string(range_hex(EPOCH_NAME, #EXPECTED_EPOCH_NAME)),
		"}",
	})
end

local serialized_state = read_file(state_path)
local state_loaded = false
local trace_hooks_armed = false
local prepared = false
local relative_frame = 0
local overflow = false
local callbacks = {}
local observer_error = nil
local direct_page = nil
local cached_absolute_frame = 0
local pending_write = nil
local pre_json = nil
local post_json = nil
local load_hook = nil

local function is_watched_wram_offset(offset)
	return (offset >= OLD_BLOCK_START and offset <= OLD_BLOCK_END)
		or (
			offset >= CANDIDATE_GUARDS_START
			and offset <= CANDIDATE_GUARDS_END
		)
end

local function read_pointer(direct_page_offset)
	assert(direct_page ~= nil, "direct page was not cached")
	local base = (direct_page + direct_page_offset) & 0xFFFF
	local address = read8(base) | (read8((base + 1) & 0xFFFF) << 8)
	local bank = read8((base + 2) & 0xFFFF)
	local wram_offset = nil
	if bank == 0x7E then
		wram_offset = address
	elseif bank == 0x7F then
		wram_offset = 0x10000 + address
	end
	return bank * 0x10000 + address, wram_offset
end

local function callback_record(
	access,
	address,
	wram_offset,
	value,
	pc24,
	absolute_frame
)
	if not prepared then
		return
	end
	if wram_offset == nil or not is_watched_wram_offset(wram_offset) then
		return
	end
	if #callbacks >= CALLBACK_LIMIT then
		overflow = true
		return
	end
	table.insert(callbacks, {
		seq = #callbacks,
		frame = relative_frame,
		absolute_frame = absolute_frame,
		access = access,
		address = address,
		raw_wram_offset = wram_offset,
		value = value,
		pc24 = pc24,
	})
end

local function observe_handler(address)
	if not prepared then
		return
	end
	if pending_write ~= nil then
		local completed = pending_write
		pending_write = nil
		local value = completed.wram_offset == nil
			and 0
			or read8(completed.wram_offset)
		callback_record(
			"write",
			completed.address,
			completed.wram_offset,
			value,
			WRITE_ABS_FROM_MEM8_PC,
			completed.absolute_frame
		)
	end
	if address ~= READ_ABS8_PC and address ~= WRITE_ABS_FROM_MEM8_PC then
		return
	end
	if address == READ_ABS8_PC then
		local target, wram_offset = read_pointer(0xCD)
		local value = wram_offset == nil and 0 or read8(wram_offset)
		callback_record(
			"read",
			target,
			wram_offset,
			value,
			READ_ABS8_PC,
			cached_absolute_frame
		)
	elseif address == WRITE_ABS_FROM_MEM8_PC then
		local target, wram_offset = read_pointer(0xD0)
		pending_write = {
			address = target,
			wram_offset = wram_offset,
			absolute_frame = cached_absolute_frame,
		}
	end
end

local function prepare()
	assert(trace_hooks_armed, "trace hooks were not armed after state load")
	direct_page = CHECKPOINT_DIRECT_PAGE
	cached_absolute_frame = CHECKPOINT_FRAME
	assert(read16(LOCATION) == 0x01D1, "checkpoint location mismatch")
	assert(read8(EXPLORE_MODE) == 1, "checkpoint is not controllable")
	assert(read8(DIALOG_STATE) == 0, "checkpoint has dialogue open")
	local object = read8(LEADER_OBJECT)
	assert(read16(OBJECT_X + object) == 1568, "checkpoint X mismatch")
	assert(read16(OBJECT_Y + object) == 2623, "checkpoint Y mismatch")
	assert(range_hex(ACTIVE_PARTY, 3) == "060403", "source party mismatch")
	assert(range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH), "front guard is not zero")
	assert(range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH), "candidate is not zero")
	assert(range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH), "rear guard is not zero")
	assert(range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME), "Epoch name mismatch")

	write8(STORYLINE, 0x4C)
	write8(LAP_SCRATCH, 0x03)
	write8(MAGIC_FLAGS, read8(MAGIC_FLAGS) & (~profile.clear_magic_bits & 0xFF))
	if profile.clear_robo_bits ~= 0 then
		write8(ROBO_FLAGS, read8(ROBO_FLAGS) & (~profile.clear_robo_bits & 0xFF))
	end
	for index, pc_id in ipairs(profile.active_party) do
		write8(ACTIVE_PARTY + index - 1, pc_id)
	end
	for _, offset in ipairs(profile.tech_count_offsets) do
		write8(offset, 0)
	end
	for _, offset in ipairs(profile.learned_mask_offsets) do
		write8(offset, read8(offset) & 0x1F)
	end
	for _, offset in ipairs(profile.remaining_tp_offsets) do
		write16(offset, 0)
	end
	if variant == "canary" then
		for index, value in ipairs(CANARY) do
			write8(CANDIDATE_START + index - 1, value)
		end
	end

	assert(candidate_matches_variant(), "candidate preparation mismatch")
	assert(range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH), "front guard changed")
	assert(range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH), "rear guard changed")
	assert(range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME), "Epoch name changed")
	pre_json = snapshot_json()
	prepared = true
end

local function callback_json(record)
	return table.concat({
		"{",
		'"seq":', tostring(record.seq), ",",
		'"frame":', tostring(record.frame), ",",
		'"absolute_frame":', tostring(record.absolute_frame), ",",
		'"access":', json_string(record.access), ",",
		'"address":', tostring(record.address), ",",
		'"raw_wram_offset":', tostring(record.raw_wram_offset), ",",
		'"value":', tostring(record.value), ",",
		'"pc24":', tostring(record.pc24),
		"}",
	})
end

local function unexpected_access_count()
	local expected = profile.expected_callbacks
	local count = math.abs(#callbacks - #expected)
	local shared = math.min(#callbacks, #expected)
	for index = 1, shared do
		local actual = callbacks[index]
		local wanted = expected[index]
		if actual.access ~= wanted.access or actual.address ~= wanted.address then
			count = count + 1
		end
	end
	return count
end

local function final_fields_match()
	if read8(STORYLINE) ~= 0x4D then
		return false
	end
	if range_hex(LEARNED_MASKS, 7) ~= "ffffffffffffff" then
		return false
	end
	local counts = range_hex(TECH_COUNTS, 7)
	if profile_name == "frog-robo" then
		return counts == "08080808030808"
	end
	return counts == "03030308080808"
end

local function emit_trace(success)
	post_json = snapshot_json()
	local callback_parts = {}
	for _, record in ipairs(callbacks) do
		table.insert(callback_parts, callback_json(record))
	end
	local unexpected = unexpected_access_count()
	local trace = table.concat({
		"{",
		'"schema":"project-epoch-mesen-event11c-access-trace-v1",',
		'"collector_version":2,',
		'"profile":', json_string(profile_name), ",",
		'"variant":', json_string(variant), ",",
		'"observer":{',
		'"read_pc24":', tostring(READ_ABS8_PC), ",",
		'"read_mapped_address":', tostring(READ_ABS8_MAPPING.address), ",",
		'"read_mapping_is_prg_rom":', bool_json(READ_ABS8_MAPPING.memType == PRG_ROM), ",",
		'"write_pc24":', tostring(WRITE_ABS_FROM_MEM8_PC), ",",
		'"write_mapped_address":', tostring(WRITE_ABS_FROM_MEM8_MAPPING.address), ",",
		'"write_mapping_is_prg_rom":', bool_json(WRITE_ABS_FROM_MEM8_MAPPING.memType == PRG_ROM),
		',"mechanism":"broad-exec-callback-exact-pc-router",',
		'"checkpoint_direct_page":', tostring(CHECKPOINT_DIRECT_PAGE), ",",
		'"checkpoint_frame":', tostring(CHECKPOINT_FRAME),
		"},",
		'"pre":', pre_json or "null", ",",
		'"callbacks":[', table.concat(callback_parts, ","), "],",
		'"post":', post_json, ",",
		'"termination":{',
		'"collector_stopped":true,',
		'"success":', bool_json(success), ",",
		'"overflow":', bool_json(overflow), ",",
		'"observer_error":',
		observer_error == nil and "null" or json_string(observer_error), ",",
		'"unexpected_accesses":', tostring(unexpected),
		"}",
		"}\n",
	})
	write_file(trace_path, trace)
	write_file(screenshot_path, emu.takeScreenshot())
end

load_hook = emu.addMemoryCallback(
	function(address)
		if not state_loaded then
			state_loaded = true
			emu.loadSavestate(serialized_state)
			return
		end
		if not trace_hooks_armed then
			trace_hooks_armed = true
		end
		if observer_error == nil then
			local ok, message = pcall(observe_handler, address)
			if not ok then
				observer_error = tostring(message)
				write_file(
					trace_path .. ".observer-error",
					observer_error .. "\n"
				)
			end
		end
	end,
	emu.callbackType.exec,
	0,
	0xFFFFFF,
	CPU,
	CPU_MEMORY
)

local function pulse(frame, first, last)
	return frame >= first and frame <= last
end

emu.addEventCallback(
	function()
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

		if state_loaded and not prepared then
			prepare()
		elseif prepared then
			relative_frame = relative_frame + 1
			cached_absolute_frame = cached_absolute_frame + 1
			input.a = pulse(relative_frame, 60, 61)
				or pulse(relative_frame, 180, 181)
				or pulse(relative_frame, 300, 301)
				or pulse(relative_frame, 420, 421)
				or pulse(relative_frame, 540, 541)
				or pulse(relative_frame, 660, 661)
				or pulse(relative_frame, 780, 781)
				or pulse(relative_frame, 900, 901)
				or pulse(relative_frame, 1020, 1021)
				or pulse(relative_frame, 1140, 1141)
			if profile_name == "crono-marle-lucca" then
				input.a = input.a or pulse(relative_frame, 1860, 1861)
			end

			if relative_frame >= profile.minimum_terminal_frame
				and final_fields_match()
				and candidate_matches_variant()
				and range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)
				and range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)
				and range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME)
				and observer_error == nil
				and pending_write == nil
				and not overflow
				and unexpected_access_count() == 0
			then
				emit_trace(true)
				emu.stop(41)
			elseif relative_frame >= 2400 then
				emit_trace(false)
				emu.stop(91)
			end
		end

		emu.setInput(input, 0)
	end,
	emu.eventType.inputPolled
)
