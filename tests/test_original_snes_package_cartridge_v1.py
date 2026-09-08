"""Original fixture and guarded-builder contracts; no cartridge is written."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import original_snes_package_fixtures_v1 as fixtures
import build_original_snes_package_cartridge_v1 as builder
import original_snes_diagnostic_write_contract_v1 as contract


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload,cls.registry,cls.report=fixtures.build()

    def test_exact_original_payload_and_unbound_registry(self):
        self.assertEqual(len(self.payload),897)
        self.assertEqual(contract.sha(self.payload),"2eaa608733618d79876b55e9bde43f4bf213f9556484b15216781a5df52dce70")
        self.assertEqual(len(self.registry),0x500)
        self.assertEqual(contract.sha(self.registry),"6cb7223449fca8f93771e37639cf0e9e28ac520ce5bb2b77d43154447e1ac965")
        self.assertEqual(self.registry[64:256],bytes(192))
        self.assertEqual(self.registry[0x200:],bytes(0x300))
        self.assertFalse(self.report["production_approval"])

    def test_both_masks_all_flags_and_registry_target_authority(self):
        bank=self.payload+b"\xff"*(0x10000-len(self.payload))
        for index,(selector,mask0,mask1) in enumerate(fixtures.SPECS):
            row=self.registry[index*16:index*16+16]
            words=[int.from_bytes(row[n:n+2],"little") for n in range(0,16,2)]
            self.assertEqual(words[0],1)
            self.assertEqual(words[2],0x42)
            self.assertEqual(words[4],0)
            self.assertEqual(words[6:], [0,0])
            source=fixtures.policy.adapter.make_package_source(selector=selector,bank=0x42,
                root_offset=words[1],allocation_name=f"ORIGINAL_TEST_PACKAGE_{selector:02X}_DESCRIPTOR",source_kind="synthetic-test")
            declared=[int.from_bytes(self.registry[0x100+index*64+2*n:0x102+index*64+2*n],"little") for n in range(words[5])]
            all_observed=set()
            for flag in range(256):
                result=fixtures.policy.adapter.simulate_descriptor_install(bank,source,a0b3=flag)
                observed=[p.script_offset for p in result.publications]
                self.assertEqual(len(observed),(mask0 if flag==0 else mask1).bit_count())
                self.assertTrue(set(observed)<=set(declared))
                all_observed.update(observed)
            self.assertEqual(all_observed,set(declared))
            self.assertEqual(self.registry[0x100+index*64+2*words[5]:0x140+index*64],bytes(64-2*words[5]))

    def test_certification_refuses_unsupported_command_and_overlap(self):
        p=self.report["packages"][0]
        source=fixtures.policy.adapter.make_package_source(selector=0x80,bank=0x42,root_offset=0,
            allocation_name="ORIGINAL_TEST_PACKAGE_80_DESCRIPTOR",source_kind="synthetic-test")
        layout=fixtures.policy.ExpandedPackageLayout(source,
            fixtures.policy.NamedSpan("ORIGINAL_TEST_PACKAGE_80_DESCRIPTOR",0x42,0,68),
            (fixtures.policy.NamedSpan("A",0x42,0x80,0x81),fixtures.policy.NamedSpan("B",0x42,0x81,0x82)))
        image=bytearray(self.payload+b"\xff"*(0x10000-len(self.payload)))
        image[0x80]=0x1e
        with self.assertRaises(fixtures.policy.ExpandedPackageCommandPolicyError):
            fixtures.policy.validate_expanded_package_command_policy(bytes(image),layout)
        overlap=fixtures.policy.ExpandedPackageLayout(source,layout.descriptor_span,
            (fixtures.policy.NamedSpan("A",0x42,0x40,0x81),layout.stream_spans[1]))
        with self.assertRaises(fixtures.policy.ExpandedPackageCommandPolicyError):
            fixtures.policy.validate_expanded_package_command_policy(self.payload+b"\xff"*(0x10000-len(self.payload)),overlap)


class BuilderTests(unittest.TestCase):
    def test_header_routes_match_original_source_entries(self):
        header=builder.make_header()
        self.assertEqual(len(header),64)
        self.assertEqual(header[:21],contract.TITLE)
        vectors=[int.from_bytes(header[n:n+2],"little") for n in range(32,64,2)]
        self.assertEqual(vectors[5],0x8080)
        self.assertEqual(vectors[13],0x8080)
        self.assertEqual(vectors[7],0x8090)
        self.assertEqual(vectors[15],0x8090)
        self.assertEqual(vectors[14],0x8000)
        self.assertEqual(set(vectors),{0x8000,0x8080,0x8090,0x80a0})

    def test_image_creation_requires_both_explicit_guard_passes(self):
        packages,registry,_=fixtures.build()
        sources=builder.original_sources()
        for intent_status,audit_status in (("refused","images-valid"),("metadata-valid","refused")):
            with mock.patch.object(builder.guard,"validate_original_diagnostic_manifest",return_value={"status":intent_status}), \
                 mock.patch.object(builder.guard,"audit_original_diagnostic_images",return_value={"status":audit_status,"complete_diff_coverage":True}), \
                 self.assertRaisesRegex(ValueError,"explicitly pass"):
                builder.build_image(bytes(0x122),bytes(577),packages,registry,sources,
                    "private/test_runs/guard-test/original.sfc")

    def test_real_guard_rejects_component_capacity_and_invalid_boot_extent(self):
        packages,registry,_=fixtures.build()
        for boot in (bytes(0x1001),bytes(8)):
            with self.subTest(size=len(boot)),self.assertRaises(ValueError):
                builder.build_image(boot,bytes(577),packages,registry,builder.original_sources(),
                    "private/test_runs/guard-test/original.sfc")

    def test_writer_refuses_existing_private_artifact_before_open(self):
        with mock.patch.object(builder.contract,"output_path",return_value=builder.ROOT/"private/test_runs/mock/a.sfc"), \
             mock.patch.object(Path,"exists",return_value=True), \
             mock.patch.object(Path,"open") as opened, self.assertRaises(ValueError):
            builder.exclusive(builder.ROOT/"private/test_runs/mock/a.sfc",b"original")
        opened.assert_not_called()

    def test_raw_assembler_never_receives_cartridge_path(self):
        class Proc:
            returncode=0
            stdout=b""
            stderr=b""
        import io
        with mock.patch.object(builder,"exclusive") as write, \
             mock.patch.object(builder.subprocess,"run",return_value=Proc()) as run, \
             mock.patch.object(Path,"open",return_value=io.BytesIO(b"\xea")):
            data,_=builder.assemble_raw(builder.ROOT/"private/test_runs/mock","component","norom\n",maximum=64)
        command=run.call_args.args[0]
        self.assertEqual(Path(command[-1]).suffix,".bin")
        self.assertEqual(Path(command[-2]).suffix,".asm")
        self.assertNotIn(".sfc"," ".join(command))
        self.assertEqual(data,b"\xea")


if __name__=="__main__": unittest.main()
