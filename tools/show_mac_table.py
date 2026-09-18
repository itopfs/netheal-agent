NAME = "show_mac_table"
DESCRIPTION = "Show the MAC address table on a switch. If an end device's MAC is absent, the switch has never seen its traffic — indicating a physical (Layer 1) or VLAN (Layer 2) problem on that port. Use this to confirm whether an end device is actually connected."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Switch name to query (e.g. switch1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_mac_table(params["device"])
