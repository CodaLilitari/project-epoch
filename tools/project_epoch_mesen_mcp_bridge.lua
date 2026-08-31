-- Project Epoch hardened Mesen 2.1.1 bridge, protocol version 1.
--
-- This bridge is deliberately not a Lua REPL.  It accepts a closed command
-- grammar from tools/project_epoch_mesen_mcp_server.py and never evaluates,
-- loads, imports, or executes caller-supplied code.  The only host paths it
-- opens come from launcher-controlled environment variables.  Request fields
-- contain numbers and fixed enums only; no request can supply a path.
--
-- Explicit emulator mutation is limited to:
--   * loading the one launcher-pinned native checkpoint;
--   * forcing an empty Player-1 input state; and
--   * registering/removing bounded diagnostic callbacks.
--
-- There is no emu.write call in this source.  In particular, this bridge
-- cannot write WRAM, SRAM, ROM, VRAM, registers, or cartridge data.

local WRAM = emu.memType.snesWorkRam
local CPU_MEMORY = emu.memType.snesMemory
local CPU = emu.cpuType.snes

local PROTOCOL = "project-epoch-mesen-mcp-bridge-v1"
local PROFILE = "event11c-checkpoint-v5-spekkio-talkable"
local EXPECTED_STATE_SIZE = 133993
local EXPECTED_LOCATION = 0x01D1
local EXPECTED_DIRECT_PAGE = 0x0100
local EXPECTED_EXPLORE_MODE = 1
local EXPECTED_DIALOG_STATE = 0
local EXPECTED_LEADER_X = 1568
local EXPECTED_LEADER_Y = 2623
local EXPECTED_PARTY_HEX = "060403"
local EXPECTED_EPOCH_HEX = "a4c9c8bcc100"
local EXPECTED_EXIT_CODE = 47

local LOCATION = 0x0100
local FIELD_FRAME_COUNTER = 0x014B
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local LEADER_OBJECT = 0x0197
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
local ACTIVE_PARTY_START = 0x2980
local EPOCH_NAME_START = 0x2C4D
local FRONT_GUARD_START = 0x2C9C
local REAR_GUARD_END = 0x2CFF

local MAX_REQUEST_BYTES = 4096
local MAX_READ_BYTES = 256
local MAX_CAPTURE_SPAN = 256
local MAX_CAPTURE_FRAMES = 1800
local MAX_CAPTURE_RECORDS = 1024

