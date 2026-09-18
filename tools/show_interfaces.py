NAME = "show_interfaces"
DESCRIPTION = "Display all interfaces on a device with their operational status, IP address, and description."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. router1, switch1, firewall)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_interfaces(params["device"])
