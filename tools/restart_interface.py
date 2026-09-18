NAME = "restart_interface"
DESCRIPTION = "Bring an interface down then back up (shutdown / no shutdown). Use to recover an admin-down or error-disabled interface."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. router1)"},
        "interface": {"type": "string", "description": "Interface identifier (e.g. Gi0/1)"},
    },
    "required": ["device", "interface"],
}


def execute(params: dict, simulator) -> str:
    return simulator.restart_interface(params["device"], params["interface"])
