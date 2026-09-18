NAME = "show_arp"
DESCRIPTION = "Show the ARP table on a router or Layer 3 switch. An 'Incomplete' entry means the device's IP is known but its MAC cannot be resolved — indicating a Layer 2 connectivity problem upstream of this device."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name to query ARP table on (e.g. router1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_arp(params["device"])
