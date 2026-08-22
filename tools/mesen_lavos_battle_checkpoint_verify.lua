-- Project Epoch private fresh-load verifier for the canonical Lavos checkpoint.
--
-- The host runs this exact script twice from the same canonical native state.
-- The control route performs Down then Up, returning to Attack while forcing a
-- completed command-window redraw. The Down route stops on Tech. Both routes
-- must remain in the full-HP Lavos battle without executing an action.

local CPU = emu.cpuType.snes
local CPU_MEMORY = emu.memType.snesMemory
local WRAM = emu.memType.snesWorkRam
local SRAM = emu.memType.snesSaveRam

local LOCATION = 0x0100
local PENDING_REQUEST = 0x0117
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local BATTLE_UI_STATE_0 = 0x06E2
local BATTLE_UI_STATE_1 = 0x06E6
local BATTLE_UI_STATE_2 = 0x06E7
local ACTIVE_MENU_SLOT = 0x95D5
local COMMAND_CURSOR_ROWS = 0x95DC
local MENU_READY_BATTLERS = 0xA6D9
local ACTIVE_READY_PC = 0xA6DD
local PC_LOCK_STATUS = 0xA0D1
local COMMAND_REDRAW = 0xA43F
local STORYLINE = 0x10000
local ACTIVE_PARTY = 0x2980
local ROSTER = 0x2980
local JOINED_FLAGS = 0x29AF

local CANDIDATE_START = 0x2CA0
local CANDIDATE_LENGTH = 0x50
local FRONT_GUARD_START = 0x2C9C
local FRONT_GUARD_LENGTH = 4
local REAR_GUARD_START = 0x2CF0
local REAR_GUARD_LENGTH = 0x10
local EPOCH_NAME_START = 0x2C4D
local EPOCH_NAME = { 0xA4, 0xC9, 0xC8, 0xBC, 0xC1, 0x00 }

local BATTLE_RECORD_BASE = 0x5E2D
local BATTLE_RECORD_STRIDE = 0x80
local BATTLE_CURRENT_HP = 0x03
local BATTLE_MAX_HP = 0x05
local LAVOS_SLOTS = {
	{ slot = 0, identity = 0x00 },
	{ slot = 1, identity = 0x01 },
	{ slot = 2, identity = 0x02 },
	{ slot = 3, identity = 0xCD },
	{ slot = 6, identity = 0xCC },
	{ slot = 10, identity = 0xCB },
}

local EXPECTED_ACTIVE = { 0x00, 0x01, 0x02 }
local EXPECTED_ROSTER = {
	0x00, 0x01, 0x02, 0x82, 0x80, 0x04, 0x03, 0x06, 0x05,
}
local EXPECTED_JOINED = 0xFE
local EXPECTED_STORYLINE = 0xD6
local LAVOS_CORE = 0x01DB
local EXPECTED_SRAM_LENGTH = 8192
local DOWN_FIRST_FRAME = 20
local DOWN_LAST_FRAME = 23
local UP_FIRST_FRAME = 32
local UP_LAST_FRAME = 35
local TERMINAL_FRAME = 60
local SUCCESS_EXIT = 47
local FAILURE_EXIT = 91

