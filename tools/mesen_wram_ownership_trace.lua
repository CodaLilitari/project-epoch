-- Project Epoch Mesen 2.1.1 WRAM ownership-matrix collector.
--
-- This source-only diagnostic loads one pinned private native savestate,
-- performs a bounded scenario fixture before observation, resets Mesen's
-- access counters, and then observes reads and writes to the proposed
-- compatibility-block relocation area and nearby ownership sentinels.
--
-- Every explicit emu.write/emu.write16 call is centralized in the named
-- wrappers below and is checked against the preparation whitelist. The
-- collector makes no explicit ROM or SRAM write. Loading a savestate and
-- running the game can still change other transient emulator state. The host
-- launcher must independently prove preservation of the source ROM, SRAM,
-- savestate, and shared Mesen Saves tree.

local WRAM = emu.memType.snesWorkRam
local CPU_MEMORY = emu.memType.snesMemory
local CPU = emu.cpuType.snes

local LOCATION = 0x0100
local FIELD_FRAME_COUNTER = 0x014B
local EXPLORE_MODE = 0x011F
local DIALOG_STATE = 0x0162
local LEADER_OBJECT = 0x0197
local OBJECT_X = 0x1800
local OBJECT_Y = 0x1880
local SPEKKIO_SPRITE_FRAME = 0x0F15
local STORYLINE = 0x10000
local MAGIC_FLAGS = 0x101E0
local ROBO_FLAGS = 0x101E2
local LAP_SCRATCH = 0x1021C

local OLD_BLOCK_START = 0x2830
local OLD_BLOCK_END = 0x287F
local ACTIVE_PARTY_START = 0x2980
local ACTIVE_PARTY_END = 0x2988
local JOINED_FLAGS = 0x29AF
local EPOCH_NAME_START = 0x2C4D
local EPOCH_NAME_END = 0x2C52
local FRONT_GUARD_START = 0x2C9C
local FRONT_GUARD_END = 0x2C9F
local CANDIDATE_START = 0x2CA0
local CANDIDATE_END = 0x2CEF
local REAR_GUARD_START = 0x2CF0
local REAR_GUARD_END = 0x2CFF

local CALLBACK_LIMIT = 4096
local EVENT_ENDPOINT_PNG_SIZE = 9503
local EVENT_ENDPOINT_PNG_SHA256 =
	"0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb"
local EVENT_ENDPOINT_PNG_MAX_WAIT_FRAMES = 120
local EXPECTED_STATE_SIZE = 133993
local CHECKPOINT_ID = "event11c-checkpoint-v5-spekkio-talkable"
local CHECKPOINT_SOURCE_FRAME = 3237
local EXPECTED_STATE_SHA256 =
	"26788b52f63a32a7539d8acb18495df" ..
	"1a458064f700d5411916e2bfc34c4522e"
local EXPECTED_EPOCH_NAME = { 0xA4, 0xC9, 0xC8, 0xBC, 0xC1, 0x00 }

local CANARY_HEX =
	"471eea9705fecea2040cc7e0d72b4a50a9a996d83f9cc34b46c753b1968f659b" ..
	"aaa47f0daf10c8d9074953390d34d25c5f631b7bbf6d1f08e1ff2387281084f7" ..
	"844c9cda36c941873207b6269ea72566"

-- Ordered deliberately: the validator and host evidence use this order.
local WATCHED_RANGES = {
	{
		name = "old-compatibility",
		start_offset = OLD_BLOCK_START,
		end_offset = OLD_BLOCK_END,
		include_hex = false,
	},
	{
		name = "roster",
		start_offset = ACTIVE_PARTY_START,
		end_offset = ACTIVE_PARTY_END,
		include_hex = true,
	},
	{
		name = "joined",
		start_offset = JOINED_FLAGS,
		end_offset = JOINED_FLAGS,
		include_hex = true,
	},
	{
		name = "epoch-name",
		start_offset = EPOCH_NAME_START,
		end_offset = EPOCH_NAME_END,
		include_hex = true,
	},
	{
		name = "front-guard",
		start_offset = FRONT_GUARD_START,
		end_offset = FRONT_GUARD_END,
		include_hex = true,
	},
	{
		name = "candidate",
		start_offset = CANDIDATE_START,
		end_offset = CANDIDATE_END,
		include_hex = true,
	},
	{
		name = "rear-guard",
		start_offset = REAR_GUARD_START,
		end_offset = REAR_GUARD_END,
		include_hex = true,
	},
}

local SCENARIOS = {
	["calibration"] = {
		terminal_frame = 0,
		minimum_terminal_frame = 0,
		maximum_frame = 0,
		phase_stable = false,
	},
	["field-idle"] = {
		terminal_frame = 600,
		minimum_terminal_frame = 600,
		maximum_frame = 600,
		phase_stable = false,
	},
	["main-menu"] = {
		terminal_frame = 600,
		minimum_terminal_frame = 600,
		maximum_frame = 600,
		phase_stable = false,
	},
	["event11c-frog"] = {
		terminal_frame = nil,
		minimum_terminal_frame = 1500,
		maximum_frame = 2400,
		phase_stable = true,
	},
}

