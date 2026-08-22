-- Project Epoch Mesen 2.1.1 volatile relocation trace for event $11C.
--
-- This source-only diagnostic loads a private native Mesen checkpoint and two
-- private, host-built raw event packets. It requires the live decompressed
-- event at $7F:2000 to match the complete source packet, proves that the
-- transformed packet differs at exactly the 24 pinned address-operand bytes,
-- and applies only those 24 bytes to live WRAM. It then moves the complete
-- vanilla compatibility block from $7E:2830-$287F to the candidate
-- $7E:2CA0-$2CEF span and traces the same bounded Spekkio route used by the
-- accepted unmodified-event collector.
--
-- The collector's explicit write8/write16 calls target snesWorkRam only; it
-- makes no explicit PRG ROM or SRAM write. Loading the checkpoint and running
-- the game may change other transient emulator state. Its filesystem writes are
-- limited to the requested compact JSON trace, endpoint PNG, and an
-- observer-error text file on failure.

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
local EPOCH_NAME = 0x2C4D

local EVENT_PACKET_START = 0x12000
local EVENT_PACKET_LENGTH = 0x0C6B
local EXPECTED_CHANGED_BYTE_COUNT = 24
local SOURCE_PACKET_SHA256 =
	"31d5b222828eca6c1c91a309f1543a8f" ..
	"dccf2e2f5deea7a4074b7376eaa70d8a"
local TRANSFORMED_PACKET_SHA256 =
	"8e2952bd5e8c25eaf0ad4244dece929b" ..
	"6f4fc1eea8317ea707fcd782c898e50b"

local OLD_BLOCK_START = 0x2830
local OLD_BLOCK_END = 0x287F
local OLD_BLOCK_LENGTH = 0x50
local OLD_EVENT_TARGET_LENGTH = 0x0C
local CANDIDATE_START = 0x2CA0
local CANDIDATE_END = 0x2CEF
local CANDIDATE_LENGTH = 0x50
local CANDIDATE_TECH_COUNTS = 0x2CA0
local CANDIDATE_LEARNED_MASKS = 0x2CA7
local CANDIDATE_GUARDS_START = 0x2C9C
local CANDIDATE_GUARDS_END = 0x2CFF
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
local FIELD_FRAME_COUNTER = 0x014B
local SPEKKIO_SPRITE_FRAME = 0x0F15

local EXPECTED_EPOCH_NAME = { 0xA4, 0xC9, 0xC8, 0xBC, 0xC1, 0x00 }
local TARGET_CANARY_HEX = "471eea9705fecea2040cc7e0"

-- Offsets are zero-based within the complete decompressed event packet.
-- Each old/new address pair differs in its low and middle bytes only; the
-- unchanged $7E bank byte is checked but is not written by this collector.
local RELOCATION_SITES = {
	{
		command_offset = 0x05C0,
		opcode_offset = 0x05C1,
		opcode = 0x4C,
		operand_offset = 0x05C2,
		old_address = 0x7E2830,
		new_address = 0x7E2CA0,
	},
	{
		command_offset = 0x05C5,
		opcode_offset = 0x05C6,
		opcode = 0x48,
		operand_offset = 0x05C7,
		old_address = 0x7E2837,
		new_address = 0x7E2CA7,
	},
	{
		command_offset = 0x05CD,
		opcode_offset = 0x05CE,
		opcode = 0x4C,
		operand_offset = 0x05CF,
		old_address = 0x7E2837,
		new_address = 0x7E2CA7,
	},
	{
		command_offset = 0x0609,
		opcode_offset = 0x060A,
		opcode = 0x4C,
		operand_offset = 0x060B,
		old_address = 0x7E2831,
		new_address = 0x7E2CA1,
	},
	{
		command_offset = 0x060E,
		opcode_offset = 0x060F,
		opcode = 0x48,
		operand_offset = 0x0610,
		old_address = 0x7E2838,
		new_address = 0x7E2CA8,
	},
	{
		command_offset = 0x0616,
		opcode_offset = 0x0617,
		opcode = 0x4C,
		operand_offset = 0x0618,
		old_address = 0x7E2838,
		new_address = 0x7E2CA8,
	},
	{
		command_offset = 0x0652,
		opcode_offset = 0x0653,
		opcode = 0x4C,
		operand_offset = 0x0654,
		old_address = 0x7E2832,
		new_address = 0x7E2CA2,
	},
	{
		command_offset = 0x0657,
		opcode_offset = 0x0658,
		opcode = 0x48,
		operand_offset = 0x0659,
		old_address = 0x7E2839,
		new_address = 0x7E2CA9,
	},
	{
		command_offset = 0x065F,
		opcode_offset = 0x0660,
		opcode = 0x4C,
		operand_offset = 0x0661,
		old_address = 0x7E2839,
		new_address = 0x7E2CA9,
	},
	{
		command_offset = 0x06B4,
		opcode_offset = 0x06B5,
		opcode = 0x4C,
		operand_offset = 0x06B6,
		old_address = 0x7E2834,
		new_address = 0x7E2CA4,
	},
	{
		command_offset = 0x06B9,
		opcode_offset = 0x06BA,
		opcode = 0x48,
		operand_offset = 0x06BB,
		old_address = 0x7E283B,
		new_address = 0x7E2CAB,
	},
	{
		command_offset = 0x06C1,
		opcode_offset = 0x06C2,
		opcode = 0x4C,
		operand_offset = 0x06C3,
		old_address = 0x7E283B,
		new_address = 0x7E2CAB,
	},
}