local mode = assert(os.getenv("PE_VERIFY_MODE"), "PE_VERIFY_MODE is required")
assert(mode == "control" or mode == "down", "PE_VERIFY_MODE is invalid")
local state_path = assert(
	os.getenv("PE_VERIFY_STATE"),
	"PE_VERIFY_STATE is required"
)
local sram_path = assert(os.getenv("PE_SRAM_PATH"), "PE_SRAM_PATH is required")
local trace_path = assert(
	os.getenv("PE_VERIFY_TRACE"),
	"PE_VERIFY_TRACE is required"
)
local screenshot_path = assert(
	os.getenv("PE_VERIFY_SCREENSHOT"),
	"PE_VERIFY_SCREENSHOT is required"
)
local error_path = assert(
	os.getenv("PE_VERIFY_ERROR"),
	"PE_VERIFY_ERROR is required"
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

local function bytes_are_exact(start_offset, expected)
	for index, value in ipairs(expected) do
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

local function byte_range_hex(start_offset, length)
	local parts = {}
	for offset = start_offset, start_offset + length - 1 do
		table.insert(parts, string.format("%02x", read8(offset)))
	end
	return table.concat(parts)
end

local source_sram = read_file(sram_path)
assert(#source_sram == EXPECTED_SRAM_LENGTH, "source SRAM length mismatch")
assert(
	emu.getMemorySize(SRAM) == EXPECTED_SRAM_LENGTH,
	"emulated SRAM length mismatch"
)

local function sram_is_exact()
	for index = 1, #source_sram do
		if emu.read(index - 1, SRAM) ~= source_sram:byte(index) then
			return false
		end
	end
	return true
end

local function battle_record_offset(slot)
	return BATTLE_RECORD_BASE + slot * BATTLE_RECORD_STRIDE
end

local function battle_ids_hex()
	local parts = {}
	for slot = 0, 11 do
		table.insert(
			parts,
			string.format("%02x", read8(battle_record_offset(slot)))
		)
	end
	return table.concat(parts)
end

local function battle_hp_csv(field_offset)
	local parts = {}
	for _, row in ipairs(LAVOS_SLOTS) do
		table.insert(
			parts,
			tostring(read16(battle_record_offset(row.slot) + field_offset))
		)
	end
	return table.concat(parts, ",")
end

local function battle_ui_hex()
	return string.format(
		"%02x%02x%02x",
		read8(BATTLE_UI_STATE_0),
		read8(BATTLE_UI_STATE_1),
		read8(BATTLE_UI_STATE_2)
	)
end

local function command_state_hex()
	return table.concat({
		byte_range_hex(ACTIVE_MENU_SLOT, 1),
		byte_range_hex(COMMAND_CURSOR_ROWS, 3),
		byte_range_hex(MENU_READY_BATTLERS, 3),
		byte_range_hex(ACTIVE_READY_PC, 2),
		byte_range_hex(PC_LOCK_STATUS, 3),
		byte_range_hex(COMMAND_REDRAW, 1),
	})
end

local function command_ready()
	local active_pc = read8(ACTIVE_READY_PC)
	if active_pc > 2 then
		return false
	end
	local battler = read8(MENU_READY_BATTLERS + active_pc)
	if battler >= 0x80 or read8(PC_LOCK_STATUS + battler) ~= 0 then
		return false
	end
	local menu_slot = read8(ACTIVE_MENU_SLOT)
	if menu_slot > 2 then
		return false
	end
	return read8(COMMAND_CURSOR_ROWS + menu_slot) <= 2
end

local function anchor_matches()
	if read16(LOCATION) ~= LAVOS_CORE
		or read8(STORYLINE) ~= EXPECTED_STORYLINE
		or read8(PENDING_REQUEST) ~= 0x01
		or read8(EXPLORE_MODE) ~= 0
		or read8(DIALOG_STATE) ~= 0
		or not bytes_are_exact(ACTIVE_PARTY, EXPECTED_ACTIVE)
		or not bytes_are_exact(ROSTER, EXPECTED_ROSTER)
		or read8(JOINED_FLAGS) ~= EXPECTED_JOINED
		or not command_ready()
		or not range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH)
		or not range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)
		or not range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)
		or not bytes_are_exact(EPOCH_NAME_START, EPOCH_NAME)
		or not sram_is_exact()
	then
		return false
	end
	for _, row in ipairs(LAVOS_SLOTS) do
		local record = battle_record_offset(row.slot)
		local current_hp = read16(record + BATTLE_CURRENT_HP)
		local max_hp = read16(record + BATTLE_MAX_HP)
		if read8(record) ~= row.identity
			or current_hp == 0
			or current_hp ~= max_hp
		then
			return false
		end
	end
	return true
end

