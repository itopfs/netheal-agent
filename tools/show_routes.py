NAME = "show_routes"
DESCRIPTION = "Display the IP routing table for a device. Use to identify missing or incorrect routes."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. router1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_routes(params["device"])
