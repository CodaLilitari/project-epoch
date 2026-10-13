# First-Attack checkpoint: archived-source reproduction

The [October 13 Attack checkpoint](pc07_first_attack_checkpoint_2026_10_13.md)
and its [v1 metadata](../references/pc07_first_attack_checkpoint_2026_10_13.json)
remain unchanged. The later, separately approved presentation contract extended
the shared write guard. Consequently the old public auditor correctly refuses
its original live-path guard pin. This is a source-location drift in the
reproduction path, not a new native failure or a changed accepted trace.

The additive v2 auditor uses the existing exact historical guard archive. It
checks all 98 frozen source rows and all 22 builder source rows before invoking
the unchanged full review and validator. Exactly one row gains a new lookup
location; its bytes, hash, source-bundle identity and every other source row
remain unchanged. A changed-hash adversary is explicitly refused. The complete
review result must reproduce the original saved JSON byte for byte.

```powershell
python -B tools/audit_pc07_first_attack_checkpoint_2026_10_13_v2.py
```

The public [v2 metadata](../references/pc07_first_attack_checkpoint_2026_10_13_v2.json)
records this resolution and its full offline result. Exact local private evidence
is required; neither that evidence nor extracted game data is published.

This remains one previously recorded ordinary Attack, using the critical
selector family, with 962 observed damage, 30 qualified battle-hook windows and
the preserved 270,687-row pilot-prefix comparison. All original scope limits
remain: this reproduction launches no emulator, emits no image, changes no
frozen artifact, and proves no additional save/load, vehicle, victory or
production behavior.
