"""Original terminal-only package fixtures, certified in memory before assembly.

These synthetic selectors and bank spans never bind a production game action.
No game ROM, extracted bytes or action-config donor is an input.
"""
from __future__ import annotations
import dataclasses
import hashlib
from pathlib import Path

import audit_schala_expanded_package_command_policy_v0 as policy

BANK = 0x42
# Owner masks in native descriptor order; pointer lists deliberately retain aliases.
SPECS = ((0x80, 0xFFFF, 0xFFFF), (0x81, 0xA501, 0x0080),
         (0x82, 0x8000, 0x0000), (0x83, 0x0000, 0x0001))


def certification_dependencies():
    root=Path(__file__).resolve().parents[1]
    result=[]
    for path,size,expected in (
        ("tools/audit_schala_expanded_package_command_policy_v0.py",39897,"5f9417cb5c44d6dd71577bcd48de0a3c90c9d7f2b790c57a26d1e8c4bd5b5c3f"),
        ("references/schala_expanded_package_command_policy_v0.json",6717,"35246c00e274f35a80cfe589cfe3557b7585ff515c7e43747453d161de99f0d9")):
        source=root/path
        if source.resolve(strict=True)!=source or not source.is_file():
            raise ValueError("certification dependency must be unaliased")
        with source.open("rb") as stream: data=stream.read(size+1)
        if len(data)!=size or hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError("pinned package certification dependency changed")
        result.append({"path":path,"size":size,"sha256":expected})
    return result


def build():
    dependencies=certification_dependencies()
    policy_contract = policy.load_reference_contract()
    bank = bytearray(b"\xff" * 0x10000)
    registry = bytearray(0x500)
    packages = []
    end = 0
    for index, (selector, mask0, mask1) in enumerate(SPECS):
        root = index * 0x100
        count = mask0.bit_count() + mask1.bit_count()
        stream_count = min(count, 2)
        targets = [root + 0x80 + n for n in range(stream_count)]
        pointers = [targets[n % stream_count] for n in range(count)]
        descriptor = mask0.to_bytes(2, "big") + mask1.to_bytes(2, "big")
        descriptor += b"".join(p.to_bytes(2, "little") for p in pointers)
        descriptor_end = root + len(descriptor)
        bank[root:descriptor_end] = descriptor
        for target in targets:
            bank[target] = 0x00  # Original authored terminal command; no effect semantics.
        prefix = f"ORIGINAL_TEST_PACKAGE_{selector:02X}"
        source = policy.adapter.make_package_source(selector=selector, bank=BANK,
            root_offset=root, allocation_name=prefix+"_DESCRIPTOR", source_kind="synthetic-test")
        layout = policy.ExpandedPackageLayout(source=source,
            descriptor_span=policy.NamedSpan(prefix+"_DESCRIPTOR", BANK, root, descriptor_end),
            stream_spans=tuple(policy.NamedSpan(prefix+f"_TERMINAL_{n}", BANK, target, target+1)
                               for n,target in enumerate(targets)))
        # Both masks, every direct/suffix entry, disjoint names, terminal 00 and
        # complete token ownership are checked under the pinned interpreter.
        certificate = policy.validate_expanded_package_command_policy(bytes(bank), layout)
        if certificate["decoded_command_1e_site_count"] != 0 or certificate["unowned_stream_byte_count"] != 0:
            raise ValueError("original fixture command ownership failed")
        words = (1, root, BANK, descriptor_end, 0, len(targets), 0, 0)
        registry[index*16:index*16+16] = b"".join(w.to_bytes(2,"little") for w in words)
        target_start = 0x100 + index*64
        registry[target_start:target_start+len(targets)*2] = b"".join(t.to_bytes(2,"little") for t in targets)
        packages.append({"selector":selector,"layout":dataclasses.asdict(layout),
                         "targets":targets,"descriptor_size":len(descriptor),
                         "descriptor_sha256":hashlib.sha256(descriptor).hexdigest(),
                         "certificate":certificate})
        end = max(end, targets[-1]+1)
    payload = bytes(bank[:end])
    return payload, bytes(registry), {
        "schema":"project-epoch-original-package-fixtures-v1", "evidence_level":"verified-static",
        "bank":BANK,"packages":packages,"package_payload_size":len(payload),
        "package_payload_sha256":hashlib.sha256(payload).hexdigest(),
        "registry_size":len(registry),"registry_sha256":hashlib.sha256(registry).hexdigest(),
        "certification_dependencies":dependencies,
        "policy_contract_dependencies":policy_contract["dependencies"],
        "production_approval":False,"pointed_stream_execution_proved":False,
        "scope":"original terminal-only transport fixtures; all unlisted synthetic registry records are zero/unbound"}