local state_path = assert(os.getenv("PE_STATE_PATH"), "PE_STATE_PATH is required")
local trace_path = assert(os.getenv("PE_TRACE_OUT"), "PE_TRACE_OUT is required")
local screenshot_path = assert(
	os.getenv("PE_TRACE_SCREENSHOT"),
	"PE_TRACE_SCREENSHOT is required"
)
local scenario_name = assert(os.getenv("PE_SCENARIO"), "PE_SCENARIO is required")
local variant = assert(os.getenv("PE_VARIANT"), "PE_VARIANT is required")
local scenario = assert(SCENARIOS[scenario_name], "unknown PE_SCENARIO")
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

local MASK32 = 0xFFFFFFFF
local SHA256_K = {
	0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
	0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
	0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
	0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
	0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
	0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
	0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
	0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
	0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
	0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
	0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
	0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
	0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
	0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
	0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
	0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
}

local function ror32(value, count)
	value = value & MASK32
	return ((value >> count) | (value << (32 - count))) & MASK32
end

local function add32(...)
	local result = 0
	for index = 1, select("#", ...) do
		result = (result + select(index, ...)) & MASK32
	end
	return result
end

local function sha256(data)
	local bit_length = #data * 8
	local padded = data .. string.char(0x80)
	local zero_count = (56 - (#padded % 64)) % 64
	padded = padded .. string.rep(string.char(0), zero_count)
	for shift = 56, 0, -8 do
		padded = padded .. string.char((bit_length >> shift) & 0xFF)
	end

	local hash = {
		0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
		0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
	}
	local words = {}
	for chunk_start = 1, #padded, 64 do
		for index = 0, 15 do
			local base = chunk_start + index * 4
			words[index] =
				(padded:byte(base) << 24)
				| (padded:byte(base + 1) << 16)
				| (padded:byte(base + 2) << 8)
				| padded:byte(base + 3)
		end
		for index = 16, 63 do
			local x = words[index - 15]
			local y = words[index - 2]
			local sigma0 = ror32(x, 7) ~ ror32(x, 18) ~ (x >> 3)
			local sigma1 = ror32(y, 17) ~ ror32(y, 19) ~ (y >> 10)
			words[index] = add32(
				words[index - 16],
				sigma0,
				words[index - 7],
				sigma1
			)
		end
		local a, b, c, d = hash[1], hash[2], hash[3], hash[4]
		local e, f, g, h = hash[5], hash[6], hash[7], hash[8]
		for index = 0, 63 do
			local sum1 = ror32(e, 6) ~ ror32(e, 11) ~ ror32(e, 25)
			local choose = (e & f) ~ ((~e) & g)
			local temp1 = add32(
				h,
				sum1,
				choose,
				SHA256_K[index + 1],
				words[index]
			)
			local sum0 = ror32(a, 2) ~ ror32(a, 13) ~ ror32(a, 22)
			local majority = (a & b) ~ (a & c) ~ (b & c)
			local temp2 = add32(sum0, majority)
			h = g
			g = f
			f = e
			e = add32(d, temp1)
			d = c
			c = b
			b = a
			a = add32(temp1, temp2)
		end
		hash[1] = add32(hash[1], a)
		hash[2] = add32(hash[2], b)
		hash[3] = add32(hash[3], c)
		hash[4] = add32(hash[4], d)
		hash[5] = add32(hash[5], e)
		hash[6] = add32(hash[6], f)
		hash[7] = add32(hash[7], g)
		hash[8] = add32(hash[8], h)
	end
	local parts = {}
	for _, value in ipairs(hash) do
		table.insert(parts, string.format("%08x", value & MASK32))
	end
	return table.concat(parts)
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
assert(#CANARY == CANDIDATE_END - CANDIDATE_START + 1)

local function read8(offset)
	return emu.read(offset, WRAM)
end

local function read16(offset)
	return emu.read16(offset, WRAM)
end

local explicit_writes = {}
local counters_armed = false
local preparation_writes_after_arm = 0

local function write_is_allowed(offset, width, label)
	if label == "candidate-variant" then
		return width == 1
			and variant == "canary"
			and offset >= CANDIDATE_START
			and offset <= CANDIDATE_END
	end
	if scenario_name ~= "event11c-frog" then
		return false
	end
	if width == 2 then
		return label == "frog-remaining-tp" and offset == 0x276D
	end
	local allowed = {
		["storyline"] = STORYLINE,
		["lap-scratch"] = LAP_SCRATCH,
		["magic-flags"] = MAGIC_FLAGS,
		["robo-flags"] = ROBO_FLAGS,
		["frog-tech-count"] = 0x2834,
		["frog-learned-mask"] = 0x283B,
	}
	return width == 1 and allowed[label] == offset
end

local function record_explicit_write(width, offset, value, label)
	if counters_armed then
		preparation_writes_after_arm = preparation_writes_after_arm + 1
	end
	assert(
		write_is_allowed(offset, width, label),
		"explicit WRAM write is outside the scenario whitelist"
	)
	table.insert(explicit_writes, {
		seq = #explicit_writes,
		width = width,
		raw_wram_offset = offset,
		value = value,
		label = label,
	})
end

local function wram_write8(offset, value, label)
	value = value & 0xFF
	record_explicit_write(1, offset, value, label)
	emu.write(offset, value, WRAM)
end

local function wram_write16(offset, value, label)
	value = value & 0xFFFF
	record_explicit_write(2, offset, value, label)
	emu.write16(offset, value, WRAM)
end

local function range_values(start_offset, end_offset)
	local values = {}
	for offset = start_offset, end_offset do
		table.insert(values, read8(offset))
	end
	return values
end

local function values_string(values)
	return string.char(table.unpack(values))
end

local function values_hex(values)
	local parts = {}
	for _, value in ipairs(values) do
		table.insert(parts, string.format("%02x", value))
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

local function range_matches(start_offset, values)
	for index, value in ipairs(values) do
		if read8(start_offset + index - 1) ~= value then
			return false
		end
	end
	return true
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

local function route_snapshot()
	local object = read8(LEADER_OBJECT)
	return {
		location = read16(LOCATION),
		storyline = read8(STORYLINE),
		lap_scratch = read8(LAP_SCRATCH),
		magic_flags = read8(MAGIC_FLAGS),
		robo_flags = read8(ROBO_FLAGS),
		explore_mode = read8(EXPLORE_MODE),
		dialog_state = read8(DIALOG_STATE),
		leader_x = read16(OBJECT_X + object),
		leader_y = read16(OBJECT_Y + object),
		active_party_hex = values_hex(
			range_values(ACTIVE_PARTY_START, ACTIVE_PARTY_START + 2)
		),
		field_phase_mod16 = read8(FIELD_FRAME_COUNTER) & 0x0F,
		spekkio_sprite_frame = read8(SPEKKIO_SPRITE_FRAME),
	}
end

local function route_json(route)
	return table.concat({
		"{",
		'"location":', tostring(route.location), ",",
		'"storyline":', tostring(route.storyline), ",",
		'"lap_scratch":', tostring(route.lap_scratch), ",",
		'"magic_flags":', tostring(route.magic_flags), ",",
		'"robo_flags":', tostring(route.robo_flags), ",",
		'"explore_mode":', tostring(route.explore_mode), ",",
		'"dialog_state":', tostring(route.dialog_state), ",",
		'"leader_x":', tostring(route.leader_x), ",",
		'"leader_y":', tostring(route.leader_y), ",",
		'"active_party_hex":', json_string(route.active_party_hex), ",",
		'"field_phase_mod16":', tostring(route.field_phase_mod16), ",",
		'"spekkio_sprite_frame":', tostring(route.spekkio_sprite_frame),
		"}",
	})
end

local serialized_state = read_file(state_path)
assert(#serialized_state == EXPECTED_STATE_SIZE, "PE_STATE_PATH size mismatch")
-- The fail-closed host launcher hash-verifies the source checkpoint, stages
-- those exact bytes, and verifies the source again after emulation. Rehashing
-- the 133,993-byte state in interpreted Lua takes longer than the bounded
-- test-runner window, so the collector reports the host-pinned digest and
-- independently validates the loaded checkpoint's size and live preimage.
local pinned_state_sha256 = EXPECTED_STATE_SHA256

local load_requested = false
local post_load_exec_seen = false
local checkpoint_cpu = nil
local load_hook = nil
local prepared = false
local tracing = false
local pending_exit_code = nil
local pending_screenshot_wait_frames = 0
local relative_frame = 0
local observer_error = nil
local overflow = false
local callbacks = {}
local callback_totals = {}
local callback_read_total = 0
local callback_write_total = 0
local memory_hooks = {}
local pre_ranges = {}
local pre_route = nil
local counters_zero_after_preparation = false
local initial_counter_index_base = nil

local watched_offsets = {}
for _, range in ipairs(WATCHED_RANGES) do
	for offset = range.start_offset, range.end_offset do
		assert(not watched_offsets[offset], "watched ranges overlap")
		watched_offsets[offset] = range.name
		callback_totals[offset] = { read = 0, write = 0 }
	end
end

local function capture_ranges()
	local result = {}
	for _, range in ipairs(WATCHED_RANGES) do
		local values = range_values(range.start_offset, range.end_offset)
		result[range.name] = {
			values = values,
			sha256 = sha256(values_string(values)),
			hex = range.include_hex and values_hex(values) or nil,
		}
	end
	return result
end

local function prepare_fixture()
	assert(post_load_exec_seen, "savestate did not resume through the exec hook")
	assert(checkpoint_cpu ~= nil, "checkpoint CPU state was not captured")
	assert(
		checkpoint_cpu.d == 0x0100,
		"checkpoint direct-page preimage mismatch"
	)
	assert(read16(LOCATION) == 0x01D1, "checkpoint location mismatch")
	assert(read8(EXPLORE_MODE) == 1, "checkpoint is not controllable")
	assert(read8(DIALOG_STATE) == 0, "checkpoint has dialogue open")
	local object = read8(LEADER_OBJECT)
	assert(read16(OBJECT_X + object) == 1568, "checkpoint X mismatch")
	assert(read16(OBJECT_Y + object) == 2623, "checkpoint Y mismatch")
	assert(
		values_hex(range_values(ACTIVE_PARTY_START, ACTIVE_PARTY_START + 2))
			== "060403",
		"checkpoint party mismatch"
	)
	assert(
		range_is_zero(FRONT_GUARD_START, REAR_GUARD_END),
		"checkpoint candidate or guards are not zero"
	)
	assert(
		range_matches(EPOCH_NAME_START, EXPECTED_EPOCH_NAME),
		"checkpoint Epoch name mismatch"
	)

	if scenario_name == "event11c-frog" then
		wram_write8(STORYLINE, 0x4C, "storyline")
		wram_write8(LAP_SCRATCH, 0x03, "lap-scratch")
		wram_write8(
			MAGIC_FLAGS,
			read8(MAGIC_FLAGS) & (~0x18 & 0xFF),
			"magic-flags"
		)
		wram_write8(
			ROBO_FLAGS,
			read8(ROBO_FLAGS) & (~0x01 & 0xFF),
			"robo-flags"
		)
		wram_write8(0x2834, 0, "frog-tech-count")
		wram_write8(
			0x283B,
			read8(0x283B) & 0x1F,
			"frog-learned-mask"
		)
		wram_write16(0x276D, 0, "frog-remaining-tp")
	end

	if variant == "canary" then
		for index, value in ipairs(CANARY) do
			wram_write8(
				CANDIDATE_START + index - 1,
				value,
				"candidate-variant"
			)
		end
	end

	assert(
		variant == "canary"
			and range_matches(CANDIDATE_START, CANARY)
			or variant == "zero"
				and range_is_zero(CANDIDATE_START, CANDIDATE_END),
		"candidate variant preparation mismatch"
	)
	assert(
		range_is_zero(FRONT_GUARD_START, FRONT_GUARD_END),
		"front guard changed during preparation"
	)
	assert(
		range_is_zero(REAR_GUARD_START, REAR_GUARD_END),
		"rear guard changed during preparation"
	)
	assert(
		range_matches(EPOCH_NAME_START, EXPECTED_EPOCH_NAME),
		"Epoch name changed during preparation"
	)

	pre_ranges = capture_ranges()
	pre_route = route_snapshot()
	prepared = true
end

local function counter_index_base(counters)
	assert(type(counters) == "table", "access counter result is not a table")
	if type(counters[0]) == "number" then
		return 0
	end
	assert(type(counters[1]) == "number", "access counter array has no index 0 or 1")
	return 1
end

local function counter_value(counters, base, offset)
	local value = counters[offset + base]
	assert(
		type(value) == "number" and value == math.floor(value) and value >= 0,
		"access counter entry is unavailable"
	)
	return value
end

local function watched_counters_are_zero(read_counters, write_counters, base)
	for offset, _ in pairs(watched_offsets) do
		if counter_value(read_counters, base, offset) ~= 0
			or counter_value(write_counters, base, offset) ~= 0
		then
			return false
		end
	end
	return true
end

local function observe_access(access, address, value)
	if not tracing or not watched_offsets[address] then
		return
	end
	local totals = assert(callback_totals[address])
	totals[access] = totals[access] + 1
	if access == "read" then
		callback_read_total = callback_read_total + 1
	else
		callback_write_total = callback_write_total + 1
	end
	if observer_error ~= nil then
		return
	end
	local ok, message = pcall(function()
		assert(
			type(value) == "number" and value == math.floor(value),
			"memory callback value is unavailable"
		)
		if #callbacks >= CALLBACK_LIMIT then
			overflow = true
			return
		end
		local cpu = cpu_snapshot()
		table.insert(callbacks, {
			seq = #callbacks,
			frame = relative_frame,
			access = access,
			address = address,
			value = value & 0xFF,
			cpu = cpu,
		})
	end)
	if not ok then
		observer_error = tostring(message)
	end
	-- Deliberately no return value: returning an integer would alter emulation.
end

local function make_memory_callback(access)
	return function(address, value)
		-- Mesen matches an absolute snesWorkRam registration by converting the
		-- CPU-relative access internally, but the Lua callback still receives
		-- that original CPU address. Normalize it back to the raw WRAM offset
		-- before comparing it with counters or watched ranges.
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
			observer_error =
				"could not normalize WRAM callback address "
				.. string.format("$%06X", address)
			return
		end
		observe_access(access, mapping.address, value)
		-- Deliberately return nil.
	end
end

local function arm_observers()
	assert(prepared, "fixture was not prepared")
	assert(not tracing and #memory_hooks == 0, "observer already armed")
	emu.resetAccessCounters()
	-- Mesen 2.1.1's tagged Lua implementation pops arguments from the stack
	-- in reverse and reads AccessCounterType first. Despite the generated
	-- documentation's displayed order, this version therefore requires
	-- (memoryType, counterType) at the Lua call site.
	local reset_reads = emu.getAccessCounters(
		WRAM,
		emu.counterType.readCount
	)
	local reset_writes = emu.getAccessCounters(
		WRAM,
		emu.counterType.writeCount
	)
	initial_counter_index_base = counter_index_base(reset_reads)
	assert(
		counter_index_base(reset_writes) == initial_counter_index_base,
		"read/write counter arrays use different indexing"
	)
	counters_zero_after_preparation = watched_counters_are_zero(
		reset_reads,
		reset_writes,
		initial_counter_index_base
	)
	assert(
		counters_zero_after_preparation,
		"watched counters were not zero after reset"
	)

	counters_armed = true
	tracing = true
	for _, range in ipairs(WATCHED_RANGES) do
		for _, access in ipairs({ "read", "write" }) do
			local callback_type = access == "read"
				and emu.callbackType.read
				or emu.callbackType.write
			local reference = emu.addMemoryCallback(
				make_memory_callback(access),
				callback_type,
				range.start_offset,
				range.end_offset,
				CPU,
				WRAM
			)
			table.insert(memory_hooks, {
				reference = reference,
				callback_type = callback_type,
				start_offset = range.start_offset,
				end_offset = range.end_offset,
			})
		end
	end
end

local function disarm_observers()
	tracing = false
	for _, hook in ipairs(memory_hooks) do
		emu.removeMemoryCallback(
			hook.reference,
			hook.callback_type,
			hook.start_offset,
			hook.end_offset,
			CPU,
			WRAM
		)
	end
	memory_hooks = {}
end

local function callback_json(record)
	local cpu = record.cpu
	return table.concat({
		"{",
		'"seq":', tostring(record.seq), ",",
		'"frame":', tostring(record.frame), ",",
		'"access":', json_string(record.access), ",",
		'"address":', tostring(0x7E0000 + record.address), ",",
		'"value":', tostring(record.value), ",",
		'"pc24":', tostring(cpu.pc24),
		"}",
	})
end

local function write_json(record)
	return table.concat({
		"{",
		'"seq":', tostring(record.seq), ",",
		'"width":', tostring(record.width), ",",
		'"raw_wram_offset":', tostring(record.raw_wram_offset), ",",
		'"value":', tostring(record.value), ",",
		'"label":', json_string(record.label),
		"}",
	})
end

local function range_snapshot_json(snapshot)
	return table.concat({
		"{",
		'"sha256":', json_string(snapshot.sha256), ",",
		'"hex":',
		snapshot.hex == nil and "null" or json_string(snapshot.hex),
		"}",
	})
end

local function snapshot_json(ranges)
	return table.concat({
		"{",
		'"old_compatibility_hex":',
		json_string(values_hex(ranges["old-compatibility"].values)), ",",
		'"roster_hex":',
		json_string(values_hex(ranges["roster"].values)), ",",
		'"joined_hex":',
		json_string(values_hex(ranges["joined"].values)), ",",
		'"epoch_name_hex":',
		json_string(values_hex(ranges["epoch-name"].values)), ",",
		'"front_guard_hex":',
		json_string(values_hex(ranges["front-guard"].values)), ",",
		'"candidate_hex":',
		json_string(values_hex(ranges["candidate"].values)), ",",
		'"rear_guard_hex":',
		json_string(values_hex(ranges["rear-guard"].values)),
		"}",
	})
end

local function watched_range_json(range, pre, post)
	local changed = {}
	for index, before in ipairs(pre.values) do
		local after = post.values[index]
		if before ~= after then
			table.insert(changed, table.concat({
				"{",
				'"raw_wram_offset":',
				tostring(range.start_offset + index - 1), ",",
				'"before":', tostring(before), ",",
				'"after":', tostring(after),
				"}",
			}))
		end
	end
	return table.concat({
		"{",
		'"name":', json_string(range.name), ",",
		'"start":', tostring(range.start_offset), ",",
		'"end":', tostring(range.end_offset), ",",
		'"length":', tostring(range.end_offset - range.start_offset + 1), ",",
		'"pre":', range_snapshot_json(pre), ",",
		'"post":', range_snapshot_json(post), ",",
		'"changed_offsets":[', table.concat(changed, ","), "]",
		"}",
	})
end

local function scenario_contract_json()
	local pulses = {}
	if scenario_name == "main-menu" then
		table.insert(
			pulses,
			'{"port":1,"button":"X","start_frame":60,"end_frame":61}'
		)
	elseif scenario_name == "event11c-frog" then
		for first = 60, 1140, 120 do
			table.insert(pulses, table.concat({
				'{"port":1,"button":"A","start_frame":',
				tostring(first),
				',"end_frame":',
				tostring(first + 1),
				"}",
			}))
		end
	end
	local access_class = "ownership-negative-control"
	if scenario_name == "calibration" then
		access_class = "none"
	elseif scenario_name == "event11c-frog" then
		access_class = "old-compatibility-positive-control"
	end
	return table.concat({
		"{",
		'"terminal_frame_min":',
		tostring(scenario.minimum_terminal_frame), ",",
		'"terminal_frame_max":', tostring(scenario.maximum_frame), ",",
		'"expected_access_class":', json_string(access_class), ",",
		'"inputs":[', table.concat(pulses, ","), "]",
		"}",
	})
end

local function event_control_matches()
	if scenario_name ~= "event11c-frog" then
		return true
	end
	local expected = {
		{ access = "write", address = 0x2834, value = 0x03, pc24 = 0xC06824 },
		{ access = "read", address = 0x283B, value = 0x1F, pc24 = 0xC06799 },
		{ access = "write", address = 0x283B, value = 0xFF, pc24 = 0xC06824 },
	}
	local filtered = {}
	for _, actual in ipairs(callbacks) do
		-- Read callbacks run after the read and therefore report $C06799;
		-- write callbacks run after the source instruction has advanced and
		-- report $C06824 in current Mesen 2.1.1.
		local is_target =
			actual.frame == 985
				and actual.access == "write"
				and actual.address == 0x2834
				and actual.cpu.pc24 == 0xC06824
			or actual.frame == 989
				and actual.access == "read"
				and actual.address == 0x283B
				and actual.cpu.pc24 == 0xC06799
			or actual.frame == 989
				and actual.access == "write"
				and actual.address == 0x283B
				and actual.cpu.pc24 == 0xC06824
		if is_target then
			table.insert(filtered, actual)
		end
	end
	if #filtered ~= #expected then
		return false
	end
	for index, wanted in ipairs(expected) do
		local actual = filtered[index]
		if actual.access ~= wanted.access
			or actual.address ~= wanted.address
			or actual.value ~= wanted.value
			or actual.cpu.pc24 ~= wanted.pc24
		then
			return false
		end
	end
	return true
end

local function range_unchanged(pre, post)
	return pre.sha256 == post.sha256
end

local function preservation_matches(post_ranges)
	for _, name in ipairs({
		"roster",
		"joined",
		"epoch-name",
		"front-guard",
		"candidate",
		"rear-guard",
	}) do
		if not range_unchanged(pre_ranges[name], post_ranges[name]) then
			return false
		end
	end
	local old_pre = pre_ranges["old-compatibility"].values
	local old_post = post_ranges["old-compatibility"].values
	if scenario_name ~= "event11c-frog" then
		return range_unchanged(
			pre_ranges["old-compatibility"],
			post_ranges["old-compatibility"]
		)
	end
	for index, before in ipairs(old_pre) do
		local expected = before
		local offset = OLD_BLOCK_START + index - 1
		if offset == 0x2834 then
			expected = 0x03
		elseif offset == 0x283B then
			expected = 0xFF
		end
		if old_post[index] ~= expected then
			return false
		end
	end
	return true
end

local function protected_accesses_zero(counter_records)
	for _, record in ipairs(counter_records) do
		if watched_offsets[record.address] == "front-guard"
			or watched_offsets[record.address] == "candidate"
			or watched_offsets[record.address] == "rear-guard"
		then
			if record.read_count ~= 0 or record.write_count ~= 0 then
				return false
			end
		end
	end
	return true
end

local function route_endpoint_matches(route)
	if scenario_name ~= "event11c-frog" then
		return true
	end
	return route.location == 0x01D1
		and route.storyline == 0x4D
		and route.lap_scratch == 0x03
		and route.magic_flags == 0x5F
		and route.robo_flags == 0
		and route.explore_mode == 0
		and route.dialog_state == 0
		and route.leader_x == 1925
		and route.leader_y == 3061
		and route.active_party_hex == "060403"
		and route.field_phase_mod16 == 0
		and route.spekkio_sprite_frame == 22
end

local function emit_trace(requested_success, require_canonical_event_png)
	assert(tracing, "observer was not armed at termination")
	disarm_observers()

	local read_counters = emu.getAccessCounters(
		WRAM,
		emu.counterType.readCount
	)
	local write_counters = emu.getAccessCounters(
		WRAM,
		emu.counterType.writeCount
	)
	local counter_base = counter_index_base(read_counters)
	assert(
		counter_base == initial_counter_index_base
			and counter_index_base(write_counters) == counter_base,
		"access counter array indexing changed"
	)

	local counter_records = {}
	local counter_parts = {}
	local counters_match = true
	local read_total = 0
	local write_total = 0
	for _, range in ipairs(WATCHED_RANGES) do
		for offset = range.start_offset, range.end_offset do
			local totals = assert(callback_totals[offset])
			local record = {
				address = offset,
				read_count = counter_value(read_counters, counter_base, offset),
				write_count = counter_value(write_counters, counter_base, offset),
				callback_read_count = totals.read,
				callback_write_count = totals.write,
			}
			read_total = read_total + record.read_count
			write_total = write_total + record.write_count
			if record.read_count ~= record.callback_read_count
				or record.write_count ~= record.callback_write_count
			then
				counters_match = false
			end
			table.insert(counter_records, record)
			table.insert(counter_parts, table.concat({
				"{",
				'"address":', tostring(0x7E0000 + record.address), ",",
				'"read_count":', tostring(record.read_count), ",",
				'"write_count":', tostring(record.write_count),
				"}",
			}))
		end
	end

	local post_ranges = capture_ranges()
	local post_route = route_snapshot()
	local range_parts = {}
	for _, range in ipairs(WATCHED_RANGES) do
		table.insert(range_parts, table.concat({
			"{",
			'"name":', json_string(range.name), ",",
			'"start_address":',
			tostring(0x7E0000 + range.start_offset), ",",
			'"length":',
			tostring(range.end_offset - range.start_offset + 1),
			"}",
		}))
	end
	local callback_parts = {}
	for _, record in ipairs(callbacks) do
		table.insert(callback_parts, callback_json(record))
	end
	local write_parts = {}
	for _, record in ipairs(explicit_writes) do
		table.insert(write_parts, write_json(record))
	end

	local calibration_zero = scenario_name ~= "calibration"
		or (
			read_total == 0
			and write_total == 0
			and callback_read_total == 0
			and callback_write_total == 0
			and #callbacks == 0
		)
	local protected_zero = protected_accesses_zero(counter_records)
	local preservation_ok = preservation_matches(post_ranges)
	local positive_control_match = event_control_matches()
	local route_ok = route_endpoint_matches(post_route)
	local success = requested_success
		and observer_error == nil
		and not overflow
		and counters_match
		and calibration_zero
		and protected_zero
		and preservation_ok
		and positive_control_match
		and route_ok
		and preparation_writes_after_arm == 0
	local exit_code = success and 41 or 91
	local failure_parts = {}
	if not success then
		table.insert(
			failure_parts,
			table.concat({
				"requested_success=", tostring(requested_success),
				" observer_error=", tostring(observer_error),
				" overflow=", tostring(overflow),
				" counters_match=", tostring(counters_match),
				" calibration_zero=", tostring(calibration_zero),
				" protected_zero=", tostring(protected_zero),
				" preservation_ok=", tostring(preservation_ok),
				" positive_control_match=", tostring(positive_control_match),
				" route_ok=", tostring(route_ok),
				" preparation_writes_after_arm=",
				tostring(preparation_writes_after_arm),
				" callback_count=", tostring(#callbacks),
				" read_total=", tostring(read_total),
				" write_total=", tostring(write_total),
			})
		)
		local reported = 0
		for _, record in ipairs(counter_records) do
			if record.read_count ~= 0 or record.write_count ~= 0 then
				table.insert(
					failure_parts,
					string.format(
						"counter $7E%04X read=%d write=%d callback_read=%d callback_write=%d",
						record.address,
						record.read_count,
						record.write_count,
						record.callback_read_count,
						record.callback_write_count
					)
				)
				reported = reported + 1
				if reported >= 32 then
					break
				end
			end
		end
		for index = 1, math.min(#callbacks, 32) do
			local record = callbacks[index]
			table.insert(
				failure_parts,
				string.format(
					"callback %d frame=%d %s $7E%04X value=%02X pc=%06X",
					record.seq,
					record.frame,
					record.access,
					record.address,
					record.value,
					record.cpu.pc24
				)
			)
		end
		for _, record in ipairs(callbacks) do
			if record.address == 0x2834 or record.address == 0x283B then
				table.insert(
					failure_parts,
					string.format(
						"event-target-candidate %d frame=%d %s $7E%04X value=%02X pc=%06X",
						record.seq,
						record.frame,
						record.access,
						record.address,
						record.value,
						record.cpu.pc24
					)
				)
			end
		end
	end

	local trace = table.concat({
		"{",
		'"schema":"project-epoch-mesen-wram-ownership-trace-v1",',
		'"collector_version":1,',
		'"scenario":', json_string(scenario_name), ",",
		'"variant":', json_string(variant), ",",
		'"collector_explicit_write_scope":',
		'"snes-work-ram-preparation-before-counters-arm-only",',
		'"checkpoint":{',
		'"id":', json_string(CHECKPOINT_ID), ",",
		'"state_size":', tostring(#serialized_state), ",",
		'"state_sha256":', json_string(pinned_state_sha256), ",",
		'"source_frame":', tostring(CHECKPOINT_SOURCE_FRAME), ",",
		'"direct_page":256,',
		'"location":465',
		"},",
		'"scenario_contract":', scenario_contract_json(), ",",
		'"observer":{',
		'"mechanism":"snes-work-ram-read-write-memory-callbacks",',
		'"memory_type":"snes-work-ram",',
		'"counter_granularity":"byte-address-and-access",',
		'"callback_limit":', tostring(CALLBACK_LIMIT), ",",
		'"counters_cover_every_watched_byte":true',
		"},",
		'"watched_ranges":[', table.concat(range_parts, ","), "],",
		'"preparation":{',
		'"completed_before_counters_armed":true,',
		'"counters_zero_after_preparation":',
		bool_json(counters_zero_after_preparation), ",",
		'"writes":[', table.concat(write_parts, ","), "]",
		"},",
		'"pre":', snapshot_json(pre_ranges), ",",
		'"callbacks":[', table.concat(callback_parts, ","), "],",
		'"counters":[', table.concat(counter_parts, ","), "],",
		'"post":', snapshot_json(post_ranges), ",",
		'"termination":{',
		'"collector_stopped":true,',
		'"success":', bool_json(success), ",",
		'"overflow":', bool_json(overflow), ",",
		'"observer_error":',
		observer_error == nil and "null" or json_string(observer_error), ",",
		'"counters_armed":', bool_json(counters_armed), ",",
		'"preparation_writes_after_arm":',
		tostring(preparation_writes_after_arm), ",",
		'"terminal_frame":', tostring(relative_frame), ",",
		'"unexpected_accesses":', success and "0" or "1",
		"}",
		"}\n",
	})
	write_file(trace_path, trace)
	local screenshot = emu.takeScreenshot()
	if require_canonical_event_png
		and (
			#screenshot ~= EVENT_ENDPOINT_PNG_SIZE
			or sha256(screenshot) ~= EVENT_ENDPOINT_PNG_SHA256
		)
	then
		-- Freeze the trace at the first valid route endpoint, but allow the
		-- presentation buffer to catch up without collecting more accesses.
		pending_exit_code = exit_code
		pending_screenshot_wait_frames = 0
		return
	end
	write_file(screenshot_path, screenshot)
	if not success then
		write_file(
			trace_path .. ".observer-error",
			table.concat(failure_parts, "\n") .. "\n"
		)
	end
	emu.stop(exit_code)
end

load_hook = emu.addMemoryCallback(
	function()
		if not load_requested then
			load_requested = true
			emu.loadSavestate(serialized_state)
			return
		end
		if checkpoint_cpu == nil then
			-- The state becomes authoritative when execution resumes after the
			-- load callback returns, not inside the callback that requested it.
			checkpoint_cpu = cpu_snapshot()
		end
		post_load_exec_seen = true
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
				emu.removeMemoryCallback(
					load_hook,
					emu.callbackType.exec,
					0,
					0xFFFFFF,
					CPU,
					CPU_MEMORY
				)
				prepare_fixture()
				arm_observers()
				if scenario_name == "calibration" then
					emit_trace(true)
					return
				end
			elseif prepared and tracing then
				relative_frame = relative_frame + 1
				if scenario_name == "main-menu" then
					input.x = pulse(relative_frame, 60, 61)
				elseif scenario_name == "event11c-frog" then
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
				end

				if observer_error ~= nil or overflow then
					emit_trace(false)
					return
				end
				if scenario.terminal_frame ~= nil
					and relative_frame == scenario.terminal_frame
				then
					emit_trace(true)
					return
				end
			end
			emu.setInput(input, 0)
		end)
		if not ok then
			observer_error = tostring(message)
			write_file(trace_path .. ".observer-error", observer_error .. "\n")
			emu.stop(91)
		end
	end,
	emu.eventType.inputPolled
)

-- The event scenario terminates only after a completed rendered frame.  At
-- inputPolled, the live route fields can already describe the next frame while
-- takeScreenshot() still sees the prior presentation buffer.  endFrame binds
-- the route snapshot, trace endpoint, and proof image to one frame.
emu.addEventCallback(
	function()
		if pending_exit_code ~= nil then
			pending_screenshot_wait_frames =
				pending_screenshot_wait_frames + 1
			local screenshot = emu.takeScreenshot()
			if #screenshot == EVENT_ENDPOINT_PNG_SIZE
				and sha256(screenshot) == EVENT_ENDPOINT_PNG_SHA256
			then
				local exit_code = pending_exit_code
				pending_exit_code = nil
				write_file(screenshot_path, screenshot)
				emu.stop(exit_code)
				return
			end
			if pending_screenshot_wait_frames
				>= EVENT_ENDPOINT_PNG_MAX_WAIT_FRAMES
			then
				write_file(
					trace_path .. ".observer-error",
					"canonical event endpoint PNG was not observed\n"
				)
				emu.stop(91)
			end
			return
		end
		if scenario_name ~= "event11c-frog"
			or not prepared
			or not tracing
		then
			return
		end
		local ok, message = pcall(function()
			if relative_frame >= scenario.minimum_terminal_frame
				and route_endpoint_matches(route_snapshot())
			then
				emit_trace(true, true)
				return
			end
			if relative_frame >= scenario.maximum_frame then
				emit_trace(false)
			end
		end)
		if not ok then
			observer_error = tostring(message)
			write_file(trace_path .. ".observer-error", observer_error .. "\n")
			emu.stop(91)
		end
	end,
	emu.eventType.endFrame
)