local TRACE_HEADER = table.concat({
	"event",
	"mode",
	"relative_frame",
	"location",
	"storyline",
	"pending",
	"explore",
	"dialog",
	"active",
	"roster",
	"joined",
	"battle_ids",
	"battle_current_hp",
	"battle_max_hp",
	"battle_ui",
	"command_state",
	"candidate_zero",
	"front_guard_zero",
	"rear_guard_zero",
	"epoch_exact",
	"sram_exact",
}, "\t")
local trace_lines = { TRACE_HEADER }

local function bool_text(value)
	return value and "true" or "false"
end

local function append_snapshot(event, relative_frame)
	table.insert(
		trace_lines,
		table.concat({
			event,
			mode,
			tostring(relative_frame),
			string.format("%04x", read16(LOCATION)),
			string.format("%02x", read8(STORYLINE)),
			string.format("%02x", read8(PENDING_REQUEST)),
			string.format("%02x", read8(EXPLORE_MODE)),
			string.format("%02x", read8(DIALOG_STATE)),
			byte_range_hex(ACTIVE_PARTY, 3),
			byte_range_hex(ROSTER, 9),
			string.format("%02x", read8(JOINED_FLAGS)),
			battle_ids_hex(),
			battle_hp_csv(BATTLE_CURRENT_HP),
			battle_hp_csv(BATTLE_MAX_HP),
			battle_ui_hex(),
			command_state_hex(),
			bool_text(range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH)),
			bool_text(range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)),
			bool_text(range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)),
			bool_text(bytes_are_exact(EPOCH_NAME_START, EPOCH_NAME)),
			bool_text(sram_is_exact()),
		}, "\t")
	)
end

local function flush_trace()
	write_file(trace_path, table.concat(trace_lines, "\n") .. "\n")
end

local function fail(message)
	pcall(function()
		write_file(error_path, tostring(message) .. "\n")
	end)
	emu.stop(FAILURE_EXIT)
end

local function empty_input()
	return {
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
end

local serialized_state = read_file(state_path)
assert(#serialized_state > 0, "canonical state is empty")
local load_requested = false
local post_load_exec_seen = false
local prepared = false
local relative_frame = 0
local capture_pending = false
local load_hook = nil

load_hook = emu.addMemoryCallback(
	function()
		local ok, message = pcall(function()
			if not load_requested then
				load_requested = true
				emu.loadSavestate(serialized_state)
				return
			end
			post_load_exec_seen = true
		end)
		if not ok then
			fail(message)
		end
	end,
	emu.callbackType.exec,
	0,
	0xFFFFFF,
	CPU,
	CPU_MEMORY
)

emu.addEventCallback(
	function()
		local ok, message = pcall(function()
			local input = empty_input()
			if post_load_exec_seen and not prepared then
				emu.removeMemoryCallback(
					load_hook,
					emu.callbackType.exec,
					0,
					0xFFFFFF,
					CPU,
					CPU_MEMORY
				)
				assert(anchor_matches(), "fresh-load baseline anchor failed")
				prepared = true
				append_snapshot("baseline", 0)
				flush_trace()
			elseif prepared and not capture_pending then
				relative_frame = relative_frame + 1
				input.down = relative_frame >= DOWN_FIRST_FRAME
					and relative_frame <= DOWN_LAST_FRAME
				if mode == "control" then
					input.up = relative_frame >= UP_FIRST_FRAME
						and relative_frame <= UP_LAST_FRAME
				end
			end
			emu.setInput(input, 0)
		end)
		if not ok then
			fail(message)
		end
	end,
	emu.eventType.inputPolled
)

emu.addEventCallback(
	function()
		if not prepared
			or capture_pending
			or relative_frame < TERMINAL_FRAME
		then
			return
		end
		local ok, message = pcall(function()
			assert(anchor_matches(), "fresh-load terminal anchor failed")
			capture_pending = true
			append_snapshot("success", relative_frame)
			flush_trace()
			write_file(screenshot_path, emu.takeScreenshot())
			emu.stop(SUCCESS_EXIT)
		end)
		if not ok then
			fail(message)
		end
	end,
	emu.eventType.endFrame
)