local PROFILES = {
	["frog-robo"] = {
		active_party = { 0x06, 0x04, 0x03 },
		clear_magic_bits = 0x18,
		clear_robo_bits = 0x01,
		candidate_tech_count_offsets = { 0x2CA4 },
		candidate_learned_mask_offsets = { 0x2CAB },
		remaining_tp_offsets = { 0x276D },
		expected_callbacks = {
			{ access = "write", address = 0x7E2CA4 },
			{ access = "read", address = 0x7E2CAB },
			{ access = "write", address = 0x7E2CAB },
		},
		expected_counts_hex = "08080808030808",
		expected_dialog_state = 0,
		expected_spekkio_sprite_frame = 22,
		minimum_terminal_frame = 1500,
	},
	["crono-marle-lucca"] = {
		active_party = { 0x00, 0x01, 0x02 },
		clear_magic_bits = 0x47,
		clear_robo_bits = 0x00,
		candidate_tech_count_offsets = { 0x2CA0, 0x2CA1, 0x2CA2 },
		candidate_learned_mask_offsets = { 0x2CA7, 0x2CA8, 0x2CA9 },
		remaining_tp_offsets = { 0x262D, 0x267D, 0x26CD },
		expected_callbacks = {
			{ access = "write", address = 0x7E2CA0 },
			{ access = "read", address = 0x7E2CA7 },
			{ access = "write", address = 0x7E2CA7 },
			{ access = "write", address = 0x7E2CA1 },
			{ access = "read", address = 0x7E2CA8 },
			{ access = "write", address = 0x7E2CA8 },
			{ access = "write", address = 0x7E2CA2 },
			{ access = "read", address = 0x7E2CA9 },
			{ access = "write", address = 0x7E2CA9 },
		},
		expected_counts_hex = "03030308080808",
		expected_dialog_state = 2,
		expected_spekkio_sprite_frame = 4,
		minimum_terminal_frame = 2000,
	},
}

