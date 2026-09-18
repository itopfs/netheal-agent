NAME = "show_dhcp_leases"
DESCRIPTION = "Show DHCP lease bindings on a router or DHCP server. An Expired lease for an end device confirms it lost Layer 2 connectivity and could not renew — corroborates a physical or VLAN fault. An Active lease with no ARP entry suggests a more recent disconnection."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device acting as DHCP server (e.g. router1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_dhcp_leases(params["device"])
