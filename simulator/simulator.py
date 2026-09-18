import json
from pathlib import Path


class NetworkSimulator:
    def __init__(self):
        self.state = {}
        self._active_faults = []

    def load(self, network_json_path: Path):
        with open(network_json_path) as f:
            self.state = json.load(f)
        self._active_faults = [dict(f) for f in self.state.get("faults", [])]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _device(self, name: str) -> dict:
        d = self.state["devices"].get(name.lower())
        if not d:
            raise KeyError(f"Unknown device: {name}")
        return d

    def _is_reachable(self, source: str, destination: str) -> bool:
        for fault in self._active_faults:
            if fault.get("breaks_connectivity"):
                return False
        return True

    def _broken_link_set(self) -> set:
        """Links that are currently down due to an active fault."""
        broken = set()
        for f in self._active_faults:
            endpoints = f.get("link") or []
            if len(endpoints) == 2:
                broken.add(frozenset(e.lower() for e in endpoints))
        return broken

    def _is_mgmt_reachable(self, device: str) -> bool:
        """
        MGMT-SRV has out-of-band access only to router1.
        All other devices are reached through the data-plane topology;
        a broken link isolates the far side from management.
        """
        target = device.lower().replace(" ", "")
        if target in ("mgmt", "mgmt_server", "router1"):
            return True
        if target not in self.state.get("devices", {}):
            return False

        broken = self._broken_link_set()
        adj: dict[str, set[str]] = {}
        for link in self.state.get("topology", {}).get("links", []):
            frm, to = link["from"].lower(), link["to"].lower()
            if frozenset((frm, to)) in broken:
                continue
            adj.setdefault(frm, set()).add(to)
            adj.setdefault(to, set()).add(frm)

        seen = {"router1"}
        queue = ["router1"]
        while queue:
            node = queue.pop(0)
            for nbr in adj.get(node, ()):
                if nbr not in seen:
                    seen.add(nbr)
                    queue.append(nbr)
        return target in seen

    def _mgmt_unreachable(self, device: str) -> str | None:
        if self._is_mgmt_reachable(device):
            return None
        return (
            f"Connection to {device.upper()} failed: device unreachable from MGMT-SERVER.\n"
            f"  Management plane has out-of-band access to ROUTER1 only.\n"
            f"  {device.upper()} is behind a down link — SSH/CLI not available.\n"
            f"  Inspect reachable upstream devices (e.g. router1) instead."
        )

    def _remove_fault(self, fault_type: str, **match) -> bool:
        before = len(self._active_faults)
        self._active_faults = [
            f for f in self._active_faults
            if not (f["type"] == fault_type and all(f.get(k) == v for k, v in match.items()))
        ]
        removed = len(self._active_faults) < before
        if removed:
            # Persist the fix into live device state
            self._apply_fix(fault_type, **match)
        return removed

    def _apply_fix(self, fault_type: str, **match):
        if fault_type == "interface_down":
            dev = self._device(match.get("device", ""))
            iface = match.get("interface", "")
            if iface in dev.get("interfaces", {}):
                dev["interfaces"][iface]["status"] = "up"
        elif fault_type == "wrong_vlan":
            dev = self._device(match.get("device", ""))
            port = match.get("port", "")
            correct_vlan = match.get("correct_vlan", 1)
            if port in dev.get("interfaces", {}):
                dev["interfaces"][port]["vlan"] = correct_vlan
        elif fault_type == "missing_route":
            dev = self._device(match.get("device", ""))
            dev.setdefault("routing_table", []).append({
                "network": match.get("network", ""),
                "via": match.get("via", ""),
                "interface": match.get("interface", ""),
                "metric": 1,
            })
        elif fault_type == "acl_block":
            dev = self._device(match.get("device", ""))
            rule_id = str(match.get("rule_id", ""))
            dev["acls"] = [r for r in dev.get("acls", []) if str(r.get("id", "")) != rule_id]
        elif fault_type == "high_cpu":
            dev = self._device(match.get("device", ""))
            dev["cpu"] = 12

    # ── diagnostic tools ─────────────────────────────────────────────────────

    def ping(self, source: str = "mgmt", destination: str = "") -> str:
        src = source.lower().replace(" ", "") if source else "mgmt"
        dst = destination.lower().replace(" ", "")
        src_label = "MGMT-SERVER" if src == "mgmt" else source.upper()
        reachable = self._is_reachable(src, dst)
        dest_ip = self._get_ip(dst)
        source = src_label  # use for display below
        if reachable:
            return (
                f"PING {dest_ip} from {source.upper()}:\n"
                "64 bytes from {}: icmp_seq=1 ttl=63 time=1.2ms\n"
                "64 bytes from {}: icmp_seq=2 ttl=63 time=0.9ms\n"
                "64 bytes from {}: icmp_seq=3 ttl=63 time=1.1ms\n"
                "--- {} ping statistics ---\n"
                "3 packets transmitted, 3 received, 0% packet loss"
            ).format(dest_ip, dest_ip, dest_ip, dest_ip)
        return (
            f"PING {dest_ip} from {source.upper()}:\n"
            "Request timeout for icmp_seq 1\n"
            "Request timeout for icmp_seq 2\n"
            "Request timeout for icmp_seq 3\n"
            f"--- {dest_ip} ping statistics ---\n"
            "3 packets transmitted, 0 received, 100% packet loss"
        )

    def _get_ip(self, device_name: str) -> str:
        try:
            dev = self._device(device_name)
            return dev.get("ip", dev.get("interfaces", {}).get(
                next(iter(dev.get("interfaces", {}))), {}
            ).get("ip", "unknown").split("/")[0])
        except Exception:
            return device_name

    def traceroute(self, source: str = "mgmt", destination: str = "") -> str:
        src = source.lower().replace(" ", "") if source else "mgmt"
        dst = destination.lower().replace(" ", "")
        src_label = "MGMT-SERVER" if src == "mgmt" else source.upper()
        dest_ip = self._get_ip(dst)
        hops = self.state.get("topology", {}).get(f"{src}_to_{dst}_hops", [])
        if not hops:
            hops = self.state.get("topology", {}).get("pc1_to_server1_hops", [])
        fully_up = self._is_reachable(src, dst)
        lines = [f"Traceroute from {src_label} to {dest_ip}:"]
        for i, hop in enumerate(hops, 1):
            reachable = fully_up or hop.get("reachable", True)
            if reachable:
                ip = hop.get("ip", "?")
                lines.append(f"  {i}  {ip} ({hop['label']})  {hop.get('ms', 1)}ms")
            else:
                lines.append(f"  {i}  * * *  ({hop['label']} - no response)")
        if not hops:
            lines.append("  1  * * *  (no route to host)")
        return "\n".join(lines)

    def show_interfaces(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        lines = [f"{device.upper()} Interfaces:", f"{'Interface':<14}{'Status':<14}{'IP Address':<18}Description"]
        lines.append("-" * 60)
        for iface, info in dev.get("interfaces", {}).items():
            status = info.get("status", "up")
            ip = info.get("ip", "-")
            desc = info.get("description", "-")
            lines.append(f"{iface:<14}{status:<14}{ip:<18}{desc}")
        return "\n".join(lines)

    def show_routes(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        routes = dev.get("routing_table", [])
        lines = [f"{device.upper()} Routing Table:", f"{'Destination':<20}{'Next Hop':<18}{'Interface':<14}Metric"]
        lines.append("-" * 60)
        for r in routes:
            lines.append(f"{r['network']:<20}{r.get('via', 'direct'):<18}{r.get('interface', '-'):<14}{r.get('metric', 0)}")
        if not routes:
            lines.append("  (empty routing table)")
        return "\n".join(lines)

    def show_vlan(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        lines = [f"{device.upper()} VLAN Table:", f"{'VLAN':<8}{'Name':<16}Ports"]
        lines.append("-" * 50)
        for vlan in dev.get("vlans", []):
            ports = ", ".join(vlan.get("ports", []))
            lines.append(f"{vlan['id']:<8}{vlan['name']:<16}{ports}")
        lines.append("")
        lines.append("Port VLAN Assignments:")
        for iface, info in dev.get("interfaces", {}).items():
            if "vlan" in info:
                lines.append(f"  {iface}  →  VLAN {info['vlan']}")
        return "\n".join(lines)

    def show_acl(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        acls = dev.get("acls", [])
        lines = [f"{device.upper()} Access Control List:", f"{'ID':<6}{'Action':<10}{'Proto':<10}{'Source':<18}{'Destination':<18}Port"]
        lines.append("-" * 70)
        for rule in acls:
            lines.append(
                f"{rule.get('id', '-'):<6}{rule['action']:<10}{rule.get('protocol', 'any'):<10}"
                f"{rule.get('source', 'any'):<18}{rule.get('destination', 'any'):<18}{rule.get('port', '-')}"
            )
        if not acls:
            lines.append("  (no ACL rules - all traffic permitted)")
        return "\n".join(lines)

    def show_logs(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        logs = dev.get("logs", [])
        lines = [f"{device.upper()} Recent System Logs:", "-" * 70]
        for entry in logs:
            lines.append(f"[{entry['time']}] {entry['level']:<8} {entry['msg']}")
        if not logs:
            lines.append("  (no log entries)")
        return "\n".join(lines)

    # ── repair tools ─────────────────────────────────────────────────────────

    def restart_interface(self, device: str, interface: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        cable_fault = next(
            (f for f in self._active_faults
             if f["type"] == "cable_unplugged"
             and f.get("device") == device.lower()
             and f.get("interface") == interface),
            None,
        )
        if cable_fault:
            return (
                f"Attempting to restart interface {interface} on {device.upper()}...\n"
                f"  [ERROR] Interface {interface} cannot be brought up — no physical carrier detected\n"
                f"  Hardware diagnosis: cable disconnected or physically damaged\n"
                f"  Remote remediation: NOT POSSIBLE\n"
                f"  Required action: on-site inspection — check/reseat/replace cable on port {interface}"
            )
        fixed = self._remove_fault("interface_down", device=device.lower(), interface=interface)
        dev = self._device(device)
        iface_info = dev.get("interfaces", {}).get(interface, {})
        if fixed or iface_info.get("status") == "up":
            ip = iface_info.get("ip", "N/A")
            return (
                f"Restarting interface {interface} on {device.upper()}...\n"
                f"  [OK] Interface {interface} brought UP\n"
                f"  [OK] IP address {ip} configured\n"
                f"  Status: OPERATIONAL"
            )
        return (
            f"Restarting interface {interface} on {device.upper()}...\n"
            f"  Interface {interface} status: {iface_info.get('status', 'unknown')}\n"
            "  No fault cleared — interface was not the root cause."
        )

    def move_port_vlan(self, device: str, port: str, vlan: int) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        fault = next(
            (f for f in self._active_faults if f["type"] == "wrong_vlan"
             and f.get("device") == device.lower() and f.get("port") == port),
            None,
        )
        correct = fault.get("correct_vlan") if fault else vlan
        fixed = self._remove_fault("wrong_vlan", device=device.lower(), port=port, correct_vlan=correct)
        current = dev.get("interfaces", {}).get(port, {}).get("vlan", "?")
        if fixed:
            return (
                f"Moving {device.upper()} port {port} to VLAN {vlan}...\n"
                f"  [OK] Port {port} assigned to VLAN {vlan}\n"
                f"  Status: Port is now in the correct VLAN."
            )
        return (
            f"Moving {device.upper()} port {port} to VLAN {vlan}...\n"
            f"  Port {port} is already on VLAN {current}. No fault resolved."
        )

    def add_route(self, device: str, network: str, via: str, interface: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        fault = next(
            (f for f in self._active_faults if f["type"] == "missing_route"
             and f.get("device") == device.lower() and f.get("network") == network),
            None,
        )
        if fault:
            self._remove_fault("missing_route", device=device.lower(), network=network,
                               via=fault.get("via", via), interface=fault.get("interface", interface))
            return (
                f"Adding static route on {device.upper()}...\n"
                f"  [OK] Route {network} via {via} {interface} installed\n"
                "  Routing table updated."
            )
        dev = self._device(device)
        dev.setdefault("routing_table", []).append(
            {"network": network, "via": via, "interface": interface, "metric": 1}
        )
        return (
            f"Adding static route on {device.upper()}...\n"
            f"  [OK] Route {network} via {via} {interface} installed\n"
            "  Note: this route did not resolve a tracked fault."
        )

    def update_acl(self, device: str, action: str, rule_id: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        fixed = self._remove_fault("acl_block", device=device.lower(), rule_id=str(rule_id))
        if action.lower() in ("remove", "delete", "deny-remove") and fixed:
            return (
                f"Updating ACL on {device.upper()}...\n"
                f"  [OK] Rule {rule_id} removed\n"
                "  Traffic is now permitted."
            )
        dev = self._device(device)
        acls = dev.get("acls", [])
        if action.lower() == "remove":
            dev["acls"] = [r for r in acls if str(r.get("id")) != str(rule_id)]
            return f"Removed ACL rule {rule_id} from {device.upper()}. (was not a tracked fault)"
        return f"ACL update on {device.upper()}: action='{action}' rule_id='{rule_id}'. No matching fault found."

    def verify_connectivity(self, source: str, destination: str) -> str:
        src = source.lower().replace(" ", "")
        dst = destination.lower().replace(" ", "")
        dest_ip = self._get_ip(dst)
        if self._is_reachable(src, dst):
            return (
                f"Connectivity Verification: {source.upper()} → {destination.upper()}\n"
                f"  Destination: {dest_ip}\n"
                "  Result: REACHABLE\n"
                "  [PASS] All network paths are operational."
            )
        return (
            f"Connectivity Verification: {source.upper()} → {destination.upper()}\n"
            f"  Destination: {dest_ip}\n"
            "  Result: UNREACHABLE\n"
            "  [FAIL] Network issue persists — further investigation required."
        )

    def show_arp(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        entries = dev.get("arp_table", [])
        if not entries:
            return f"{device.upper()} ARP Table: (no entries — device may not act as a Layer 3 gateway)"
        lines = [
            f"{device.upper()} ARP Table:",
            f"{'IP Address':<18}{'MAC Address':<22}{'Interface':<14}{'Host':<16}State",
            "-" * 80,
        ]
        for e in entries:
            lines.append(
                f"{e['ip']:<18}{e['mac']:<22}{e['interface']:<14}{e.get('host', '-'):<16}{e.get('state', 'active')}"
            )
        return "\n".join(lines)

    def show_mac_table(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        entries = dev.get("mac_table", [])
        if not entries:
            return f"{device.upper()} MAC Address Table: (no entries)"
        lines = [
            f"{device.upper()} MAC Address Table:",
            f"{'VLAN':<8}{'MAC Address':<22}{'Interface':<14}{'Type':<12}Host",
            "-" * 70,
        ]
        for e in entries:
            lines.append(
                f"{e['vlan']:<8}{e['mac']:<22}{e['interface']:<14}{e.get('type', 'DYNAMIC'):<12}{e.get('host', '-')}"
            )
        return "\n".join(lines)

    def show_dhcp_leases(self, device: str) -> str:
        if err := self._mgmt_unreachable(device):
            return err
        dev = self._device(device)
        leases = dev.get("dhcp_leases", [])
        if not leases:
            return f"{device.upper()} DHCP Bindings: (no leases — DHCP may not be configured on this device)"
        lines = [
            f"{device.upper()} DHCP Lease Bindings:",
            f"{'IP Address':<18}{'MAC Address':<22}{'Host':<16}{'Expires':<24}State",
            "-" * 90,
        ]
        for l in leases:
            lines.append(
                f"{l['ip']:<18}{l['mac']:<22}{l.get('host', '-'):<16}{l.get('expires', '-'):<24}{l.get('state', 'Active')}"
            )
        return "\n".join(lines)

    # ── topology state for UI ────────────────────────────────────────────────

    def get_topology_state(self) -> dict:
        # Physical cable faults live on a link, not a device — don't paint the switch red.
        LINK_ONLY_TYPES = {"cable_unplugged"}

        fault_devices = set()
        broken_links = set()  # frozenset of endpoint names (UI red)
        for f in self._active_faults:
            # Physical break (also used for mgmt reachability)
            endpoints = f.get("link") or []
            if len(endpoints) == 2:
                broken_links.add(frozenset(e.lower() for e in endpoints))
            # Logical / path highlight only (e.g. missing route toward a subnet)
            for pair in f.get("highlight_links") or []:
                if len(pair) == 2:
                    broken_links.add(frozenset(e.lower() for e in pair))

            if f["type"] in LINK_ONLY_TYPES:
                continue
            d = f.get("device")
            if d:
                fault_devices.add(d.lower())

        devices = {}
        for name, dev in self.state["devices"].items():
            status = "fault" if name.lower() in fault_devices else "healthy"
            devices[name] = {"type": dev.get("type", "device"), "status": status}

        links = []
        for link in self.state.get("topology", {}).get("links", []):
            frm, to = link["from"].lower(), link["to"].lower()
            endpoints = frozenset((frm, to))
            if endpoints in broken_links:
                broken = True
            else:
                # Only fall back to "all links touching device" when the fault has no explicit links
                broken = any(
                    f["type"] not in LINK_ONLY_TYPES
                    and not self._fault_has_explicit_links(f)
                    and f.get("device", "").lower() in (frm, to)
                    for f in self._active_faults
                )
            links.append({"from": frm, "to": to, "status": "fault" if broken else "healthy"})

        return {"devices": devices, "links": links}

    @staticmethod
    def _fault_has_explicit_links(fault: dict) -> bool:
        link = fault.get("link") or []
        if len(link) == 2:
            return True
        return any(len(p) == 2 for p in (fault.get("highlight_links") or []))
