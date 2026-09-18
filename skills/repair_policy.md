## Repair Policy

- **Minimum intervention**: fix only what is broken. Do not change things that are working.
- **No cascade repairs**: apply one repair at a time, verify, then decide if more work is needed.
- **Interface restart is low-risk**: safe to apply when an interface is admin-down.
- **Route additions are permanent**: confirm the route is actually missing before adding.
- **ACL changes are high-impact**: inspect the full ACL before removing any rule.
- **VLAN moves affect the host immediately**: confirm the correct VLAN from documentation or incident notes before moving.
- **Hardware faults require escalation**: if a repair tool returns "NOT POSSIBLE" or "no carrier detected", the fault is physical and cannot be resolved remotely. Call `finish` immediately with the confirmed fault as `reason` and an on-site technician escalation as `summary`. Do not attempt further software repairs.
