# Project Epoch hardened Mesen MCP feasibility, 2026-08-31

## Result

Project Epoch now has a project-scoped, read-only-by-construction Mesen MCP
adapter. It launches one pinned Chrono Trigger checkpoint in a unique
disposable Mesen 2.1.1 installation, permits only six named diagnostic
operations, forces empty Player-1 input, and removes the disposable session
only after exact integrity checks pass.

Two independent current-Mesen runs reproduce the complete accepted
`field-idle/zero` callback sequence after an explicitly bounded one-frame
relative-origin translation. Each run observes 450 reads over 600 frames:

- 150 reads of `$7E2980 == $06`;
- 150 reads of `$7E2981 == $04`;
- 150 reads of `$7E2982 == $03`;
- every read at CPU PC `$C0:6799`;
- the same four-frame cadence as the accepted collector; and
- no overflow, dropped record, observer error, input, memory write, source
  mutation, shared-save mutation, or retained session directory.

The bounded feasibility result is `verified-runtime`. It proves that the
hardened MCP path can reproduce one already accepted observation. It does not
establish a new Chrono Trigger fact. Individual MCP observations remain
`exploratory-only` and have no production or acceptance authority until they
are promoted to a tracked deterministic collector and independently replayed.

## Why the public bridge was not installed

The useful design reference was
[`gareve/mesen-lua-bridge-mcp`](https://github.com/gareve/mesen-lua-bridge-mcp),
audited at exact commit
`66e46463352d9dfa8e57fd1307ec32808e2c4fc5`. Its MIT-licensed file transport,
sequence tagging, and stdio MCP shape are sensible. Its intended feature,
however, is arbitrary caller-supplied Lua execution inside Mesen. The upstream
setup also enables Lua I/O and OS functions. That is a valuable general
reverse-engineering interface, but it is broader than Project Epoch's ROM,
save, provenance, and evidence boundaries allow.

The upstream checkout was preserved under ignored `private/quarantine/`, its
push URL was disabled, and no dependency install or upstream code execution
occurred. The audited identities were:

| Artifact | SHA-256 |
|---|---|
| Commit | `66e46463352d9dfa8e57fd1307ec32808e2c4fc5` |
| Lua bridge | `cd1a09a7784d0f21244ccaa0bf4cc2b2e6e4a05cfe59973d537eebde451b54f1` |
| `src/server.ts` | `210f1e32a5cbb339b415471539262093506f5274f204c092d6c1de036e4f444f` |
| `package-lock.json` | `3199ab5d871b68085d71f614b3d01353f5f9e7ddee3f396e8801c99c5b42450c` |
| `LICENSE` | `b6504f540f994c3b8297ba9eea76816725bf6231f9c062bbb405b4998999d3a9` |

Project Epoch therefore reimplemented only the useful transport idea, with no
upstream source copied into the adapter and no Node dependency chain.

## Architecture and trust boundary

Codex supports local stdio MCP servers and project-scoped
`.codex/config.toml` configuration for trusted projects. The official
[Codex MCP documentation](https://developers.openai.com/codex/mcp) also
supports a tool allowlist and server instructions. Project Epoch uses all
three controls:

1. `.codex/config.toml` starts the zero-dependency Python server only from this
   workspace.
2. `enabled_tools` repeats the exact six-tool server allowlist.
3. The server's MCP `instructions` field says that its output is exploratory
   and must be promoted through the deterministic harness.

The adapter has three layers:

| Layer | Tracked source | Responsibility |
|---|---|---|
| Codex registration | `.codex/config.toml` | Project scope, stdio command, exact tool allowlist, and timeouts. |
| MCP controller | `tools/project_epoch_mesen_mcp_server.py` | Input/hash verification, unique staging, hidden process lifecycle, framed requests, output classification, and fail-closed cleanup. |
| Mesen bridge | `tools/project_epoch_mesen_mcp_bridge.lua` | Fixed command grammar, checkpoint load, empty input, bounded reads/callbacks, and state/integrity witnesses. |

The bridge follows Mesen's official
[Lua API](https://www.mesen.ca/docs/apireference.html) for reads, state,
input, savestate loading, and callbacks. It is deliberately not a Lua REPL.

## Exposed tool surface

The exact tool order is part of the unit-tested contract:

| Tool | Accepted caller data | Bound |
|---|---|---|
| `start_disposable_session` | One enumerated profile, or its default | Only `event11c-checkpoint-v5-spekkio-talkable` |
| `session_status` | Nothing | One active disposable session per server process |
| `read_wram` | Numeric WRAM offset and length | 1-256 bytes, WRAM only |
| `read_cpu_state` | Nothing | Read-only register/state snapshot |
| `capture_wram_accesses` | Numeric WRAM range, read/write enum, frames, record limit | Span at most 256 bytes; 1-1,800 frames; 1-1,024 records |
| `stop_disposable_session` | Nothing | Exact active session only |

There is no tool or schema field for Lua, source code, shell commands,
filesystem paths, ROM/SRAM/WRAM writes, save-state selection, controller
sequences, sockets, screenshots, or bulk memory dumps. Every input schema has
`additionalProperties = false`.

## Hardened lifecycle

Session startup fails closed unless every pinned source has the exact expected
path type, size, and SHA-256 identity. The controller then:

1. creates one cryptographically random `session_<24 hex>` directory beneath
   ignored `private/test_runs/mesen_mcp/`;
2. copies the pinned Mesen executable, core and support files, clean ROM,
   SRAM, checkpoint, settings, and hashed Lua bridge into that directory;
3. verifies the staged copies before execution;
4. snapshots the shared Mesen `Saves` tree;
5. starts only the staged Mesen process, hidden, with launcher-controlled
   environment paths and a 256-bit session token;
6. requires the bridge to validate the checkpoint's location, field state,
   party, Epoch name, guards, and candidate compatibility span before becoming
   ready;
7. forces an empty Player-1 input on every frame;
8. binds every request and response to protocol, sequence, token, status, and
   exact payload length; and
9. on stop, requires exit code 47, re-hashes every source and staged input,
   proves the shared `Saves` tree unchanged, and deletes only the exact
   validated session root.

If integrity cannot be proved, cleanup is intentionally conservative: the
failed private stage is retained for diagnosis rather than deleting an
unverified path or claiming success.

## Static security gates

The Python server pins the Lua bridge's exact SHA-256 and refuses startup if
it drifts. Both the server self-test and unit suite reject bridge source that
contains any of the following:

- dynamic `load`, `dofile`, or `require`;
- `package` or `debug` access;
- `os.execute` or `io.popen`;
- an `emu.write*` memory-write call;
- a caller-supplied path or code field; or
- any tool outside the six-name allowlist.

The bridge necessarily uses bounded file I/O for the private request/response
transport. Those filenames are assembled only from launcher-controlled
environment variables. Network access is neither enabled nor used.

## Runtime feasibility replay

The replay pins the already accepted trace:

- source: `private/test_runs/mesen2/wram_ownership_accepted_v2/field-idle/zero/trace.json`;
- size: 50,208 bytes;
- SHA-256:
  `d6a5d0cbbd39708a7970108d1027a99b42e8b6ded2d7558d55998fa958dc1168`.

The two passing private receipts are:

| Run | Receipt SHA-256 | Receipt size |
|---|---|---:|
| `mesen_mcp_feasibility_20260831_pass_r1` | `5d3f004f2ab4172dd940706b17ed15c062c42015993c916f80286083318c20d4` | 2,720 bytes |
| `mesen_mcp_feasibility_20260831_pass_r2` | `5d3f004f2ab4172dd940706b17ed15c062c42015993c916f80286083318c20d4` | 2,720 bytes |

The receipts are byte-identical. Their normalized callback-sequence SHA-256 is
`cd7aec30531533d38b2467cb76ab1320cc10a867e0dc754a92b1e5275b3b2ae8`.

The accepted collector begins at relative frame 3. The stdio MCP capture
begins at relative frame 2 because Mesen continues executing between the
session-start reply and the later capture request. The feasibility runner
therefore permits only the predeclared relative-origin deltas `-1`, `0`, `+1`,
and `+2`; the observed delta was `+1`. After shifting only the relative frame
origin, every address, value, PC, order, count, and cadence entry matches.
The receipt explicitly records `byte_exact_trace_match_claimed: false`. This
is not a disguised byte-identical trace claim.

Two implementation errors were found and corrected before acceptance:

1. Mesen memory callbacks had to be registered against direct SNES WRAM, not
   the CPU-memory view used by the existing load/read hook.
2. The callback-reported CPU address had to be converted through
   `emu.convertAddress` and verified to resolve to WRAM before normalization.

Those corrections are exactly why the known accepted scenario was used as a
gate instead of treating a successful process launch as proof.

## Reproduction

Static and protocol tests:

```powershell
py -3 -m unittest tests.test_project_epoch_mesen_mcp_server -v
py -3 tools/project_epoch_mesen_mcp_server.py --self-test
```

Real Mesen replay, using a fresh output directory that does not already exist:

```powershell
py -3 tools/run_project_epoch_mesen_mcp_feasibility.py `
  --output-dir private/test_runs/mesen_mcp_feasibility_<fresh-name>
```

The replay never writes a ROM or patch. It publishes only the private JSON
receipt after the emulator exits and every integrity gate succeeds.

The project registration is visible to a newly started or restarted Codex
client for this trusted workspace. Editing `.codex/config.toml` does not make
the new MCP server callable inside a Codex session that was already running
before the edit.

## Evidence and nonclaims

This work proves only that a tightly constrained MCP adapter can accelerate
interactive inspection without weakening the existing evidence rules. It is:

- not a production PC `$07` hook or allocation;
- not a save, New Game+, erase, menu, battle, or recruitment proof;
- not approval to expose arbitrary Lua or emulator writes;
- not a replacement for BSV/input hashes, deterministic trace collectors,
  matched controls, source hashes, complete-diff guards, or two-emulator
  release regression; and
- not permission to commit ROM, SRAM, state, screenshot, extracted graphics,
  or raw trace data.

The next useful extension should be driven by a concrete Project Epoch gate.
Any new operation must receive its own fixed schema, bounds, integrity
witnesses, unit tests, and known-scenario replay. An arbitrary-Lua escape hatch
is not an acceptable extension.
