-- Project Epoch private Mesen 2.1.1 Lavos battle checkpoint collector.
--
-- This script loads a disposable recovered final-battle SRAM, selects slot 1,
-- follows the already reproduced Lavos Tunnel route, advances the bounded
-- dialogue, and emits a native Mesen state only after the Lavos Core battle
-- structure is stable. ROM, SRAM, state, screenshot, and trace outputs must
-- remain under private/.

local CPU = emu.cpuType.snes
local CPU_MEMORY = emu.memType.snesMemory
local WRAM = emu.memType.snesWorkRam
local SRAM = emu.memType.snesSaveRam

local LOCATION = 0x0100
local PENDING_REQUEST = 0x0117
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local LEADER_OBJECT = 0x0197
local BATTLE_UI_STATE_0 = 0x06E2
local BATTLE_UI_STATE_1 = 0x06E6
local BATTLE_UI_STATE_2 = 0x06E7
local ACTIVE_MENU_SLOT = 0x95D5
local COMMAND_CURSOR_ROWS = 0x95DC
local MENU_READY_BATTLERS = 0xA6D9
local ACTIVE_READY_PC = 0xA6DD
local READY_PC_COUNT = 0xA6DE
local PC_LOCK_STATUS = 0xA0D1
local COMMAND_REDRAW = 0xA43F
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
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
local BATTLE_IDENTITY = 0x00
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
local LAVOS_TUNNEL = 0x01DA
local LAVOS_CORE = 0x01DB
local ROUTE_START_X = 2944
local ROUTE_START_Y = 15615
local EVENT_CMD_START_BATTLE = 0xC03A83

local EXPECTED_SRAM_LENGTH = 8192
local MAX_FRAME = 20000
local STABLE_BATTLE_FRAMES = 120
local CAPTURE_AFTER_BATTLE_FRAMES = 360
local SUCCESS_EXIT = 39
local FAILURE_EXIT = 91

local sram_path = assert(os.getenv("PE_SRAM_PATH"), "PE_SRAM_PATH is required")
local trace_path = assert(
	os.getenv("PE_CHECKPOINT_TRACE"),
	"PE_CHECKPOINT_TRACE is required"
)
local state_path = assert(
	os.getenv("PE_CHECKPOINT_STATE"),
	"PE_CHECKPOINT_STATE is required"
)
local screenshot_path = assert(
	os.getenv("PE_CHECKPOINT_SCREENSHOT"),
	"PE_CHECKPOINT_SCREENSHOT is required"
)
local error_path = assert(
	os.getenv("PE_CHECKPOINT_ERROR"),
	"PE_CHECKPOINT_ERROR is required"
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
assert(#source_sram == EXPECTED_SRAM_LENGTH, "disposable SRAM length mismatch")
assert(
	emu.getMemorySize(SRAM) == EXPECTED_SRAM_LENGTH,
	"emulated SRAM length mismatch"
)
for index = 1, #source_sram do
	emu.write(index - 1, source_sram:byte(index), SRAM)
end

local function sram_is_exact()
	for index = 1, #source_sram do
		if emu.read(index - 1, SRAM) ~= source_sram:byte(index) then
			return false
		end
	end
	return true
end

local function protected_ranges_are_exact()
	return range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH)
		and range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)
		and range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)
		and bytes_are_exact(EPOCH_NAME_START, EPOCH_NAME)
end

local function save_identity_is_exact()
	return location() == LAVOS_TUNNEL
		and read8(STORYLINE) == EXPECTED_STORYLINE
		and bytes_are_exact(ACTIVE_PARTY, EXPECTED_ACTIVE)
		and bytes_are_exact(ROSTER, EXPECTED_ROSTER)
		and read8(JOINED_FLAGS) == EXPECTED_JOINED
end

local function battle_record_offset(slot)
	return BATTLE_RECORD_BASE + slot * BATTLE_RECORD_STRIDE
end

local function battle_ids_hex()
	local parts = {}
	for slot = 0, 11 do
		table.insert(
			parts,
			string.format(
				"%02x",
				read8(battle_record_offset(slot) + BATTLE_IDENTITY)
			)
		)
	end
	return table.concat(parts)
end

local function battle_max_hp_csv()
	local parts = {}
	for _, row in ipairs(LAVOS_SLOTS) do
		table.insert(
			parts,
			tostring(read16(battle_record_offset(row.slot) + BATTLE_MAX_HP))
		)
	end
	return table.concat(parts, ",")
