-- Project Epoch native-Mesen field-animation probe v0.
--
-- Launcher-only exploratory collector. The paired Python launcher binds all
-- paths to this workspace's ignored private tree, stages disposable copies of
-- the ROM/SRAM/state/runtime, and verifies their identities before and after
-- execution. This collector performs no emulated-memory writes.

local WRAM = emu.memType.snesWorkRam
local CPU_MEMORY = emu.memType.snesMemory
local PRG_ROM = emu.memType.snesPrgRom
local CPU = emu.cpuType.snes

local SCHEMA = "project-epoch-private-mesen-field-animation-probe-v0"
local COLLECTOR_VERSION = 1
local LAUNCH_PROTOCOL = "project-epoch-field-animation-launcher-v0"
local EVIDENCE_LEVEL = "exploratory-runtime-not-accepted"

local LOCATION = 0x0100
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local FIELD_FRAME_COUNTER = 0x014B
local CURRENT_OBJECT_DP = 0x006D
local LEADER_OBJECT = 0x0197
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
local ACTIVE_PARTY = 0x2980

local OBJECT_STATUS = 0x1100
local OBJECT_ID = 0x1101
local OBJECT_ANIM_STRIDE = 0x1480
local OBJECT_MAIN_BASE = 0x1500
local OBJECT_TIMING_BASE = 0x1580
local OBJECT_FACING = 0x1600
local OBJECT_DELAY = 0x1601
local OBJECT_SELECTOR = 0x1680
local OBJECT_CURSOR = 0x1681
local OBJECT_ALT_MODE = 0x1780
local OBJECT_ALT_SELECTOR = 0x1781
local OBJECT_CACHED_FRAME = 0x0F01
local OBJECT_ASSEMBLY_BANK = 0x1300
local OBJECT_ASSEMBLY_BASE = 0x1380

local WATCHED_PCS = {
	[0xC0CA18] = "timing-selector-load",
	[0xC0CA35] = "timing-stream-read",
	[0xC0CA3D] = "timing-reload-read",
	[0xC0CB3A] = "main-facing-pointer-entry",
	[0xC0CBC2] = "main-frame-stream-read",
	[0xC0CC04] = "frame-cache-compare",
}
local EXPECTED_OPCODES = {
	[0xC0CA18] = 0xBD,
	[0xC0CA35] = 0xBF,
	[0xC0CA3D] = 0xBF,
	[0xC0CB3A] = 0xBD,
	[0xC0CBC2] = 0xA7,
	[0xC0CC04] = 0xDD,
}
local ORDERED_PCS = {
	0xC0CA18,
	0xC0CA35,
	0xC0CA3D,
	0xC0CB3A,
	0xC0CBC2,
	0xC0CC04,
}
local EXPECTED_BINDINGS = {
	{
		object_slot = 0x08,
		logical_pc_id = 0x03,
		object_status = 0x02,
		main_base = 0x3CF0,
		timing_base = 0xAB3C,
	},
	{
		object_slot = 0x0A,
		logical_pc_id = 0x04,
		object_status = 0x01,
		main_base = 0x4160,
		timing_base = 0xAC58,
	},
	{
		object_slot = 0x0E,
		logical_pc_id = 0x06,
		object_status = 0x00,
		main_base = 0x4B00,
		timing_base = 0xAEC0,
	},
}

local EXPECTED_STATE_SIZE = 133993
local EXPECTED_LOCATION = 0x01D1
local EXPECTED_PARTY_HEX = "060403"
local EXPECTED_LEADER_OBJECT = 0x0E
local EXPECTED_LEADER_X = 1568
local EXPECTED_LEADER_Y = 2623
local TERMINAL_FRAME = 240
local CALLBACK_LIMIT = 20000

local function normalize_absolute_path(path, label)
	assert(type(path) == "string" and path ~= "", label .. " is required")
	local normalized = path:gsub("\\", "/")
	assert(normalized:match("^%a:/") ~= nil, label .. " must be absolute")
	assert(normalized:find("//", 1, true) == nil, label .. " has an empty segment")
	for part in normalized:gmatch("[^/]+") do
		assert(part ~= "." and part ~= "..", label .. " contains traversal")
	end
	return normalized:lower()
end