local state_path = assert(os.getenv("PE_STATE_PATH"), "PE_STATE_PATH is required")
local trace_path = assert(os.getenv("PE_TRACE_OUT"), "PE_TRACE_OUT is required")
local screenshot_path = assert(
	os.getenv("PE_TRACE_SCREENSHOT"),
	"PE_TRACE_SCREENSHOT is required"
)
local source_packet_path = assert(
	os.getenv("PE_SOURCE_PACKET"),
	"PE_SOURCE_PACKET is required"
)
local transformed_packet_path = assert(
	os.getenv("PE_TRANSFORMED_PACKET"),
	"PE_TRANSFORMED_PACKET is required"
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
source_packet_path = require_private_path(
	source_packet_path,
	"PE_SOURCE_PACKET"
)
transformed_packet_path = require_private_path(
	transformed_packet_path,
	"PE_TRANSFORMED_PACKET"
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

local TARGET_CANARY = bytes_from_hex(TARGET_CANARY_HEX)
assert(#TARGET_CANARY == OLD_EVENT_TARGET_LENGTH)
local source_compatibility_values = nil

local function range_values(start_offset, length)
	local values = {}
	for index = 0, length - 1 do
		table.insert(values, read8(start_offset + index))
	end
	return values
end

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

local function old_block_matches_variant()
	if source_compatibility_values == nil then
		return false
	end
	for index = 0, OLD_BLOCK_LENGTH - 1 do
		local expected = source_compatibility_values[index + 1]
		if index < OLD_EVENT_TARGET_LENGTH then
			expected = variant == "zero"
				and 0
				or TARGET_CANARY[index + 1]
		end
		if read8(OLD_BLOCK_START + index) ~= expected then
			return false
		end
	end
	return true
end

local function packet_byte(packet, offset)
	assert(offset >= 0 and offset < #packet, "packet byte offset is out of range")
	return assert(packet:byte(offset + 1))
end

local source_packet = read_file(source_packet_path)
local transformed_packet = read_file(transformed_packet_path)
assert(
	#source_packet == EVENT_PACKET_LENGTH,
	"PE_SOURCE_PACKET length mismatch"
)
assert(
	#transformed_packet == EVENT_PACKET_LENGTH,
	"PE_TRANSFORMED_PACKET length mismatch"
)

local expected_diffs = {}
local packet_patches = {}
local relocation_site_by_command_offset = {}
local expected_diff_count = 0

for site_index, site in ipairs(RELOCATION_SITES) do
	assert(
		site.opcode_offset == site.command_offset + 1
			and site.operand_offset == site.command_offset + 2,
		"relocation site packet offsets are inconsistent"
	)
	assert(
		relocation_site_by_command_offset[site.command_offset] == nil,
		"duplicate relocation command offset"
	)
	relocation_site_by_command_offset[site.command_offset] = site
	assert(
		packet_byte(source_packet, site.opcode_offset) == site.opcode,
		"source packet opcode preimage mismatch"
	)
	assert(
		packet_byte(transformed_packet, site.opcode_offset) == site.opcode,
		"transformed packet opcode drift"
	)
	for byte_index = 0, 2 do
		local offset = site.operand_offset + byte_index
		local old_value = (site.old_address >> (byte_index * 8)) & 0xFF
		local new_value = (site.new_address >> (byte_index * 8)) & 0xFF
		assert(
			packet_byte(source_packet, offset) == old_value,
			"source packet address-operand preimage mismatch"
		)
		assert(
			packet_byte(transformed_packet, offset) == new_value,
			"transformed packet address-operand mismatch"
		)
		if old_value ~= new_value then
			assert(expected_diffs[offset] == nil, "duplicate changed packet offset")
			expected_diffs[offset] = {
				old_value = old_value,
				new_value = new_value,
			}
			table.insert(packet_patches, {
				seq = #packet_patches,
				site_seq = site_index - 1,
				event_data_command_offset = site.command_offset,
				opcode_offset = site.opcode_offset,
				opcode = site.opcode,
				operand_offset = site.operand_offset,
				byte_index = byte_index,
				packet_offset = offset,
				offset = offset,
				old_value = old_value,
				new_value = new_value,
				old_address = site.old_address,
				new_address = site.new_address,
			})
			expected_diff_count = expected_diff_count + 1
		end
	end
end

assert(
	expected_diff_count == EXPECTED_CHANGED_BYTE_COUNT,
	"pinned relocation does not describe exactly 24 changed bytes"
)

local observed_diff_count = 0
for offset = 0, EVENT_PACKET_LENGTH - 1 do
	local old_value = packet_byte(source_packet, offset)
	local new_value = packet_byte(transformed_packet, offset)
	if old_value ~= new_value then
		local expected = expected_diffs[offset]
		assert(expected ~= nil, "transformed packet changed an unapproved byte")
		assert(
			old_value == expected.old_value
				and new_value == expected.new_value,
			"transformed packet changed an approved byte to the wrong value"
		)
		observed_diff_count = observed_diff_count + 1
	end
end
assert(
	observed_diff_count == EXPECTED_CHANGED_BYTE_COUNT,
	"transformed packet does not contain exactly 24 byte differences"
)
for offset, expected in pairs(expected_diffs) do
	assert(
		packet_byte(source_packet, offset) == expected.old_value
			and packet_byte(transformed_packet, offset) == expected.new_value,
		"expected packet difference is absent"
	)
end
local packet_exact_expected_diff = true

local candidate_target_offsets = {}
for _, offset in ipairs(profile.candidate_tech_count_offsets) do
	assert(
		offset >= CANDIDATE_START and offset <= CANDIDATE_END,
		"candidate tech-count target is outside candidate block"
	)
	candidate_target_offsets[offset] = true
end
for _, offset in ipairs(profile.candidate_learned_mask_offsets) do
	assert(
		offset >= CANDIDATE_START and offset <= CANDIDATE_END,
		"candidate learned-mask target is outside candidate block"
	)
	candidate_target_offsets[offset] = true
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

local serialized_state = read_file(state_path)
local state_loaded = false
local trace_hooks_armed = false
local prepared = false
local relative_frame = 0
local overflow = false
local callbacks = {}
local observer_error = nil
local direct_page = nil
local pending_write = nil
local pre_json = nil
local post_json = nil
local load_hook = nil
local candidate_pre_values = nil
local source_compatibility_hex = nil
local candidate_copy_match_before_profile = false
local packet_live_source_match_before = false
local packet_live_transformed_match_after_prepare = false
local packet_live_transformed_match_at_end = false
local packet_patch_write_count = 0

local function live_packet_matches(packet)
	for offset = 0, EVENT_PACKET_LENGTH - 1 do
		if read8(EVENT_PACKET_START + offset) ~= packet_byte(packet, offset) then
			return false
		end
	end
	return true
end

local function candidate_non_target_preserved()
	if candidate_pre_values == nil then
		return false
	end
	for index = 0, CANDIDATE_LENGTH - 1 do
		local offset = CANDIDATE_START + index
		if not candidate_target_offsets[offset]
			and read8(offset) ~= candidate_pre_values[index + 1]
		then
			return false
		end
	end
	return true
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
		'"candidate_tech_counts_hex":',
		json_string(range_hex(CANDIDATE_TECH_COUNTS, 7)), ",",
		'"candidate_learned_masks_hex":',
		json_string(range_hex(CANDIDATE_LEARNED_MASKS, 7)), ",",
		'"old_block_hex":',
		json_string(range_hex(OLD_BLOCK_START, OLD_BLOCK_LENGTH)), ",",
		'"candidate_hex":',
		json_string(range_hex(CANDIDATE_START, CANDIDATE_LENGTH)), ",",
		'"old_block_matches_variant":',
		bool_json(old_block_matches_variant()), ",",
		'"candidate_non_target_preserved":',
		bool_json(candidate_non_target_preserved()), ",",
		'"front_guard_hex":',
		json_string(range_hex(FRONT_GUARD_START, FRONT_GUARD_LENGTH)), ",",
		'"rear_guard_hex":',
		json_string(range_hex(REAR_GUARD_START, REAR_GUARD_LENGTH)), ",",
		'"epoch_name_hex":',
		json_string(range_hex(EPOCH_NAME, #EXPECTED_EPOCH_NAME)),
		"}",
	})
end

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

local function require_cpu_state()
	local state = emu.getState()
	assert(type(state) == "table", "emu.getState() did not return a table")
	local cpu = {}
	for _, key in ipairs({ "d", "y", "a", "ps" }) do
		local value = state["cpu." .. key]
		assert(
			type(value) == "number" and value == math.floor(value),
			"emu.getState().cpu." .. key .. " is unavailable"
		)
		cpu[key] = value
	end
	return {
		direct_page = cpu.d & 0xFFFF,
		y = cpu.y & 0xFFFF,
		accumulator = cpu.a & 0xFFFF,
		status = cpu.ps & 0xFF,
	}
end

local function live_operand_at(site)
	local base = EVENT_PACKET_START + site.operand_offset
	return read8(base)
		| (read8(base + 1) << 8)
		| (read8(base + 2) << 16)
end

local function bind_runtime_command(access, address)
	local cpu = require_cpu_state()
	assert(
		cpu.direct_page == CHECKPOINT_DIRECT_PAGE,
		"handler direct-page register changed"
	)
	assert((cpu.status & 0x20) ~= 0, "handler did not execute with M set")
	local site = relocation_site_by_command_offset[cpu.y]
	assert(site ~= nil, "watched access has an unapproved event command Y")
	local expected_opcode = access == "read" and 0x48 or 0x4C
	assert(site.opcode == expected_opcode, "event command access kind mismatch")
	assert(
		read8(EVENT_PACKET_START + site.opcode_offset) == site.opcode,
		"live event opcode changed before watched access"
	)
	assert(
		live_operand_at(site) == site.new_address,
		"live relocated operand does not match the pinned destination"
	)
	assert(
		address == site.new_address,
		"direct-page pointer does not match the live relocated operand"
	)
	return cpu, site
end

local function callback_record(record)
	if not prepared then
		return
	end
	if record.raw_wram_offset == nil
		or not is_watched_wram_offset(record.raw_wram_offset)
	then
		return
	end
	if #callbacks >= CALLBACK_LIMIT then
		overflow = true
		return
	end
	record.seq = #callbacks
	table.insert(callbacks, record)
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
		assert(
			value == completed.deferred_value,
			"deferred post-STA byte does not match accumulator"
		)
		callback_record({
			frame = completed.frame,
			access = "write",
			address = completed.address,
			raw_wram_offset = completed.wram_offset,
			value = value,
			pc24 = WRITE_ABS_FROM_MEM8_PC,
			cpu_y = completed.cpu_y,
			command_offset = completed.command_offset,
			opcode_offset = completed.opcode_offset,
			opcode = completed.opcode,
			operand_offset = completed.operand_offset,
			operand_address = completed.operand_address,
			direct_page = completed.direct_page,
			memory_flag_set = completed.memory_flag_set,
			accumulator = completed.accumulator,
			deferred_value = completed.deferred_value,
		})
	end
	if address ~= READ_ABS8_PC and address ~= WRITE_ABS_FROM_MEM8_PC then
		return
	end
	if address == READ_ABS8_PC then
		local target, wram_offset = read_pointer(0xCD)
		if wram_offset == nil or not is_watched_wram_offset(wram_offset) then
			return
		end
		local cpu, site = bind_runtime_command("read", target)
		local value = wram_offset == nil and 0 or read8(wram_offset)
		callback_record({
			frame = relative_frame,
			access = "read",
			address = target,
			raw_wram_offset = wram_offset,
			value = value,
			pc24 = READ_ABS8_PC,
			cpu_y = cpu.y,
			command_offset = site.command_offset,
			opcode_offset = site.opcode_offset,
			opcode = site.opcode,
			operand_offset = site.operand_offset,
			operand_address = site.new_address,
			direct_page = cpu.direct_page,
			memory_flag_set = (cpu.status & 0x20) ~= 0,
			accumulator = nil,
			deferred_value = nil,
		})
	elseif address == WRITE_ABS_FROM_MEM8_PC then
		local target, wram_offset = read_pointer(0xD0)
		if wram_offset == nil or not is_watched_wram_offset(wram_offset) then
			return
		end
		local cpu, site = bind_runtime_command("write", target)
		pending_write = {
			address = target,
			wram_offset = wram_offset,
			frame = relative_frame,
			cpu_y = cpu.y,
			command_offset = site.command_offset,
			opcode_offset = site.opcode_offset,
			opcode = site.opcode,
			operand_offset = site.operand_offset,
			operand_address = site.new_address,
			direct_page = cpu.direct_page,
			memory_flag_set = (cpu.status & 0x20) ~= 0,
			accumulator = cpu.accumulator & 0xFF,
			deferred_value = cpu.accumulator & 0xFF,
		}
	end
end

local function apply_volatile_packet_patch()
	packet_live_source_match_before = live_packet_matches(source_packet)
	assert(
		packet_live_source_match_before,
		"live $7F:2000 packet does not match PE_SOURCE_PACKET"
	)
	for _, patch in ipairs(packet_patches) do
		local live_offset = EVENT_PACKET_START + patch.offset
		assert(
			read8(live_offset) == patch.old_value,
			"live packet changed before an approved volatile write"
		)
		write8(live_offset, patch.new_value)
		assert(
			read8(live_offset) == patch.new_value,
			"volatile packet write did not take effect"
		)
		packet_patch_write_count = packet_patch_write_count + 1
	end
	assert(
		packet_patch_write_count == EXPECTED_CHANGED_BYTE_COUNT,
		"volatile packet write count mismatch"
	)
	packet_live_transformed_match_after_prepare =
		live_packet_matches(transformed_packet)
	assert(
		packet_live_transformed_match_after_prepare,
		"live packet does not match PE_TRANSFORMED_PACKET after patch"
	)
end

local function prepare()
	assert(trace_hooks_armed, "trace hooks were not armed after state load")
	direct_page = CHECKPOINT_DIRECT_PAGE
	assert(read16(LOCATION) == 0x01D1, "checkpoint location mismatch")
	assert(read8(EXPLORE_MODE) == 1, "checkpoint is not controllable")
	assert(read8(DIALOG_STATE) == 0, "checkpoint has dialogue open")
	local object = read8(LEADER_OBJECT)
	assert(read16(OBJECT_X + object) == 1568, "checkpoint X mismatch")
	assert(read16(OBJECT_Y + object) == 2623, "checkpoint Y mismatch")
	assert(range_hex(ACTIVE_PARTY, 3) == "060403", "source party mismatch")
	assert(
		range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH),
		"front guard is not zero"
	)
	assert(
		range_is_zero(CANDIDATE_START, CANDIDATE_LENGTH),
		"candidate is not zero"
	)
	assert(
		range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH),
		"rear guard is not zero"
	)
	assert(range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME), "Epoch name mismatch")

	apply_volatile_packet_patch()

	source_compatibility_values = range_values(
		OLD_BLOCK_START,
		OLD_BLOCK_LENGTH
	)
	source_compatibility_hex = range_hex(OLD_BLOCK_START, OLD_BLOCK_LENGTH)
	assert(
		source_compatibility_hex:sub(1, 28)
			== "08080808080808ffffffffffffff",
		"checkpoint compatibility-block prefix mismatch"
	)
	for index, value in ipairs(source_compatibility_values) do
		write8(CANDIDATE_START + index - 1, value)
	end
	assert(
		range_matches(CANDIDATE_START, source_compatibility_values),
		"candidate compatibility-block copy mismatch"
	)
	candidate_copy_match_before_profile = true

	write8(STORYLINE, 0x4C)
	write8(LAP_SCRATCH, 0x03)
	write8(MAGIC_FLAGS, read8(MAGIC_FLAGS) & (~profile.clear_magic_bits & 0xFF))
	if profile.clear_robo_bits ~= 0 then
		write8(ROBO_FLAGS, read8(ROBO_FLAGS) & (~profile.clear_robo_bits & 0xFF))
	end
	for index, pc_id in ipairs(profile.active_party) do
		write8(ACTIVE_PARTY + index - 1, pc_id)
	end
	for _, offset in ipairs(profile.candidate_tech_count_offsets) do
		write8(offset, 0)
	end
	for _, offset in ipairs(profile.candidate_learned_mask_offsets) do
		write8(offset, read8(offset) & 0x1F)
	end
	for _, offset in ipairs(profile.remaining_tp_offsets) do
		write16(offset, 0)
	end

	if variant == "canary" then
		for index, value in ipairs(TARGET_CANARY) do
			write8(OLD_BLOCK_START + index - 1, value)
		end
	else
		for index = 0, OLD_EVENT_TARGET_LENGTH - 1 do
			write8(OLD_BLOCK_START + index, 0)
		end
	end

	candidate_pre_values = range_values(CANDIDATE_START, CANDIDATE_LENGTH)
	assert(old_block_matches_variant(), "old-block sentinel preparation mismatch")
	assert(
		candidate_non_target_preserved(),
		"candidate pre-snapshot preservation mismatch"
	)
	assert(
		range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH),
		"front guard changed"
	)
	assert(
		range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH),
		"rear guard changed"
	)
	assert(range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME), "Epoch name changed")
	assert(
		live_packet_matches(transformed_packet),
		"transformed live packet changed during profile preparation"
	)
	pre_json = snapshot_json()
	prepared = true