end

local function battle_current_hp_csv()
	local parts = {}
	for _, row in ipairs(LAVOS_SLOTS) do
		table.insert(
			parts,
			tostring(read16(battle_record_offset(row.slot) + BATTLE_CURRENT_HP))
		)
	end
	return table.concat(parts, ",")
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

local battle_launch_seen = false
local battle_launch_frame = nil

local function battle_anchor_matches()
	if not battle_launch_seen
		or location() ~= LAVOS_CORE
		or read8(STORYLINE) ~= EXPECTED_STORYLINE
		or read8(PENDING_REQUEST) ~= 0x01
		or read8(EXPLORE_MODE) ~= 0
		or read8(DIALOG_STATE) ~= 0
		or not bytes_are_exact(ACTIVE_PARTY, EXPECTED_ACTIVE)
		or not bytes_are_exact(ROSTER, EXPECTED_ROSTER)
		or read8(JOINED_FLAGS) ~= EXPECTED_JOINED
		or not command_ready()
	then
		return false
	end

	for _, row in ipairs(LAVOS_SLOTS) do
		local record = battle_record_offset(row.slot)
		local current_hp = read16(record + BATTLE_CURRENT_HP)
		local max_hp = read16(record + BATTLE_MAX_HP)
		if read8(record + BATTLE_IDENTITY) ~= row.identity
			or current_hp == 0
			or max_hp == 0
			or current_hp ~= max_hp
		then
			return false
		end
	end
	return true
end

local TRACE_HEADER = table.concat({
	"event",
	"frame",
	"stage",
	"location",
	"storyline",
	"pending",
	"explore",
	"dialog",
	"leader_x",
	"leader_y",
	"active",
	"roster",
	"joined",
	"battle_ids",
	"battle_current_hp",
	"battle_max_hp",
	"battle_ui",
	"command_state",
	"battle_launch_seen",
	"candidate_zero",
	"front_guard_zero",
	"rear_guard_zero",
	"epoch_exact",
	"sram_exact",
}, "\t")

local trace_lines = { TRACE_HEADER }
local frame = 0
local stage = "boot"
local stage_start = 0
local battle_stable_frames = 0
local capture_pending = false
local state_hook = nil
local battle_hook = nil

local function bool_text(value)
	return value and "true" or "false"
end

