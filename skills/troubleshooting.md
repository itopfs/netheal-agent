## Troubleshooting Methodology

### Phase 1 – Establish Baseline
- Run `ping` first to confirm the problem is real.
- Run `traceroute` to identify where the path breaks.

### Phase 2 – Isolate the Layer
- **Physical/Interface issues** → `show_interfaces` on the device where traceroute stopped.
- **VLAN/switching issues** → `show_vlan` on the upstream switch.
- **Routing issues** → `show_routes` on the router.
- **Firewall/ACL issues** → `show_acl` on the firewall or router.
- **Unexplained drops or high CPU** → `show_logs` on the suspicious device.

### Phase 3 – Repair
- Apply only the repair tool that matches the identified fault.
- Use `restart_interface` for admin-down or error-disabled interfaces.
- Use `move_port_vlan` for VLAN mismatches.
- Use `add_route` for missing routes.
- Use `update_acl` to remove blocking rules.

### Phase 4 – Verify
- Always call `verify_connectivity` after every repair.
- If it fails, continue investigation — the fix was incomplete.