end

local function callback_json(record)
	return table.concat({
		"{",
		'"seq":', tostring(record.seq), ",",
		'"frame":', tostring(record.frame), ",",
		'"access":', json_string(record.access), ",",
		'"address":', tostring(record.address), ",",
		'"raw_wram_offset":', tostring(record.raw_wram_offset), ",",
		'"value":', tostring(record.value), ",",
		'"pc24":', tostring(record.pc24), ",",
		'"cpu_y":', tostring(record.cpu_y), ",",
		'"command_offset":', tostring(record.command_offset), ",",
		'"opcode_offset":', tostring(record.opcode_offset), ",",
		'"opcode":', tostring(record.opcode), ",",
		'"operand_offset":', tostring(record.operand_offset), ",",
		'"operand_address":', tostring(record.operand_address), ",",
		'"direct_page":', tostring(record.direct_page), ",",
		'"memory_flag_set":', bool_json(record.memory_flag_set), ",",
		'"accumulator":',
		record.accumulator == nil
			and "null"
			or tostring(record.accumulator), ",",
		'"deferred_value":',
		record.deferred_value == nil
			and "null"
			or tostring(record.deferred_value),
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
	if read16(LOCATION) ~= 0x01D1 then
		return false
	end
	if read8(STORYLINE) ~= 0x4D or read8(LAP_SCRATCH) ~= 0x03 then
		return false
	end
	if read8(MAGIC_FLAGS) ~= 0x5F or read8(ROBO_FLAGS) ~= 0 then
		return false
	end
	if read8(EXPLORE_MODE) ~= 0
		or read8(DIALOG_STATE) ~= profile.expected_dialog_state
	then
		return false
	end
	local object = read8(LEADER_OBJECT)
	if read16(OBJECT_X + object) ~= 1925
		or read16(OBJECT_Y + object) ~= 3061
	then
		return false
	end
	if range_hex(ACTIVE_PARTY, 3)
		~= string.format(
			"%02x%02x%02x",
			profile.active_party[1],
			profile.active_party[2],
			profile.active_party[3]
		)
	then
		return false
	end
	if range_hex(CANDIDATE_LEARNED_MASKS, 7) ~= "ffffffffffffff" then
		return false
	end
	return range_hex(CANDIDATE_TECH_COUNTS, 7)
		== profile.expected_counts_hex
end

local function packet_json()
	local edit_parts = {}
	for site_index, site in ipairs(RELOCATION_SITES) do
		local changed_offsets = {}
		for byte_index = 0, 2 do
			local old_value =
				(site.old_address >> (byte_index * 8)) & 0xFF
			local new_value =
				(site.new_address >> (byte_index * 8)) & 0xFF
			if old_value ~= new_value then
				table.insert(
					changed_offsets,
					tostring(site.operand_offset + byte_index)
				)
			end
		end
		assert(
			#changed_offsets == 2,
			"relocation site does not contain exactly two changed bytes"
		)
		table.insert(edit_parts, table.concat({
			"{",
			'"seq":', tostring(site_index - 1), ",",
			'"event_data_command_offset":',
			tostring(site.command_offset), ",",
			'"opcode_offset":', tostring(site.opcode_offset), ",",
			'"opcode":', tostring(site.opcode), ",",
			'"operand_offset":', tostring(site.operand_offset), ",",
			'"old_address":', tostring(site.old_address), ",",
			'"new_address":', tostring(site.new_address), ",",
			'"changed_offsets":[',
			table.concat(changed_offsets, ","), "]",
			"}",
		}))
	end
	return table.concat({
		"{",
		'"base_wram_offset":', tostring(EVENT_PACKET_START), ",",
		'"length":', tostring(EVENT_PACKET_LENGTH), ",",
		'"source_sha256":', json_string(SOURCE_PACKET_SHA256), ",",
		'"transformed_sha256":',
		json_string(TRANSFORMED_PACKET_SHA256), ",",
		'"changed_byte_count":', tostring(observed_diff_count), ",",
		'"edit_count":', tostring(#RELOCATION_SITES), ",",
		'"edits":[', table.concat(edit_parts, ","), "],",
		'"live_source_match_before":',
		bool_json(packet_live_source_match_before), ",",
		'"exact_expected_diff":', bool_json(packet_exact_expected_diff), ",",
		'"live_transformed_match_after_prepare":',
		bool_json(packet_live_transformed_match_after_prepare), ",",
		'"live_transformed_match_at_end":',
		bool_json(packet_live_transformed_match_at_end),
		"}",
	})
end

local function emit_trace(requested_success)
	packet_live_transformed_match_at_end =
		live_packet_matches(transformed_packet)
	post_json = snapshot_json()
	local callback_parts = {}
	for _, record in ipairs(callbacks) do
		table.insert(callback_parts, callback_json(record))
	end
	local unexpected = unexpected_access_count()
	local success = requested_success
		and packet_patch_write_count == EXPECTED_CHANGED_BYTE_COUNT
		and candidate_copy_match_before_profile
		and packet_live_source_match_before
		and packet_exact_expected_diff
		and packet_live_transformed_match_after_prepare
		and packet_live_transformed_match_at_end
		and old_block_matches_variant()
		and candidate_non_target_preserved()
		and range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)
		and range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)
		and range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME)
		and observer_error == nil
		and pending_write == nil
		and not overflow
		and unexpected == 0
		and final_fields_match()
	local trace = table.concat({
		"{",
		'"schema":"project-epoch-mesen-event11c-relocated-trace-v2",',
		'"collector_version":2,',
		'"profile":', json_string(profile_name), ",",
		'"variant":', json_string(variant), ",",
		'"collector_explicit_write_scope":',
		'"snes-work-ram-via-write8-write16-only",',
		'"source_compatibility_hex":',
		json_string(assert(
			source_compatibility_hex,
			"source compatibility block was not captured"
		)), ",",
		'"candidate_copy_match_before_profile":',
		bool_json(candidate_copy_match_before_profile), ",",
		'"packet":', packet_json(), ",",
		'"observer":{',
		'"read_pc24":', tostring(READ_ABS8_PC), ",",
		'"read_mapped_address":', tostring(READ_ABS8_MAPPING.address), ",",
		'"read_mapping_is_prg_rom":',
		bool_json(READ_ABS8_MAPPING.memType == PRG_ROM), ",",
		'"write_pc24":', tostring(WRITE_ABS_FROM_MEM8_PC), ",",
		'"write_mapped_address":',
		tostring(WRITE_ABS_FROM_MEM8_MAPPING.address), ",",
		'"write_mapping_is_prg_rom":',
		bool_json(WRITE_ABS_FROM_MEM8_MAPPING.memType == PRG_ROM),
		',"mechanism":"broad-exec-callback-exact-pc-router",',
		'"checkpoint_direct_page":', tostring(CHECKPOINT_DIRECT_PAGE),
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
		'"screenshot_phase_mod16":',
		tostring(read8(FIELD_FRAME_COUNTER) & 0x0F), ",",
		'"spekkio_sprite_frame":',
		tostring(read8(SPEKKIO_SPRITE_FRAME)), ",",
		'"unexpected_accesses":', tostring(unexpected),
		"}",
		"}\n",
	})
	write_file(trace_path, trace)
	write_file(screenshot_path, emu.takeScreenshot())
	return success
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
				and old_block_matches_variant()
				and candidate_non_target_preserved()
				and range_is_zero(FRONT_GUARD_START, FRONT_GUARD_LENGTH)
				and range_is_zero(REAR_GUARD_START, REAR_GUARD_LENGTH)
				and range_matches(EPOCH_NAME, EXPECTED_EPOCH_NAME)
				and live_packet_matches(transformed_packet)
				and observer_error == nil
				and pending_write == nil
				and not overflow
				and unexpected_access_count() == 0
				and (read8(FIELD_FRAME_COUNTER) & 0x0F) == 0
				and read8(SPEKKIO_SPRITE_FRAME)
					== profile.expected_spekkio_sprite_frame
			then
				local success = emit_trace(true)
				emu.stop(success and 41 or 91)
			elseif relative_frame >= 2400 then
				emit_trace(false)
				emu.stop(91)
			end
		end

		emu.setInput(input, 0)
	end,
	emu.eventType.inputPolled
)