local function path_is_strict_child(path, parent)
	return path:sub(1, #parent + 1) == parent .. "/"
end

local function path_parent(path)
	return assert(path:match("^(.*)/[^/]+$"), "path has no parent")
end

local state_path = assert(os.getenv("PE_STATE_PATH"), "PE_STATE_PATH is required")
local trace_path = assert(os.getenv("PE_TRACE_OUT"), "PE_TRACE_OUT is required")
local screenshot_path = assert(
	os.getenv("PE_TRACE_SCREENSHOT"),
	"PE_TRACE_SCREENSHOT is required"
)
local private_root = normalize_absolute_path(
	assert(os.getenv("PE_WORKSPACE_PRIVATE_ROOT")),
	"PE_WORKSPACE_PRIVATE_ROOT"
)
local output_root = normalize_absolute_path(
	assert(os.getenv("PE_OUTPUT_ROOT")),
	"PE_OUTPUT_ROOT"
)
local staging_root = normalize_absolute_path(
	assert(os.getenv("PE_STAGING_ROOT")),
	"PE_STAGING_ROOT"
)
local launch_protocol = assert(
	os.getenv("PE_LAUNCH_PROTOCOL"),
	"PE_LAUNCH_PROTOCOL is required"
)
local launch_nonce = assert(os.getenv("PE_LAUNCH_NONCE"), "PE_LAUNCH_NONCE is required")
local route = assert(os.getenv("PE_ROUTE"), "PE_ROUTE is required")
local repetition = assert(
	tonumber(os.getenv("PE_REPETITION")),
	"PE_REPETITION is required"
)

assert(launch_protocol == LAUNCH_PROTOCOL, "launcher protocol mismatch")
assert(#launch_nonce == 32 and launch_nonce:match("^[0-9a-f]+$") ~= nil, "launch nonce invalid")
assert(route == "idle" or route == "right", "unknown PE_ROUTE")
assert(repetition == math.floor(repetition) and repetition >= 1, "invalid PE_REPETITION")
assert(private_root:sub(-8) == "/private", "workspace private root suffix mismatch")
local test_runs_root = private_root .. "/test_runs"
assert(
	path_is_strict_child(output_root, test_runs_root),
	"output root escaped workspace private test-runs root"
)
assert(path_is_strict_child(staging_root, output_root), "staging root escaped output root")

local normalized_state = normalize_absolute_path(state_path, "PE_STATE_PATH")
local normalized_trace = normalize_absolute_path(trace_path, "PE_TRACE_OUT")
local normalized_screenshot = normalize_absolute_path(
	screenshot_path,
	"PE_TRACE_SCREENSHOT"
)
assert(path_parent(normalized_state) == staging_root, "state is not directly inside staging root")
assert(path_parent(normalized_trace) == output_root, "trace is not directly inside output root")
assert(path_parent(normalized_screenshot) == output_root, "screenshot is not directly inside output root")
assert(normalized_trace ~= normalized_screenshot, "trace and screenshot paths collide")

local function read_file(path)
	local file = assert(io.open(path, "rb"))
	local data = assert(file:read("*a"))
	file:close()
	return data
end

local function write_new_file(path, data)
	local existing = io.open(path, "rb")
	assert(existing == nil, "refusing to overwrite output: " .. path)
	local file = assert(io.open(path, "wb"))
	assert(file:write(data))
	file:close()
end

local function read8(offset)
	return emu.read(offset & 0x1FFFF, WRAM)
end

local function read16(offset)
	local low = read8(offset)
	local high = read8((offset + 1) & 0x1FFFF)
	return low | (high << 8)
end

local function read_cpu8(address)
	return emu.read(address & 0xFFFFFF, CPU_MEMORY)
end

local function range_hex(start_offset, length)
	local values = {}
	for offset = start_offset, start_offset + length - 1 do
		table.insert(values, string.format("%02x", read8(offset)))
	end
	return table.concat(values)
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

local function nullable_number(value)
	return value == nil and "null" or tostring(value)
end

local function state_number(state, key, required)
	local value = state["cpu." .. key]
	if required then
		assert(
			type(value) == "number" and value == math.floor(value),
			"emu.getState().cpu." .. key .. " is unavailable"
		)
	end
	if type(value) ~= "number" or value ~= math.floor(value) then
		return nil
	end
	return value
end

local function cpu_snapshot()
	local state = emu.getState()
	assert(type(state) == "table", "emu.getState() did not return a table")
	local result = {
		a = state_number(state, "a", true) & 0xFFFF,
		x = state_number(state, "x", true) & 0xFFFF,
		y = state_number(state, "y", true) & 0xFFFF,
		d = state_number(state, "d", true) & 0xFFFF,
		ps = state_number(state, "ps", true) & 0xFF,
		sp = state_number(state, "sp", false),
		db = state_number(state, "db", false),
		pc = state_number(state, "pc", true) & 0xFFFF,
		k = state_number(state, "k", true) & 0xFF,
	}
	result.pc24 = (result.k << 16) | result.pc
	if result.sp ~= nil then
		result.sp = result.sp & 0xFFFF
	end
	if result.db ~= nil then
		result.db = result.db & 0xFF
	end
	return result
end

local function raw_dp_offset(cpu, operand)
	return (cpu.d + operand) & 0xFFFF
end

local function current_object_slot(cpu, address)
	if address == 0xC0CA18 or address == 0xC0CB3A
		or address == 0xC0CBC2 or address == 0xC0CC04
	then
		return cpu.x & 0xFF
	end
	return read8(raw_dp_offset(cpu, CURRENT_OBJECT_DP))
end

local function snapshot_route()
	local leader = read8(LEADER_OBJECT)
	return {
		location = read16(LOCATION),
		explore_mode = read8(EXPLORE_MODE),
		dialog_state = read8(DIALOG_STATE),
		field_phase_mod16 = read8(FIELD_FRAME_COUNTER) & 0x0F,
		leader_object = leader,
		leader_x = read16(OBJECT_X + leader),
		leader_y = read16(OBJECT_Y + leader),
		active_party_hex = range_hex(ACTIVE_PARTY, 3),
	}
end

local serialized_state = read_file(state_path)
assert(#serialized_state == EXPECTED_STATE_SIZE, "PE_STATE_PATH size mismatch")

local load_requested = false
local post_load_exec_seen = false
local prepared = false
local tracing = false
local relative_frame = 0
local records = {}
local counts = {}
local overflow = false
local observer_error = nil
local pre_route = nil
local post_route = nil
for _, address in ipairs(ORDERED_PCS) do
	counts[address] = 0
end

local function record_callback(address)
	if not tracing then
		return
	end
	local cpu = cpu_snapshot()
	assert(cpu.pc24 == address, "exact-PC router CPU mismatch")
	local expected_opcode = assert(EXPECTED_OPCODES[address])
	assert(read_cpu8(address) == expected_opcode, "watched instruction preimage mismatch")
	if #records >= CALLBACK_LIMIT then
		overflow = true
		return
	end

	local object_slot = current_object_slot(cpu, address)
	assert(object_slot >= 0 and object_slot <= 0x7F, "object slot out of range")
	local stream_address = nil
	local stream_value = nil
	if address == 0xC0CA35 or address == 0xC0CA3D then
		stream_address = 0xE40000 + (cpu.x & 0xFFFF)
		stream_value = read_cpu8(stream_address)
	elseif address == 0xC0CBC2 or address == 0xC0CC04 then
		local low = read16(raw_dp_offset(cpu, 0xD6))
		local bank = read8(raw_dp_offset(cpu, 0xD8))
		stream_address = (bank << 16) | low
		stream_value = read_cpu8(stream_address)
	end

	counts[address] = counts[address] + 1
	table.insert(records, {
		seq = #records,
		frame = relative_frame,
		pc24 = address,
		role = WATCHED_PCS[address],
		opcode = expected_opcode,
		cpu = cpu,
		object_slot = object_slot,
		object_status = read8(OBJECT_STATUS + object_slot),
		object_id = read8(OBJECT_ID + object_slot),
		selector = read8(OBJECT_SELECTOR + object_slot),
		cursor = read8(OBJECT_CURSOR + object_slot),
		alt_mode = read8(OBJECT_ALT_MODE + object_slot),
		alt_selector = read8(OBJECT_ALT_SELECTOR + object_slot),
		facing = read8(OBJECT_FACING + object_slot),
		delay = read8(OBJECT_DELAY + object_slot),
		timing_base = read16(OBJECT_TIMING_BASE + object_slot),
		main_base = read16(OBJECT_MAIN_BASE + object_slot),
		facing_stride = read16(OBJECT_ANIM_STRIDE + object_slot),
		cached_frame = read8(OBJECT_CACHED_FRAME + object_slot),
		assembly_bank = read8(OBJECT_ASSEMBLY_BANK + object_slot),
		assembly_base = read16(OBJECT_ASSEMBLY_BASE + object_slot),
		dp_c1 = read16(raw_dp_offset(cpu, 0xC1)),
		dp_d6 = read16(raw_dp_offset(cpu, 0xD6)),
		dp_d8 = read8(raw_dp_offset(cpu, 0xD8)),
		dp_d9 = read16(raw_dp_offset(cpu, 0xD9)),
		stream_address = stream_address,
		stream_value = stream_value,
	})
end

local function cpu_json(cpu)
	return table.concat({
		"{",
		'"a":', tostring(cpu.a), ",",
		'"x":', tostring(cpu.x), ",",
		'"y":', tostring(cpu.y), ",",
		'"d":', tostring(cpu.d), ",",
		'"ps":', tostring(cpu.ps), ",",
		'"sp":', nullable_number(cpu.sp), ",",
		'"db":', nullable_number(cpu.db),
		"}",
	})
end

local function record_json(record)
	return table.concat({
		"{",
		'"seq":', tostring(record.seq), ",",
		'"frame":', tostring(record.frame), ",",
		'"pc24":', tostring(record.pc24), ",",
		'"role":', json_string(record.role), ",",
		'"opcode":', tostring(record.opcode), ",",
		'"cpu":', cpu_json(record.cpu), ",",
		'"object_slot":', tostring(record.object_slot), ",",
		'"object_status":', tostring(record.object_status), ",",
		'"object_id":', tostring(record.object_id), ",",
		'"selector":', tostring(record.selector), ",",
		'"cursor":', tostring(record.cursor), ",",
		'"alt_mode":', tostring(record.alt_mode), ",",
		'"alt_selector":', tostring(record.alt_selector), ",",
		'"facing":', tostring(record.facing), ",",
		'"delay":', tostring(record.delay), ",",
		'"timing_base":', tostring(record.timing_base), ",",
		'"main_base":', tostring(record.main_base), ",",
		'"facing_stride":', tostring(record.facing_stride), ",",
		'"cached_frame":', tostring(record.cached_frame), ",",
		'"assembly_bank":', tostring(record.assembly_bank), ",",
		'"assembly_base":', tostring(record.assembly_base), ",",
		'"dp_c1":', tostring(record.dp_c1), ",",
		'"dp_d6":', tostring(record.dp_d6), ",",
		'"dp_d8":', tostring(record.dp_d8), ",",
		'"dp_d9":', tostring(record.dp_d9), ",",
		'"stream_address":', nullable_number(record.stream_address), ",",
		'"stream_value":', nullable_number(record.stream_value),
		"}",
	})
end

local function route_json(snapshot)
	return table.concat({
		"{",
		'"location":', tostring(snapshot.location), ",",
		'"explore_mode":', tostring(snapshot.explore_mode), ",",
		'"dialog_state":', tostring(snapshot.dialog_state), ",",
		'"field_phase_mod16":', tostring(snapshot.field_phase_mod16), ",",
		'"leader_object":', tostring(snapshot.leader_object), ",",
		'"leader_x":', tostring(snapshot.leader_x), ",",
		'"leader_y":', tostring(snapshot.leader_y), ",",
		'"active_party_hex":', json_string(snapshot.active_party_hex),
		"}",
	})
end

local function binding_json(binding)
	return table.concat({
		"{",
		'"object_slot":', tostring(binding.object_slot), ",",
		'"logical_pc_id":', tostring(binding.logical_pc_id), ",",
		'"object_status":', tostring(read8(OBJECT_STATUS + binding.object_slot)), ",",
		'"main_base":', tostring(read16(OBJECT_MAIN_BASE + binding.object_slot)), ",",
		'"timing_base":', tostring(read16(OBJECT_TIMING_BASE + binding.object_slot)),
		"}",
	})
end

local function emit_trace(success, exit_code)
	tracing = false
	post_route = snapshot_route()
	local record_parts = {}
	for _, record in ipairs(records) do
		table.insert(record_parts, record_json(record))
	end
	local count_parts = {}
	local mapping_parts = {}
	for _, address in ipairs(ORDERED_PCS) do
		local mapping = assert(
			emu.convertAddress(address, CPU_MEMORY, CPU),
			"watched PC is not mapped"
		)
		table.insert(
			count_parts,
			json_string(string.format("%06X", address)) .. ":" .. tostring(counts[address])
		)
		table.insert(mapping_parts, table.concat({
			"{",
			'"pc24":', tostring(address), ",",
			'"role":', json_string(WATCHED_PCS[address]), ",",
			'"opcode":', tostring(EXPECTED_OPCODES[address]), ",",
			'"mapped_address":', tostring(mapping.address), ",",
			'"mapping_is_prg_rom":', bool_json(mapping.memType == PRG_ROM),
			"}",
		}))
	end
	local binding_parts = {}
	for _, binding in ipairs(EXPECTED_BINDINGS) do
		table.insert(binding_parts, binding_json(binding))
	end
	local trace = table.concat({
		"{",
		'"schema":', json_string(SCHEMA), ",",
		'"evidence_level":', json_string(EVIDENCE_LEVEL), ",",
		'"collector_version":', tostring(COLLECTOR_VERSION), ",",
		'"emulator":"Mesen 2.1.1",',
		'"route":', json_string(route), ",",
		'"repetition":', tostring(repetition), ",",
		'"observer":{',
		'"mechanism":"broad-exec-callback-exact-pc-router",',
		'"write_calls":0,',
		'"watched_pc_mappings":[', table.concat(mapping_parts, ","), "]",
		"},",
		'"input_contract":{',
		'"terminal_frame":', tostring(TERMINAL_FRAME), ",",
		'"right_start_frame":', route == "right" and "20" or "null", ",",
		'"right_end_frame":', route == "right" and "99" or "null",
		"},",
		'"checkpoint_bindings":[', table.concat(binding_parts, ","), "],",
		'"pre":', route_json(pre_route), ",",
		'"counts":{', table.concat(count_parts, ","), "},",
		'"records":[', table.concat(record_parts, ","), "],",
		'"post":', route_json(post_route), ",",
		'"termination":{',
		'"collector_stopped":true,',
		'"success":', bool_json(success), ",",
		'"overflow":', bool_json(overflow), ",",
		'"observer_error":',
		observer_error == nil and "null" or json_string(observer_error),
		"}",
		"}\n",
	})
	write_new_file(trace_path, trace)
	write_new_file(screenshot_path, emu.takeScreenshot())
	emu.stop(exit_code)
end

emu.addMemoryCallback(
	function(address)
		if not load_requested then
			load_requested = true
			emu.loadSavestate(serialized_state)
			return
		end
		if not post_load_exec_seen then
			post_load_exec_seen = true
		end
		if prepared and WATCHED_PCS[address] ~= nil and observer_error == nil then
			local ok, message = pcall(record_callback, address)
			if not ok then
				observer_error = tostring(message)
				write_new_file(trace_path .. ".observer-error", observer_error .. "\n")
			end
		end
	end,
	emu.callbackType.exec,
	0,
	0xFFFFFF,
	CPU,
	CPU_MEMORY
)

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

emu.addEventCallback(
	function()
		local ok, message = pcall(function()
			local input = empty_input()
			if post_load_exec_seen and not prepared then
				assert(read16(LOCATION) == EXPECTED_LOCATION, "checkpoint location mismatch")
				assert(read8(EXPLORE_MODE) == 1, "checkpoint is not controllable")
				assert(read8(DIALOG_STATE) == 0, "checkpoint has dialogue open")
				assert(range_hex(ACTIVE_PARTY, 3) == EXPECTED_PARTY_HEX, "checkpoint party mismatch")
				assert(read8(LEADER_OBJECT) == EXPECTED_LEADER_OBJECT, "leader object mismatch")
				assert(read16(OBJECT_X + EXPECTED_LEADER_OBJECT) == EXPECTED_LEADER_X, "leader X mismatch")
				assert(read16(OBJECT_Y + EXPECTED_LEADER_OBJECT) == EXPECTED_LEADER_Y, "leader Y mismatch")
				for address, opcode in pairs(EXPECTED_OPCODES) do
					assert(read_cpu8(address) == opcode, "watched instruction preimage mismatch")
				end
				for _, binding in ipairs(EXPECTED_BINDINGS) do
					assert(read8(OBJECT_ID + binding.object_slot) == binding.logical_pc_id, "checkpoint object/PC binding mismatch")
					assert(read8(OBJECT_STATUS + binding.object_slot) == binding.object_status, "checkpoint object status mismatch")
					assert(read16(OBJECT_MAIN_BASE + binding.object_slot) == binding.main_base, "checkpoint main base mismatch")
					assert(read16(OBJECT_TIMING_BASE + binding.object_slot) == binding.timing_base, "checkpoint timing base mismatch")
				end
				pre_route = snapshot_route()
				prepared = true
				tracing = true
			elseif prepared and tracing then
				relative_frame = relative_frame + 1
				if route == "right" then
					input.right = relative_frame >= 20 and relative_frame <= 99
				end
				if observer_error ~= nil or overflow then
					emit_trace(false, 91)
					return
				end
				if relative_frame >= TERMINAL_FRAME then
					emit_trace(true, 41)
					return
				end
			end
			emu.setInput(input, 0)
		end)
		if not ok then
			observer_error = tostring(message)
			local error_path = trace_path .. ".observer-error"
			local existing = io.open(error_path, "rb")
			if existing ~= nil then
				existing:close()
			else
				write_new_file(error_path, observer_error .. "\n")
			end
			emu.stop(91)
		end
	end,
	emu.eventType.inputPolled
)