local function append_snapshot(event)
	local x, y = leader_position()
	table.insert(
		trace_lines,
		table.concat({
			event,
			tostring(frame),
			stage,
			string.format("%04x", location()),
			string.format("%02x", read8(STORYLINE)),
			string.format("%02x", read8(PENDING_REQUEST)),
			string.format("%02x", read8(EXPLORE_MODE)),
			string.format("%02x", read8(DIALOG_STATE)),
			tostring(x),
			tostring(y),
			byte_range_hex(ACTIVE_PARTY, 3),
			byte_range_hex(ROSTER, 9),
			string.format("%02x", read8(JOINED_FLAGS)),
			battle_ids_hex(),
			battle_current_hp_csv(),
			battle_max_hp_csv(),
			string.format(
				"%02x%02x%02x",
				read8(BATTLE_UI_STATE_0),
				read8(BATTLE_UI_STATE_1),
				read8(BATTLE_UI_STATE_2)
			),
			command_state_hex(),
			bool_text(battle_launch_seen),
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
	local ok = pcall(function()
		append_snapshot("failure")
		flush_trace()
		write_file(error_path, tostring(message) .. "\n")
	end)
	if not ok then
		-- The host still treats the non-success exit and missing outputs as a
		-- failure even if the diagnostic path itself could not be written.
	end
	emu.stop(FAILURE_EXIT)
end

local function begin_stage(name)
	stage = name
	stage_start = frame
	append_snapshot("stage")
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

local function span(active_frame, first, duration)
	return active_frame >= first and active_frame < first + duration
end

local function dialogue_confirm(relative)
	if battle_launch_seen or relative < 200 then
		return false
	end
	-- The accepted current-bsnes route used six released one-frame confirms in
	-- two groups. A two-frame pulse every 400 frames is more tolerant of the
	-- presentation boundary; the exact battle-launch hook below permanently
	-- suppresses all later confirms before the command menu can consume them.
	return ((relative - 200) % 400) < 2
end

local function arm_battle_launch_hook()
	assert(battle_hook == nil, "battle hook already armed")
	battle_hook = emu.addMemoryCallback(
		function()
			local ok, message = pcall(function()
				if not battle_launch_seen then
					battle_launch_seen = true
					battle_launch_frame = frame
					append_snapshot("battle-launch")
				end
			end)
			if not ok then
				fail(message)
			end
		end,
		emu.callbackType.exec,
		EVENT_CMD_START_BATTLE,
		EVENT_CMD_START_BATTLE,
		CPU,
		CPU_MEMORY
	)
end

local function queue_checkpoint_capture()
	if capture_pending then
		return
	end
	assert(battle_anchor_matches(), "battle anchor drifted before capture")
	assert(protected_ranges_are_exact(), "protected WRAM changed")
	assert(sram_is_exact(), "emulated SRAM changed")

	capture_pending = true
	write_file(screenshot_path, emu.takeScreenshot())
	append_snapshot("capture-queued")
	flush_trace()

	state_hook = emu.addMemoryCallback(
		function()
			local ok, message = pcall(function()
				assert(battle_anchor_matches(), "battle anchor drifted in capture")
				assert(protected_ranges_are_exact(), "protected WRAM changed in capture")
				assert(sram_is_exact(), "emulated SRAM changed in capture")
				local state = emu.createSavestate()
				assert(type(state) == "string" and #state > 0, "empty native state")
				write_file(state_path, state)
				append_snapshot("success")
				flush_trace()
				emu.removeMemoryCallback(
					state_hook,
					emu.callbackType.exec,
					0,
					0xFFFFFF,
					CPU,
					CPU_MEMORY
				)
				emu.stop(SUCCESS_EXIT)
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
end

append_snapshot("start")

emu.addEventCallback(
	function()
		local ok, message = pcall(function()
			frame = frame + 1
			local input = empty_input()

			if stage == "boot" then
				input.left = span(frame, 1800, 2)
				-- Left exposes Continue; slot 1 is already selected.
				input.a = span(frame, 2450, 4)

				if save_identity_is_exact()
					and read8(EXPLORE_MODE) == 1
				then
					local x, y = leader_position()
					if x == ROUTE_START_X and y == ROUTE_START_Y then
						assert(protected_ranges_are_exact(), "protected WRAM changed at load")
						assert(sram_is_exact(), "emulated SRAM changed at load")
						begin_stage("lavos-tunnel-route")
					end
				end
			elseif stage == "lavos-tunnel-route" then
				local relative = frame - stage_start
				input.up = span(relative, 60, 192)
					or span(relative, 316, 432)
					or span(relative, 796, 320)
					or span(relative, 1150, 64)
				input.left = span(relative, 260, 48)
					or span(relative, 756, 32)
				input.right = span(relative, 1124, 16)

				if location() == LAVOS_CORE
					and read8(STORYLINE) == EXPECTED_STORYLINE
					and bytes_are_exact(ACTIVE_PARTY, EXPECTED_ACTIVE)
					and bytes_are_exact(ROSTER, EXPECTED_ROSTER)
					and read8(JOINED_FLAGS) == EXPECTED_JOINED
				then
					arm_battle_launch_hook()
					begin_stage("lavos-dialogue")
				end
			elseif stage == "lavos-dialogue" then
				local relative = frame - stage_start
				input.a = dialogue_confirm(relative)
				if battle_launch_seen then
					begin_stage("battle-settle")
				end
			elseif stage == "battle-settle" then
				if battle_anchor_matches() then
					battle_stable_frames = battle_stable_frames + 1
				else
					battle_stable_frames = 0
				end
			end

			emu.setInput(input, 0)

			if frame % 600 == 0 then
				append_snapshot("probe")
				flush_trace()
			end
			if frame >= MAX_FRAME and not capture_pending then
				write_file(screenshot_path, emu.takeScreenshot())
				fail("Lavos battle checkpoint timed out")
			end
		end)
		if not ok then
			fail(message)
		end
	end,
	emu.eventType.inputPolled
)

emu.addEventCallback(
	function()
		if stage == "battle-settle"
			and battle_launch_frame ~= nil
			and frame - battle_launch_frame
				>= CAPTURE_AFTER_BATTLE_FRAMES
			and battle_stable_frames >= STABLE_BATTLE_FRAMES
			and not capture_pending
		then
			local ok, message = pcall(queue_checkpoint_capture)
			if not ok then
				fail(message)
			end
		end
	end,
	emu.eventType.endFrame
)