local function required_env(name)
	local value = os.getenv(name)
	assert(type(value) == "string" and #value > 0, name .. " is missing")
	return value
end

local bridge_dir = required_env("PE_MCP_BRIDGE_DIR")
local session_token = required_env("PE_MCP_SESSION_TOKEN")
local state_path = required_env("PE_MCP_STATE_PATH")

assert(
	session_token:match("^[0-9a-f]+$") and #session_token == 64,
	"PE_MCP_SESSION_TOKEN must be 64 lowercase hex characters"
)

local REQUEST_PATH = bridge_dir .. "/request.txt"
local RESPONSE_PATH = bridge_dir .. "/response.txt"
local READY_PATH = bridge_dir .. "/ready.json"
local FATAL_PATH = bridge_dir .. "/fatal.txt"

local function read_file(path, maximum)
	local file = io.open(path, "rb")
	if not file then
		return nil
	end
	local data = file:read((maximum or EXPECTED_STATE_SIZE) + 1)
	file:close()
	assert(type(data) == "string", "file read did not return bytes")
	if maximum ~= nil then
		assert(#data <= maximum, "file exceeds bounded read size")
	end
	return data
end

local function write_atomic(path, data)
	local temporary = path .. ".tmp"
	local file, open_error = io.open(temporary, "wb")
	assert(file ~= nil, "could not create bridge output: " .. tostring(open_error))
	file:write(data)
	file:close()
	local ok, rename_error = os.rename(temporary, path)
	if not ok then
		pcall(os.remove, temporary)
		error("could not publish bridge output: " .. tostring(rename_error))
	end
end

local function json_escape(value)
	return (value:gsub('[%z\1-\31\\"]', function(character)
		local replacements = {
			['"'] = '\\"',
			['\\'] = '\\\\',
			['\b'] = '\\b',
			['\f'] = '\\f',
			['\n'] = '\\n',
			['\r'] = '\\r',
			['\t'] = '\\t',
		}
		local replacement = replacements[character]
		if replacement ~= nil then
			return replacement
		end
		return string.format("\\u%04x", string.byte(character))
	end))
end

local function json_string(value)
	return '"' .. json_escape(value) .. '"'
end

local function json_boolean(value)
	return value and "true" or "false"
end

local function read8(offset)
	return emu.read(offset, WRAM)
end

local function read16(offset)
	return emu.read16(offset, WRAM)
end

local function bytes_hex(start_offset, length)
	local parts = {}
	for index = 0, length - 1 do
		parts[#parts + 1] = string.format("%02x", read8(start_offset + index))
	end
	return table.concat(parts)
end

local function range_is_zero(start_offset, end_offset)
	for offset = start_offset, end_offset do
		if read8(offset) ~= 0 then
			return false
		end
	end
	return true
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
		pc = state_number(state, "pc", true) & 0xFFFF,
		k = state_number(state, "k", true) & 0xFF,
		a = state_number(state, "a", true) & 0xFFFF,
		x = state_number(state, "x", true) & 0xFFFF,
		y = state_number(state, "y", true) & 0xFFFF,
		d = state_number(state, "d", true) & 0xFFFF,
		ps = state_number(state, "ps", true) & 0xFF,
		sp = state_number(state, "sp", false),
		db = state_number(state, "db", false),
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

local function nullable_number(value)
	return value == nil and "null" or tostring(value)
end

local function cpu_json(cpu)
	return table.concat({
		"{",
		'"pc":', tostring(cpu.pc), ",",
		'"k":', tostring(cpu.k), ",",
		'"pc24":', tostring(cpu.pc24), ",",
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

local serialized_state = read_file(state_path, EXPECTED_STATE_SIZE)
assert(serialized_state ~= nil, "could not read pinned checkpoint")
assert(#serialized_state == EXPECTED_STATE_SIZE, "pinned checkpoint size mismatch")

local ready = false
local load_requested = false
local load_hook = nil
local bridge_frame = 0
local next_expected_sequence = 1
local pending_capture = nil
local stop_on_next_frame = false

local capture_hooks = {}
local capture_records = {}
local capture_overflow = false
local capture_dropped = 0
local capture_error = nil

local function clear_capture_hooks()
	for _, hook in ipairs(capture_hooks) do
		emu.removeMemoryCallback(
			hook.reference,
			hook.callback_type,
			hook.start_offset,
			hook.end_offset,
			CPU,
			WRAM
		)
	end
	capture_hooks = {}
end

local function fatal(message)
	pcall(clear_capture_hooks)
	pcall(write_atomic, FATAL_PATH, tostring(message) .. "\n")
	emu.stop(92)
end

local function validate_live_checkpoint(checkpoint_cpu)
	assert(checkpoint_cpu.d == EXPECTED_DIRECT_PAGE, "checkpoint direct-page mismatch")
	assert(read16(LOCATION) == EXPECTED_LOCATION, "checkpoint location mismatch")
	assert(read8(EXPLORE_MODE) == EXPECTED_EXPLORE_MODE, "checkpoint explore-mode mismatch")
	assert(read8(DIALOG_STATE) == EXPECTED_DIALOG_STATE, "checkpoint dialogue-state mismatch")
	local object = read8(LEADER_OBJECT)
	assert(read16(OBJECT_X + object) == EXPECTED_LEADER_X, "checkpoint leader X mismatch")
	assert(read16(OBJECT_Y + object) == EXPECTED_LEADER_Y, "checkpoint leader Y mismatch")
	assert(bytes_hex(ACTIVE_PARTY_START, 3) == EXPECTED_PARTY_HEX, "checkpoint party mismatch")
	assert(bytes_hex(EPOCH_NAME_START, 6) == EXPECTED_EPOCH_HEX, "checkpoint Epoch name mismatch")
	assert(range_is_zero(FRONT_GUARD_START, REAR_GUARD_END), "checkpoint candidate/guards mismatch")
end

local function ready_json(checkpoint_cpu)
	return table.concat({
		"{",
		'"schema":', json_string(PROTOCOL), ",",
		'"token":', json_string(session_token), ",",
		'"profile":', json_string(PROFILE), ",",
		'"state_size":', tostring(EXPECTED_STATE_SIZE), ",",
		'"location":', tostring(EXPECTED_LOCATION), ",",
		'"direct_page":', tostring(checkpoint_cpu.d), ",",
		'"explore_mode":', tostring(read8(EXPLORE_MODE)), ",",
		'"dialog_state":', tostring(read8(DIALOG_STATE)), ",",
		'"active_party_hex":', json_string(bytes_hex(ACTIVE_PARTY_START, 3)), ",",
		'"candidate_and_guards_zero":', json_boolean(range_is_zero(FRONT_GUARD_START, REAR_GUARD_END)),
		"}",
	})
end

local function parse_unsigned(value, name, maximum)
	assert(type(value) == "string" and value:match("^%d+$"), name .. " must be unsigned decimal")
	local number = tonumber(value)
	assert(number ~= nil and number == math.floor(number), name .. " is not an integer")
	assert(number >= 0 and number <= maximum, name .. " is out of range")
	return number
end

local function parse_request(source)
	assert(type(source) == "string" and #source <= MAX_REQUEST_BYTES, "request exceeds bounded size")
	assert(not source:find("\0", 1, true), "request contains NUL")
	local fields = {}
	local line_count = 0
	for line in (source .. "\n"):gmatch("([^\n]*)\n") do
		line_count = line_count + 1
		assert(line_count <= 16, "request has too many lines")
		assert(not line:find("\r", 1, true), "request contains carriage return")
		if line_count == 1 then
			assert(line == "PEMCP1", "request protocol marker mismatch")
		elseif #line > 0 then
			local key, value = line:match("^([A-Z_]+):([A-Za-z0-9_-]+)$")
			assert(key ~= nil and value ~= nil, "request line is malformed")
			assert(fields[key] == nil, "duplicate request field: " .. key)
			fields[key] = value
		end
	end
	assert(fields.TOKEN == session_token, "request token mismatch")
	local sequence = parse_unsigned(fields.SEQ, "SEQ", 2147483647)
	assert(sequence == next_expected_sequence, "request sequence mismatch")
	assert(type(fields.OP) == "string", "request OP is missing")
	return sequence, fields.OP, fields
end

local function response_frame(sequence, status, payload)
	return table.concat({
		"PEMCP1\n",
		"SEQ:", tostring(sequence), "\n",
		"TOKEN:", session_token, "\n",
		"STATUS:", status, "\n",
		"LEN:", tostring(#payload), "\n",
		payload,
	})
end

local function publish_response(sequence, status, payload)
	write_atomic(RESPONSE_PATH, response_frame(sequence, status, payload))
	next_expected_sequence = sequence + 1
end

local function make_error_payload(message)
	return table.concat({
		"{",
		'"schema":', json_string(PROTOCOL), ",",
		'"error":', json_string(tostring(message)),
		"}",
	})
end

local function record_json(record)
	return table.concat({
		"{",
		'"sequence":', tostring(record.sequence), ",",
		'"frame":', tostring(record.frame), ",",
		'"access":', json_string(record.access), ",",
		'"offset":', tostring(record.offset), ",",
		'"address":', tostring(0x7E0000 + record.offset), ",",
		'"value":', tostring(record.value), ",",
		'"pc24":', tostring(record.pc24),
		"}",
	})
end

local function capture_result_json(capture)
	local records = {}
	for _, record in ipairs(capture_records) do
		records[#records + 1] = record_json(record)
	end
	return table.concat({
		"{",
		'"schema":', json_string(PROTOCOL), ",",
		'"profile":', json_string(PROFILE), ",",
		'"start_offset":', tostring(capture.start_offset), ",",
		'"end_offset":', tostring(capture.end_offset), ",",
		'"access":', json_string(capture.access), ",",
		'"requested_frames":', tostring(capture.frames), ",",
		'"completed_frames":', tostring(capture.completed_frames), ",",
		'"start_field_counter_mod16":', tostring(capture.start_field_counter_mod16), ",",
		'"record_limit":', tostring(capture.limit), ",",
		'"record_count":', tostring(#capture_records), ",",
		'"overflow":', json_boolean(capture_overflow), ",",
		'"dropped_records":', tostring(capture_dropped), ",",
		'"observer_error":', capture_error == nil and "null" or json_string(capture_error), ",",
		'"pre_hex":', json_string(capture.pre_hex), ",",
		'"post_hex":', json_string(bytes_hex(capture.start_offset, capture.end_offset - capture.start_offset + 1)), ",",
		'"records":[', table.concat(records, ","), "]",
		"}",
	})
end

local function capture_callback(access)
	return function(address, value)
		if pending_capture == nil then
			return
		end
		local ok, mapping = pcall(
			emu.convertAddress,
			address,
			CPU_MEMORY,
			CPU
		)
		if not ok
			or type(mapping) ~= "table"
			or mapping.memType ~= WRAM
			or type(mapping.address) ~= "number"
		then
			capture_error = "could not normalize WRAM callback address"
			return
		end
		if #capture_records >= pending_capture.limit then
			capture_overflow = true
			capture_dropped = capture_dropped + 1
			return
		end
		local cpu = cpu_snapshot()
		capture_records[#capture_records + 1] = {
			sequence = #capture_records,
			frame = pending_capture.completed_frames + 1,
			access = access,
			offset = mapping.address,
			value = value & 0xFF,
			pc24 = cpu.pc24,
		}
	end
end

local function arm_capture(fields, sequence)
	clear_capture_hooks()
	local start_offset = parse_unsigned(fields.START, "START", 0x1FFFF)
	local end_offset = parse_unsigned(fields.END, "END", 0x1FFFF)
	assert(end_offset >= start_offset, "END precedes START")
	assert(end_offset - start_offset + 1 <= MAX_CAPTURE_SPAN, "capture span exceeds limit")
	local frames = parse_unsigned(fields.FRAMES, "FRAMES", MAX_CAPTURE_FRAMES)
	assert(frames >= 1, "FRAMES must be positive")
	local limit = parse_unsigned(fields.LIMIT, "LIMIT", MAX_CAPTURE_RECORDS)
	assert(limit >= 1, "LIMIT must be positive")
	local access = fields.ACCESS
	assert(access == "read" or access == "write" or access == "both", "ACCESS is invalid")

	capture_records = {}
	capture_overflow = false
	capture_dropped = 0
	capture_error = nil
	pending_capture = {
		sequence = sequence,
		start_offset = start_offset,
		end_offset = end_offset,
		frames = frames,
		limit = limit,
		access = access,
		completed_frames = 0,
		start_field_counter_mod16 = read8(FIELD_FRAME_COUNTER) & 0x0F,
		pre_hex = bytes_hex(start_offset, end_offset - start_offset + 1),
	}

	local requested = access == "both" and { "read", "write" } or { access }
	for _, requested_access in ipairs(requested) do
		local callback_type = requested_access == "read"
			and emu.callbackType.read
			or emu.callbackType.write
		local reference = emu.addMemoryCallback(
			capture_callback(requested_access),
			callback_type,
			start_offset,
			end_offset,
			CPU,
			WRAM
		)
		capture_hooks[#capture_hooks + 1] = {
			reference = reference,
			callback_type = callback_type,
			start_offset = start_offset,
			end_offset = end_offset,
		}
	end
end

local function handle_immediate_operation(sequence, operation, fields)
	if operation == "PING" then
		return table.concat({
			"{",
			'"schema":', json_string(PROTOCOL), ",",
			'"profile":', json_string(PROFILE), ",",
			'"bridge_frame":', tostring(bridge_frame), ",",
			'"ready":true,',
			'"write_operations_available":false',
			"}",
		})
	elseif operation == "READ_WRAM" then
		local start_offset = parse_unsigned(fields.START, "START", 0x1FFFF)
		local length = parse_unsigned(fields.LENGTH, "LENGTH", MAX_READ_BYTES)
		assert(length >= 1, "LENGTH must be positive")
		assert(start_offset + length - 1 <= 0x1FFFF, "WRAM read crosses boundary")
		return table.concat({
			"{",
			'"schema":', json_string(PROTOCOL), ",",
			'"start_offset":', tostring(start_offset), ",",
			'"length":', tostring(length), ",",
			'"hex":', json_string(bytes_hex(start_offset, length)),
			"}",
		})
	elseif operation == "CPU_STATE" then
		return table.concat({
			"{",
			'"schema":', json_string(PROTOCOL), ",",
			'"bridge_frame":', tostring(bridge_frame), ",",
			'"cpu":', cpu_json(cpu_snapshot()),
			"}",
		})
	elseif operation == "STOP" then
		clear_capture_hooks()
		stop_on_next_frame = true
		return table.concat({
			"{",
			'"schema":', json_string(PROTOCOL), ",",
			'"stopping":true,',
			'"expected_exit_code":', tostring(EXPECTED_EXIT_CODE),
			"}",
		})
	end
	error("unsupported operation: " .. tostring(operation))
end

local function process_request()
	if not ready or pending_capture ~= nil or stop_on_next_frame then
		return
	end
	local source = read_file(REQUEST_PATH, MAX_REQUEST_BYTES)
	if source == nil then
		return
	end
	pcall(os.remove, REQUEST_PATH)

	local sequence = nil
	local ok, message = pcall(function()
		local parsed_sequence, operation, fields = parse_request(source)
		sequence = parsed_sequence
		if operation == "CAPTURE_WRAM" then
			arm_capture(fields, parsed_sequence)
			return
		end
		local payload = handle_immediate_operation(parsed_sequence, operation, fields)
		publish_response(parsed_sequence, "OK", payload)
	end)
	if not ok then
		local response_sequence = sequence or next_expected_sequence
		pcall(publish_response, response_sequence, "ERR", make_error_payload(message))
	end
end

load_hook = emu.addMemoryCallback(
	function()
		local ok, message = pcall(function()
			if not load_requested then
				load_requested = true
				emu.loadSavestate(serialized_state)
				return
			end
			if ready then
				return
			end
			local checkpoint_cpu = cpu_snapshot()
			validate_live_checkpoint(checkpoint_cpu)
			emu.removeMemoryCallback(
				load_hook,
				emu.callbackType.exec,
				0,
				0xFFFFFF,
				CPU,
				CPU_MEMORY
			)
			ready = true
			write_atomic(READY_PATH, ready_json(checkpoint_cpu))
		end)
		if not ok then
			fatal(message)
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
			emu.setInput(empty_input(), 0)
		end)
		if not ok then
			fatal(message)
		end
	end,
	emu.eventType.inputPolled
)

emu.addEventCallback(
	function()
		local ok, message = pcall(function()
			if not ready then
				return
			end
			bridge_frame = bridge_frame + 1
			if pending_capture ~= nil then
				pending_capture.completed_frames = pending_capture.completed_frames + 1
				if pending_capture.completed_frames >= pending_capture.frames then
					local capture = pending_capture
					pending_capture = nil
					clear_capture_hooks()
					publish_response(capture.sequence, "OK", capture_result_json(capture))
				end
			elseif stop_on_next_frame then
				emu.stop(EXPECTED_EXIT_CODE)
			else
				process_request()
			end
		end)
		if not ok then
			fatal(message)
		end
	end,
	emu.eventType.endFrame
)
